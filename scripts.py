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
# Not licensed. Internal development only!
#
########################################################

import matplotlib.pyplot as plt
import numpy as np
import comm
import time
import struct
import sip
from PyQt4 import QtCore, QtGui
import sys
import re
import datetime


import plotgui

histStruct = struct.Struct("=Llffffl")
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


def readCtrlHistory() :
    """read back the control history and plot with matplotlib"""
    # read back the history
    comm.Write("gd")         # read back command
    buf = ''
    total = 0
    time.sleep(0.015)
    for i in range(0,1000) :
        buf += comm.Read()
        if len(buf) > 10 and total == 0:
            #try :
            print("Getting " + buf.splitlines()[0] + " datapoints")
            total = int(buf.splitlines()[0])
            buf = buf[len(buf.splitlines()[0])+1:]    # get rid of the first line
            #except ValueError :
            #    total = 10000   # go until we're sure we're done...
        if 0 < total and len(buf) >= total * histStruct.size :# and comm.serobj.inWaiting() == 0 :
            break
        time.sleep(0.015)
        print '.',
    else :
        print("Wanted %i bytes; got %i. Failing!" %(total * histStruct.size, len(buf)))
        return
    print len(buf) / histStruct.size, "datapoints read."

    # parse out the structures
    ts = []
    ps = []
    vs = []
    pos_error_derivs = []
    cmd_vs = []
    target_ps = []
    target_vs = []
    motor_ps = []
    with open("dumps/" + timeStamped("ctrlHistory.csv"), "w") as fout :
        fout.write("Time(s*1e5), Position (tics), Velocity (tics/min), Command Velocity (tics/min), Target Position (tics), Target Velocity (tics/min), Motor Position (tics)\n")
        for i in range(0, total * histStruct.size, histStruct.size) :
            d = histStruct.unpack_from(buf, i)
            fout.write("%f, %i, %f, %f, %f, %f, %i\n" % d)
            ts.append(d[0] * 0.00001)
            ps.append(d[1])
            #vs.append(d[2])
            pos_error_derivs.append(d[2])
            cmd_vs.append(d[3])
            target_ps.append(d[4])
            target_vs.append(d[5])
            motor_ps.append(d[6])
    
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


def closeWindows() :
    for fig in figwindows :
        fig.hide()
        fig.close()
        fig.deleteLater()
        sip.delete(fig)
    while len(figwindows) > 0 :
        figwindows.pop()
        

def uploadCustomPath() :
    """Uploads a custom path to the device. This function reads the path from 
    file path.csv in the local directory. This file can be generated using the
    Custom Path Generator.xlsm workbook. """
    print(">pcc")
    comm.Write("pcc")
    
    # read the moves out of the file
    packets = []
    with open("path.csv", "r") as fin :
         for line in fin :
             r = re.compile("[ \t\n\r,]+")
             data = r.split(line)
             if len(data) < 3 :
                break       # must be end of file.
             try :
                 packets.append((int(float(data[0])*1000), float(data[1]), float(data[2])))
             except ValueError as e :
                 print "Error parsing path.csv: " + str(e)
    print("Read %i pathpoints. Uploading." % (len(data)))
    
    # write the moves to the device
    for packet in packets :
        s = "pcp %i %f %f" % packet
        print(">" + s)
        comm.Write(s)
        time.sleep(0.02)
    

if __name__ == "__main__" :
    try :
        app = QtGui.QApplication(sys.argv)
        comm.Open("COM6", 119200)
        readCtrlHistory()
        app.exec_()
    finally :
        comm.Close()
