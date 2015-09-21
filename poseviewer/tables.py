from PySide import QtCore, QtGui
from .corewidgets import secs_from_qtime, get_time_from_secs


# Item = namedtuple('Item', 'column widget')


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


    # def make_row(self, row):
    #     for item in self.row_template():
    #         self.setCellWidget(row, item.column, item.widget)

    # def row_template(self):
    #     """Implement in subclass."""
    #     pass

    # def make_connections(self):
    #     """Implement in subclass."""
    #     pass

    # @staticmethod
    # def default_cell_widget():
    #     """Implement in subclass."""
    #     pass

    # def add_widget_to_cell(self, row, column, func=None):
    #     widget = func() if func else self.default_cell_widget()
    #     self.setCellWidget(row, column, widget)

    # def init_table_columns(self, column, func=None):
    #     for row in range(self.rowCount()):
    #         if func:
    #             self.add_widget_to_cell(row, column, func)
    #         else:
    #             self.add_widget_to_cell(row, column, self.default_cell_widget)

    # def get_all_cell_widgets_rows(self):
    #     all_widgets = []
    #     for row in range(self.rowCount()):
    #         row_widgets = []
    #         for column in range(self.columnCount()):
    #             if self.cellWidget(row, column): row_widgets.append(self.cellWidget(row, column))
    #         all_widgets.append(row_widgets)
    #     return all_widgets

    # def all_cell_widgets(self):
    #     all_widgets = []
    #     for row in range(self.rowCount()):
    #         for column in range(self.columnCount()):
    #             if self.cellWidget(row, column): all_widgets.append(self.cellWidget(row, column))
    #     return all_widgets


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


        # self.init_table_columns(1, self.default_cell_widget)
        # self.make_connections()

    # def make_connections(self):
    #     for row in self.get_all_cell_widgets_rows():
    #         for widget in row:
    #             widget.timeChanged.connect(lambda: print(widget), type=Qt.UniqueConnection)

    # def row_template(self):
    #     return Item(column=1, widget=self.default_cell_widget()),

    # @staticmethod
    # def default_cell_widget():
    #     return QTimeEdit(time=QTime(0, 5), currentSection=QDateTimeEdit.MinuteSection)


class ImagesTimeTable(BaseTable):
    totalTimeChanged = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.spinbox_delegate = SpinBoxDelegate(suffix=" images", value=5)
        self.timeedit_delegate = TimeEditDelegate()
        self.setItemDelegateForColumn(0, self.spinbox_delegate)
        self.setItemDelegateForColumn(1, self.timeedit_delegate)

        for row in range(self.rowCount()):
            self.model().setData(self.model().index(row, 0), 5)
            self.model().setData(self.model().index(row, 1), "00:01:00")

        self.cellChanged.connect(lambda: self.totalTimeChanged.emit())
        self._model = self.model()
        self._model.rowsRemoved.connect(lambda: self.totalTimeChanged.emit())

    def insert_row(self):
        """Override BaseTable method."""
        row = super().insert_row()
        self.model().setData(self.model().index(row, 0), 5)
        self.model().setData(self.model().index(row, 1), "00:01:00")


    #     self.init_table_columns(1, self.time_edit)
    #     self.init_table_columns(0, self.default_cell_widget)
    #     self.make_connections()

    # def make_connections(self):
    #     for row in self.get_all_cell_widgets_rows():
    #         for widget in row:
    #             if isinstance(widget, QSpinBox):
    #                 widget.valueChanged.connect(lambda: print(widget), type=Qt.UniqueConnection)
    #             elif isinstance(widget, QTimeEdit):
    #                 widget.timeChanged.connect(lambda: print(widget), type=Qt.UniqueConnection)

    # def row_template(self):
    #     return Item(column=1, widget=self.time_edit()), Item(column=0, widget=self.default_cell_widget())

    # @staticmethod
    # def default_cell_widget():
    #     return QSpinBox(suffix=" images", value=5)

    # @staticmethod
    # def time_edit():
    #     return QTimeEdit(time=QTime(0, 1), currentSection=QDateTimeEdit.MinuteSection)

    def calculate_total_time(self):
        total = 0
        for row in range(self.rowCount()):
            item1, item2 = self.item(row, 0), self.item(row, 1)
            if item1 and item2:
                total += item1.data(QtCore.Qt.DisplayRole) * secs_from_qtime(QtCore.QTime.fromString(item2.data(QtCore.Qt.DisplayRole), "hh:mm:ss"))

        return total

    def get_total_time_string(self):
        return get_time_from_secs(self.calculate_total_time())
