﻿from PySide.QtCore import *
from PySide.QtGui import *

import os
import scandir

from .tables import *
from .imageloader import *
from .corewidgets import get_time_from_secs
from .ui.slideshowsettingsui import Ui_Dialog as SlideshowSettingsUi


SUPPORTED_FORMATS_FILTER = ["*.BMP", "*.GIF", "*.JPG", "*.JPEG", "*.PNG", "*.PBM", "*.PGM", "*.PPM", "*.XBM", "*.XPM"]


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
        self.setTransformationAnchor(self.NoAnchor)
        self.setResizeAnchor(self.NoAnchor)

        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # disable scroll bars - drag with mouse
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setContextMenuPolicy(Qt.ActionsContextMenu)  # without this the contextmenu doesn't show on qgraphicsscene

        self.imageScene = QGraphicsScene()
        self.pix_item = QGraphicsPixmapItem()
        self.pix_item.setTransformationMode(Qt.SmoothTransformation)  # make it smooooth

        self.movie = QMovie(self)
        self.movie.updated.connect(self.update_gif)

        self.imageScene.addItem(self.pix_item)  # add pixmap to scene
        self.setScene(self.imageScene)  # apply scene to view

        self.image_path = ""

        self.show()  # show image

    def draw_image(self, image_path, size=None):
        self.image_path = image_path
        pix_image = QPixmap(image_path)  # make pixmap
        if pix_image.isNull():
            return

        if size:
            pix_image = pix_image.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.pix_item.setPixmap(pix_image)
        self.setSceneRect(QRectF(0.0, 0.0, pix_image.width(),
                                 pix_image.height()))  # update the rect so it isn't retarded like by default -- center image
        self.fit_in_view()

        if self.image_path.lower().endswith(".gif"):
            self.play_gif(self.image_path, size=size)
        else:
            self.movie.stop()

    def fit_in_view(self):
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)

    def play_gif(self, path, size=None):
        if self.movie.state() == QMovie.Running:
            self.movie.stop()
        self.movie.setFileName(path)
        if size:
            self.movie.setScaledSize(size)
        self.movie.start()

    def update_gif(self):
        self.pix_item.setPixmap(self.movie.currentPixmap())

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

    def mouseDoubleClickEvent(self, event):
        """Double click to pause/unpause the playing gif (if any). """

        if self.movie.state() == QMovie.Running:
            self.movie.setPaused(True)
        elif self.movie.state() == QMovie.Paused:
            self.movie.setPaused(False)
        else:
            event.accept()

    def wheelEvent(self, event):
        """ Zoom using the scroll wheel. """

        old_pos = self.mapToScene(event.pos())

        if event.delta() > 0:  # mouse wheel away = zoom in
            self.scale(self.ZOOM_FACTOR, self.ZOOM_FACTOR)
        else:
            self.scale(1 / self.ZOOM_FACTOR, 1 / self.ZOOM_FACTOR)

        new_pos = self.mapToScene(event.pos())  # translate pos to scene pos
        delta = new_pos - old_pos
        self.translate(delta.x(), delta.y())


class ListImageViewer(QSplitter):
    indexDoubleClicked = Signal(str)
    listImageViewerToggled = Signal()
    starImage = Signal(str, bool)
    setDefaultSequence = Signal(list)

    def __init__(self, parent=None, path=None):
        super().__init__(parent)

        self.string_list_model = QStringListModel()
        self.files_system_model = QFileSystemModel(nameFilterDisables=False)
        self.files_system_model.setNameFilters(SUPPORTED_FORMATS_FILTER)
        self.files_system_model.setRootPath(path)

        self.tree_view = QTreeView(self)
        self.tree_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tree_view.setModel(self.string_list_model)
        self.tree_view.doubleClicked.connect(self.apply_index)

        self.tree_view.currentChanged = self.currentChanged  # subclass currentChanged slot of QTreeView

        self.canvas = ImageCanvas(self)

        self.star_image_button = QPushButton("Star image")
        self.unstar_image_button = QPushButton("Unstar image")
        self.set_default_sequence = QPushButton("Load selected")

        self.button_box = QDialogButtonBox(Qt.Vertical, self, centerButtons=True)
        self.button_box.addButton(self.star_image_button, QDialogButtonBox.ActionRole)
        self.button_box.addButton(self.unstar_image_button, QDialogButtonBox.ActionRole)
        self.button_box.addButton(self.set_default_sequence, QDialogButtonBox.ActionRole)

        self.star_image_button.clicked.connect(lambda: self.starImage.emit(self.canvas.image_path, True))
        self.unstar_image_button.clicked.connect(lambda: self.starImage.emit(self.canvas.image_path, False))
        self.set_default_sequence.clicked.connect(self.load_selected)

        self.setChildrenCollapsible(False)
        self.resize(parent.size())
        self.setSizes([400, 600])

        self.hide()
        self.is_displayed = False
        self.previous_model = self.string_list_model

        self.image_loader_thread = ImageLoaderThread()

    def display(self, path, item=None):
        self.previous_model = self.tree_view.model()
        if type(path) == list:
            self.tree_view.setModel(self.string_list_model)
            self.string_list_model.setStringList(path)
        else:
            self.tree_view.setModel(self.files_system_model)
            self.tree_view.setRootIndex(self.files_system_model.setRootPath(path))

        if item:
            self.find_and_select(item)

        if self.previous_model == self.tree_view.model() or not self.is_displayed:
            self.toggle_display()
            QTimer.singleShot(0, self.listImageViewerToggled.emit)  # waits for widget to show/hide before emitting

    def toggle_display(self):
        self.is_displayed = not self.is_displayed
        self.setVisible(self.is_displayed)
        self.setFocus(Qt.ActiveWindowFocusReason)

    def find_and_select(self, item):
        found_item = self.find_item_index(item)
        if found_item:
            self.scroll_to_index(found_item)

    def find_item_index(self, path):
        model = self.tree_view.model()
        # print(path)
        if model == self.string_list_model:
            found = model.match(model.index(0, 0), Qt.DisplayRole, path, 1, Qt.MatchRecursive|Qt.MatchWrap|Qt.MatchContains)
            # print(found)
            if found:
                return found[0]
        else:
            found = self.files_system_model.index(path)
            # print(found)
            if found.isValid():
                return found
        return None

    def select_and_scroll_to(self, index):
        self.scroll_to_index(index)
        self.select_index(index)

    def select_index(self, index):
        self.tree_view.selectionModel().select(index, QItemSelectionModel.Select | QItemSelectionModel.Rows)
        self.tree_view.setCurrentIndex(index)

    def scroll_to_index(self, index):
        QTimer.singleShot(0, lambda: self.tree_view.scrollTo(index))

    def currentChanged(self, current, previous):
        """Reimplemented function from QTreeView"""
        self.paint_thumbnail(current)
        self.select_and_scroll_to(current)

    def paint_thumbnail(self, index):
        image_path = self.string_list_model.data(index, 0) if self.tree_view.model() == self.string_list_model \
            else self.files_system_model.filePath(index)
        self.canvas.draw_image(image_path, self.canvas.size())  # scale to canvas size

    def apply_index(self, index):
        self.indexDoubleClicked.emit(self.canvas.image_path)

    def get_selected(self):
        selection = []
        for index in self.tree_view.selectedIndexes():
            if index.column() == 0:
                selection.append(os.path.abspath(self.files_system_model.filePath(index)))
        return selection

    def load_selected(self):
        if self.tree_view.model() == self.files_system_model:
            all_selected = []
            selection = self.get_selected()

            stop_thread(self.image_loader_thread)
            self.image_loader_thread = load_dir_threaded(selection, all_selected)

            QTimer.singleShot(0, lambda: self.setDefaultSequence.emit(all_selected))
        else:
            QTimer.singleShot(0, lambda: self.setDefaultSequence.emit(self.string_list_model.stringList()))


class SlideshowSettings(QDialog, SlideshowSettingsUi):
    slideshowComplete = Signal()
    incrementIntervalChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)  # SlideshowSettingsUi

        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)  # removes question mark

        self.time_edit_table.horizontalHeader().show() # fix bug in designer
        self.time_edit_table.verticalHeader().show()

        self.speed_spinner.valueChanged.connect(self.get_speed)
        self.speed_spinner.valueChanged.connect(self.update_slideshow_information_labels)

        self.increment_interval_spinner.valueChanged.connect(self.get_increment_speed)
        self.increment_interval_spinner.valueChanged.connect(self.update_slideshow_information_labels)

        self.slideshowComplete.connect(self.reset_settings)

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


class NotificationPopupWidget(QLabel):
    notified = Signal()

    def __init__(self, parent=None, position=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.SplashScreen|Qt.WindowStaysOnTopHint|Qt.FramelessWindowHint)
        self.setWindowOpacity(0.65)
        self.setFixedWidth(200)
        self.move(QApplication.desktop().screenGeometry().topRight().x() - self.width() - 20, 20)

        self.setTextFormat(Qt.RichText)
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("border: 2px solid blue; "
                           "padding: 1px; "
                           "background: DeepSkyBlue; "
                           "color: blue; "
                           "font-size: 24px")

        self.close_timer = QTimer(self, singleShot=True)
        self.close_timer.timeout.connect(self.hide)

    def notify(self, msg, duration=3.5):
        self.setText(msg)
        self.adjustSize()
        self.show()
        if duration > 0:
            self.close_timer.start(duration * 1000)
        else:
            self.close_timer.stop()

        self.notified.emit()

    def mousePressEvent(self, event):
        self.hide()