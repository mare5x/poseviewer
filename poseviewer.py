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

        self.image_path = ImagePath()
        self.image_canvas = ImageCanvas(self)
        self.images_viewer = ImageViewer(parent=self)
        self.action_options = ActionOptions(self)

        # layout = QGridLayout()
        self.gridLayout.addWidget(self.image_canvas)
        self.gridLayout.addWidget(self.images_viewer)
        self.window = QWidget()
        self.window.setLayout(self.gridLayout)

        # self.setCentralWidget(self.image_canvas)  # fills the whole window
        self.setCentralWidget(self.window)

        self.images_viewer.indexDoubleClicked.connect(self.prepare_image)

        self.slideshowTimer = QTimer()  # make a timer ready to be used
        self.timeElapsedTimer = TimeElapsedThread(self)
        self.totalTimeElapsed = QElapsedTimer()  # keep a track of the whole time spent in app
        self.totalTimeElapsed.start()

        self.timerLabel = QLabel()  # timer label
        self.timerLabel.setStyleSheet("font: 17pt; color: rgb(0, 180, 255)")  # set font size to 17 and color to blueish
        self.actionTimerLabel = self.toolBar.addWidget(self.timerLabel)  # add the timer label to the toolbar

        self.actionOpen.triggered.connect(self.get_directory)
        self.actionPlay.triggered.connect(self.toggle_slideshow)  # show image and start the timer
        self.actionRandom.triggered.connect(self.random)  # make a shuffled list
        self.actionNext.triggered.connect(self.next_image)
        self.actionPrevious.triggered.connect(self.previous_image)
        self.actionFullscreen.triggered.connect(self.toggle_fullscreen)  # toggle fullscreen
        self.actionSound.triggered.connect(self.toggle_sound)  # toggle sound
        self.actionSpeed.triggered.connect(self.set_slide_speed)  # set slide show speed
        self.actionTimer.triggered.connect(self.toggle_label_timer)  # toggle timer display

        self.timeElapsedTimer.secElapsed.connect(self.update_timerLabel)  # update the timer label every second
        self.slideshowTimer.timeout.connect(self.next_image)  # every slide_speed seconds show image

        self.is_playing = False  # is the slideshow playing
        self.sound = True  # is the sound turned on
        self.slide_speed = 30
        self.timer_visible = False
        self.bars_displayed = True

        self.dirs = get_shelf('dirs', ".")
        self.starred_images = get_shelf('stars', [])
        if self.starred_images:
            self.update_starred_images_menu()

        self.action_options.enable_actions_for(self.action_options.path_actions)

        self.window_dimensions = self.geometry()  # remember the geometry for returning from fullscreen
        self.DEFAULT_PALETTE = self.palette()

    def get_directory(self):
        """
        Append the image directory to self.dirs
        """
        self.dirs = QFileDialog.getExistingDirectory(self, "Open directory", dir=self.dirs)
        set_shelf('dirs', self.dirs)
        if self.dirs:  # '' is not a valid path
            self.image_path.load_dir(self.dirs)
            self.action_options.enable_all_actions()
            self.next_image()

    def update_image(self, path=None):
        """
        Update the graphicsview with image_path or current_image_path.
        """
        if path:
            self.image_canvas.draw_image(path)
            self.image_path.current = path
        elif self.image_path.current:
            self.image_canvas.draw_image(self.image_path.current)

    def prepare_image(self, path=None):
        self.timeElapsedTimer.set_time_to_zero()
        self.update_timerLabel()
        self.set_window_title(self.image_path.current)
        self.update_image(path)  # the graphicsview still stays rotated

    def next_image(self):
        """
        Update image with the next image in sequence.
        """
        self.image_path.next()
        self.prepare_image()

        if self.sound and self.is_playing:
            self.beep()

    def previous_image(self):
        """
        Update image with the previous image in sequence.
        """
        self.image_path.prev()
        self.prepare_image()

    def shuffle(self):
        self.image_path.shuffle()
        self.next_image()

    def previous_shuffle(self):
        self.image_path.previous_shuffle()
        self.prepare_image()

    def random(self):
        self.image_path.random()
        self.prepare_image()

    def previous_random(self):
        self.image_path.previous_random()
        self.prepare_image()

    def show_stars_viewer(self):
        self.images_viewer.set_image_list(self.starred_images)
        self.images_viewer.display()

    def show_all_viewer(self):
        self.images_viewer.set_image_list(self.image_path.all_files)
        self.images_viewer.display()

    def paint_background(self, qcolor, full_background=False):
        if full_background:
            full_background = QPalette()
            full_background.setColor(self.backgroundRole(), qcolor)
            self.setPalette(full_background)
        else:
            self.setPalette(self.DEFAULT_PALETTE)

        self.image_canvas.setBackgroundBrush(QBrush(qcolor))

    def toggle_fullscreen(self):
        """
        Deal with entering/exiting fullscreen mode.
        """
        if self.isFullScreen():  # go back to normal
            self.set_icon(":/Icons/fullscreen.png", self.actionFullscreen)
            self.paint_background(Qt.NoBrush)
            self.setGeometry(self.window_dimensions)
            self.showNormal()
        else:  # go to fullscreen
            self.set_icon(":/Icons/closefullscreen.png", self.actionFullscreen)
            self.window_dimensions = self.geometry()  # save current window settings
            self.paint_background(Qt.black, True)
            self.showFullScreen()

        self.update_image()  # update the image to fit the fullscreen mode

    def toggle_slideshow(self):
        """Deals with starting/stopping the slideshow.
        """
        if self.is_playing:  # if it's playing, stop it
            self.set_icon(":/Icons/play.png", self.actionPlay)
            self.stop_slideshowTimer()
        else:  # if it's not playing, play it
            self.beep()
            self.set_icon(":/Icons/pause.png", self.actionPlay)
            self.next_image()
            self.start_slideshowTimer()
        self.is_playing = not self.is_playing

    def toggle_sound(self):
        """
        Toggle whether there should be a beep during a slideshow.
        """
        if self.sound:  # sound is on and you stop it
            self.set_icon(":/Icons/soundoff.png", self.actionSound)
        else:  # sound is not on and you put it on
            self.set_icon(":/Icons/soundon.png", self.actionSound)
        self.sound = not self.sound

    def toggle_label_timer(self):
        """
        Toggle whether the timerLabel should be displayed.
        """
        if self.timer_visible:
            self.actionTimerLabel.setVisible(False)
        else:
            self.actionTimerLabel.setVisible(True)
            self.timeElapsedTimer.start()
        self.timer_visible = not self.timer_visible

        self.update_timerLabel()
        self.timeElapsedTimer.set_time_to_zero()

    def toggle_bars(self):
        """
        Toggle bars - right click menu, action. Toggle toolbar visibility.
        """
        if self.bars_displayed:
            self.toolBar.hide()
        else:
            self.toolBar.show()
        self.bars_displayed = not self.bars_displayed

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
        subprocess.Popen(r'explorer /select,{}'.format(self.image_path.current))

    def star_image(self):
        self.starred_images.append(self.image_path.current)
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
            self.update_image(path=action.data())
        elif action.text() == "Unstar":
            self.starred_images.remove(action.data())
            self.update_starred_images_menu()

        self.set_window_title(action.data())

    def save_image(self):
        file_name = QFileDialog.getSaveFileName(self, "Save image", self.dirs, "Images (*.BMP, *.JPG, *.JPEG, *.PNG)")[0]
        if file_name:
            if self.image_canvas.save(file_name):
                QMessageBox.information(self, "Success", "Successfully saved image")
            else:
                QMessageBox.critical(self, "Failure", "An error occurred while trying to save the image.")

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
        self.image_canvas.fit_in_view()

    def closeEvent(self, event):
        self.timeElapsedTimer.exit()
        set_shelf('stars', self.starred_images)  # save starred_images
        event.accept()  # close app


class ImagePath:
    UNDO_SHUFFLE_LIMIT = 10
    UNDO_RANDOM_LIMIT = 50

    def __init__(self):
        self.current_index = 0
        self.undo_random_index = -1
        self.undo_shuffle_index = -1
        self.previous_random_storage = []
        self.previous_shuffle_storage = []
        self.all_files = []
        self.current_image_path = "."

    def next(self):
        if self.current_index + 1 > len(self.all_files):  # if we go through all files go back to start
            self.current_index = 0
        else:
            self.current_index += 1

        self.current = self.all_files[self.current_index]

    def prev(self):
        if not abs(self.current_index) + 1 > len(self.all_files):
            self.current_index -= 1
        else:
            self.current_index = 0

        self.current = self.all_files[self.current_index]

    def shuffle(self):
        if len(self.previous_shuffle_storage) > self.UNDO_SHUFFLE_LIMIT:
            self.previous_shuffle_storage.pop(0)
        self.previous_shuffle_storage.append((self.all_files, self.current_index))
        self.undo_shuffle_index = -1
        self.current_index = 0
        self.all_files = random.sample(self.all_files, len(self.all_files))

    def previous_shuffle(self):
        if abs(self.undo_shuffle_index) <= len(self.previous_shuffle_storage):
            self.all_files, self.current_index = self.previous_shuffle_storage[self.undo_shuffle_index]
            self.undo_shuffle_index -= 1

        if self.undo_shuffle_index < -(self.UNDO_SHUFFLE_LIMIT - 1):
            self.undo_shuffle_index = -(self.UNDO_SHUFFLE_LIMIT - 1)

        self.current = self.all_files[self.current_index]

    def random(self):
        if len(self.previous_random_storage) > self.UNDO_RANDOM_LIMIT:
            self.previous_random_storage.pop(0)

        self.previous_random_storage.append(self.current)
        self.current = random.choice(self.all_files)
        self.undo_random_index = -1

    def previous_random(self):
        if abs(self.undo_random_index) <= len(self.previous_random_storage):
            self.current = self.previous_random_storage[self.undo_random_index]
            self.undo_random_index -= 1

        if self.undo_random_index < -(self.UNDO_RANDOM_LIMIT - 1):
            self.undo_random_index = -(self.UNDO_RANDOM_LIMIT - 1)

    @property
    def current(self):
        return self.current_image_path

    @current.setter
    def current(self, value):
        self.current_image_path = value

    def load_dir(self, path):
        self.all_files = [os.path.abspath(os.path.join(path, img)) for img in scandir.listdir(path)
                          if os.path.isfile(os.path.join(path, img))]
        return self.all_files


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

        self.random_actions = QActionGroup(self.mw)
        self.random_actions.addAction(self.mw.actionRandom)

        self.stars_actions = QActionGroup(self.mw)

        self.create_actions()
        self.add_actions()

    def add_actions(self):
        self.add_actions_to(self.path_actions, self.mw)
        self.add_actions_to(self.random_actions, self.mw)
        self.add_actions_to(self.stars_actions, self.mw)

        self.mw.addAction(self.mw.actionSpeed)
        self.mw.addAction(self.mw.actionOpen)
        self.mw.addAction(self.mw.actionFullscreen)
        self.mw.addAction(self.mw.actionPrevious)
        self.mw.addAction(self.mw.actionPlay)
        self.mw.addAction(self.mw.actionNext)
        self.mw.addAction(self.mw.actionSound)
        self.mw.addAction(self.mw.actionTimer)

    def create_actions(self):
        self.mw.actionStats = QAction("Run time", self.mw,
                                      triggered=self.mw.show_stats)
        self.mw.actionBars = QAction("Hide/Show toolbar", self.mw,
                                     triggered=self.mw.toggle_bars)

        # ------- image_actions -------
        self.mw.image_canvas.actionFlipUpDown = self.create_action("Flip upside down", self.mw,
                                                                   triggered=self.mw.image_canvas.flip_upside_down,
                                                                   enabled=False, checkable=True,
                                                                   action_group=self.image_actions)
        self.mw.image_canvas.actionMirror = self.create_action("Mirror image", self.mw,
                                                               triggered=self.mw.image_canvas.mirror,
                                                               enabled=False, checkable=True,
                                                               action_group=self.image_actions)
        self.mw.image_canvas.actionRotateRight = self.create_action("Rotate image right", self.mw,
                                                                    triggered=self.mw.image_canvas.rotate_right,
                                                                    enabled=False, action_group=self.image_actions)
        self.mw.image_canvas.actionRotateLeft = self.create_action("Rotate image left", self.mw,
                                                                   triggered=self.mw.image_canvas.rotate_left,
                                                                   enabled=False, action_group=self.image_actions)
        self.mw.image_canvas.actionNormal = self.create_action("Normal fit", self.mw,
                                                               triggered=self.mw.image_canvas.normal, enabled=False,
                                                               action_group=self.image_actions)
        self.mw.image_canvas.actionSave = self.create_action("Save", self.mw, triggered=self.mw.save_image,
                                                             enabled=False, action_group=self.image_actions)
        # ------- /image_actions -------

        # ------- path_actions ---------
        self.mw.actionOpenInFolder = self.create_action("Open containing folder", self.mw,
                                                        triggered=self.mw.open_in_folder, enabled=False,
                                                        action_group=self.path_actions)

        self.mw.actionViewImages = self.create_action("View the current list of images", self.mw,
                                                       triggered=self.mw.show_all_viewer, enabled=True,
                                                       shortcut=QKeySequence.fromString("Alt+D"),
                                                       action_group=self.path_actions)
        # ------- /path_actions --------

        # ------- random_actions -------
        self.mw.actionPreviousRandom = self.create_action("Undo random", self.mw,
                                                           triggered=self.mw.previous_random,
                                                           enabled=False,
                                                           shortcut=QKeySequence.fromString("Shift+F5"),
                                                           action_group=self.random_actions)
        self.mw.actionShuffle = self.create_action("Shuffle images", self.mw, triggered=self.mw.shuffle, enabled=False,
                                                   shortcut=QKeySequence.fromString("Ctrl+F5"), action_group=self.random_actions)
        self.mw.actionPreviousShuffle = self.create_action("Undo shuffle", self.mw,
                                                            triggered=self.mw.previous_shuffle,
                                                            enabled=False,
                                                            shortcut=QKeySequence.fromString("Shift+Ctrl+F5"),
                                                            action_group=self.random_actions)
        # ------- /random_actions ------

        # ------- stars_actions --------
        self.mw.actionStar = self.create_action("Star this image", self.mw,
                                                 triggered=self.mw.star_image, enabled=False,
                                                 shortcut=QKeySequence.fromString("Ctrl+D"), action_group=self.stars_actions)

        self.mw.actionOpenStars = self.create_action("View starred images", self.mw, triggered=self.mw.show_stars_viewer,
                                                      enabled=True, shortcut=QKeySequence.fromString("Ctrl+Alt+D"),
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

    def add_actions_to(self, actions, obj):
        for action in actions.actions():
            obj.addAction(action)

    def enable_all_actions(self):
        self.mw.actionPlay.setEnabled(True)
        self.mw.actionNext.setEnabled(True)
        self.mw.actionPrevious.setEnabled(True)

        self.mw.actionSound.setEnabled(True)
        self.mw.actionTimer.setEnabled(True)

        self.enable_actions_for(self.random_actions)
        self.enable_actions_for(self.image_actions)
        self.enable_actions_for(self.stars_actions)
        self.enable_actions_for(self.path_actions)

    def add_to_context_menu(self, menu):
        menu.addAction(self.mw.actionOpen)
        self.add_actions_to(self.path_actions, menu)
        menu.addAction(self.mw.actionSpeed)
        menu.addAction(self.mw.actionFullscreen)
        menu.addSeparator()

        menu.addAction(self.mw.actionPrevious)
        menu.addAction(self.mw.actionPlay)
        menu.addAction(self.mw.actionNext)
        menu.addSeparator()

        self.add_actions_to(self.random_actions, menu)
        menu.addAction(self.mw.actionSound)
        menu.addAction(self.mw.actionTimer)
        menu.addSeparator()

        self.add_actions_to(self.image_actions, menu)

        menu.addSeparator()
        menu.addAction(self.mw.actionStats)
        menu.addAction(self.mw.actionBars)

        menu.addSeparator()
        self.add_actions_to(self.stars_actions, menu)
        menu.addMenu(self.stars_menu)

        self.main_menu = menu


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


class ImageCanvas(QGraphicsView):
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

    def flip_upside_down(self):
        if self.actionFlipUpDown.isChecked():
            self.rotate(180)  # no need to update image since the rect will stay the same - just flipped
        else:
            self.normal()

    def mirror(self):
        if self.actionMirror.isChecked():
            self.setTransform(QTransform().rotate(180, Qt.YAxis), combine=True)
        else:
            self.normal()

    def rotate_right(self):
        self.rotate(90)

    def rotate_left(self):
        self.rotate(-90)

    def normal(self):
        self.actionFlipUpDown.setChecked(False)
        self.actionMirror.setChecked(False)
        self.resetTransform()
        self.fit_in_view()

    def save(self, file_name):
        pix = QPixmap.grabWidget(self)
        return pix.save(file_name)

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


class ImageViewer(QSplitter):
    indexDoubleClicked = Signal(str)

    def __init__(self, parent=None, image_list=None):
        super().__init__(parent)

        self.image_list = image_list
        self.model = QStringListModel(self.image_list)

        self.list_view = QListView(self)
        self.list_view.setModel(self.model)
        self.list_view.clicked.connect(self.paint)
        self.list_view.doubleClicked.connect(self.apply_index)

        self.canvas = ImageCanvas(self)

        # other side shows preview
        # double click to set the image to mainwindow and close this widget
        # option to "play all" ( set all images in view to all_files )
        self.setChildrenCollapsible(False)
        self.resize(parent.size())
        self.setSizes([400, 600])

        self.hide()
        self.is_displayed = False

    @Slot()
    def display(self):
        if self.is_displayed:
            self.hide()
        else:
            self.show()
        self.is_displayed = not self.is_displayed

    def set_image_list(self, image_list):
        self.model.setStringList(image_list)

    def paint(self, index):
        self.canvas.draw_image(self.model.data(index, 0))

    def apply_index(self, index):
        self.indexDoubleClicked.emit(self.model.data(index, 0))


if __name__ == '__main__':
    myappid = 'Marko.Poseviewer.python.1'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    app = QApplication(sys.argv)
    form = MainWindow()
    form.show()
    app.exec_()


# TODO create efficient mechanism for loading large amounts of images (>3000)
# TODO load multiple dirs for images and mix them up
# TODO fix, so the app shows the correct icon in the taskbar
# TODO draw tool
# TODO save image (with transformation applied)
# TODO delete option

# def get_img(path, index):
#     if index >= len(scandir.listdir(path)):
#         index -= len(scandir.listdir(path))

#     for i, j in enumerate(scandir.listdir(path)):
#         if i == index:
#             return j
