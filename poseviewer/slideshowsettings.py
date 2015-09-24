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

    def base_speed(self):
        return secs_from_qtime(self.base_speed_timeedit.time())

    def transition_speed(self):
        return self.transition_speed_spinner.value()

    def selected_preset(self):
        return int(self.preset_selector.currentText())

    def run(self):
        return self.exec_()


class Slideshow(QObject):
    slideshowComplete = Signal()
    slideshowNotifyChange = Signal()
    slideshowNext = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings_ui = SlideshowSettings()
        self.settings_ui.preset_selector.currentIndexChanged.connect(self.stop)

        self.incremental_slideshow = IncrementalSlideshow(self.settings_ui)
        self.incremental_slideshow.incrementIntervalChanged.connect(self.slideshowNotifyChange.emit)
        self.incremental_slideshow.slideshowComplete.connect(self.slideshowComplete.emit)
        self.image_time_product_slideshow = ImageTimeProductSlideshow(self.settings_ui)

        self.slideshow_time_left = 0
        self.slideshow_active = False  # is the slideshow playing

        self.timer = QTimer(self, singleShot=True)  # make a timer ready to be used
        self.timer_elapsed = QTime()
        self.timer.timeout.connect(self.next)  # every slide_speed seconds show image
        self.timer.timeout.connect(self.timer_elapsed.restart)

    def start_timer(self, speed=0):
        if speed:
            self.timer.start(speed)
        else:
            self.timer.start(self.settings_ui.base_speed() * 1000)  # ms to s

    def pause(self):
        if self.actionPause.isChecked() and self.slideshow_active:
            self.slideshow_time_left = self.timer.interval() - self.timer_elapsed.elapsed()
            self.timer.stop()
            self.slideshow_active = False
        else:
            QTimer.singleShot(self.slideshow_time_left, self.next)
            QTimer.singleShot(self.slideshow_time_left, self.timer.start)
            self.slideshow_active = True

    def next(self):
        if self.settings_ui.selected_preset() == 1:
            if self.settings_ui.increment_speed_checkbox.isChecked():
                self.start_timer(self.incremental_slideshow.increment_speed() * 1000)
            else:
                self.timer.start()

        QTimer.singleShot(0, self.slideshowNext.emit)

    def start(self):
        if not self.is_active():
            if self.settings_ui.selected_preset() == 1:
                self.incremental_slideshow.reset_settings()
                self.timer_elapsed.start()
                self.start_timer()
        self.slideshow_active = True

    def stop(self):
        if self.is_active():
            self.timer.stop()
        self.slideshow_active = False

    def is_active(self):
        return self.slideshow_active

    def speed(self):
        if self.settings_ui.selected_preset() == 1:
            return self.incremental_slideshow.speed

    def format_notify_message(self):
        if self.settings_ui.selected_preset() == 1:
            return self.incremental_slideshow.format_increment_changed_message()


class IncrementalSlideshow(QObject):
    slideshowComplete = Signal()
    incrementIntervalChanged = Signal()

    def __init__(self, ui):
        self.ui = ui
        super().__init__(self.ui)

        self.speed = self.ui.base_speed()
        self.slideshow_counter = 1  # current index of slideshow
        self.increment_interval = self.base_increment_speed()  # change speed length speed (by images)

        self.ui.base_speed_timeedit.timeChanged.connect(self.update_speed_slot)
        self.ui.base_speed_timeedit.timeChanged.connect(self.update_slideshow_information_labels)

        self.ui.increment_interval_spinner.valueChanged.connect(self.set_increment_speed_slot)
        self.ui.increment_interval_spinner.valueChanged.connect(self.update_slideshow_information_labels)

        self.slideshowComplete.connect(self.reset_settings)

        self.update_slideshow_information_labels()

    def update_speed_slot(self):
        self.speed = self.ui.base_speed()

    def set_increment_speed_slot(self):
        self.increment_interval = self.base_increment_speed()

    def base_increment_speed(self):
        return self.ui.increment_interval_spinner.value()

    def increment_speed(self):
        if self.increment_interval == 0:
            QTimer.singleShot(0, self.slideshowComplete.emit)
        elif self.slideshow_counter >= self.increment_interval and self.increment_interval != 0:
            self.speed = self.ui.base_speed() * 2 ** ((self.base_increment_speed() - self.slideshow_counter) + 1)
            self.slideshow_counter = 1
            self.increment_interval -= 1
            QTimer.singleShot(0, self.incrementIntervalChanged.emit)
        else:
            self.slideshow_counter += 1

        return self.speed

    def reset_settings(self):
        self.speed = self.ui.base_speed()
        self.slideshow_counter = 1
        self.increment_interval = self.base_increment_speed()

    def calculate_slideshow_time_left(self):
        total = 0
        if self.increment_interval > 1:
            total = 0
        elif self.increment_interval == 0:
            total = self.ui.base_speed() * 2 ** self.base_increment_speed()
        elif self.increment_interval == 1 and self.base_increment_speed() > 1:
            total = self.ui.base_speed() * 2 ** (self.base_increment_speed() - 1)
        else:
            total = self.ui.base_speed()

        for i in range(1, self.increment_interval + 1):
            total += i * (self.ui.base_speed() * 2 ** ((self.base_increment_speed() - i) + 1))
        return total

    def calculate_total_images(self):
        return sum([i if i > 0 else 1 for i in range(self.base_increment_speed() + 1)])

    def update_slideshow_information_labels(self):
        self.ui.increment_time_left_label.setText((format_secs(self.calculate_slideshow_time_left())))
        self.ui.increment_total_images_label.setText(str(self.calculate_total_images()))

    def format_increment_changed_message(self):
        msg = "Turning it up to {}".format(format_secs(self.speed))
        if self.ui.increment_speed_checkbox.isChecked():
            msg += " for {} images!\nTime left in slideshow: {}".format(1 if self.increment_interval == 0 else
                    self.increment_interval, format_secs(self.calculate_slideshow_time_left()))
        return msg


class ImageTimeProductSlideshow(QObject):
    def __init__(self, ui):
        self.ui = ui
        super().__init__(self.ui)

        self.ui.images_time_table.totalTimeChanged.connect(self.update_images_total_time_label)

        self.update_images_total_time_label()

    def update_images_total_time_label(self):
        self.ui.images_total_time_label.setText(self.ui.images_time_table.get_total_time_string())


# move slideshow stuff into Slideshow class and have that emit signals for slideshows not slideshowsettings
