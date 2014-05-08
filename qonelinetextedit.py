from PyQt4 import QtCore, QtGui

class QOneLineTextEdit(QtGui.QPlainTextEdit):
    enterPressed = QtCore.pyqtSignal()
    def keyReleaseEvent(self, e) :
        if e.key() == QtCore.Qt.Key_Return or e.key() == QtCore.Qt.Key_Enter :
            self.enterPressed.emit()
            e.accept()
            return
        QtGui.QPlainTextEdit.keyReleaseEvent(self, e)

    # catch and handle <enter> on key press too so no crlf is created.
    def keyPressEvent(self, e) :
        if e.key() == QtCore.Qt.Key_Return or e.key() == QtCore.Qt.Key_Enter :
            e.accept()
            return
        QtGui.QPlainTextEdit.keyPressEvent(self, e)
