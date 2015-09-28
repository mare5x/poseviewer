from PySide import QtCore, QtGui
from .corewidgets import secs_from_qtime, format_secs, Settings


class SpinBoxDelegate(QtGui.QStyledItemDelegate):
    def __init__(self, **attributes):
        super().__init__()
        self._widget_attributes = attributes

    def createEditor(self, parent, option, index):
        editor = QtGui.QSpinBox(parent, **self._widget_attributes)
        return editor

    def setEditorData(self, spin_box, index):
        value = index.data(QtCore.Qt.EditRole)
        if value:
            spin_box.setValue(value)
        else:
            spin_box.setValue(self._widget_attributes.get("value", 5))

    def setModelData(self, spin_box, model, index):
        spin_box.interpretText()
        value = spin_box.value()

        model.setData(index, value, QtCore.Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)


class TimeEditDelegate(QtGui.QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        return QtGui.QTimeEdit(parent, time=QtCore.QTime(0, 5), currentSection=QtGui.QDateTimeEdit.MinuteSection,
                               currentSectionIndex=1, displayFormat="hh:mm:ss")

    def setEditorData(self, time_edit, index):
        value = index.data(QtCore.Qt.EditRole)
        time_edit.setTime(QtCore.QTime.fromString(value, "hh:mm:ss"))

    def setModelData(self, time_edit, model, index):
        value = time_edit.time().toString("hh:mm:ss")
        model.setData(index, value, QtCore.Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)


class BaseTable(QtGui.QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi()

        self.verticalHeader().show()
        self.horizontalHeader().show()
        self.resizeColumnsToContents()

    def setupUi(self):
        self.setRowCount(3)
        self.setColumnCount(2)
        self.setHorizontalHeaderItem(0, QtGui.QTableWidgetItem())
        self.horizontalHeaderItem(0).setText("Description")
        self.setHorizontalHeaderItem(1, QtGui.QTableWidgetItem())
        self.horizontalHeaderItem(1).setText("Value")
        self.horizontalHeader().setResizeMode(QtGui.QHeaderView.Stretch)

    def insert_row(self, row=None):
        row = row if row else self.currentRow() + 1
        self.insertRow(row)
        return row

    def remove_row(self, row=None):
        if row:
            return self.removeRow(row)
        return self.removeRow(self.currentRow())


class TotalTimeTable(BaseTable):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.delegate = TimeEditDelegate()
        self.setItemDelegateForColumn(1, self.delegate)

        for row in range(self.rowCount()):
            index = self.model().index(row, 1)
            self.model().setData(index, "00:00:30")

    def insert_row(self):
        row = super().insert_row()
        index = self.model().index(row, 1)
        self.model().setData(index, "00:00:30")


class ImagesTimeTable(BaseTable):
    totalTimeChanged = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.spinbox_delegate = SpinBoxDelegate(suffix=" images", value=5)
        self.timeedit_delegate = TimeEditDelegate()
        self.setItemDelegateForColumn(0, self.spinbox_delegate)
        self.setItemDelegateForColumn(1, self.timeedit_delegate)

        # for row in range(self.rowCount()):
        #     self.model().setData(self.model().index(row, 0), 5)
        #     self.model().setData(self.model().index(row, 1), "00:01:00")

        self.cellChanged.connect(lambda: self.totalTimeChanged.emit())
        self._model = self.model()
        self._model.rowsRemoved.connect(lambda: self.totalTimeChanged.emit())

        self._settings = Settings()
        self.load_settings()

    def insert_row(self):
        """Override BaseTable method."""
        row = super().insert_row()
        self.model().setData(self.model().index(row, 0), 5)
        self.model().setData(self.model().index(row, 1), "00:01:00")

    def calculate_total_time(self):
        total = 0
        for row in range(self.rowCount()):
            item1, item2 = self.get_row_values(row)
            total += item1 * item2

        return total

    def get_total_time_string(self):
        return format_secs(self.calculate_total_time())

    def get_row_values(self, row):
        item1, item2 = self.item(row, 0), self.item(row, 1)
        if item1 and item2:
            return item1.data(QtCore.Qt.DisplayRole), secs_from_qtime(QtCore.QTime.fromString(item2.data(QtCore.Qt.DisplayRole), "hh:mm:ss"))
        return 0, 0

    def rows(self):
        return self.rowCount()

    def load_settings(self):
        with self._settings.in_group('settings_ui'):
            with self._settings.in_group('images_time_table'):
                for row in range(int(self._settings.value('rows', self.rowCount()))):
                    image, time = self._settings.value(str(row), (5, "00:01:00"))
                    self.model().setData(self.model().index(row, 0), int(image))
                    self.model().setData(self.model().index(row, 1), time)

    def write_settings(self):
        with self._settings.in_group('settings_ui'):
            with self._settings.in_group('images_time_table'):
                settings = {'rows': self.rowCount()}
                for row in range(self.rowCount()):
                    settings[str(row)] = self.item(row, 0).data(QtCore.Qt.DisplayRole), \
                                         self.item(row, 1).data(QtCore.Qt.DisplayRole)
                self._settings.set_values(settings)

