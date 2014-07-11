#-------------------------------------------------------------------------------
# Name:        subprocess test module
# Purpose:     
#
# Author:      Ben Weiss, University of Washington
#
# Created:     27/06/2014
# Copyright:   (c) Ben Weiss, University of Washington 2014
# Licence:     None (internal devel only)
#
# Code from http://stackoverflow.com/questions/18459770/adding-button-and-separate-window-to-python-qprocess-example
#-------------------------------------------------------------------------------

from comm import *
from PyQt4.QtGui import * 
from PyQt4.QtCore import * 
import sys


class MyWindow(QWidget):     
  def __init__(self):    
   #Call base class method 
   QWidget.__init__(self)
   #Create an instance variable here (of type QTextEdit)
   self.edit    = QTextEdit()
   self.edit.setWindowTitle("QTextEdit Standard Output Redirection")
   self.button = QPushButton('Send')
   self.button.clicked.connect(self.onClick)
   self.button2 = QPushButton('Receive')
   self.button2.clicked.connect(self.onClick2)
   layout = QVBoxLayout(self)
   layout.addWidget(self.edit)
   layout.addWidget(self.button)
   layout.addWidget(self.button2)
   
   comm.Init()
   
   #self.proc = QProcess()
   #self.proc.start("rawhid_listener.exe")
   #self.proc.setProcessChannelMode(QProcess.MergedChannels);
   #QObject.connect(self.proc, SIGNAL("readyReadStandardOutput()"), self, SLOT("readStdOutput()"));
   #self.proc.readyReadStandardOutput.connect(self.readStdOutput)

  #Define Slot Here 
  #@pyqtSlot()
  def readStdOutput(self):
    #self.edit.append(QString(self.proc.readAllStandardOutput()))
    self.edit.append(QString(comm.Read()))
    
  def onClick(self):
    #self.proc.writeData("o\n")
    comm.Write("o\n")
    
  def onClick2(self):
    #self.edit.append(QString(self.proc.readAll()))
    self.edit.append(QString(comm.Read()))
    
def main():  
    app     = QApplication(sys.argv)
    qWin    = MyWindow()    
    qWin.show()
    return app.exec_()

if __name__ == '__main__':
    main()