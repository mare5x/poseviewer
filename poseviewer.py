# coding: utf-8

from PySide.QtCore import *
from PySide.QtGui import *
import scandir
import sys
import os
import random
import ctypes
import subprocess
import shelve

import poseviewerMainGui


def get_shelf(key, fallback=None):
    try:
        with shelve.open('settings') as db:
            return db[key]
    except KeyError:
        return fallback

def set_shelf(key, item):
    with shelve.open('settings') as db:
        db[key] = item


def get_time_from_secs(secs, pretty=True):
    """
    Calculate hours, minutes, seconds from seconds.
    Return tuple (h, min, s)
    """
    # divmod = divide and modulo -- divmod(1200 / 1000)  =  (1, 200)
    mins, secs = divmod(secs, 60)
    hours, mins = divmod(mins, 60)
    if pretty:
        return "{0:02.0f}:{1:02.0f}:{2:02.0f}".format(hours, mins, secs)
    else:
        return hours, mins, secs


class MainWindow(QMainWindow, poseviewerMainGui.Ui_MainWindow):
    WINDOW_TITLE = "Poseviewer"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.drawImage = DrawImage(self)
        self.imageOptions = ImageOptions(self)

        self.setCentralWidget(self.drawImage)  # fills the whole window

        self.slideshowTimer = QTimer()  # make a timer ready to be used
        self.timeElapsedTimer = TimeElapsedThread(self)
        self.totalTimeElapsed = QElapsedTimer()  # keep a track of the whole time spent in app
        self.totalTimeElapsed.start()

        self.action_options = ActionOptions(self)

        self.timerLabel = QLabel()  # timer label
        self.timerLabel.setStyleSheet("font: 17pt; color: rgb(0, 180, 255)")  # set font size to 17 and color to blueish
        self.actionTimerLabel = self.toolBar.addWidget(self.timerLabel)  # add the timer label to the toolbar

        self.actionOpen.triggered.connect(self.open_dir)
        self.actionPlay.triggered.connect(self.toggle_slideshow)  # show image and start the timer
        self.actionShuffle.triggered.connect(self.shuffle_list)  # make a shuffled list
        self.actionNext.triggered.connect(self.next_image)
        self.actionPrevious.triggered.connect(self.previous_image)
        self.actionFullscreen.triggered.connect(self.toggle_fullscreen)  # toggle fullscreen
        self.actionSound.triggered.connect(self.toggle_sound)  # toggle sound
        self.actionSpeed.triggered.connect(self.set_slide_speed)  # set slide show speed
        self.actionTimer.triggered.connect(self.toggle_label_timer)  # toggle timer display

        self.timeElapsedTimer.secElapsed.connect(self.update_timerLabel)  # update the timer label every second
        self.slideshowTimer.timeout.connect(self.next_image)  # every slide_speed seconds show image

        self.step = 0  # go through all files
        self.is_playing = False  # is the slideshow playing
        self.sound = True  # is the sound turned on
        self.slide_speed = 30
        self.timer_visible = False
        self.bars_displayed = True
        self.previous_shuffle = []
        self.undo_shuffle_index = -1
        self.current_image_path = "."
        self.all_files = []

        self._next = None

        self.dirs = get_shelf('dirs', ["."])
        self.starred_images = get_shelf('stars', [])
        if self.starred_images:
            self.update_starred_images_menu()

        self.action_options.enable_actions_for(self.action_options.path_actions)

        self.window_dimensions = self.geometry()  # remember the geometry for returning from fullscreen
        self.DEFAULT_PALETTE = self.palette()

    def open_dir(self):
        """
        Append the image directory to self.dirs
        """
        self.dirs.append(QFileDialog.getExistingDirectory(self, "Open directory", dir=self.dirs[-1]))
        self.dirs.pop(0)
        set_shelf('dirs', self.dirs)
        if not self.dirs[-1] == '':  # '' is not a valid path
            # self.all_files_dir()
            self._next = self.get_next_image()
            self.current_image_path = next(self._next)
            self.next_image()
            self.action_options.enable_all_actions()

    def all_files_dir(self):
        """
        Constructs all_files and enables all actions.
        """
        self.all_files = [os.path.join(self.dirs[-1], f) for f in scandir.listdir(
            self.dirs[-1]) if os.path.isfile(os.path.join(self.dirs[-1], f))]
        self.next_image()

        self.action_options.enable_all_actions()  # enable the actions

    def update_image(self, image_path=None):
        """
        Update the graphicsview with image_path or current_image_path.
        """
        if image_path:
            self.drawImage.draw_image(image_path)
            self.current_image_path = image_path
        elif self.current_image_path:
            self.drawImage.draw_image(self.current_image_path)

    def prepare_image(self):
        self.set_window_title(self.current_image_path)
        if self.actionMirror.isChecked() or self.actionFlipUpDown.isChecked():
            self.update_image()  # the graphicsview still stays rotated
        else:
            self.imageOptions.normal()  # update image and reset any transformations

    def next_image(self):
        """
        Update image with the next image in sequence.
        """
        # if not self.step + 1 > len(self.all_files):  # if we go through all files go back to start
        #     self.step += 1
        # else:
        #     self.step = 0

        self.current_image_path = next(self._next)
        self.timeElapsedTimer.set_time_to_zero()
        self.update_timerLabel()
        self.prepare_image()

        if self.sound and self.is_playing:  # if the slide show is playing and the sound is on (called by timer timeout)
            self.beep()

    def previous_image(self):
        """
        Update image with the previous image in sequence.
        """
        if not abs(self.step) + 1 > len(self.all_files):
            self.step -= 1
        else:
            self.step = 0

        self.timeElapsedTimer.set_time_to_zero()  # reset timer back to 0
        self.update_timerLabel()  # immediately update
        self.prepare_image()

    def shuffle_list(self):
        """
        Shuffle the current list of images. Also initialize the settings again.
        """
        if len(self.previous_shuffle) > 10:
            self.previous_shuffle.pop(0)
        self.previous_shuffle.append(self.get_current_state())
        self.undo_shuffle_index = -1
        self.step = 0
        self.all_files = random.sample(self.all_files, len(self.all_files))  # create a shuffled new list
        self.next_image()

    def undo_shuffle(self):
        if abs(self.undo_shuffle_index) <= len(self.previous_shuffle):
            all_files, step = self.previous_shuffle[self.undo_shuffle_index]
            self.all_files = all_files
            self.step = step
            self.prepare_image()
            self.undo_shuffle_index -= 1

        if self.undo_shuffle_index < -9:
            self.undo_shuffle_index = -9

    def _paint_background(self, qcolor, full_background=False):
        if full_background:
            full_background = QPalette()
            full_background.setColor(self.backgroundRole(), qcolor)
            self.setPalette(full_background)
        else:
            self.setPalette(self.DEFAULT_PALETTE)

        self.drawImage.setBackgroundBrush(QBrush(qcolor))

    def toggle_fullscreen(self):
        """
        Deal with entering/exiting fullscreen mode.
        """
        if self.isFullScreen():  # go back to normal
            self.set_icon(":/Icons/fullscreen.png", self.actionFullscreen)
            self._paint_background(Qt.NoBrush)
            self.setGeometry(self.window_dimensions)
            self.showNormal()
        else:  # go to fullscreen
            self.set_icon(":/Icons/closefullscreen.png", self.actionFullscreen)
            self.window_dimensions = self.geometry()  # save current window settings
            self._paint_background(Qt.black, True)
            self.showFullScreen()

        self.update_image()  # update the image to fit the fullscreen mode

    def toggle_slideshow(self):
        """Deals with starting/stopping the slideshow.
        """
        if self.is_playing:  # if it's playing, stop it
            self.set_icon(":/Icons/play.png", self.actionPlay)
            self.stop_slideshowTimer()
            self.is_playing = False
        else:  # if it's not playing, play it
            self.beep()
            self.set_icon(":/Icons/pause.png", self.actionPlay)
            self.next_image()
            self.start_slideshowTimer()
            self.is_playing = True

    def toggle_sound(self):
        """
        Toggle whether there should be a beep during a slideshow.
        """
        if self.sound:  # sound is on and you stop it
            self.sound = False
            self.set_icon(":/Icons/soundoff.png", self.actionSound)
        else:  # sound is not on and you put it on
            self.sound = True
            self.set_icon(":/Icons/soundon.png", self.actionSound)

    def toggle_label_timer(self):
        """
        Toggle whether the timerLabel should be displayed.
        """
        if self.timer_visible:
            self.timer_visible = False
            self.actionTimerLabel.setVisible(False)
        else:
            self.actionTimerLabel.setVisible(True)
            self.timer_visible = True
            self.timeElapsedTimer.start()

        self.update_timerLabel()
        self.timeElapsedTimer.set_time_to_zero()

    def toggle_bars(self):
        """
        Toggle bars - right click menu, action. Toggle toolbar visibility.
        """
        if self.bars_displayed:
            self.toolBar.hide()
            self.bars_displayed = False
        else:
            self.toolBar.show()
            self.bars_displayed = True

        self.update_image()

    def start_slideshowTimer(self):
        self.slideshowTimer.start(self.slide_speed * 1000)  # ms to s

    def stop_slideshowTimer(self):
        self.slideshowTimer.stop()

    @staticmethod
    def beep():
        beep = QSound("beep.wav")
        beep.play()

    def update_timerLabel(self):
        if self.timer_visible:
            self.timerLabel.setText(self.timeElapsedTimer.time_elapsed())

    def show_stats(self):
        QMessageBox.information(self, 'Stats',
                                'Total time in app: ' + get_time_from_secs(self.totalTimeElapsed.elapsed() / 1000))

    def open_in_folder(self):
        subprocess.Popen(r'explorer /select,{}'.format(self.current_image_path))

    def star_image(self):
        self.starred_images.append(self.current_image_path)
        set_shelf('stars', self.starred_images)
        self.update_starred_images_menu()

    def update_starred_images_menu(self):
        stars_menu = QMenu("Starred images")
        for star in self.starred_images:
            each_star_menu = QMenu(star)
            show_act = QAction("Show", each_star_menu)
            show_act.setData(star)
            each_star_menu.addAction(show_act)
            unstar_act = QAction("Unstar", each_star_menu)
            unstar_act.setData(star)
            each_star_menu.addAction(unstar_act)
            stars_menu.addMenu(each_star_menu)
        self.action_options.stars_menu = stars_menu
        return stars_menu

    def set_window_title(self, title):
        if os.path.isfile(title):
            self.setWindowTitle("{} - {}".format(title.rsplit('\\', 1)[-1], self.WINDOW_TITLE))
        else:
            self.setWindowTitle("{} - {}".format(title, self.WINDOW_TITLE))

    def set_slide_speed(self):
        """
        Set the slideshow speed by opening a inputdialog.
        """
        slide_speed = QInputDialog()
        self.slide_speed = slide_speed.getInt(self, "Slideshow speed",
                                              "Enter slideshow speed (seconds): ",
                                              value=30, minValue=1)[0]
        # return type: (int, bool)

    def set_icon(self, path, target):
        icon = QIcon()
        icon.addPixmap(QPixmap(path), QIcon.Normal, QIcon.Off)
        target.setIcon(icon)

    def get_starred_image(self, action):
        self.action_options.stars_menu.triggered.disconnect(self.get_starred_image)
        if self.action_options.image_actions.isEnabled():
            self.action_options.enable_actions_for(self.action_options.image_actions)

        if action.text() == "Show":
            self.update_image(image_path=action.data())
        elif action.text() == "Unstar":
            self.starred_images.remove(action.data())
            self.update_starred_images_menu()

        self.set_window_title(action.data())

    def get_current_state(self):
        return self.all_files, self.step

    def get_current_image_path(self):
        return self.all_files[self.step]

    def get_next_image(self):
        for root, dirs, files in scandir.walk(self.dirs[-1]):
            for _file in files:
                yield os.path.abspath(os.path.join(root, _file))

    def contextMenuEvent(self, event):
        """Show a context menu on right click."""
        menu = QMenu()
        self.action_options.add_to_context_menu(menu)
        self.action_options.stars_menu.triggered.connect(self.get_starred_image)
        menu.exec_(event.globalPos())  # show menu at mouse position

    def resizeEvent(self, event):
        """
        Update the image as you resize the window.
        """
        self.drawImage.fit_in_view()

    def closeEvent(self, event):
        self.timeElapsedTimer.exit()
        set_shelf('stars', self.starred_images)  # save starred_images
        event.accept()  # close app


class ActionOptions:
    def __init__(self, parent):
        self.mw = parent

        self.stars_menu = QMenu("Starred images")
        self.main_menu = QMenu()

        self.image_actions = QActionGroup(self.mw)
        self.image_actions.setExclusive(False)

        self.path_actions = QActionGroup(self.mw)
        self.path_actions.addAction(self.mw.actionOpen)
        self.path_actions.addAction(self.mw.actionSpeed)
        self.path_actions.addAction(self.mw.actionFullscreen)

        self.create_actions()
        self.add_actions()

    def add_actions(self):
        self.add_actions_to(self.path_actions, self.mw)

        self.mw.addAction(self.mw.actionSpeed)
        self.mw.addAction(self.mw.actionOpen)
        self.mw.addAction(self.mw.actionFullscreen)
        self.mw.addAction(self.mw.actionPrevious)
        self.mw.addAction(self.mw.actionPlay)
        self.mw.addAction(self.mw.actionNext)
        self.mw.addAction(self.mw.actionShuffle)
        self.mw.addAction(self.mw.actionSound)
        self.mw.addAction(self.mw.actionTimer)
        self.mw.addAction(self.mw.actionPreviousShuffle)
        self.mw.addAction(self.mw.actionStar)

    def create_actions(self):
        self.mw.actionStats = QAction("Run time", self.mw,
                                      triggered=self.mw.show_stats)
        self.mw.actionBars = QAction("Hide/Show toolbar", self.mw,
                                     triggered=self.mw.toggle_bars)

        # ------- image_actions -------
        self.mw.actionFlipUpDown = self.create_action("Flip upside down", self.mw,
                                                      triggered=self.mw.imageOptions.flip_upside_down,
                                                      enabled=False, checkable=True, action_group=self.image_actions)
        self.mw.actionMirror = self.create_action("Mirror image", self.mw,
                                                  triggered=self.mw.imageOptions.mirror,
                                                  enabled=False, checkable=True,
                                                  action_group=self.image_actions)
        self.mw.actionRotateRight = self.create_action("Rotate image right", self.mw,
                                                       triggered=self.mw.imageOptions.rotate_right,
                                                       enabled=False, action_group=self.image_actions)
        self.mw.actionRotateLeft = self.create_action("Rotate image left", self.mw,

                                                      triggered=self.mw.imageOptions.rotate_left,
                                                      enabled=False, action_group=self.image_actions)
        self.mw.actionNormal = self.create_action("Normal fit", self.mw,
                                                  triggered=self.mw.imageOptions.normal, enabled=False,
                                                  action_group=self.image_actions)
        # ------- image_actions -------

        self.mw.actionOpenInFolder = self.create_action("Open containing folder", self.mw,
                                                        triggered=self.mw.open_in_folder, enabled=False,
                                                        action_group=self.path_actions)
        self.mw.actionPreviousShuffle = QAction("Undo shuffle", self.mw,
                                                triggered=self.mw.undo_shuffle,
                                                enabled=False,
                                                shortcut=QKeySequence.fromString("Shift+F5"))
        self.mw.actionStar = QAction("Star this image", self.mw,
                                     triggered=self.mw.star_image, enabled=False,
                                     shortcut=QKeySequence.fromString("Ctrl+D"))

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

    def add_actions_to(self, actions, obj):
        for action in actions.actions():
            obj.addAction(action)

    def enable_all_actions(self):
        self.mw.actionPlay.setEnabled(True)
        self.mw.actionNext.setEnabled(True)
        self.mw.actionPrevious.setEnabled(True)

        self.mw.actionShuffle.setEnabled(True)
        self.mw.actionPreviousShuffle.setEnabled(True)

        self.mw.actionSound.setEnabled(True)
        self.mw.actionTimer.setEnabled(True)

        self.enable_actions_for(self.image_actions)

        self.mw.actionOpenInFolder.setEnabled(True)
        self.mw.actionStar.setEnabled(True)

    def add_to_context_menu(self, menu):
        menu.addAction(self.mw.actionOpen)
        menu.addAction(self.mw.actionOpenInFolder)
        menu.addAction(self.mw.actionSpeed)
        menu.addAction(self.mw.actionFullscreen)
        menu.addSeparator()

        menu.addAction(self.mw.actionPrevious)
        menu.addAction(self.mw.actionPlay)
        menu.addAction(self.mw.actionNext)
        menu.addSeparator()

        menu.addAction(self.mw.actionShuffle)
        menu.addAction(self.mw.actionPreviousShuffle)
        menu.addAction(self.mw.actionSound)
        menu.addAction(self.mw.actionTimer)
        menu.addSeparator()

        self.add_actions_to(self.image_actions, menu)

        menu.addSeparator()
        menu.addAction(self.mw.actionStats)
        menu.addAction(self.mw.actionBars)

        menu.addSeparator()
        menu.addAction(self.mw.actionStar)
        stars_menu = menu.addMenu(self.stars_menu)

        self.main_menu = menu


class ImageOptions:
    def __init__(self, parent):
        self.mw = parent

    def flip_upside_down(self):
        if self.mw.actionFlipUpDown.isChecked():
            self.mw.drawImage.rotate(180)  # no need to update image since the rect will stay the same - just flipped
        else:
            self.normal()

    def mirror(self):
        if self.mw.actionMirror.isChecked():
            transform = QTransform().rotate(180, Qt.YAxis)
            self.mw.drawImage.setTransform(transform)
            self.mw.update_image()
        else:
            self.normal()

    def rotate_right(self):
        self.mw.drawImage.rotate(90)
        self.mw.update_image()

    def rotate_left(self):
        self.mw.drawImage.rotate(-90)
        self.mw.update_image()

    def normal(self):
        self.mw.actionFlipUpDown.setChecked(False)
        self.mw.actionMirror.setChecked(False)
        self.mw.drawImage.resetTransform()
        self.mw.update_image()


class TimeElapsedThread(QThread):
    """
    Thread for continuous time tracking.
    Emits a secElapsed signal after each second.
    """

    secElapsed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.secs_elapsed = 0
        self.secs = 0
        self.mins = 0
        self.hours = 0

        # self.exit = False  # for safe exiting  -  not stuck in while loop

    def run(self):
        while True:
            self.sleep(1)  # 1 seconds expired
            self.secs_elapsed += 1  # secs_elapsed instead of secs because secs is recalculated
            self.time_elapsed()  # don't calculate from ms because we always restart the timer
            self.secElapsed.emit()

    def time_elapsed(self):
        """
        Calculate elapsed hours, minutes, seconds.
        """
        self.hours, self.mins, self.secs = get_time_from_secs(self.secs_elapsed, False)
        return get_time_from_secs(self.secs_elapsed)

    def set_time_to_zero(self):
        self.secs_elapsed, self.secs, self.mins, self.hours = 0, 0, 0, 0


class DrawImage(QGraphicsView):
    ZOOM_FACTOR = 1.2

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFrameShape(QFrame.NoFrame)  # PySide.QtGui.QFrame draws nothing
        self.setInteractive(False)
        self.setRenderHints(QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setRubberBandSelectionMode(Qt.IntersectsItemShape)

        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # disable scroll bars - drag with mouse
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setContextMenuPolicy(Qt.ActionsContextMenu)  # without this the contextmenu doesn't show on qgraphicsscene

        self.imageScene = QGraphicsScene()
        self.pix_item = QGraphicsPixmapItem()
        self.pix_item.setTransformationMode(Qt.SmoothTransformation)  # make it smooooth

        self.imageScene.addItem(self.pix_item)  # add pixmap to scene
        self.setScene(self.imageScene)  # apply scene to view
        self.show()  # show image

    def draw_image(self, image):
        pix_image = QPixmap(image)  # make pixmap
        self.pix_item.setPixmap(pix_image)
        self.setSceneRect(QRectF(0.0, 0.0, pix_image.width(),
                                 pix_image.height()))  # update the rect so it isn't retarded like by default -- center image
        self.fit_in_view()

    def fit_in_view(self):
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)

    def wheelEvent(self, event):
        self.setTransformationAnchor(self.NoAnchor)
        self.setResizeAnchor(self.NoAnchor)

        old_pos = self.mapToScene(event.pos())

        if event.delta() > 0:  # mouse wheel away = zoom in
            self.scale(self.ZOOM_FACTOR, self.ZOOM_FACTOR)
        else:
            self.scale(1 / self.ZOOM_FACTOR, 1 / self.ZOOM_FACTOR)

        new_pos = self.mapToScene(event.pos())  # translate pos to scene pos
        delta = new_pos - old_pos
        self.translate(delta.x(), delta.y())


if __name__ == '__main__':
    myappid = 'Marko.Poseviewer.python.1'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    app = QApplication(sys.argv)
    form = MainWindow()
    form.show()
    app.exec_()

#TODO create efficient mechanism for loading large amounts of images (>3000)
#TODO load multiple dirs for images and mix them up
#TODO fix, so the app shows the correct icon in the taskbar
