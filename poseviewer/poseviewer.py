# coding: utf-8

from PySide.QtCore import *
from PySide.QtGui import *
import sys
import os
import ctypes
import subprocess

from .ui import poseviewerMainGui
from .corewidgets import *
from .guiwidgets import *


class MainWindow(QMainWindow, poseviewerMainGui.Ui_MainWindow):
    WINDOW_TITLE = "Poseviewer"
    BEEP = QSound(os.path.join(os.path.dirname(os.path.abspath(__file__)), './Sounds/beep.wav'))

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.settings = Settings()

        self.notification_widget = NotificationPopupWidget(self)
        self.image_path = ImagePath(self)
        self.image_canvas = ImageCanvas(self)
        self.list_image_viewer = ListImageViewer(parent=self)
        self.slideshow = Slideshow(self)
        self.star_actions = StarActions(self.actionStar)

        self.gridLayout.addWidget(self.image_canvas)
        self.gridLayout.addWidget(self.list_image_viewer)
        self.window = QWidget()
        self.window.setLayout(self.gridLayout)

        self.setCentralWidget(self.window)

        self.notification_widget.notified.connect(self.activateWindow)

        self.slideshow.slideshowComplete.connect(self.toggle_slideshow)
        self.slideshow.slideshowComplete.connect(lambda: self.notification_widget.notify('Slideshow Complete!', duration=0))
        self.slideshow.slideshowComplete.connect(self.beep)
        self.slideshow.slideshowNotifyChange.connect(self.notify_slideshow_change)
        self.slideshow.slideshowNext.connect(self.next_image)

        self.list_image_viewer.indexDoubleClicked.connect(self.prepare_image)
        self.list_image_viewer.listImageViewerToggled.connect(self.image_canvas.fit_in_view)
        self.list_image_viewer.setDefaultSequence.connect(lambda seq: self.image_path.set_sequence(seq))
        self.list_image_viewer.starChange.connect(self.star_actions.handle_star_icon)

        self.time_elapsed_timer = TimeElapsedTimer(self)
        self.totalTimeElapsed = QElapsedTimer()  # keep a track of the whole time spent in app
        self.totalTimeElapsed.start()

        self.timerLabel = QLabel()  # timer label
        self.timerLabel.setStyleSheet("font: 17pt; color: rgb(0, 180, 255)")  # set font size to 17 and color to blueish
        self.toolBar.setStyleSheet("border-color: black;")

        self.actionTimerLabel = self.toolBar.addWidget(self.timerLabel)  # add the timer label to the toolbar
        # self.toolBar.removeAction(self.actionStar)
        # self.toolBar.insertAction(self.actionTimerLabel, self.actionStar)
        self.actionStar.triggered.connect(lambda: self.star_actions.star_image(self.image_path.current))
        self.actionStar.triggered.connect(lambda: self.list_image_viewer.handle_star(self.image_path.current, update=False))
        # self.actionStar.triggered.connect(self.display_list_image_viewer)
        # self.actionStar.triggered.connect(lambda: self.list_image_viewer.handle_star_icon(self.image_path.current))
        self.actionOpen.triggered.connect(self.get_directory)
        self.actionPlay.triggered.connect(self.toggle_slideshow)  # show image and start the timer
        self.actionPause.triggered.connect(self.pause_slideshow)
        self.actionRandom.triggered.connect(self.image_path.random)  # make a shuffled list
        self.actionNext.triggered.connect(self.next_image)
        self.actionPrevious.triggered.connect(self.image_path.prev)
        self.actionFullscreen.triggered.connect(self.toggle_fullscreen)  # toggle fullscreen
        self.actionSound.triggered.connect(self.toggle_sound)  # toggle sound
        self.actionSettings.triggered.connect(self.slideshow.settings_ui.run)  # set slide show speed
        self.actionTimer.triggered.connect(self.toggle_label_timer)  # toggle timer display

        self.action_options = ActionOptions(self)

        self.image_path.imageChanged.connect(self.prepare_image)
        self.image_path.sequenceChanged.connect(self.action_options.enable_all_actions)

        self.time_elapsed_timer.secElapsed.connect(self.update_timerLabel)  # update the timer label every second

        self.sound = True  # is the sound turned on
        self.timer_visible = False
        self.force_toolbar_display = False

        self.toolBar.hide()

        self.dirs = self.settings.value('dirs', '.')

        self.action_options.enable_actions_for(self.action_options.path_actions)

        self.window_dimensions = self.geometry()  # remember the geometry for returning from fullscreen
        self.DEFAULT_PALETTE = self.palette()

        self.centralWidget().layout().setContentsMargins(0, 0, 0, 0)
        QApplication.instance().installEventFilter(self)

    def get_directory(self):
        """
        Append the image directory to self.dirs
        """
        dirs = QFileDialog.getExistingDirectory(self, "Open directory", dir=self.dirs)
        if dirs:
            self.dirs = dirs
        self.settings['dirs'] = self.dirs
        if self.dirs:  # '' is not a valid path
            self.image_path.set_sequence(self.dirs)

    def update_image(self, path=None):
        """
        Update the graphicsview with image_path or current_image_path.
        """
        if path:
            self.image_path.current = path

        if self.image_path.current == self.image_canvas.image_path:
            self.image_canvas.fit_in_view()
        else:
            self.image_canvas.draw_image(self.image_path.current)

    def prepare_image(self, path=None):
        self.update_image(path)  # the graphicsview still stays rotated
        self.set_window_title(self.image_path.current)
        self.star_actions.handle_star_icon(self.image_path.current)
        self.time_elapsed_timer.set_time_to_zero()
        self.update_timerLabel()

    def next_image(self):
        """
        Update image with the next image in sequence.
        """
        self.image_path.next()

        if self.slideshow.is_active():
            self.slideshow.reset_timer()

        if self.sound and self.slideshow.is_active():
            self.beep()

    def paint_background(self, widget, qcolor, full_background=False):
        if full_background:
            full_background = QPalette()
            full_background.setColor(widget.backgroundRole(), qcolor)
            widget.setPalette(full_background)
        else:
            widget.setPalette(self.DEFAULT_PALETTE)

        self.image_canvas.setBackgroundBrush(QBrush(qcolor))
        self.list_image_viewer.canvas.setBackgroundBrush(QBrush(qcolor))

    def toggle_fullscreen(self):
        """
        Deal with entering/exiting fullscreen mode.
        """
        if self.isFullScreen():  # go back to normal
            set_icon("fullscreen.png", self.actionFullscreen)
            self.paint_background(self, Qt.NoBrush)
            self.setGeometry(self.window_dimensions)
            self.showNormal()
        else:  # go to fullscreen
            set_icon("closefullscreen.png", self.actionFullscreen)
            self.window_dimensions = self.geometry()  # save current window settings
            self.paint_background(self, Qt.black, True)
            self.showFullScreen()

        if not self.force_toolbar_display: self.toolBar.hide()

        self.update_image()  # update the image to fit the fullscreen mode

    def stop_slideshow(self):
        set_icon("play.png", self.actionPlay)
        self.slideshow.stop()
        self.actionPause.setEnabled(False)

    def start_slideshow(self):
        set_icon("stop.png", self.actionPlay)
        self.beep()
        self.notify_slideshow_change()
        self.time_elapsed_timer.set_time_to_zero()
        self.slideshow.start()
        self.actionPause.setEnabled(True)

    def toggle_slideshow(self):
        """Deals with starting/stopping the slideshow.
        """
        if self.slideshow.is_active():  # if it's playing, stop it
            self.stop_slideshow()
        else:  # if it's not playing, play it
            self.start_slideshow()

    def toggle_sound(self):
        """
        Toggle whether there should be a beep during a slideshow.
        """
        if self.sound:  # sound is on and you stop it
            set_icon("soundoff.png", self.actionSound)
        else:  # sound is not on and you put it on
            set_icon("soundon.png", self.actionSound)
        self.sound = not self.sound

    def toggle_label_timer(self):
        """
        Toggle whether the timerLabel should be displayed.
        """
        if not self.timer_visible:
            self.time_elapsed_timer.start()
        self.timer_visible = not self.timer_visible
        self.actionTimerLabel.setVisible(self.timer_visible)

        self.update_timerLabel()
        self.time_elapsed_timer.set_time_to_zero()

    def toggle_bars(self):
        """
        Toggle bars - right click menu, action. Toggle toolbar visibility.
        """
        self.force_toolbar_display = not self.force_toolbar_display
        self.toolBar.setVisible(self.force_toolbar_display)

        self.update_image()

    def pause_slideshow(self):
        pass

    def notify_slideshow_change(self):
        self.notification_widget.notify(self.slideshow.format_notify_message())

    def beep(self):
        if self.sound:
            self.BEEP.play()

    def update_timerLabel(self):
        if self.timer_visible:
            if self.slideshow.is_active():
                self.timerLabel.setText(format_secs(self.slideshow.speed() - self.time_elapsed_timer.secs_elapsed))
            else:
                self.timerLabel.setText(self.time_elapsed_timer.get_time_elapsed())

    def show_stats(self):
        QMessageBox.information(self, 'Stats',
                                'Total time in app: ' + format_secs(self.totalTimeElapsed.elapsed() / 1000))

    def open_in_folder(self):
        subprocess.Popen(r'explorer /select,{}'.format(self.image_path.current))

    def set_window_title(self, title):
        if os.path.isfile(title):
            self.setWindowTitle("{} - {}".format(os.path.basename(title), self.WINDOW_TITLE))
        else:
            self.setWindowTitle("{} - {}".format(title, self.WINDOW_TITLE))

    def display_list_image_viewer(self):
        if not self.list_image_viewer.string_list_model.stringList() == self.image_path.sequence:
            self.list_image_viewer.display(self.star_actions.starred_images(), self.image_path.current)
            self.list_image_viewer.toggle_display()

    def save_image(self):
        file_name = QFileDialog.getSaveFileName(self, "Save image", self.dirs, "Images (*.BMP, *.JPG, *.JPEG, *.PNG)")[
            0]
        if file_name:
            if self.image_canvas.save(file_name):
                QMessageBox.information(self, "Success", "Successfully saved image")
            else:
                QMessageBox.critical(self, "Failure", "An error occurred while trying to save the image.")

    def eventFilter(self, obj, event):
        if not self.force_toolbar_display:
            if event.type() == QEvent.MouseMove:
                rect = self.geometry()
                rect.setHeight(50)
                if self.toolBar.isVisible() and not rect.contains(event.globalPos()):
                    self.toolBar.hide()
                elif rect.contains(event.globalPos()):
                    self.toolBar.show()
            elif event.type() == QEvent.Leave and obj is self:
                self.toolBar.hide()

        return QMainWindow.eventFilter(self, obj, event)

    def contextMenuEvent(self, event):
        """Show a context menu on right click."""
        menu = QMenu()
        self.action_options.add_to_context_menu(menu)
        menu.exec_(event.globalPos())  # show menu at mouse position

    def resizeEvent(self, event):
        """
        Update the image as you resize the window.
        """
        self.image_canvas.fit_in_view()

    def closeEvent(self, event):
        event.accept()  # close app


class ActionOptions:
    def __init__(self, main_window):
        self.main_window = main_window

        self.image_actions = QActionGroup(self.main_window)
        self.image_actions.setExclusive(False)

        self.path_actions = QActionGroup(self.main_window)
        self.path_actions.addAction(self.main_window.actionOpen)
        self.path_actions.addAction(self.main_window.actionFullscreen)

        self.random_actions = QActionGroup(self.main_window)
        self.random_actions.addAction(self.main_window.actionRandom)

        self.misc_actions = QActionGroup(self.main_window)
        self.slideshow_actions = QActionGroup(self.main_window)
        self.slideshow_actions.addAction(self.main_window.actionSettings)
        self.slideshow_actions.addAction(self.main_window.actionPlay)
        self.slideshow_actions.addAction(self.main_window.actionNext)
        self.slideshow_actions.addAction(self.main_window.actionPrevious)

        self.stars_actions = QActionGroup(self.main_window)
        self.stars_actions.addAction(self.main_window.actionStar)

        self.create_actions()
        self.add_actions()

    def add_actions(self):
        self.main_window.addActions(self.path_actions.actions())
        self.main_window.addActions(self.random_actions.actions())
        self.main_window.addActions(self.stars_actions.actions())
        self.main_window.addActions(self.misc_actions.actions())
        self.main_window.addActions(self.slideshow_actions.actions())
        self.main_window.addActions(self.image_actions.actions())

        self.main_window.addAction(self.main_window.actionOpen)
        self.main_window.addAction(self.main_window.actionFullscreen)
        self.main_window.addAction(self.main_window.actionSound)
        self.main_window.addAction(self.main_window.actionTimer)

    def create_actions(self):
        # ------- misc_actions --------
        self.main_window.actionStats = self.create_action("Run time", self.main_window, triggered=self.main_window.show_stats, action_group=self.misc_actions)
        self.main_window.actionBars = self.create_action("Hide/Show toolbar", self.main_window, triggered=self.main_window.toggle_bars, action_group=self.misc_actions)
        # ------- /misc_actions -------

        # ------- image_actions -------
        self.main_window.image_canvas.actionFlipUpDown = self.create_action("Flip upside down", self.main_window,
                                                                   triggered=self.main_window.image_canvas.flip_upside_down,
                                                                   enabled=False, checkable=True, shortcut=QKeySequence('Q'),
                                                                   action_group=self.image_actions)
        self.main_window.image_canvas.actionMirror = self.create_action("Mirror image", self.main_window,
                                                               triggered=self.main_window.image_canvas.mirror, shortcut=QKeySequence('W'),
                                                               enabled=False, checkable=True,
                                                               action_group=self.image_actions)
        self.main_window.image_canvas.actionRotateRight = self.create_action("Rotate image right", self.main_window,
                                                                    triggered=self.main_window.image_canvas.rotate_right,
                                                                    enabled=False, shortcut=QKeySequence('E'),
                                                                    action_group=self.image_actions)
        self.main_window.image_canvas.actionRotateLeft = self.create_action("Rotate image left", self.main_window,
                                                                   triggered=self.main_window.image_canvas.rotate_left,
                                                                   enabled=False, shortcut=QKeySequence('R'),
                                                                   action_group=self.image_actions)
        self.main_window.image_canvas.actionNormal = self.create_action("Normal fit", self.main_window,
                                                               triggered=self.main_window.image_canvas.normal, enabled=False,
                                                               shortcut=QKeySequence('2'),
                                                               action_group=self.image_actions)
        self.main_window.image_canvas.actionSave = self.create_action("Save", self.main_window, triggered=self.main_window.save_image,
                                                             enabled=False, action_group=self.image_actions)
        # ------- /image_actions -------

        # ------- path_actions ---------
        self.main_window.actionOpenInFolder = self.create_action("Open containing folder", self.main_window,
                                                        triggered=self.main_window.open_in_folder, enabled=False,
                                                        action_group=self.path_actions)

        self.main_window.actionViewImages = self.create_action("View the current list of images", self.main_window,
                                                      triggered=lambda: self.main_window.list_image_viewer.display(self.main_window.dirs, self.main_window.image_path.current),
                                                      enabled=True,
                                                      shortcut=QKeySequence("Alt+D"),
                                                      action_group=self.path_actions)
        # ------- /path_actions --------

        # ------- random_actions -------
        self.main_window.actionPreviousRandom = self.create_action("Undo random", self.main_window,
                                                          triggered=self.main_window.image_path.previous_random,
                                                          enabled=False,
                                                          shortcut=QKeySequence("Shift+F5"),
                                                          action_group=self.random_actions)
        self.main_window.actionShuffle = self.create_action("Shuffle images", self.main_window, triggered=self.main_window.image_path.shuffle,
                                                   enabled=False, shortcut=QKeySequence("Ctrl+F5"),
                                                   action_group=self.random_actions)
        self.main_window.actionPreviousShuffle = self.create_action("Undo shuffle", self.main_window,
                                                           triggered=self.main_window.image_path.previous_shuffle,
                                                           enabled=False,
                                                           shortcut=QKeySequence("Shift+Ctrl+F5"),
                                                           action_group=self.random_actions)
        # ------- /random_actions ------

        # ------- stars_actions --------
        self.main_window.actionOpenStars = self.create_action("View starred images", self.main_window,
                                                     triggered=lambda: self.main_window.list_image_viewer.display(
                                                         self.main_window.star_actions.starred_images(), self.main_window.image_path.current),
                                                     enabled=True, shortcut=QKeySequence("Ctrl+Alt+D"),
                                                     action_group=self.stars_actions)
        # ------- /stars_actions -------

    def create_action(self, *args, **kwargs):
        """Construct an action and add it to an action_group."""
        action_group = kwargs.pop('action_group', None)
        act = QAction(*args, **kwargs)
        if action_group:
            act.setActionGroup(action_group)

        return act

    def enable_actions_for(self, actions):
        for action in actions.actions():
            action.setEnabled(True)

    def enable_all_actions(self):
        self.main_window.actionSound.setEnabled(True)
        self.main_window.actionTimer.setEnabled(True)

        self.enable_actions_for(self.random_actions)
        self.enable_actions_for(self.image_actions)
        self.enable_actions_for(self.stars_actions)
        self.enable_actions_for(self.path_actions)
        self.enable_actions_for(self.slideshow_actions)

    def add_to_context_menu(self, menu):
        menu.addAction(self.main_window.actionOpen)
        menu.addActions(self.path_actions.actions())
        menu.addAction(self.main_window.actionFullscreen)
        menu.addSeparator()

        menu.addActions(self.slideshow_actions.actions())
        menu.addSeparator()

        menu.addActions(self.random_actions.actions())
        menu.addAction(self.main_window.actionSound)
        menu.addAction(self.main_window.actionTimer)
        menu.addSeparator()

        menu.addActions(self.image_actions.actions())

        menu.addSeparator()
        menu.addActions(self.misc_actions.actions())

        menu.addSeparator()
        menu.addActions(self.stars_actions.actions())


def run():
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('Mare5.Poseviewer.python.1')

    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    app.exec_()
