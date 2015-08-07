from PySide.QtCore import *
from PySide.QtGui import *
import os
import scandir
from .imageloader import *


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

        self.imageScene.addItem(self.pix_item)  # add pixmap to scene
        self.setScene(self.imageScene)  # apply scene to view

        self.image_path = ""

        self.show()  # show image

    def draw_image(self, image_path, size=None):
        self.image_path = image_path
        pix_image = QPixmap(image_path)  # make pixmap
        if size:
            pix_image = pix_image.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
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

    def display(self, path):
        self.previous_model = self.tree_view.model()
        if type(path) == list:
            self.tree_view.setModel(self.string_list_model)
            self.string_list_model.setStringList(path)
        else:
            self.tree_view.setModel(self.files_system_model)
            self.tree_view.setRootIndex(self.files_system_model.setRootPath(path))

        if self.previous_model == self.tree_view.model() or not self.is_displayed:
            self.toggle_display()
            QTimer.singleShot(0, self.listImageViewerToggled.emit)  # waits for widget to show/hide before emitting

    def toggle_display(self):
        self.is_displayed = not self.is_displayed
        self.setVisible(self.is_displayed)

    def currentChanged(self, current, previous):
        """Reimplemented function from QTreeView"""
        self.paint_thumbnail(current)
        self.tree_view.scrollTo(current)

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
                #if os.path.isdir(path):
                #    selection.extend([os.path.join(path, p) for p in scandir.listdir(path) if p.endswith(SUPPORTED_FORMATS_EXTENSIONS)
                #                      and os.path.join(path, p) not in selection])
                #else:
                #    selection.append(path)
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


class SlideshowSettings(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Slideshow Settings")
        self.setMinimumSize(300, 150)

        layout = QGridLayout(self)

        speed_label = QLabel("Enter slideshow speed:", self)
        self.speed_spinner = QSpinBox(parent=self, minimum=1, maximum=24*3600, value=30, singleStep=5, suffix=" s")

        self.increment_checkbox = QCheckBox("Increment slideshow speed?", self, checked=False)

        increment = QWidget(self)
        increment_layout = QGridLayout(increment)
        increment_label = QLabel("Enter increment interval:", self)
        self.increment_interval_spinner = QSpinBox(parent=self, minimum=1, value=5)
        increment_layout.addWidget(increment_label, 0, 0)
        increment_layout.addWidget(self.increment_interval_spinner, 0, 1)
        increment.setLayout(increment_layout)
        increment.hide()
        self.increment_checkbox.toggled.connect(lambda: increment.setVisible(not increment.isVisible()))
        self.increment_interval_spinner.valueChanged.connect(self.get_increment_speed)

        layout.addWidget(speed_label, 0, 0)
        layout.addWidget(self.speed_spinner, 0, 1)
        layout.addWidget(self.increment_checkbox)
        layout.addWidget(increment, 2, 0)

        self._speed = 30
        self.increment_index = 0  # current index of slideshow
        self._increment_speed = 0  # change speed length speed (by images)
        self.speed_index = 1

    @property
    def speed(self):
        self._speed = self.speed_spinner.value()
        return self._speed

    @speed.setter
    def speed(self, value):
        self._speed = value

    def get_increment_speed(self):
        self._increment_speed = self.increment_interval_spinner.value()

    def increment_speed(self):
        if self.increment_index >= self._increment_speed:
            self.speed *= 2 ** self.speed_index
            self.increment_index = 0
            self._increment_speed -= 1
            self.speed_index += 1
        else:
            self.increment_index += 1

        return self.speed

    def run(self):
        return self.exec_()

