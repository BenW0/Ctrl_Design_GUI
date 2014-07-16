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
# http://matplotlib.org/examples/animation/strip_chart_demo.html
#
# Not licensed. Internal development only!
#
########################################################

import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
from comm import *
import time
import struct
import sip
from PyQt4 import QtCore, QtGui
import sys
import re
import datetime
import machineInterface as mach


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
##  uchar8_t flags;
##} hist_data_t;

DS_STREAM_HIST = 0           # data stream used for history downloading



def timeStamped(fname, fmt='%Y-%m-%d-%H-%M-%S_{fname}'):
    return datetime.datetime.now().strftime(fmt).format(fname=fname)

        

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
    

    
def convertBinaryDump(fname_in, fname_out) :
    """Converts a RawHID binary file dump into csv format. This is NOT the
    same as converting a binary dump from the old over-serial ADS stream because
    it does not use separator characters."""
    with open(fname_in, "rb") as fin, open(fname_out, "w") as fout :
        # print out the header
        fout.write("Time (*10us), Position (tics), Position Error Derivative (tics), Cmd Vel (tics/min), Target Pos (tics), Target Vel (tics), Motor Position (tics), Flags\n")
        while True :
            chunk = fin.read(histStruct.size)
            if len(chunk) < histStruct.size :
                break
            else :
                # parse out a hist struct
                d = histStruct.unpack(chunk)
                fout.write("%f, %i, %f, %f, %f, %f, %i, %i\n" % d)

# Plotting Class - plots single plots and data streams.
# The next few script functions implement streaming data plotting, using the 
# alternate data stream functionality of the comm module. After the plot is
# started, a callback is called every few hundred ms to update the graphs.

class Plotter :
    
    # Storage class for keeping track of line traces
    class Trace :
        def __init__(self, fig, x, y, color, legend) :
            self.x = x
            self.y = y
            self.line2d = fig.plot(self.x, self.y, color, label=legend)
        def update(self) :
            self.line2d[0].set_data(self.x, self.y)
    
    def __init__(self) :
        self.ts = []
        self.ps = []
        self.pos_error_derivs = []
        self.cmd_vs = []
        self.target_ps = []
        self.target_vs = []
        self.motor_ps = []
        self.stream_fname = ''
        
        # Figure windows (plotgui:FigureWindow objects)
        self.figwindows = []
        
        self.streaming = False
    
    def readCtrlHistory(self) :
        """read back the control history and plot with matplotlib"""
        # read back the history
        comm.Write("gd")         # read back command
        buf = ''
        total = 0
        time.sleep(0.1)
        for i in range(0,100) :
            buf += comm.ReadBlocking(50)
            if len(buf) > 10 and total == 0:
                #try :
                print("Getting " + buf.splitlines()[0] + " datapoints")
                total = int(buf.splitlines()[0])
                buf = buf[len(buf.splitlines()[0])+1:]    # get rid of the first line
                #except ValueError :
                #    total = 10000   # go until we're sure we're done...
            if 0 < total and len(buf) >= total * histStruct.size :# and comm.serobj.inWaiting() == 0 :
                break
            time.sleep(0.03)
            print '.',
        else :
            print("Wanted %i bytes; got %i. Failing!" %(total * histStruct.size, len(buf)))
            return
        print len(buf) / histStruct.size, "datapoints read."
    
        # parse out the structures
        self.ts = []
        self.ps = []
        self.vs = []
        self.pos_error_derivs = []
        self.cmd_vs = []
        self.target_ps = []
        self.target_vs = []
        self.motor_ps = []
        stamp = timeStamped("")
        with open("dumps/" + stamp + 'ctrlHistory.csv', "w") as fout :
            fout.write("Time(s*1e5), Position (tics), Velocity (tics/min), Command Velocity (tics/min), Target Position (tics), Target Velocity (tics/min), Motor Position (tics)\n")
            for i in range(0, total * histStruct.size, histStruct.size) :
                d = histStruct.unpack_from(buf, i)
                fout.write("%f, %i, %f, %f, %f, %f, %i\n" % d)
                self.ts.append(d[0] * 0.00001)
                self.ps.append(d[1])
                #vs.append(d[2])
                self.pos_error_derivs.append(d[2])
                self.cmd_vs.append(d[3])
                self.target_ps.append(d[4])
                self.target_vs.append(d[5])
                self.motor_ps.append(d[6])
        
        self.plotData()
        
        # also save off a copy of the machine at this time (so we know what was going on later)
        mach.machine.save("dumps/" + stamp + 'machine.xml')

    def readHistFromFile(self, csvfname) :
        # read back the history from file
        self.ts = []
        self.ps = []
        self.vs = []
        self.pos_error_derivs = []
        self.cmd_vs = []
        self.target_ps = []
        self.target_vs = []
        self.motor_ps = []
        
        with open(csvfname, "r") as fin :
            fin.readline()      # read header line
            for line in fin :
                r = re.compile("[ \t\n\r,]+")
                d = r.split(line)
                if len(d) < 7 :
                    break       # we're done with the file
                self.ts.append(float(d[0]) * 0.00001)
                self.ps.append(int(d[1]))
                #vs.append(d[2])
                self.pos_error_derivs.append(float(d[2]))
                self.cmd_vs.append(float(d[3]))
                self.target_ps.append(float(d[4]))
                self.target_vs.append(float(d[5]))
                self.motor_ps.append(float(d[6]))
        
        self.plotData()
                
    def plotData(self) :
        """Plots the data generated using readCtrlHistory and/or streaming and stored in the class's data arrays"""
        
        # plot the data!
        if len(self.figwindows) == 0 :
            self.figwindows.append(plotgui.PlotWindow())
            self.figwindows[0].move(0,0)
            self.figwindows.append(plotgui.PlotWindow())
            self.figwindows[1].move(400, 0)
            self.figwindows.append(plotgui.PlotWindow())
            self.figwindows[2].move(800, 0)
            self.figwindows.append(plotgui.PlotWindow())
            self.figwindows[3].move(1200, 0)
        
        self.traces = []
        
        fig = self.figwindows[0].init_plot()
        self.traces.append(self.Trace(fig, self.ts, self.ps, 'b-','Position'))
        fig.hold(True)
        self.traces.append(self.Trace(fig, self.ts, self.target_ps, 'r--','Target Position'))
        fig.legend(loc=2)
        fig.xaxis.label.set_text('Time (s)')
        fig.yaxis.label.set_text('Position (encoder tics)')
        fig.title.set_text('Position Tracking')
        # NOTE: additional properties of the plot (text size, etc) are set using 
        # the matplotlibrc file in the project folder.
        
        self.figwindows[0].render_plot()
        self.figwindows[0].show()
        
        fig = self.figwindows[1].init_plot()
        #fig.plot(ts, vs, 'c-', label='Velocity')
        fig.hold(True)
        self.traces.append(self.Trace(fig, self.ts, self.target_vs, 'r--','Target Velocity'))
        self.traces.append(self.Trace(fig, self.ts, self.cmd_vs, 'g-', 'Command Velocity'))
        fig.legend(loc=2)
        fig.xaxis.label.set_text('Time (s)')
        fig.yaxis.label.set_text('Velocity (encoder tics/min)')
        fig.title.set_text('Velocity Tracking')
        
        self.figwindows[1].render_plot()
        self.figwindows[1].show()
        
        fig = self.figwindows[2].init_plot()
        self.traces.append(self.Trace(fig, self.ts, self.ps, 'b-', 'Encoder Position'))
        fig.hold(True)
        self.traces.append(self.Trace(fig, self.ts, self.motor_ps, 'g-', 'Motor Step Position'))
        fig.legend(loc=2)
        fig.xaxis.label.set_text('Time (s)')
        fig.yaxis.label.set_text('Position (encoder tics)')
        fig.title.set_text('Motor Reported Location')
        
        self.figwindows[2].render_plot()
        self.figwindows[2].show()
        
        fig = self.figwindows[3].init_plot()
        self.traces.append(self.Trace(fig, self.ts, self.pos_error_derivs, 'b-', 'Position Error Derivative'))
        fig.xaxis.label.set_text('Time (s)')
        fig.yaxis.label.set_text('Error change (tics/update)')
        fig.title.set_text('Position Error Derivative')
        
        self.figwindows[3].render_plot()
        self.figwindows[3].show()
    
    
    def closeWindows(self) :
        if self.streaming :
            self.stopStreamPlot()
        for fig in self.figwindows :
            fig.hide()
            fig.close()
            fig.deleteLater()
            sip.delete(fig)
        while len(self.figwindows) > 0 :
            self.figwindows.pop()
        
    '''
    # Starts a stream plot; creating the windows if they weren't already and 
    # opening a file to save the results to. This is depricated in favor of
    # the RawHID communication channel.
    def startStreamPlot(self) :
        """Starts a stream plot"""
        # Comm init is handled by the issuing command (and should be "ss 1")
        
        # Clear the ads streams
        comm.GetAds()
        
        self.ts = []
        self.ps = []
        self.pos_error_derivs = []
        self.cmd_vs = []
        self.target_ps = []
        self.target_vs = []
        self.motor_ps = []
        
        self.streaming = True
        
        self.plotData()
        
        # open a file to save this strip plot to:
        stamp = timeStamped("")
        self.fstream = open("dumps/" + stamp + 'ctrlStream.csv', "w")
        
        # also save off a copy of the machine at this time (so we know what was going on later)
        mach.machine.save("dumps/" + stamp + 'machine.xml')
        
        self.plotData()
        
        # setup the animation
        self.anim = animation.FuncAnimation(self.figwindows[0], self.updateStreamPlot, interval=10, blit=False)
        
        
    def updateStreamPlot(self, args) :
        """Updates the stream plot, reading new data from the device"""
        print "In Update"
        
        for d in comm.GetAds() :
            d = histStruct.unpack_from(buf, i)
            try :
                self.fstream.write("%f, %i, %f, %f, %f, %f, %i\n" % d)
            finally :
                pass
            self.ts.append(d[0] * 0.00001)
            self.ps.append(d[1])
            #vs.append(d[2])
            self.pos_error_derivs.append(d[2])
            self.cmd_vs.append(d[3])
            self.target_ps.append(d[4])
            self.target_vs.append(d[5])
            self.motor_ps.append(d[6])
        
        out = []
        for tr in self.traces :
            tr.update()
            out.append(tr.line2d)
        
        return out
    
    def stopStreamPlot(self) :
        """Stops stream plotting"""
        # stop recording
        self.fstream.close()
        self.streaming = False
    '''
    
    def startStreaming(self) :
        """Starts streaming collection of data from the device, saved to a time-stamped
        .bin file in the streams directory using the RawHID USB mode. This works better
        than the old plotter.startStreamPlot mode, which used the serial console."""
        # tell the rawhid interface program to start saving out data streams
        self.streaming = True
        fbase = "streams/" + timeStamped(comm.port)
        self.stream_fname = fbase + "stream.bin"
        comm.DataStreamStartSave(DS_STREAM_HIST, self.stream_fname)
        
        # also save off a copy of the machine at this time (so we know what was going on later)
        mach.machine.save(fbase + 'machine.xml')
        
        # tell the device to start streaming
        comm.Write("ss 1")

    def stopStreaming(self) :
        """Stops streaming collection of data from the device being saved to the .bin
        file, converts the .bin to .csv, and shows the results."""
        # disable streaming
        comm.Write("ss 0")
        
        # tell the rawhid proxy to stop saving the data stream
        comm.DataStreamStopSave(DS_STREAM_HIST)
        
        self.streaming = False
        
        # convert the .bin to .csv
        newname = self.stream_fname[:-3] + 'csv'
        convertBinaryDump(self.stream_fname, newname)
        
        # display the data
        self.readHistFromFile(newname)
        
    
                
    
    
plotter = Plotter()

if __name__ == "__main__" :
    try :
        app = QtGui.QApplication(sys.argv)
        #comm.Open("COM6", 119200)
        #readCtrlHistory()
        plotter.startStreamPlot()
        plotter.updateStreamPlot()
        app.exec_()
    finally :
        comm.Close()
