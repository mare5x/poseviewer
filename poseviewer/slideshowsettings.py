from PySide.QtCore import *
from PySide.QtGui import *

from .ui.slideshowsettingsui import Ui_Dialog as SlideshowSettingsUi
from .corewidgets import format_secs, secs_from_qtime
from .tables import *


class SlideshowSettings(QDialog, SlideshowSettingsUi):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)  # SlideshowSettingsUi

        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)  # removes question mark

        self.base_speed_timeedit.timeChanged.connect(self.update_speed)
        self.base_speed_timeedit.timeChanged.connect(self.update_slideshow_information_labels)

        self.increment_interval_spinner.valueChanged.connect(self.get_increment_speed)
        self.increment_interval_spinner.valueChanged.connect(self.update_slideshow_information_labels)

        self.images_time_table.totalTimeChanged.connect(lambda: self.images_total_time_label.setText(self.images_time_table.get_total_time_string()))

        self.speed = self.get_base_speed()
        self.slideshow_counter = 1  # current index of slideshow
        self.increment_interval = self.increment_interval_spinner.value()  # change speed length speed (by images)

    def get_base_speed(self):
        return secs_from_qtime(self.base_speed_timeedit.time())

    def update_speed_slot(self):
        self.speed = self.get_base_speed()

    def get_increment_speed(self):
        self.increment_interval = self.increment_interval_spinner.value()

    def increment_speed(self):
        if self.increment_interval == 0:
            QTimer.singleShot(0, self.slideshowComplete.emit)
        elif self.slideshow_counter >= self.increment_interval and self.increment_interval != 0:
            self.speed = self.get_base_speed() * 2 ** ((self.increment_interval_spinner.value() - self.slideshow_counter) + 1)
            self.slideshow_counter = 1
            self.increment_interval -= 1
            QTimer.singleShot(0, self.incrementIntervalChanged.emit)
        else:
            self.slideshow_counter += 1

        return self.speed

    def reset_settings(self):
        self.speed = self.get_base_speed()
        self.slideshow_counter = 1
        self.increment_interval = self.increment_interval_spinner.value()

    def calculate_slideshow_time_left(self):
        total = 0
        if self.increment_interval > 1:
            total = 0
        elif self.increment_interval == 0:
            total = self.get_base_speed() * 2 ** self.increment_interval_spinner.value()
        elif self.increment_interval == 1 and self.increment_interval_spinner.value() > 1:
            total = self.get_base_speed() * 2 ** (self.increment_interval_spinner.value() - 1)
        else:
            total = self.get_base_speed()

        for i in range(1, self.increment_interval + 1):
            total += i * (self.get_base_speed() * 2 ** ((self.increment_interval_spinner.value() - i) + 1))
        return total

    def calculate_total_images(self):
        return sum([i if i > 0 else 1 for i in range(self.increment_interval_spinner.value() + 1)])

    def update_slideshow_information_labels(self):
        self.increment_time_left_label.setText((format_secs(self.calculate_slideshow_time_left())))
        self.increment_total_images_label.setText(str(self.calculate_total_images()))

    def get_transition_speed(self):
        return self.transition_speed_spinner.value()

    def run(self):
        self.update_slideshow_information_labels()
        return self.exec_()


class Slideshow(QObject):
    slideshowComplete = Signal()
    incrementIntervalChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.slideshow_settings = SlideshowSettings(self)
        self.incremental_slideshow = IncrementalSlideshow(self.slideshow_settings)

        self.slideshowComplete.connect(self.reset_settings)

        self.slideshow_time_left = 0
        self.slideshow_active = False  # is the slideshow playing

        self.slideshow_timer = QTimer(self, singleShot=True)  # make a timer ready to be used
        self.slideshow_timer_elapsed = QTime()
        self.slideshow_timer.timeout.connect(self.next_image)  # every slide_speed seconds show image
        self.slideshow_timer.timeout.connect(self.slideshow_timer_elapsed.restart)

    def start_slideshow_timer(self, speed=0):
        if speed:
            self.slideshow_timer.start(speed)
        else:
            self.slideshow_timer.start(self.slideshow_settings.get_base_speed() * 1000)  # ms to s

    def pause(self):
        if self.actionPause.isChecked() and self.slideshow_active:
            self.slideshow_time_left = self.slideshow_timer.interval() - self.slideshow_timer_elapsed.elapsed()
            self.slideshow_timer.stop()
            self.slideshow_active = False
        else:
            QTimer.singleShot(self.slideshow_time_left, self.next_image)
            QTimer.singleShot(self.slideshow_time_left, self.slideshow_timer.start)
            self.slideshow_active = True

    def is_active(self):
        return self.slideshow_active

    def next(self):
        if self.slideshow_settings.increment_speed_checkbox.isChecked() and self.slideshow_active:
            self.start_slideshow_timer(self.slideshow_settings.increment_speed() * 1000)
        elif self.slideshow_active:
            self.slideshow_timer.start()

    def toggle(self):
        if self.is_active():  # if it's playing, stop it
            self.slideshow_timer.stop()
        else:  # if it's not playing, play it
            self.slideshow_settings.reset_settings()
            self.slideshow_timer_elapsed.start()
            self.start_slideshow_timer()

        self.slideshow_active = not self.slideshow_active

    def format_change_message(self):
        msg = "Turning it up to {}".format(format_secs(self.slideshow_settings.speed))
        if self.slideshow_settings.increment_speed_checkbox.isChecked():
            msg += " for {} images!\nTime left in slideshow: {}".format(1 if self.slideshow_settings.increment_interval == 0 else self.slideshow_settings.increment_interval,
                                                                        format_secs(self.slideshow_settings.calculate_slideshow_time_left()))


class IncrementalSlideshow:
    def __init__(self, slideshowsettings, parent=None):
        pass




# move slideshow stuff into Slideshow class and have that emit signals for slideshows not slideshowsettings
