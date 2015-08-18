# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'poseviewer\ui\slideshowsettingsui.ui'
#
# Created: Tue Aug 18 17:50:30 2015
#      by: pyside-uic 0.2.15 running on PySide 1.2.2
#
# WARNING! All changes made in this file will be lost!

from PySide import QtCore, QtGui

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.setWindowModality(QtCore.Qt.ApplicationModal)
        Dialog.resize(340, 180)
        Dialog.setMinimumSize(QtCore.QSize(340, 180))
        self.gridLayout = QtGui.QGridLayout(Dialog)
        self.gridLayout.setObjectName("gridLayout")
        self.label = QtGui.QLabel(Dialog)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)
        self.speed_spinner = QtGui.QSpinBox(Dialog)
        self.speed_spinner.setFrame(True)
        self.speed_spinner.setMinimum(1)
        self.speed_spinner.setMaximum(999999999)
        self.speed_spinner.setSingleStep(5)
        self.speed_spinner.setProperty("value", 30)
        self.speed_spinner.setObjectName("speed_spinner")
        self.gridLayout.addWidget(self.speed_spinner, 0, 1, 1, 1)
        self.increment_checkbox = QtGui.QCheckBox(Dialog)
        self.increment_checkbox.setObjectName("increment_checkbox")
        self.gridLayout.addWidget(self.increment_checkbox, 2, 0, 1, 1)
        self.groupBox = QtGui.QGroupBox(Dialog)
        self.groupBox.setEnabled(False)
        self.groupBox.setObjectName("groupBox")
        self.gridLayout_2 = QtGui.QGridLayout(self.groupBox)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.slideshow_time_left_label = QtGui.QLabel(self.groupBox)
        self.slideshow_time_left_label.setObjectName("slideshow_time_left_label")
        self.gridLayout_2.addWidget(self.slideshow_time_left_label, 1, 0, 1, 1)
        self.increment_interval_spinner = QtGui.QSpinBox(self.groupBox)
        self.increment_interval_spinner.setMinimum(1)
        self.increment_interval_spinner.setMaximum(999999999)
        self.increment_interval_spinner.setProperty("value", 5)
        self.increment_interval_spinner.setObjectName("increment_interval_spinner")
        self.gridLayout_2.addWidget(self.increment_interval_spinner, 0, 1, 1, 1)
        self.label_2 = QtGui.QLabel(self.groupBox)
        self.label_2.setObjectName("label_2")
        self.gridLayout_2.addWidget(self.label_2, 0, 0, 1, 1)
        self.gridLayout.addWidget(self.groupBox, 4, 0, 1, 2)
        self.label_3 = QtGui.QLabel(Dialog)
        self.label_3.setObjectName("label_3")
        self.gridLayout.addWidget(self.label_3, 1, 0, 1, 1)
        self.transition_interval_spinner = QtGui.QDoubleSpinBox(Dialog)
        self.transition_interval_spinner.setReadOnly(False)
        self.transition_interval_spinner.setSingleStep(0.5)
        self.transition_interval_spinner.setProperty("value", 1.0)
        self.transition_interval_spinner.setObjectName("transition_interval_spinner")
        self.gridLayout.addWidget(self.transition_interval_spinner, 1, 1, 1, 1)

        self.retranslateUi(Dialog)
        QtCore.QObject.connect(self.increment_checkbox, QtCore.SIGNAL("toggled(bool)"), self.groupBox.setEnabled)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QtGui.QApplication.translate("Dialog", "Slideshow settings", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("Dialog", "Slideshow speed: ", None, QtGui.QApplication.UnicodeUTF8))
        self.speed_spinner.setSuffix(QtGui.QApplication.translate("Dialog", " s", None, QtGui.QApplication.UnicodeUTF8))
        self.increment_checkbox.setText(QtGui.QApplication.translate("Dialog", "Increment slideshow speed?", None, QtGui.QApplication.UnicodeUTF8))
        self.groupBox.setTitle(QtGui.QApplication.translate("Dialog", "Increment settings", None, QtGui.QApplication.UnicodeUTF8))
        self.slideshow_time_left_label.setText(QtGui.QApplication.translate("Dialog", "Slideshow time left: 00:00:30", None, QtGui.QApplication.UnicodeUTF8))
        self.increment_interval_spinner.setSuffix(QtGui.QApplication.translate("Dialog", " image(s)", None, QtGui.QApplication.UnicodeUTF8))
        self.label_2.setText(QtGui.QApplication.translate("Dialog", "Enter increment interval: ", None, QtGui.QApplication.UnicodeUTF8))
        self.label_3.setToolTip(QtGui.QApplication.translate("Dialog", "The slideshow will transition for this amount of seconds before going to the next image.", None, QtGui.QApplication.UnicodeUTF8))
        self.label_3.setText(QtGui.QApplication.translate("Dialog", "Image transition speed: ", None, QtGui.QApplication.UnicodeUTF8))
        self.transition_interval_spinner.setSuffix(QtGui.QApplication.translate("Dialog", " s", None, QtGui.QApplication.UnicodeUTF8))

