from PySide.QtCore import *
from PySide.QtGui import *
import sys
import os
import random
import ctypes

import poseviewerMainGui


class MainWindow(QMainWindow, poseviewerMainGui.Ui_MainWindow):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.imageOptions = ImageOptions()
        self.drawImage = DrawImage(self, self.graphicsView)

        self.slideshowTimer = QTimer()  # make a timer ready to be used
        self.timeElapsedTimer = TimeElapsedThread()
        self.totalTimeElapsed = QElapsedTimer()  # keep a track of the whole time spent in app
        self.totalTimeElapsed.start()

        self.setActionOptions = SetActionOptions(self)
        self.setActionOptions.create_actions()  # SetActionOptions  --  creates actions not created in designer
        self.setActionOptions.add_actions()  # SetActionOptions -- adds actions to MainWindow

        self.timerLabel = QLabel()  # timer label
        self.timerLabel.setStyleSheet("font: 17pt; color: rgb(0, 180, 255)")  # set font size to 17 and color to blueish
        self.actionTimerLabel = self.toolBar.addWidget(self.timerLabel)  # add the timer label to the toolbar

        self.dirs = ["."]  # the directory of the images, "." = default value
        self.all_files = None  # a list

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

        self.window_dimensions = self.geometry()  # remember the geometry for returning from fullscreen
        self.image_view_dimensions = self.graphicsView.width(), self.graphicsView.height()  # scale the label from fullscreen
        self.default_palette = self.palette()  # the default palette for returning from fullscreen

    def open_dir(self):
        """
        Append the image directory to self.dirs
        """
        self.dirs.append(QFileDialog.getExistingDirectory(self, "Open directory", dir=self.dirs[-1]))
        if not self.dirs[-1] == '':  # '' is not a valid path
            self.all_files_dir()

    def all_files_dir(self):
        """
        Appends dir + file
        Append all files in the directory to self.all_files if the file is a file.
        Also use os.path.join to correctly connect the dir with the file.
        Don't append in case we change the working dir. - Make new all files list.
        Update the display with an image. Enable the buttons.
        """
        self.all_files = [os.path.join(self.dirs[-1], f) for f in os.listdir(
                        self.dirs[-1]) if os.path.isfile(os.path.join(self.dirs[-1], f))]
        self.update_image()

        self.setActionOptions.enable_actions()  # enable the actions

    def toggle_slideshow(self):
        """
        Updates the imageLabel with the current image from self.step.
        Also increments self.step and it is called every timer timeout.
        If the slideshow is playing change the icon.
        """
        icon = QIcon()
        if self.is_playing:  # if it's playing, stop it
            icon.addPixmap(QPixmap(":/Icons/play.png"), QIcon.Normal, QIcon.Off)
            self.actionPlay.setIcon(icon)  # set the icon to a pause button
            self.stop_slideshowTimer()
            self.is_playing = False

        else:  # if it's not playing, play it
            self.beep()
            icon.addPixmap(QPixmap(":/Icons/pause.png"), QIcon.Normal, QIcon.Off)
            self.actionPlay.setIcon(icon)  # set the icon to a play button
            self.next_image()
            self.start_slideshowTimer()
            self.is_playing = True

    def update_image(self, size=None, factor=1):
        """
        Updates the imageLabel with the current image from self.step.
        Scale the image to size, if included.
        Use the factor for zooming.
        """
        if self.all_files and self.step < len(self.all_files):
            self.drawImage.draw_image(self.all_files[self.step])
            self.update_status_bar(self.all_files)

    def next_image(self):
        """
        Called when the next image is clicked. Increments self.step and calls update_image.
        """
        if not self.step + 1 > len(self.all_files):  # if we go through all files go back to start
            self.step += 1
        else:
            self.step = 0

        self.timeElapsedTimer.set_time_to_zero()
        self.imageOptions.set_flip_options()
        self.update_timerLabel()
        self.update_image()

        if self.sound and self.is_playing:  # if the slide show is playing and the sound is on (called by timer timeout)
            self.beep()

    def previous_image(self):
        """
        Called when the previous image is clicked. Decrements self.step and calls update_image.
        """
        if not abs(self.step) + 1 > len(self.all_files):
            self.step -= 1
        else:
            self.step = 0

        self.timeElapsedTimer.set_time_to_zero()  # reset timer back to 0
        self.imageOptions.set_flip_options()
        self.update_timerLabel()  # immediately update
        self.update_image()

    def scale_image(self, width=0, height=0, factor=1):
        """
        Scale the image so if it is too big resize it. Takes a pixmap as an argument.
        Scale to width and height.
        """
        if width > 0 and height > 0:
            return self.pix_image.scaled(width * factor, height * factor,
                                         Qt.KeepAspectRatio,
                                         Qt.SmoothTransformation)
        else:
            return self.pix_image.scaled(self.imageLabel.width() * factor,
                                         self.imageLabel.height() * factor,
                                         Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def update_status_bar(self, image_list):
        """
        Update the status bar with the image title and file location.
        """
        self.statusBar.showMessage("{0}".format(image_list[self.step], self.step, len(image_list)))

    def set_slide_speed(self):
        """
        Set the slideshow speed by opening a inputdialog.
        """
        slide_speed = QInputDialog()
        self.slide_speed = slide_speed.getInt(self, "Slideshow speed",
                                              "Enter slideshow speed (seconds): ",
                                               value=30, minValue=1)[0]
        # return type: (int, bool)

    def shuffle_list(self):
        """
        Shuffle the current list of images. Also initialize the settings again.
        Show a warning, if the user tries to click to early.
        """
        self.step = 0
        self.all_files = random.sample(self.all_files, len(self.all_files))  # create a shuffled new list

    def toggle_fullscreen(self):
        """
        Toggles fullscreen mode (F11). If already in fullscreen, first scale the image to the given size
        remembered from before entering fullscreen mode. The same goes for resizing the geometry back to
        default.
        Set the color and remove the menubar, except the control buttons.
        """
        icon = QIcon()
        if self.isFullScreen():  # go back to normal
            icon.addPixmap(QPixmap(":/Icons/fullscreen.png"), QIcon.Normal, QIcon.Off)  # change icon
            self.actionFullscreen.setIcon(icon)

            self.update_image(size=self.image_view_dimensions)
            self.showNormal()
            self.setGeometry(self.window_dimensions)
            self.setPalette(self.default_palette)  # set background to the default color

        else:  # go to fullscreen
            icon.addPixmap(QPixmap(":/Icons/closefullscreen.png"), QIcon.Normal, QIcon.Off)  # change icon
            self.actionFullscreen.setIcon(icon)

            self.window_dimensions = self.geometry()  # save current window settings
            self.image_view_dimensions = self.graphicsView.width(), self.graphicsView.height()
            self.showFullScreen()

            palette = QPalette()
            palette.setColor(self.backgroundRole(), Qt.black)  # set background to black
            self.setPalette(palette)
            self.update_image()  # update the image to fit the fullscreen mode

    def toggle_sound(self):
        """
        Toggle whether there should be a beep during a slideshow.
        """
        icon = QIcon()
        if self.sound:  # sound is on and you stop it
            self.sound = False
            icon.addPixmap(QPixmap(":/Icons/soundoff.png"), QIcon.Normal, QIcon.Off)
            self.actionSound.setIcon(icon)
        else:  # sound is not on and you put it on
            self.sound = True
            icon.addPixmap(QPixmap(":/Icons/soundon.png"), QIcon.Normal, QIcon.Off)
            self.actionSound.setIcon(icon)

    def toggle_label_timer(self):
        """
        Toggle whether the timerLabel should be displayed.
        """
        if self.timer_visible:
            self.timeElapsedTimer.set_time_to_zero()
            self.timer_visible = False
            self.actionTimerLabel.setVisible(False)
            self.update_timerLabel()
        else:
            self.actionTimerLabel.setVisible(True)
            self.timer_visible = True
            self.timeElapsedTimer.set_time_to_zero()
            self.update_timerLabel()  # for responsiveness
            self.timeElapsedTimer.start()

    def toggle_bars(self):
        """
        Toggle bars - right click menu, action. Toggle toolbar and
        statusbar visibility.
        """
        if self.bars_displayed:
            self.toolBar.hide()
            self.statusBar.hide()
            self.bars_displayed = False
        else:
            self.toolBar.show()
            self.statusBar.show()
            self.bars_displayed = True

    def flip_upside_down(self):
        pix = self.imageOptions.flip_upside_down_pix(self.pix_image)
        self.imageLabel.setPixmap(pix)

    def flip(self):
        pix = self.imageOptions.flip_pix(self.pix_image)
        self.imageLabel.setPixmap(pix)

    def rotate_right(self):
        pix = self.imageOptions.rotate_right_pix(self.pix_image)
        self.imageLabel.setPixmap(pix)

    def rotate_left(self):
        pix = self.imageOptions.rotate_left_pix(self.pix_image)
        self.imageLabel.setPixmap(pix)

    def normal_fit(self):
        pass

    def start_slideshowTimer(self):
        self.slideshowTimer.start(self.slide_speed * 1000)  # ms to s

    def stop_slideshowTimer(self):
        self.slideshowTimer.stop()

    def zoom_in(self):
        self.update_image(factor=1.2)

    def zoom_out(self):
        self.update_image(factor=0.8)

    def beep(self):
        """
        Beep sound.
        """
        beep = QSound("beep.wav")
        beep.play()

    def update_timerLabel(self):
        """
        Update the timerLabel's contents.
        """
        if self.timer_visible:
            self.timerLabel.setText("{0:02.0f}:{1:02.0f}:{2:02.0f}".format(
                                    self.timeElapsedTimer.hours,
                                    self.timeElapsedTimer.mins,
                                    self.timeElapsedTimer.secs))  # no remainder shown

    def show_stats(self):
        """
        Show stats (app run time).
        Ran with CTRL+L
        """
        # divmod = divide and modulo -- divmod(1200 / 1000)  =  (1, 200)
        # [0] = division, [1] = remainder(modulo)
        secs, ms = divmod(self.totalTimeElapsed.elapsed(), 1000)  # ms to s
        mins, secs = divmod(secs, 60)  # s to min
        hours, mins = divmod(mins, 60)  # min to h

        QMessageBox.information(self, 'Stats', 'Total time in app: {0:02.0f} hours '
                                               '{1:02.0f} minutes and {2:02.0f} seconds'.format(
                                                hours, mins, secs))

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        self.setActionOptions.add_to_context_menu(menu)
        menu.exec_(event.globalPos())  # show menu at mouse position

    def wheelEvent(self, event):
        if event.delta() > 0:  # mouse wheel away = zoom in
            self.zoom_in()
        elif event.delta() < 0:
            self.zoom_out()

    def resizeEvent(self, event):
        """
        Resize the image as you resize the window.
        (Function override)
        """
        self.update_image()

    def closeEvent(self, event):
        self.timeElapsedTimer.exit = True  # safe thread exit
        event.accept()  # close app


class TimeElapsedThread(QThread):
    """
    Thread for continuous time tracking.
    Emits a secElapsed signal after each second.
    """

    secElapsed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.set_time_to_zero()
        self.exit = False  # for safe exiting  -  not stuck in while loop

    def run(self):
        timer = QElapsedTimer()
        timer.start()

        while not self.exit:
            if timer.hasExpired(1000):  # 1 seconds expired
                self.secs_elapsed += 1  # secs_elapsed instead of secs because secs is recalculated
                self.set_time_elapsed()  # don't calculate from ms because we always restart the timer
                self.secElapsed.emit()
                timer.restart()

    def set_time_elapsed(self):
        """
        Calculate elapsed hours, minutes, seconds.
        """
        # divmod = divide and modulo -- divmod(1200 / 1000)  =  (1, 200)
        # [0] = division, [1] = remainder(modulo)
        self.mins, self.secs = divmod(self.secs_elapsed, 60)  # s to min
        self.hours, self.mins = divmod(self.mins, 60)  # min to h

    def set_time_to_zero(self):
        self.secs_elapsed, self.secs, self.mins, self.hours = 0, 0, 0, 0


class SetActionOptions():
    def __init__(self, MainWindow):
        self.MW = MainWindow

    def add_actions(self):
        self.MW.addAction(self.MW.actionSpeed)
        self.MW.addAction(self.MW.actionOpen)
        self.MW.addAction(self.MW.actionFullscreen)
        self.MW.addAction(self.MW.actionPrevious)
        self.MW.addAction(self.MW.actionPlay)
        self.MW.addAction(self.MW.actionNext)
        self.MW.addAction(self.MW.actionShuffle)
        self.MW.addAction(self.MW.actionSound)
        self.MW.addAction(self.MW.actionTimer)

    def create_actions(self):
        self.MW.actionStats = QAction("Run time", self.MW,
                statusTip="Show app run time", triggered=self.MW.show_stats)
        self.MW.actionBars = QAction("Hide/Show toolbar and statusbar", self.MW,
                statusTip="Hide/show toolbar and statusbar", triggered=self.MW.toggle_bars)

        self.MW.actionFlipUpDown = QAction("Flip upside down", self.MW,
                statusTip="Flip image upside down", triggered=self.MW.flip_upside_down,
                enabled=False)
        self.MW.actionFlip = QAction("Flip image", self.MW,
                statusTip="Flip image", triggered=self.MW.flip, enabled=False)
        self.MW.actionRotateRight = QAction("Rotate image right", self.MW,
                statusTip="Rotate image by 90° to the right", triggered=self.MW.rotate_right,
                enabled=False)
        self.MW.actionRotateLeft = QAction("Rotate image left", self.MW,
                statusTip="Rotate image by 90° to the left", triggered=self.MW.rotate_left,
                enabled=False)

    def enable_actions(self):
        self.MW.actionPlay.setEnabled(True)
        self.MW.actionNext.setEnabled(True)
        self.MW.actionPrevious.setEnabled(True)
        self.MW.actionShuffle.setEnabled(True)
        self.MW.actionSound.setEnabled(True)
        self.MW.actionTimer.setEnabled(True)
        self.MW.actionFlip.setEnabled(True)
        self.MW.actionFlipUpDown.setEnabled(True)
        self.MW.actionRotateRight.setEnabled(True)
        self.MW.actionRotateLeft.setEnabled(True)

    def add_to_context_menu(self, menu):
        menu.addAction(self.MW.actionOpen)
        menu.addAction(self.MW.actionSpeed)
        menu.addAction(self.MW.actionFullscreen)
        menu.addSeparator()

        menu.addAction(self.MW.actionPrevious)
        menu.addAction(self.MW.actionPlay)
        menu.addAction(self.MW.actionNext)
        menu.addSeparator()

        menu.addAction(self.MW.actionShuffle)
        menu.addAction(self.MW.actionSound)
        menu.addAction(self.MW.actionTimer)
        menu.addSeparator()

        menu.addAction(self.MW.actionStats)
        menu.addAction(self.MW.actionFlipUpDown)
        menu.addAction(self.MW.actionFlip)
        menu.addAction(self.MW.actionRotateRight)
        menu.addAction(self.MW.actionRotateLeft)
        menu.addAction(self.MW.actionBars)


class ImageOptions():
    def __init__(self):
        self.set_flip_options()

    def flip_upside_down_pix(self, pix_image):
        if not self.flipped_upside_down:
            transform = QTransform().rotate(180, Qt.XAxis)
            self.flipped_upside_down = True
        else:
            transform = QTransform().rotate(0, Qt.XAxis)
            self.flipped_upside_down = False

        return pix_image.transformed(transform, mode=Qt.SmoothTransformation)

    def flip_pix(self, pix_image):
        if not self.flipped:
            transform = QTransform().rotate(180, Qt.YAxis)  # flip
            self.flipped = True  # change settings for next image
        else:
            transform = QTransform().rotate(0, Qt.YAxis)  # revert back to normal
            self.flipped = False

        return pix_image.transformed(transform, mode=Qt.SmoothTransformation)  # apply transform

    def rotate_right_pix(self, pix_image):
        transform = QTransform().rotate(90)
        return pix_image.transformed(transform, mode=Qt.SmoothTransformation)

    def rotate_left_pix(self, pix_image):
        transform = QTransform().rotate(270)
        return pix_image.transformed(transform, mode=Qt.SmoothTransformation)

    def normal_fit(self, pix_image):
        pass

    def set_flip_options(self):
        self.flipped = False
        self.flipped_upside_down = False


class DrawImage():
    def __init__(self, MainWindow, graphicsView):
        self.MW = MainWindow
        self.image_scene = QGraphicsScene()
        self.image_view = graphicsView
        self.pix_item = QGraphicsPixmapItem()
        self.pix_item.setTransformationMode(Qt.SmoothTransformation)  # make it smooooth

        self.image_scene.addItem(self.pix_item)  # add pixmap to scene
        self.image_view.setScene(self.image_scene)  # apply scene to view
        self.image_view.show()  # show image

    def draw_image(self, image, size=None, factor=1):
        pix_image = QPixmap(image)  # make pixmap
        self.pix_item.setPixmap(pix_image)
        self.image_scene.setSceneRect(QRectF(0.0, 0.0, pix_image.width(), pix_image.height()))  # update the rect so it isn't retarded like by default
        self.image_view.fitInView(self.image_scene.itemsBoundingRect(), Qt.KeepAspectRatio)  # scale image

    def scale_image(self, pix_image, width=0, height=0, factor=1):
        """
        Scale the image so if it is too big resize it. Takes a pixmap as an argument.
        Scale to width and height.
        """
        return pix_image.scaled(width * factor, height * factor, Qt.KeepAspectRatio, Qt.SmoothTransformation)


if __name__ == '__main__':
    # fix, so the app shows the correct icon in the taskbar
    myappid = 'Marko.Poseviewer.python.1'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    app = QApplication(sys.argv)
    form = MainWindow()
    form.show()
    app.exec_()
