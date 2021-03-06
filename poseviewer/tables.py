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

        self.horizontalHeader().setResizeMode(QtGui.QHeaderView.Stretch)
        self.verticalHeader().show()
        self.horizontalHeader().show()
        self.resizeColumnsToContents()

    def insert_row(self, row=None):
        row = row if row else self.currentRow() + 1
        self.insertRow(row)
        return row

    def remove_row(self, row=None):
        if row:
            return self.removeRow(row)
        return self.removeRow(self.currentRow())

    def rows(self):
        return self.rowCount()

    def row_item_data(self, row):
        items = []
        for column in range(self.columnCount()):
            item = self.item(row, column)
            if item:
                items.append(item)
        return [item.data(QtCore.Qt.DisplayRole) for item in items]


class RandomTimeTable(BaseTable):
    DEFAULT_TIME = "00:00:30"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.delegate = TimeEditDelegate()
        self.setItemDelegateForColumn(0, self.delegate)

        QtCore.QTimer.singleShot(0, self.load_settings)

    def time(self, row):
        item = self.item(row, 0)
        if item:
            return secs_from_qtime(QtCore.QTime.fromString(self.item(row, 0).data(QtCore.Qt.DisplayRole), "hh:mm:ss"))
        return 0

    def insert_row(self):
        row = super().insert_row()
        self.model().setData(self.model().index(row, 0), self.DEFAULT_TIME)

    def load_settings(self):
        settings = Settings()
        with settings.in_group('settings_ui'):
            with settings.in_group('random_time_table'):
                rows = int(settings.value('rows', self.rowCount()))
                self.setRowCount(rows)
                for row in range(rows):
                    time = settings.value(str(row), self.DEFAULT_TIME)
                    self.model().setData(self.model().index(row, 0), time)

    def write_settings(self):
        settings = Settings()
        with settings.in_group('settings_ui'):
            with settings.in_group('random_time_table'):
                section_settings = {'rows': self.rowCount()}
                for row in range(self.rowCount()):
                    section_settings[str(row)] = self.item(row, 0).data(QtCore.Qt.DisplayRole)
                settings.set_values(section_settings)

                max_extra_rows = max([int(key) for key in settings.childKeys() if key != 'rows']) + 1
                if max_extra_rows > section_settings['rows']:
                    for extra_row in range(section_settings['rows'], max_extra_rows):
                        settings.remove(str(extra_row))


class ImagesTimeTable(BaseTable):
    DEFAULT_TIME = "00:01:00"
    DEFAULT_IMAGE = 5

    totalTimeChanged = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.spinbox_delegate = SpinBoxDelegate(suffix=" images", value=5)
        self.timeedit_delegate = TimeEditDelegate()
        self.setItemDelegateForColumn(0, self.spinbox_delegate)
        self.setItemDelegateForColumn(1, self.timeedit_delegate)

        self.cellChanged.connect(lambda: self.totalTimeChanged.emit())
        self._model = self.model()
        self._model.rowsRemoved.connect(lambda: self.totalTimeChanged.emit())

        QtCore.QTimer.singleShot(0, self.load_settings)

    def insert_row(self, row=None, image=5, time="00:01:00"):
        """Override BaseTable method."""
        row = super().insert_row(row=row)
        self.model().setData(self.model().index(row, 0), image)
        self.model().setData(self.model().index(row, 1), time)

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

    def load_settings(self):
        settings = Settings()
        with settings.in_group('settings_ui'):
            with settings.in_group('images_time_table'):
                rows = int(settings.value('rows', self.rowCount()))
                self.setRowCount(rows)
                for row in range(rows):
                    image, time = settings.value(str(row), (self.DEFAULT_IMAGE, self.DEFAULT_TIME))
                    # self.insert_row(row=row, image=int(image), time=time)
                    self.model().setData(self.model().index(row, 0), int(image))
                    self.model().setData(self.model().index(row, 1), time)

    def write_settings(self):
        settings = Settings()
        with settings.in_group('settings_ui'):
            with settings.in_group('images_time_table'):
                section_settings = {'rows': self.rowCount()}
                for row in range(section_settings['rows']):
                    section_settings[str(row)] = self.item(row, 0).data(QtCore.Qt.DisplayRole), \
                                                 self.item(row, 1).data(QtCore.Qt.DisplayRole)
                settings.set_values(section_settings)

                max_extra_rows = max([int(key) for key in settings.childKeys() if key != 'rows']) + 1
                if max_extra_rows > section_settings['rows']:
                    for extra_row in range(section_settings['rows'], max_extra_rows):
                        settings.remove(str(extra_row))

