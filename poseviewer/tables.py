from PySide.QtCore import *
from PySide.QtGui import *


class BaseTable(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi()

        self.verticalHeader().show()
        self.horizontalHeader().show()

    def setupUi(self):
        self.setRowCount(3)
        self.setColumnCount(2)
        self.setHorizontalHeaderItem(0, QTableWidgetItem())
        self.horizontalHeaderItem(0).setText("Description")
        self.setHorizontalHeaderItem(1, QTableWidgetItem())
        self.horizontalHeaderItem(1).setText("Value")
        self.horizontalHeader().setCascadingSectionResizes(True)
        self.horizontalHeader().setSortIndicatorShown(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().setCascadingSectionResizes(True)
        self.verticalHeader().setStretchLastSection(True)
        self.horizontalHeader().setResizeMode(QHeaderView.Stretch)

    def insert_row(self, row=None):
        if row:
            self.insertRow(row)
            self.add_value_widget_to_cell(row, 1)
        else:
            self.insertRow(self.currentRow() + 1)
            self.add_value_widget_to_cell(self.currentRow() + 1, 1)

    def remove_row(self, row=None):
        if row:
            return self.removeRow(row)
        return self.removeRow(self.currentRow())

    @staticmethod
    def make_value_widget():
        """Implement in subclass."""
        pass

    def add_value_widget_to_cell(self, row, column):
        self.setCellWidget(row, column, self.make_value_widget())

    def init_table_cells(self):
        for row in range(self.rowCount()):
            self.add_value_widget_to_cell(row, 1)



class TimeEditTable(BaseTable):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_table_cells()

    @staticmethod
    def make_value_widget():
        return QTimeEdit(time=QTime(0, 5), currentSection=QDateTimeEdit.MinuteSection)


class ValueTable(BaseTable):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_table_cells()

    @staticmethod
    def make_value_widget():
        return QSpinBox(suffix=" images", value=5)

