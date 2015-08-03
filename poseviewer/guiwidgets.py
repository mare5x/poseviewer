from PySide.QtCore import *
from PySide.QtGui import *
import os
import scandir


SUPPORTED_FORMATS_FILTER = ["*.BMP", "*.GIF", "*.JPG", "*.JPEG", "*.PNG", "*.PBM", "*.PGM", "*.PPM", "*.XBM", "*.XPM"]
SUPPORTED_FORMATS_EXTENSIONS = (".bmp", ".gif", ".jpg", ".jpeg", ".png", ".pbm", ".pgm", ".ppm", ".xbm", ".xpm")


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
        self.tree_view.clicked.connect(self.paint_thumbnail)
        self.tree_view.doubleClicked.connect(self.apply_index)

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
                path = os.path.abspath(self.files_system_model.filePath(index))
                if os.path.isdir(path):
                    selection.extend([os.path.join(path, p) for p in scandir.listdir(path) if p.endswith(SUPPORTED_FORMATS_EXTENSIONS)
                                      and os.path.join(path, p) not in selection])
                else:
                    selection.append(path)
        return selection

    def load_selected(self):
        if self.tree_view.model() == self.files_system_model:
            selection = self.get_selected()

            QTimer.singleShot(0, lambda: self.setDefaultSequence.emit(selection))
        else:
            QTimer.singleShot(0, lambda: self.setDefaultSequence.emit(self.string_list_model.stringList()))
