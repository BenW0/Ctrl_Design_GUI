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
# Not licensed. Internal development only!
#
########################################################

import serial as ser
import serial.tools.list_ports as lp


serobj = ser.Serial()
ads_data = []

# Returns a list of serial ports as a list of touples
# Touples contain (<port name>, <description>, <location>)
def GetComPorts() :
    mylist = []
    for i in lp.comports() :
        mylist.append(i)
    mylist.sort()
    return mylist

# if escape is set, incoming data will be scanned for the 
# escape character, and if found, the following escape_len bytes
# will be saved off and can be retrieved using the ads functions.
def Open(port, speed, escape="", escape_len=0) :
    serobj.setPort(port)
    serobj.setBaudrate(speed)
    serobj.setTimeout(5)
    serobj.open()
    # set up escape trapping
    serobj.escape = escape
    serobj.escape_len = escape_len

def Close() :
    serobj.close()

def IsOpen() :
    return serobj.isOpen()

# Dumps all serial input waiting on the buffer to the console.
def DumpToConsole() :
    if serobj.isOpen() :
        txt = serobj.read(serobj.inWaiting())
        if serobj.escape == "" :
            if len(txt) > 0 :
                print txt,
        else :
            # make sure we don't end mid-ads sequence
            #while txt.rfind(serobj.escape) > len(txt) - serobj.escape_len :
                # we have an escape and the packet contains a newline character. Read another line and append.
            #    txt = txt + serobj.readline()
            txt = AdsScan(txt)
            if len(txt) > 0 :
                print txt,
            

# Sends <data> to the device (if open)
def Write(data) :
    if serobj.isOpen() :
        serobj.write(data)

# Reads everything on the current buffer to the console
def Read() :
    if serobj.isOpen() :
        txt = serobj.read(serobj.inWaiting())
        if serobj.escape == "":
            return txt
        else :
            # make sure we don't end mid-ads sequence
            while txt.rfind(serobj.escape) > len(txt) - serobj.escape_len :
                # we have an escape and the packet contains a newline character. Read another line and append.
                txt = txt + serobj.readline()
            return AdsScan(txt)
        

# Reads until the next newline
def ReadLn() :
    if serobj.isOpen() :
        if serobj.escape == "":
            return serobj.readline()
        else :
            # scan through the data and look for ads escapes
            line = serobj.readline()
            while line.rfind(serobj.escape) > len(line) - serobj.escape_len :
                # we have an escape and the packet contains a newline character. Read another line and append.
                line = line + serobj.readline()
            return AdsScan(line)
        
# scans a string for ads escape sequences and removes them.
def AdsScan(str) :
    i = str.find(serobj.escape)
    while i >= 0 :
        if len(str) > i + serobj.escape_len :
            #ads_data.append(str[i+1:i+1+serobj.escape_len])
            str = str[:i] + str[i+1+serobj.escape_len:]
        i = str.find(serobj.escape)
    return str

# returns the list of alternate data stream packets that have been found, 
# then clears the internal buffer.
def GetAds() :
    global ads_data
    tmp = ads_data
    ads_data = []
    return tmp