########################################################
# Control Design GUI: serial.py
# Interfaces with serial COM port and handles communicating
# with the microcontroller.
#
# Ben Weiss, University of Washington
# Spring 2014
#
# This module exports many of the serial.Serial() methods for use
# elsewhere in the project. In addition to simply reading and writing
# data from the serial port, it allows an "alternate data stream"
# (ads) to be configured. In this mode, every read from the device is filtered,
# searching for an escape sequence (specified as escape in Open). When
# found, the following few bytes (escape_len) are saved off to a separate
# list and then eliminated from the data returned to the caller. A separate
# function, GetAds(), returns this separate list of data elements. This is
# designed to support continuous background data plotting along with normal operation.
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

import serial as ser
import serial.tools.list_ports as lp


class Serobj() :
    
    def __init__(self) :
        self.serobj = ser.Serial()
        self.ads_data = []
        self.portlist = []
        self.escape = ''
        self.ads_data = []
    
    def Init(self) :
        pass
    
    # Returns a list of serial ports as a list of touples
    # Touples contain (<port name>, <description>, <location>)
    def GetComPorts(self) :
        self.portlist = []
        for i in lp.comports() :
            self.portlist.append(i)
        self.portlist.sort()
        return self.portlist
    
    # if escape is set, incoming data will be scanned for the 
    # escape character, and if found, the following escape_len bytes
    # will be saved off and can be retrieved using the ads functions.
    def Open(self, port, speed, escape="", escape_len=0) :
        
        self.serobj.setPort(port)
        self.serobj.setBaudrate(speed)
        self.serobj.setTimeout(5)
        self.port = port
        try :
            self.serobj.open()
        except self.serobj.SerialException as e :
            print(str(e))
            return 0
        # set up escape trapping
        self.escape = escape
        self.escape_len = escape_len
        self.ads_data = []
        return 1
    
    def Close(self) :
        self.serobj.close()
        
    def Quit(self) :
        pass
    
    def IsOpen(self) :
        return self.serobj.isOpen()
    
    # Dumps all serial input waiting on the buffer to the console.
    def DumpToConsole(self) :
        if self.serobj.isOpen() :
            txt = self.serobj.read(self.serobj.inWaiting())
            if self.escape == "" :
                if len(txt) > 0 :
                    print txt,
            else :
                # make sure we don't end mid-ads sequence
                #while txt.rfind(serobj.escape) > len(txt) - serobj.escape_len :
                    # we have an escape and the packet contains a newline character. Read another line and append.
                #    txt = txt + serobj.readline()
                txt = self.AdsScan(txt)
                if len(txt) > 0 :
                    print txt,
                
    
    # Sends <data> to the device (if open)
    def Write(self, data) :
        if self.serobj.isOpen() :
            self.serobj.write(data)
    
    # Reads everything on the current buffer to the console
    def Read(self) :
        if self.serobj.isOpen() :
            txt = self.serobj.read(serobj.inWaiting())
            if self.escape == "":
                return txt
            else :
                # make sure we don't end mid-ads sequence
                while txt.rfind(self.escape) > len(txt) - self.escape_len :
                    # we have an escape and the packet contains a newline character. Read another line and append.
                    txt = txt + self.serobj.readline()
                return self.AdsScan(txt)
            
    def ReadBlocking(self, msec) :
        return self.Read()
    
    # Reads until the next newline
    def ReadLn(self) :
        if self.serobj.isOpen() :
            if self.escape == "":
                return self.serobj.readline()
            else :
                # scan through the data and look for ads escapes
                line = self.serobj.readline()
                while line.rfind(self.escape) >= 0 and line.rfind(self.escape) > len(line) - self.escape_len :
                    # we have an escape and the packet contains a newline character. Read another line and append.
                    line = line + self.serobj.readline()
                return self.AdsScan(line)
            
    # scans a string for ads escape sequences and removes them.
    def AdsScan(self, str) :
        i = str.find(self.escape)
        while i >= 0 :
            if len(str) > i + self.escape_len :
                self.ads_data.append(str[i+1:i+1+serobj.escape_len])
                str = str[:i] + str[i+1+self.escape_len:]
            i = str.find(self.escape)
        return str
    
    # returns the list of alternate data stream packets that have been found, 
    # then clears the internal buffer.
    def GetAds(self) :
        tmp = self.ads_data
        self.ads_data = []
        return tmp

    
    # The following functions are only applicable to comm_rawhid.
    def DataStreamStartSave(self, ds_id, fname) :
        pass
    
    def DataStreamStopSave(self, ds_id) :
        pass
        
    def DataStreamToConsole(self, ds_id, enable) :
        pass