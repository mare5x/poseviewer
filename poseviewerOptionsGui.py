# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'poseviewerOptions.ui'
#
# Created: Fri Dec 19 19:28:48 2014
#      by: pyside-uic 0.2.15 running on PySide 1.2.2
#
# WARNING! All changes made in this file will be lost!

from PySide import QtCore, QtGui

class Ui_Options(object):
    def setupUi(self, Options):
        Options.setObjectName("Options")
        Options.setWindowModality(QtCore.Qt.NonModal)
        Options.resize(326, 278)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(Options.sizePolicy().hasHeightForWidth())
        Options.setSizePolicy(sizePolicy)
        Options.setSizeGripEnabled(False)
        Options.setModal(False)
        self.gridLayout = QtGui.QGridLayout(Options)
        self.gridLayout.setObjectName("gridLayout")
        self.osdCheckBox = QtGui.QCheckBox(Options)
        self.osdCheckBox.setObjectName("osdCheckBox")
        self.gridLayout.addWidget(self.osdCheckBox, 1, 2, 1, 1)
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem, 0, 0, 2, 2)
        self.spinBox = QtGui.QSpinBox(Options)
        self.spinBox.setProperty("value", 30)
        self.spinBox.setObjectName("spinBox")
        self.gridLayout.addWidget(self.spinBox, 2, 3, 1, 2)
        self.fullscreenCheckBox = QtGui.QCheckBox(Options)
        self.fullscreenCheckBox.setObjectName("fullscreenCheckBox")
        self.gridLayout.addWidget(self.fullscreenCheckBox, 0, 2, 1, 1)
        self.label_3 = QtGui.QLabel(Options)
        self.label_3.setObjectName("label_3")
        self.gridLayout.addWidget(self.label_3, 2, 0, 1, 3)
        self.buttonBox = QtGui.QDialogButtonBox(Options)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.gridLayout.addWidget(self.buttonBox, 4, 1, 1, 3)
        spacerItem1 = QtGui.QSpacerItem(67, 65, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.gridLayout.addItem(spacerItem1, 3, 4, 2, 1)
        self.changeDirButton = QtGui.QPushButton(Options)
        self.changeDirButton.setObjectName("changeDirButton")
        self.gridLayout.addWidget(self.changeDirButton, 3, 2, 1, 1)
        spacerItem2 = QtGui.QSpacerItem(67, 65, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.gridLayout.addItem(spacerItem2, 3, 0, 2, 1)

        self.retranslateUi(Options)
        QtCore.QMetaObject.connectSlotsByName(Options)

    def retranslateUi(self, Options):
        Options.setWindowTitle(QtGui.QApplication.translate("Options", "Options", None, QtGui.QApplication.UnicodeUTF8))
        self.osdCheckBox.setText(QtGui.QApplication.translate("Options", "OSD countdown", None, QtGui.QApplication.UnicodeUTF8))
        self.fullscreenCheckBox.setText(QtGui.QApplication.translate("Options", "Fullscreen", None, QtGui.QApplication.UnicodeUTF8))
        self.label_3.setText(QtGui.QApplication.translate("Options", "Change slideshow speed (seconds)", None, QtGui.QApplication.UnicodeUTF8))
        self.changeDirButton.setText(QtGui.QApplication.translate("Options", "Change directory", None, QtGui.QApplication.UnicodeUTF8))

