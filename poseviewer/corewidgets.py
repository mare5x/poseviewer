from PySide.QtCore import *
from PySide.QtGui import *
import os
import scandir
import random
from .imageloader import *


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


def secs_from_qtime(qtime):
    return (qtime.hour() * 3600) + (qtime.minute() * 60) + qtime.second() + (qtime.msec() / 1000)


class Settings(QSettings):
    def __init__(self, *args, parent=None, **kwargs):
        super().__init__(*args, parent=parent, **kwargs)

    def __getitem__(self, key):
        return self.value(key)

    def __setitem__(self, key, value):
        self.setValue(key, value)


class ImagePath(QObject):
    imageChanged = Signal(str)
    sequenceChanged = Signal()

    UNDO_SHUFFLE_LIMIT = 10
    UNDO_RANDOM_LIMIT = 50

    def __init__(self, parent=None):
        super().__init__(parent)

        self.current_index = 0
        self.undo_random_index = -1
        self.undo_shuffle_index = -1
        self.previous_random_storage = []
        self.previous_shuffle_storage = []
        self._sequence = []
        self.current_image_path = ""

        self.image_loader_thread = ImageLoaderThread(sequence=self._sequence)

    def next(self):
        if self.current_index + 1 >= len(self.sequence):  # if we go through all files go back to start
            self.current_index = 0
        else:
            self.current_index += 1

        self.current = self.sequence[self.current_index]

    def prev(self):
        if not abs(self.current_index) + 1 >= len(self.sequence):
            self.current_index -= 1
        else:
            self.current_index = 0

        self.current = self.sequence[self.current_index]

    def shuffle(self):
        if len(self.previous_shuffle_storage) > self.UNDO_SHUFFLE_LIMIT:
            self.previous_shuffle_storage.pop(0)
        self.previous_shuffle_storage.append((self.sequence, self.current_index))
        self.undo_shuffle_index = -1
        self.current_index = 0
        self.sequence = random.sample(self.sequence, len(self.sequence))

    def previous_shuffle(self):
        if abs(self.undo_shuffle_index) <= len(self.previous_shuffle_storage):
            self.sequence, self.current_index = self.previous_shuffle_storage[self.undo_shuffle_index]
            self.undo_shuffle_index -= 1

        if self.undo_shuffle_index < -(self.UNDO_SHUFFLE_LIMIT - 1):
            self.undo_shuffle_index = -(self.UNDO_SHUFFLE_LIMIT - 1)

        self.current = self.sequence[self.current_index]

    def random(self):
        if len(self.previous_random_storage) > self.UNDO_RANDOM_LIMIT:
            self.previous_random_storage.pop(0)

        self.previous_random_storage.append(self.current)
        self.current = random.choice(self.sequence)
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
        if value != self.current:
            QTimer.singleShot(0, lambda: self.imageChanged.emit(self.current))

        self.current_image_path = value

    @property
    def sequence(self):
        return self._sequence

    @sequence.setter
    def sequence(self, value):
        self.set_sequence(value)

    def set_sequence(self, value):
        if value != self.sequence:
            QTimer.singleShot(0, self.sequenceChanged.emit)

        stop_thread(self.image_loader_thread)

        if type(value) == str and os.path.isdir(value):
            self._sequence = []
            self.image_loader_thread = load_dir_threaded(value, self._sequence)
        elif type(value) == str:
            self._sequence = [str]
        else:
            self._sequence = value
        self.current_index = 0
        if len(self._sequence) > 0:
            self.current = self.sequence[self.current_index]

    #def append_dir(self, dir_path):
    #    dir_path = os.path.abspath(dir_path)
    #    for path in scandir.listdir(dir_path):
    #        path = os.path.join(dir_path, path)
    #        if path.endswith(SUPPORTED_FORMATS_EXTENSIONS) and path not in self._sequence:
    #            self._sequence.append(path)


    #    #return [os.path.abspath(os.path.join(path, img)) for img in scandir.listdir(path)
    #    #        if os.path.isfile(os.path.join(path, img))]


class TimeElapsedTimer(QObject):
    """
    Thread for continuous time tracking.
    Emits a secElapsed signal after each second.
    """

    secElapsed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.secs_elapsed = 0

        self.timer = QTimer(self, interval=1000)
        self.timer.timeout.connect(self.update_time)

    def start(self):
        self.timer.start()

    def update_time(self):
        self.secs_elapsed += 1
        QTimer.singleShot(0, self.secElapsed.emit)

    def get_time_elapsed(self):
        """
        Calculate elapsed hours, minutes, seconds.
        """
        return get_time_from_secs(self.secs_elapsed)

    def set_time_to_zero(self):
        self.secs_elapsed = 0
