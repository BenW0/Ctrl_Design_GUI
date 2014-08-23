########################################################
# Control Design GUI gui.py
# Implements the GUI for the control design program.
# This code imports gui.ui and exposes some members,
# handles events, etc.
#
# Ben Weiss, University of Washington
# Spring 2014
#
# A little help with Qt from the following sources:
#  http://stackoverflow.com/questions/16997652/unable-to-get-key-event-when-using-uic-loadui-in-pyqt4
#  http://www.bitools.nl/technical_bits/pyqt/index.html
#  http://zetcode.com/gui/pyqt4/eventsandsignals/
#
# The MIT License (MIT)
# 
# Copyright (c) 2014 Ben Weiss
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
########################################################

from PyQt4 import uic, QtCore, QtGui
from qonelinetextedit import *
import sys

from comm import *
import machineInterface as mach
import scripts

BAUDRATE = 119200   # Built to work with a Teensy, which is baudrate-agnostic
ADS_ESCAPE = ""    # Escape character to use with an alternate data stream (see scripts.py, comm.py). Disabled because it doesn't work with the datarate I need.
ADS_FIELDLEN = 28   # length of alternate data streams (bytes)

# structure to hold information about tabs and their widgets
class TabContents :
    def __init__(self) :
        self.name = ''
        self.lPropList = []
        self.tPropList = []
        self.bSetList = []
        self.bGetList = []
        self.bAutoList = []
        # more parameters added dynamically
        


class cMainGui(QtGui.QMainWindow) :

    tabData = []        # list of TabContents classes
    actionButtons = []
    onlineWidgets = []  # list of widgets we can only use when online (disable otherwise)
    
    
    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self)
        
        comm.Init()     # let the comm do things now that qt is set up (rawhid needs this)
        
        self.ctrl_down = False

        uic.loadUi("gui.ui", self)

        # add the Send button to the online widgets list
        self.onlineWidgets.append(self.bSend)

        # add a timer for keeping track of the serial port
        self.tSerialListener = QtCore.QTimer()
        self.tSerialListener.timeout.connect(self.serialTimer)
        self.tSerialListener.setInterval(50)
        self.tSerialListener.start()
        
        # add a timer for updating fields marked "auto"
        self.tAutoTimer = QtCore.QTimer()
        self.tAutoTimer.timeout.connect(self.autoTimer)
        self.tAutoTimer.setInterval(200)
        self.tAutoTimer.start()

        # generate the controls for the commands and values of this machine
        self.generateExtraControls()
        
        # map events to the various buttons
        self.mapEvents()

        # populate the list of ports
        self.bPort_click(True);
        
        #self.delayedcalls = []      # list of functions to call on the next tSerialListener loop (needed because rawhid doesn't receive new data during an event)
        
        self.show()

    def closeEvent(self, event) :
        scripts.plotter.closeWindows()
        comm.Quit()
        app.quit()
        event.accept()

    # uses the structure of machine.machine to generate extra controls for
    # commands and parameters.
    def generateExtraControls(self) :
        # wipe out all the tabs; we'll re-create them by hand.
        while self.tabWidget.count() :
            self.tabWidget.removeTab(0)

        # Hide the template Action button and add a spacer, if this is the first time
        if not self.bbbAction.isHidden() :
            self.bbbAction.hide()
            spacerItem1 = QtGui.QSpacerItem(20, 100, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
            self.saActionsLayout.addItem(spacerItem1, 50, 1, 1, 1)

        # Hide any already-created action buttons
        for b in self.actionButtons :
            b.hide()

        # Hide all properties on current tabs and clear tab names
        for td in self.tabData :
            for d in td.lPropList :
                d.hide()
            for d in td.tPropList :
                d.hide()
            for d in bSetList :
                d.hide()
            for d in bGetList :
                d.hide()
            for d in bAutoList :
                d.hide()
            td.name = ''
        
        # Go through the parameters and create widgets for them
        if mach.machine != None :
            for param in mach.machine.params :
                # figure out which tab this goes in
                for td in self.tabData :
                    if td.name.lower() == param.tab.lower() :
                        curTab = td
                        break
                    if td.name == '' :        # unused tab! We'll use this one!
                        td.name = param.tab
                        curTab = td
                        break
                else :      # no tab match found!
                    # Need a new tab. This is copied out of ui_gui.py and modified
                    td = TabContents()      # new tab container
                    td.name = param.tab
                    
                    self.tabData.append(td)
                    
                    td.tab = QtGui.QWidget()
                    
                    td.tab.setObjectName(param.tab)
                    td.gridLayout_2 = QtGui.QGridLayout(td.tab)
                    
                    td.saTab = QtGui.QScrollArea(td.tab)
                    td.saTab.setWidgetResizable(True)
                    td.saTab.setFrameShape(QtGui.QFrame.NoFrame)
                    
                    td.scrollAreaWidgetContents = QtGui.QWidget()
                    td.scrollAreaWidgetContents.setGeometry(QtCore.QRect(0, 0, 345, 429))

                    td.gridLayout_3 = QtGui.QGridLayout(td.scrollAreaWidgetContents)

                    
                    spacerItem1 = QtGui.QSpacerItem(20, 100, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
                    td.gridLayout_3.addItem(spacerItem1, 50, 1, 1, 1)

                    td.saTab.setWidget(td.scrollAreaWidgetContents)
                    td.gridLayout_2.addWidget(td.saTab, 0, 0, 1, 1)
                    
                    curTab = td

                # Try to find an unused property
                for i in range(0, len(curTab.lPropList)) :
                    if curTab.lPropList[i].isHidden() :
                        # this row is hidden so we can use it!
                        rowToUse = i
                        break
                else :  # didn't find an unused property
                    # Add a property row
                    i = len(curTab.lPropList)
                    lProp = QtGui.QLabel(self.scrollAreaWidgetContents)
                    curTab.gridLayout_3.addWidget(lProp, i, 0, 1, 1)
                    curTab.lPropList.append(lProp)

                    tProp = QOneLineTextEdit(curTab.scrollAreaWidgetContents)
                    sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
                    sizePolicy.setHorizontalStretch(0)
                    sizePolicy.setVerticalStretch(0)
                    sizePolicy.setHeightForWidth(tProp.sizePolicy().hasHeightForWidth())
                    tProp.setSizePolicy(sizePolicy)
                    tProp.setMinimumSize(QtCore.QSize(0, 5))
                    tProp.setMaximumSize(QtCore.QSize(16777215, 20))
                    tProp.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
                    tProp.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
                    tProp.setTabChangesFocus(True)
                    tProp.setLineWrapMode(QtGui.QPlainTextEdit.NoWrap)
                    tProp.machine_paramLink = param      # our backdoor connection into the machine structure
                    tProp.enterPressed.connect(self.tProp_EnterPressed)
                    curTab.gridLayout_3.addWidget(tProp, i, 1, 1, 1)
                    curTab.tPropList.append(tProp)
                    self.onlineWidgets.append(tProp)
                    
                    bGet = QtGui.QPushButton(curTab.scrollAreaWidgetContents)
                    bGet.setText("Get")
                    bGet.setMaximumSize(QtCore.QSize(30, 16777215))
                    bGet.machine_paramLink = param      # our backdoor connection into the machine structure
                    bGet.textField_Link = tProp         # backdoor to access the text box from button events
                    bGet.clicked.connect(self.bGetParam_Clicked)
                    curTab.gridLayout_3.addWidget(bGet, i, 2, 1, 1)
                    curTab.bGetList.append(bGet)
                    self.onlineWidgets.append(bGet)
                    
                    bSet = QtGui.QPushButton(curTab.scrollAreaWidgetContents)
                    bSet.setText("Set")
                    bSet.setMaximumSize(QtCore.QSize(30, 16777215))
                    bSet.machine_paramLink = param      # our backdoor connection into the machine structure
                    bSet.textField_Link = tProp         # backdoor to access the text box from button events
                    bSet.clicked.connect(self.bSetParam_Clicked)
                    curTab.gridLayout_3.addWidget(bSet, i, 3, 1, 1)
                    curTab.bSetList.append(bSet)
                    self.onlineWidgets.append(bSet)
                    
                    bAuto = QtGui.QPushButton(curTab.scrollAreaWidgetContents)
                    bAuto.setText("Auto")
                    bAuto.setMaximumSize(QtCore.QSize(35, 16777215))
                    bAuto.machine_paramLink = param      # our backdoor connection into the machine structure
                    bAuto.textField_Link = tProp         # backdoor to access the text box from button events
                    bAuto.clicked.connect(self.bAutoParam_Clicked)
                    bAuto.setCheckable(True)
                    curTab.gridLayout_3.addWidget(bAuto, i, 4, 1, 1)
                    curTab.bAutoList.append(bAuto)
                    self.onlineWidgets.append(bAuto)
                    
                    # link the set button to the auto button for "reset" function
                    bSet.bAuto_Link = bAuto;
                    bAuto.bSet_Link = bSet;

                    rowToUse = i

                # use this row!
                curTab.lPropList[rowToUse].setText(param.name)
                curTab.lPropList[rowToUse].show()
                curTab.tPropList[rowToUse].setPlainText(str(param.value))
                curTab.tPropList[rowToUse].show()
                if param.readOnly != "1" and param.readOnly != True :
                    curTab.bSetList[rowToUse].show()
                else :
                    curTab.bSetList[rowToUse].hide()
                curTab.bGetList[rowToUse].show()
                curTab.bAutoList[rowToUse].show()

            # Enable all non-empty tabs
            for td in self.tabData :
                if td.name != '' :
                    self.tabWidget.addTab(td.tab, td.name)
            
            self.tabWidget.setCurrentIndex(0)


            # Create the action buttons
            for i in range(0, len(mach.machine.cmds)) :
                if i >= len(self.actionButtons) :
                    # need to create a new button
                    bAction = QtGui.QPushButton(self.saActionsContents)
                    bAction.clicked.connect(self.bAction_Clicked)
                    self.actionButtons.append(bAction)
                    self.saActionsLayout.addWidget(bAction, i, 0, 1, 1)
                    self.onlineWidgets.append(bAction)
                self.actionButtons[i].setText(mach.machine.cmds[i].name)
                self.actionButtons[i].show()
                self.actionButtons[i].machine_cmdLink = mach.machine.cmds[i]
                
            # if we're not yet connected, disable all of these objects
            value = not comm.IsOpen()
            for widget in self.onlineWidgets :
                widget.setDisabled(value)
            

                    
    def mapEvents(self):
        # object names for form controls are set using Qt Designer in "gui.ui"
        self.bLoadSettings.clicked[bool].connect(self.bLoadSettings_click)
        self.bSaveSettings.clicked[bool].connect(self.bSaveSettings_click)
        self.bApplySettings.clicked[bool].connect(self.bApplySettings_click)
        self.bPort.clicked[bool].connect(self.bPort_click)
        self.bConnect.clicked[bool].connect(self.bConnect_click)
        self.bSend.clicked[bool].connect(self.bSend_click)
        self.tCommand.enterPressed.connect(self.tCommand_Enter)
        
        
    def bLoadSettings_click(self) :
        fname = QtGui.QFileDialog.getOpenFileName(directory="settings", caption="Open Settings File", filter="Machine Settings (*.xml);;All Files (*.*)")
        if fname != "" :
            mach.machine.loadSettings(fname)
            
            # update the gui with the new values
            for tab in self.tabData :
                for tProp in tab.tPropList :
                    if not tProp.isHidden() :
                        tProp.setPlainText(str(tProp.machine_paramLink.value))
    
    def bSaveSettings_click(self) :
        fname = QtGui.QFileDialog.getSaveFileName(directory="settings", caption="Save Settings File", filter="Machine Settings (*.xml);;All Files (*.*)")
        if fname != "" :
           mach.machine.save(fname)
    
    def bApplySettings_click(self) :
        if comm.IsOpen() :
            for tab in self.tabData :
                for tProp in tab.tPropList :
                    if not tProp.isHidden() :
                        if tProp.machine_paramLink.readOnly != "1" :
                            if not tProp.machine_paramLink.setValidValue(tProp.toPlainText()) :
                                tProp.setPlainText(str(tProp.machine_paramLink.value))
                            tProp.machine_paramLink.setToDevice()
            
    
    def bPort_click(self, pressed):
        # populate the list of ports
        ports = comm.GetComPorts()
        self.cPort.clear()
        for i in ports :
            self.cPort.addItem(i[0])
        self.cPort.setCurrentIndex(self.cPort.count()-1)
        
    def bConnect_click(self) :
        if comm.IsOpen() :
            # send the Idle Mode command before we close, as a safety measure.
            for cmd in mach.machine.cmds :
                if cmd.name.lower().find("idle") > -1 :
                    cmd.doAction()
                    break
            try :
                comm.Close()
            except comm.ser.SerialException as e:
                print(str(e))
                self.statusBar().showMessage('Error closing connection!')
            else :
                self.statusBar().showMessage('Disconnected.')
                self.bConnect.setText('Connect')
                for widget in self.onlineWidgets :
                    widget.setDisabled(True)
        else :
            if 0 == comm.Open(str(self.cPort.currentText()), BAUDRATE, ADS_ESCAPE, ADS_FIELDLEN) :
                self.statusBar().showMessage('Error connecting to ' + str(self.cPort.currentText()))
            else :
                # change this to disconnect
                self.bConnect.setText('Disconnect')
                self.statusBar().showMessage('Connected.')
                for widget in self.onlineWidgets :
                    widget.setDisabled(False)
    
    def bSend_click(self) :
        print(">" + str(self.tCommand.toPlainText()))
        if comm.IsOpen() :
            try :
                comm.Write(str(self.tCommand.toPlainText()))
                self.statusBar().showMessage('Ready')
            except comm.ser.SerialException as e :
                print(str(e))
                self.statusBar().showMessage('Send Error!')
        self.tCommand.setPlainText('')


    def tCommand_Enter(self) :
        self.bSend_click()

    def bAction_Clicked(self) :
        self.sender().machine_cmdLink.doAction()

    def bGetParam_Clicked(self) :
        if self.sender().machine_paramLink.getFromDevice() :
            # It worked! Update the text box
            self.sender().textField_Link.setPlainText(str(self.sender().machine_paramLink.value))
            self.statusBar().showMessage('Ready')
        else :
            self.statusBar().showMessage('Read Error!')
        
    def bSetParam_Clicked(self) :
        # If we are in Auto mode or if ctrl is held down, send a reset instead of a set
        if self.sender().bAuto_Link.isChecked() or QtGui.QApplication.keyboardModifiers() == QtCore.Qt.ControlModifier :
            self.sender().machine_paramLink.restoreDefault()
            # Now re-read the result...
            if self.sender().machine_paramLink.getFromDevice() :
                # It worked! Update the text box
                self.sender().textField_Link.setPlainText(str(self.sender().machine_paramLink.value))
                self.statusBar().showMessage('Ready')
            else :
                self.statusBar().showMessage('Read Error!')
        else :
            if self.sender().machine_paramLink.setValidValue(self.sender().textField_Link.toPlainText()) :
                # Value is acceptable. Write it to the device
                self.sender().machine_paramLink.setToDevice()
                self.statusBar().showMessage('Ready. Use Ctrl+Click to Reset to Default.')
            else :
                # Invalid value
                print("Could not parse value!")
                self.statusBar().showMessage('Parse Error!')
    
    def bAutoParam_Clicked(self) :
        if self.sender().isChecked() :
            p = self.sender().textField_Link.palette()
            self.sender().textField_Link.old_palette = self.sender().textField_Link.palette()
            p.setColor(QtGui.QPalette.Active, QtGui.QPalette.Base, QtCore.Qt.yellow)
            self.sender().bSet_Link.setText("Reset")
        else :
            p = self.sender().textField_Link.old_palette
            if self.ctrl_down :
                self.sender().bSet_Link.setText("Res")
            else :
                self.sender().bSet_Link.setText("Set")
        self.sender().textField_Link.setPalette(p)

    # this is almost identical to bSetParam_Clicked, except self.sender() is the onelinetext object
    # instead of the button, so the indirection is a bit different.
    def tProp_EnterPressed(self) :
        if self.sender().machine_paramLink.setValidValue(self.sender().toPlainText()) :
            # Value is acceptable. Write it to the device
            self.sender().machine_paramLink.setToDevice()
            self.statusBar().showMessage('Ready')
        else :
            # Invalid value
            print("Could not parse value!")
            self.statusBar().showMessage('Parse Error!')

    # This routine runs every 50 ms and checks for new input from the serial port.
    # this is not a respone from a command, but debug input or something.
    def serialTimer(self) :
        #while len(self.delayedcalls) > 0 :
        #    self.delayedcalls.pop()()       # execute the delayed call
        comm.DumpToConsole()

    # This routine runs every 200 ms and updates all fields with their "auto"
    # buttons toggled.
    def autoTimer(self) :
        # check to see if we need to update Set button tetxt
        if self.ctrl_down and QtGui.QApplication.keyboardModifiers() != QtCore.Qt.ControlModifier :
            update_texts = True
            newtext = "Set"
            self.ctrl_down = False
        elif not self.ctrl_down and QtGui.QApplication.keyboardModifiers() == QtCore.Qt.ControlModifier :
            update_texts = True
            newtext = "Res"
            self.ctrl_down = True
        else :
            update_texts = False
        
        # update param values and Set button texts
        if comm.IsOpen() :
            for tab in self.tabData :
                for bAuto in tab.bAutoList :
                    if bAuto.isChecked() :
                        if bAuto.machine_paramLink.getFromDevice(True) :
                            # It worked! Update the text box
                            bAuto.textField_Link.setPlainText(str(bAuto.machine_paramLink.value))
                    elif update_texts :
                        # also update the Set button texts
                        bAuto.bSet_Link.setText(newtext)

app = None
    

def start_gui() :
    global app
    # load a machine
    mach.loadMachine("machine.xml")
    # load the gui
    app = QtGui.QApplication(sys.argv)
    try :
        myMainWindow = cMainGui()
        app.exec_()
    finally :
        comm.Close()


if __name__ == "__main__":
    start_gui()
