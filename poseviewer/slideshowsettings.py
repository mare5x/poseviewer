from PySide.QtCore import *
from PySide.QtGui import *

from .ui.slideshowsettingsui import Ui_Dialog as SlideshowSettingsUi
from .corewidgets import get_time_from_secs
from .tables import *


class SlideshowSettings(QDialog, SlideshowSettingsUi):
    slideshowComplete = Signal()
    incrementIntervalChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)  # SlideshowSettingsUi

        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)  # removes question mark

        self.speed_spinner.valueChanged.connect(self.get_speed)
        self.speed_spinner.valueChanged.connect(self.update_slideshow_information_labels)

        self.increment_interval_spinner.valueChanged.connect(self.get_increment_speed)
        self.increment_interval_spinner.valueChanged.connect(self.update_slideshow_information_labels)

        self.slideshowComplete.connect(self.reset_settings)

        self.images_time_table.totalTimeChanged.connect(lambda: self.images_total_time_label.setText(self.images_time_table.get_total_time_string()))

        self._speed = self.get_speed()
        self.slideshow_counter = 1  # current index of slideshow
        self.increment_interval = self.increment_interval_spinner.value()  # change speed length speed (by images)

    def get_speed(self):
        self._speed = self.speed_spinner.value()
        return self._speed

    def get_increment_speed(self):
        self.increment_interval = self.increment_interval_spinner.value()

    def increment_speed(self):
        if self.increment_interval == 0:
            QTimer.singleShot(0, self.slideshowComplete.emit)
        elif self.slideshow_counter >= self.increment_interval and self.increment_interval != 0:
            self._speed = self.speed_spinner.value() * 2 ** ((self.increment_interval_spinner.value() - self.slideshow_counter) + 1)
            self.slideshow_counter = 1
            self.increment_interval -= 1
            QTimer.singleShot(0, self.incrementIntervalChanged.emit)
        else:
            self.slideshow_counter += 1

        return self._speed

    def reset_settings(self):
        self._speed = self.speed_spinner.value()
        self.slideshow_counter = 1
        self.increment_interval = self.increment_interval_spinner.value()

    def calculate_slideshow_time_left(self):
        total = 0
        if self.increment_interval > 1:
            total = 0
        elif self.increment_interval == 0:
            total = self.speed_spinner.value() * 2 ** self.increment_interval_spinner.value()
        elif self.increment_interval == 1 and self.increment_interval_spinner.value() > 1:
            total = self.speed_spinner.value() * 2 ** (self.increment_interval_spinner.value() - 1)
        else:
            total = self.speed_spinner.value()

        for i in range(1, self.increment_interval + 1):
            total += i * (self.speed_spinner.value() * 2 ** ((self.increment_interval_spinner.value() - i) + 1))
        return total

    def calculate_total_images(self):
        return sum([i if i > 0 else 1 for i in range(self.increment_interval_spinner.value() + 1)])

    def update_slideshow_information_labels(self):
        self.slideshow_time_left_label.setText((get_time_from_secs(self.calculate_slideshow_time_left())))
        self.total_images_label.setText(str(self.calculate_total_images()))

    def get_transition_speed(self):
        return self.transition_speed_spinner.value()

    def run(self):
        self.update_slideshow_information_labels()
        return self.exec_()


class Slideshow:
    def __init__(self):
        pass

