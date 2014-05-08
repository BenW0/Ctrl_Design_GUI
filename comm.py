########################################################
# Control Design GUI: serial.py
# Interfaces with serial COM port and handles communicating
# with the microcontroller.
#
# Ben Weiss, University of Washington
# Spring 2014
#
# Not licensed. Internal development only!
#
########################################################

import serial as ser
import serial.tools.list_ports as lp


serobj = ser.Serial()

# Returns a list of serial ports as a list of touples
# Touples contain (<port name>, <description>, <location>)
def GetComPorts() :
    mylist = []
    for i in lp.comports() :
        mylist.append(i)
    return mylist


def Open(port, speed) :
    serobj.setPort(port)
    serobj.setBaudrate(speed)
    serobj.setTimeout(5)
    serobj.open()

def Close() :
    serobj.close()

def IsOpen() :
    return serobj.isOpen()

# Dumps all serial input waiting on the buffer to the console.
def DumpToConsole() :
    if serobj.isOpen() :
        while serobj.inWaiting() :
            print serobj.read(serobj.inWaiting()),

# Sends <data> to the device (if open)
def Write(data) :
    if serobj.isOpen() :
        serobj.write(data)

# Reads everything on the current buffer to the console
def Read() :
    if serobj.isOpen() :
        return serobj.read(serobj.inWaiting())

# Reads until the next newline
def ReadLn() :
    if serobj.isOpen() :
        return serobj.readline()
