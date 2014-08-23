########################################################
# Control Design GUI: plotting.py
# Handles plotting tasks for the GUI.
#
# This set of routines is called from actions on the GUI;
# so the actual calling code is found in the machine.xml's
# <Command> field.
#
# Ben Weiss, University of Washington
# Spring 2014
#
# Some code snipped from:
# http://stackoverflow.com/questions/5214866/python-add-date-stamp-to-text-file
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

import matplotlib.pyplot as plt
import numpy as np
import comm
import time
import struct
import sip
import sys
import re
import os
import datetime
from PyQt4 import uic, QtCore, QtGui


import plotgui


histStruct = struct.Struct("=LlfffflB")
##typedef struct
##{
##  uint32_t time;
##  int32_t position;
##  //float velocity;
##  float pos_error_deriv;
##  float cmd_velocity;
##  float target_pos;
##  float target_vel;
##  int32_t motor_position;
##} hist_data_t;


# Figure windows (plotgui:FigureWindow objects)
figwindows = []


def timeStamped(fname, fmt='%Y-%m-%d-%H-%M-%S_{fname}'):
    return datetime.datetime.now().strftime(fmt).format(fname=fname)


def readDump(fname) :
    """plots a saved control history with matplotlib"""
    # read back the history from file
    ts = []
    ps = []
    vs = []
    pos_error_derivs = []
    cmd_vs = []
    target_ps = []
    target_vs = []
    motor_ps = []
    
    with open(fname, "r") as fin :
        fin.readline()      # read header line
        for line in fin :
            r = re.compile("[ \t\n\r,]+")
            d = r.split(line)
            if len(d) < 7 :
                break       # we're done with the file
            ts.append(float(d[0]) * 0.00001)
            ps.append(int(d[1]))
            #vs.append(d[2])
            pos_error_derivs.append(float(d[2]))
            cmd_vs.append(float(d[3]))
            target_ps.append(float(d[4]))
            target_vs.append(float(d[5]))
            motor_ps.append(float(d[6]))
    
    # plot the data!
##    if len(figwindows) == 0 :
##       figwindows.append(plotgui.PlotWindow())
##       figwindows[0].move(0,0)
##       figwindows.append(plotgui.PlotWindow())
##       figwindows[1].move(400, 0)
##       figwindows.append(plotgui.PlotWindow())
##       figwindows[2].move(800, 0)
##       figwindows.append(plotgui.PlotWindow())
##       figwindows[3].move(1200, 0)
    
    
    # plot the data!
    if len(figwindows) == 0 :
       figwindows.append(plotgui.PlotWindow())
       figwindows[0].move(0,0)
       figwindows.append(plotgui.PlotWindow())
       figwindows[1].move(400, 0)
       figwindows.append(plotgui.PlotWindow())
       figwindows[2].move(800, 0)
       figwindows.append(plotgui.PlotWindow())
       figwindows[3].move(1200, 0)
    fig = figwindows[0].init_plot()
    fig.plot(ts, ps, 'b-', label='Position')
    fig.hold(True)
    fig.plot(ts, target_ps, 'r--', label='Target Position')
    fig.legend(loc=2)
    fig.xaxis.label.set_text('Time (s)')
    fig.yaxis.label.set_text('Position (encoder tics)')
    fig.title.set_text('Position Tracking')
    # NOTE: additional properties of the plot (text size, etc) are set using 
    # the matplotlibrc file in the project folder.
    
    figwindows[0].render_plot()
    figwindows[0].show()
    
    fig = figwindows[1].init_plot()
    #fig.plot(ts, vs, 'c-', label='Velocity')
    fig.hold(True)
    fig.plot(ts, target_vs, 'r--', label='Target Velocity')
    fig.plot(ts, cmd_vs, 'g-', label='Command Velocity')
    fig.legend(loc=2)
    fig.xaxis.label.set_text('Time (s)')
    fig.yaxis.label.set_text('Velocity (encoder tics/min)')
    fig.title.set_text('Velocity Tracking')
    
    figwindows[1].render_plot()
    figwindows[1].show()
    
    fig = figwindows[2].init_plot()
    fig.plot(ts, ps, 'b-', label='Encoder Position')
    fig.hold(True)
    fig.plot(ts, motor_ps, 'g-', label='Motor Step Position')
    fig.legend(loc=2)
    fig.xaxis.label.set_text('Time (s)')
    fig.yaxis.label.set_text('Position (encoder tics)')
    fig.title.set_text('Motor Reported Location')
    
    figwindows[2].render_plot()
    figwindows[2].show()
    
    fig = figwindows[3].init_plot()
    fig.plot(ts, pos_error_derivs, 'b-', label='Position Error Derivative')
    fig.xaxis.label.set_text('Time (s)')
    fig.yaxis.label.set_text('Error change (tics/update)')
    fig.title.set_text('Position Error Derivative')
    
    figwindows[3].render_plot()
    figwindows[3].show()
    
    # also save off a copy of the machine at this time (so we know what was going on later)
    mach.Machine.save(stamp + 'machine.xml')


# defines 
def convertBinaryDump(fname_in, fname_out, sep_chr="$") :
    with open(fname_in, "rb") as fin, open(fname_out, "w") as fout :
         c = ' '
         while c != "" :
            c = fin.read(1)
            if c == sep_chr :
                # next  bytes are a hist_struct
                str = fin.read(histStruct.size)
                d = histStruct.unpack(str)
                fout.write("%f, %i, %f, %f, %f, %f, %i\n" % d)
                
def closeWindows() :
    for fig in figwindows :
        fig.hide()
        fig.close()
        fig.deleteLater()
        sip.delete(fig)
    while len(figwindows) > 0 :
        figwindows.pop()
        

class cDumpReader(QtGui.QMainWindow) :

    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self)
        
        uic.loadUi("dumpreader.ui", self)
        
        # load items into the list widget
        
        
        for file in os.listdir('streams') :
            if file[-3:].lower() == 'csv' :
                listItem = QtGui.QListWidgetItem(file[:-4], self.listWidget)
        
        self.listWidget.currentItemChanged.connect(self.listWidget_Changed)
        #self.listWidget.connect(self.listWidget, QtCore.SIGNAL("selectionChanged(QItemSelection&, QItemSelection&)"),
        #                self.listWidget_Changed)
        
        self.show()

    def closeEvent(self, event) :
        closeWindows()
        app.quit()
        event.accept()
    
    def listWidget_Changed(self, selected, deselected) :
        readDump(os.getcwd() + '/streams/' + selected.text() + '.csv')
        

app = None
    

def start_gui() :
    global app
    # load the gui
    app = QtGui.QApplication(sys.argv)
    try :
        myMainWindow = cDumpReader()
        app.exec_()
    finally :
        comm.Close()


if __name__ == "__main__" :
    if len(sys.argv) > 2 :
        convertBinaryDump(sys.argv[1], sys.argv[2], "$")
    elif len(sys.argv) > 1 :
         app = QtGui.QApplication(sys.argv)
         readDump(sys.argv[1])
         app.exec_()
    else :
        start_gui()
