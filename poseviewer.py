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
        self.slideshow_timer = QTimer()  # make a timer ready to be used
        self.label_timer = QTimer()  # label timer

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.imageLabel)
        self.scroll_area.setWidgetResizable(True)  # fit to window
        self.setCentralWidget(self.scroll_area)

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
        self.actionOptions.triggered.connect(self.set_slide_speed)  # set slide show speed
        self.actionTimer.triggered.connect(self.toggle_label_timer)  # toggle timer display

        self.label_timer.timeout.connect(self.update_timerLabel)  # update the timer label every second
        self.slideshow_timer.timeout.connect(self.next_image)  # every slide_speed seconds show image

        self.step = 0  # go through all files
        self.is_playing = False  # is the slideshow playing
        self.sound = True  # is the sound turned on
        self.slide_speed = 0
        self.timer_visible = False
        self.elapsed_time = 0

        self.window_dimensions = self.geometry()  # remember the geometry for returning from fullscreen
        self.imageLabel_dimensions = self.imageLabel.width(), self.imageLabel.height()  # scale the label from fullscreen
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

        self.actionPlay.setEnabled(True)
        self.actionNext.setEnabled(True)
        self.actionPrevious.setEnabled(True)
        self.actionShuffle.setEnabled(True)
        self.actionSound.setEnabled(True)
        self.actionTimer.setEnabled(True)

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
            self.stop_slideshow_timer()
            self.is_playing = False

        else:  # if it's not playing, play it
            self.beep()
            icon.addPixmap(QPixmap(":/Icons/pause.png"), QIcon.Normal, QIcon.Off)
            self.actionPlay.setIcon(icon)  # set the icon to a play button
            self.next_image()
            self.start_slideshow_timer()
            self.is_playing = True

    def update_image(self, size=None, factor=1):
        """
        Updates the imageLabel with the current image from self.step.
        Scale the image to size, if included.
        Use the factor for zooming.
        """
        if self.all_files and self.step < len(self.all_files):
            image = QPixmap(self.all_files[self.step])
            if size is not None:
                image = self.scale_image(image, width=size[0] * factor, height=size[1] * factor)
            else:
                image = self.scale_image(image, factor=factor)
            self.imageLabel.setPixmap(image)
            self.update_status_bar(self.all_files)

    def next_image(self):
        """
        Called when the next image is clicked. Increments self.step and calls update_image.
        """
        self.step += 1
        self.elapsed_time = 0
        self.update_image()

        if self.sound and self.is_playing:  # if the slide show is playing and the sound is on (called by timer timeout)
            self.beep()

    def previous_image(self):
        """
        Called when the previous image is clicked. Decrements self.step and calls update_image.
        """
        self.step -= 1
        self.elapsed_time = 0
        self.update_image()

    def scale_image(self, pix, width=0, height=0, factor=1):
        """
        Scale the image so if it is too big resize it. Takes a pixmap as an argument.
        Scale to width and height.
        """
        if width > 0 and height > 0:
            return pix.scaled(width * factor, height * factor, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        else:
            return pix.scaled(self.imageLabel.width() * factor,
                              self.imageLabel.height() * factor,
                              Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def update_status_bar(self, image_list):
        """
        Update the status bar with the image title and file location.
        """
        self.statusBar.showMessage("{0}".format(image_list[self.step], self.step, len(image_list)))

    def set_options(self):
        """
        initialize the options, also set step to 0
        """
        self.step = 0

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
        self.set_options()
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

            self.update_image(size=self.imageLabel_dimensions)
            self.showNormal()
            self.setGeometry(self.window_dimensions)
            self.setPalette(self.default_palette)  # set background to the default color

        else:  # go to fullscreen
            icon.addPixmap(QPixmap(":/Icons/closefullscreen.png"), QIcon.Normal, QIcon.Off)  # change icon
            self.actionFullscreen.setIcon(icon)

            self.window_dimensions = self.geometry()  # save current window settings
            self.imageLabel_dimensions = self.imageLabel.width(), self.imageLabel.height()
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
            self.actionTimerLabel.setVisible(False)
            self.timer_visible = False
            self.stop_label_timer()
        else:
            self.actionTimerLabel.setVisible(True)
            self.timer_visible = True
            self.start_label_timer()

    def start_slideshow_timer(self):
        self.slideshow_timer.start(self.slide_speed * 1000)  # ms to s

    def stop_slideshow_timer(self):
        self.slideshow_timer.stop()

    def start_label_timer(self):
        self.label_timer.start(1000)  # timeout signal every second

    def stop_label_timer(self):
        self.label_timer.stop()

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
            self.timerLabel.setText("{0} seconds elapsed".format(self.elapsed_time))
            self.elapsed_time += 1

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

if __name__ == '__main__':
    # fix, so the app shows the correct icon in the taskbar
    myappid = 'Marko.Poseviewer.python.1'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    app = QApplication(sys.argv)
    form = MainWindow()
    form.show()
    app.exec_()
