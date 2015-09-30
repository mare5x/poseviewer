from PySide.QtCore import *
from PySide.QtGui import *

import random

from .ui.slideshowsettingsui import Ui_Dialog as SlideshowSettingsUi
from .corewidgets import format_secs, secs_from_qtime, signal_emitter, Settings
from .tables import *


class SlideshowSettings(QDialog, SlideshowSettingsUi):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)  # SlideshowSettingsUi

        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)  # removes question mark

        self.load_settings()

    def base_speed(self):
        return secs_from_qtime(self.base_speed_timeedit.time())

    def transition_speed(self):
        return self.transition_speed_spinner.value()

    def selected_preset(self):
        try:
            return int(self.preset_selector.currentText())
        except ValueError:
            return 0

    def run(self):
        return self.exec_()

    def load_settings(self):
        _settings = Settings()
        with _settings.in_group('settings_ui'):
            self.resize(_settings.value('size', self.size()))
            self.move(_settings.value('pos', self.pos()))
            self.base_speed_timeedit.setTime(_settings.value('base_speed', self.base_speed_timeedit.time()))
            self.transition_speed_spinner.setValue(float(_settings.value('transition_speed', self.transition_speed_spinner.value())))
            self.preset_selector.setCurrentIndex(int(_settings.value('selected_preset', 0)))
            self.total_random_time_edit.setTime(_settings.value('total_random_time_edit', self.total_random_time_edit.time()))

            with _settings.in_group('interval_settings'):
                self.increment_interval_spinner.setValue(int(_settings.value('increment_interval', self.increment_interval_spinner.value())))


    def write_settings(self):
        _settings = Settings()
        with _settings.in_group('settings_ui'):
            general_settings = {
                'size': self.size(),
                'pos': self.pos(),
                'base_speed': self.base_speed_timeedit.time(),
                'transition_speed': self.transition_speed_spinner.value(),
                'selected_preset': self.preset_selector.currentIndex(),
                'total_random_time_edit': self.total_random_time_edit.time()
            }
            _settings.set_values(general_settings)

            with _settings.in_group('interval_settings'):
                interval_settings = {
                    'increment_interval': self.increment_interval_spinner.value()
                }
                _settings.set_values(interval_settings)

    def closeEvent(self, event):
        self.write_settings()
        self.images_time_table.write_settings()
        self.random_time_table.write_settings()
        event.accept()


class BaseSlideshow(QObject):
    slideshowComplete = Signal()
    slideshowNotifyChange = Signal()
    slideshowNext = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)


class Slideshow(BaseSlideshow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings_ui = SlideshowSettings()
        self.settings_ui.preset_selector.currentIndexChanged.connect(self.stop)

        self.incremental_slideshow = IncrementalSlideshow(self.settings_ui)
        self.incremental_slideshow.incrementIntervalChanged.connect(self.slideshowNotifyChange.emit)
        self.incremental_slideshow.slideshowComplete.connect(self.slideshowComplete.emit)
        self.image_time_product_slideshow = ImageTimeProductSlideshow(self.settings_ui)
        self.image_time_product_slideshow.slideshowComplete.connect(self.slideshowComplete.emit)
        self.image_time_product_slideshow.slideshowNotifyChange.connect(self.slideshowNotifyChange.emit)
        self.random_time_slideshow = RandomTimeSlideshow(self.settings_ui)
        self.random_time_slideshow.slideshowComplete.connect(self.slideshowComplete.emit)
        self.random_time_slideshow.slideshowNotifyChange.connect(self.slideshowNotifyChange.emit)

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

    def reset_timer(self):
        if self.timer.isActive():
            self.start_timer(self.timer.interval())

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
        if self.settings_ui.selected_preset() == 0:
            self.start_timer()
        elif self.settings_ui.selected_preset() == 1:
            next_interval = self.incremental_slideshow.increment_speed()
        elif self.settings_ui.selected_preset() == 2:
            next_interval = self.random_time_slideshow.next()
        elif self.settings_ui.selected_preset() == 3:
            next_interval = self.image_time_product_slideshow.next()

        if next_interval:
            self.start_timer(next_interval * 1000)

        if self.slideshow_active:
            QTimer.singleShot(0, self.slideshowNext.emit)

    def start(self):
        if self.settings_ui.selected_preset() == 1:
            self.incremental_slideshow.reset_settings()
        elif self.settings_ui.selected_preset() == 2:
            self.random_time_slideshow.reset_settings()
        elif self.settings_ui.selected_preset() == 3:
            self.image_time_product_slideshow.reset_settings()
        self.next()
        self.timer_elapsed.start()
        self.slideshow_active = True

    def stop(self):
        self.timer.stop()
        self.slideshow_active = False

    def is_active(self):
        return self.slideshow_active

    def speed(self):
        if self.settings_ui.selected_preset() == 0:
            return self.settings_ui.base_speed()
        elif self.settings_ui.selected_preset() == 1:
            return self.incremental_slideshow.speed
        elif self.settings_ui.selected_preset() == 2:
            return self.random_time_slideshow.speed()
        elif self.settings_ui.selected_preset() == 3:
            return self.image_time_product_slideshow.speed()

    def format_notify_message(self):
        if self.settings_ui.selected_preset() == 0:
            return "Turning it up to {}".format(format_secs(self.settings_ui.base_speed()))
        elif self.settings_ui.selected_preset() == 1:
            return self.incremental_slideshow.format_increment_changed_message()
        elif self.settings_ui.selected_preset() == 2:
            return self.random_time_slideshow.format_notify_message()
        elif self.settings_ui.selected_preset() == 3:
            return self.image_time_product_slideshow.format_notify_message()


class IncrementalSlideshow(BaseSlideshow):
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
        self.ui.increment_base_speed_label.setText(self.ui.base_speed_timeedit.time().toString("H:mm:ss"))
        self.ui.increment_time_left_label.setText((format_secs(self.calculate_slideshow_time_left())))
        self.ui.increment_total_images_label.setText(str(self.calculate_total_images()))

    def format_increment_changed_message(self):
        msg = "Turning it up to {}".format(format_secs(self.speed))
        msg += " for {} images!\nTime left in slideshow: {}".format(1 if self.increment_interval == 0 else
                self.increment_interval, format_secs(self.calculate_slideshow_time_left()))
        return msg


class ImageTimeProductSlideshow(BaseSlideshow):
    def __init__(self, ui):
        self.ui = ui
        super().__init__(self.ui)

        self.table = self.ui.images_time_table
        self.table.totalTimeChanged.connect(self.update_images_total_time_label)

        self.slideshowComplete.connect(self.reset_settings)

        self.update_images_total_time_label()

        self.row_index = 0
        self.images_counter = 0

    def update_images_total_time_label(self):
        self.ui.images_total_time_label.setText(self.table.get_total_time_string())

    def next(self):
        if self.row_index < self.table.rows():
            images, secs = self.row_values()
            if self.images_counter < images:
                self.images_counter += 1
                return secs
            else:
                self.row_index += 1
                if self.row_index < self.table.rows():  # if not done
                    self.slideshowNotifyChange.emit()
                self.images_counter = 0
                return self.next()
        else:
            self.reset_settings()
            self.slideshowComplete.emit()

    def row_values(self, row=None):
        if row is None:
            return self.table.get_row_values(self.row_index)
        else:
            return self.table.get_row_values(row)

    def speed(self):
        return self.row_values()[1]

    def time_left(self):
        time_used = 0
        for row in range(self.row_index - 1):
            images, secs = self.row_values(row)
            time_used += images * secs

        if self.row_index > 0:
            current_row_secs = self.row_values(self.row_index)[1]
            time_used += self.images_counter * current_row_secs

        return self.table.calculate_total_time() - time_used

    def reset_settings(self):
        self.row_index = 0
        self.images_counter = 0

    def format_notify_message(self):
        return "Turning it up to {speed} for {images} images!\nTime left in slideshow: {time_left}".format(
                speed=format_secs(self.speed()),
                images=self.row_values()[0],
                time_left=format_secs(self.time_left()))


class RandomTimeSlideshow(BaseSlideshow):
    def __init__(self, settings_ui):
        super().__init__(settings_ui)

        self.ui = settings_ui
        self.table = settings_ui.random_time_table

        self._speed = 0
        self.time_elapsed = 0

    def reset_settings(self):
        self._speed = 0
        self.time_elapsed = 0

    def total_time(self):
        return secs_from_qtime(self.ui.total_random_time_edit.time())

    def time_left(self):
        time_left = self.total_time() - self.time_elapsed
        if time_left <= 0:
            return 0
        return time_left

    def next(self):
        random_row = random.randint(0, self.table.rows() - 1)
        self._speed = self.table.time(random_row)

        if self.time_elapsed >= self.total_time():
            self.slideshowComplete.emit()
            return
        elif self._speed + self.time_elapsed >= self.total_time():
            self._speed = self.total_time() - self.time_elapsed

        self.time_elapsed += self._speed
        signal_emitter(self.slideshowNotifyChange)
        return self._speed

    def speed(self):
        return self._speed

    def format_notify_message(self):
        return "Turning it up to {speed}!\n Time left in slideshow: {time_left}".format(
                speed=format_secs(self.speed()),
                time_left=format_secs(self.time_left()))
