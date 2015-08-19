import threading
import os
import scandir


SUPPORTED_FORMATS_EXTENSIONS = (".bmp", ".gif", ".jpg", ".jpeg", ".png", ".pbm", ".pgm", ".ppm", ".xbm", ".xpm")


class ImageLoaderThread(threading.Thread):
    def __init__(self, *args, sequence=None, dir_path=None, **kwargs):
        super().__init__(*args, **kwargs)

        self._stop_event = threading.Event()
        self._first_image_ready = threading.Event()

        self.dir_path = dir_path
        self.sequence = sequence  # this is a reference to the original

    def run(self):
        if type(self.dir_path) == list:  # we got a list of paths
            for path in self.dir_path:
                if os.path.isdir(path):
                    self.load_dir(path)
                else:
                    self.append_and_notify(os.path.abspath(path))
        elif os.path.isfile(self.dir_path):
            self.append_and_notify(os.path.abspath(self.dir_path))
        else:                            # we got only a single path
            self.load_dir(self.dir_path)

    def load_dir(self, dir_path):
        dir_path = os.path.abspath(dir_path)
        for path in scandir.listdir(dir_path):
            if self.stopped():
                return

            path = os.path.join(dir_path, path)
            if path.lower().endswith(SUPPORTED_FORMATS_EXTENSIONS) and path not in self.sequence:
                self.append_and_notify(path)

    def append_and_notify(self, path):
        self.sequence.append(path)
        if not self._first_image_ready.is_set():
            self._first_image_ready.set()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()


def load_dir_threaded(path, sequence):
    image_loader_thread = ImageLoaderThread(sequence=sequence, dir_path=path, daemon=True)
    image_loader_thread.start()
    image_loader_thread._first_image_ready.wait()
    return image_loader_thread


def stop_thread(thread):
    if thread.is_alive():
        thread.stop()
        thread.join()
