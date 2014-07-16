########################################################
# Control Design GUI: serial.py
# Interfaces with serial COM port and handles communicating
# with the microcontroller.
#
# Ben Weiss, University of Washington
# Spring 2014
#
# This module creates a Python interface for the rawhid_listener.exe program which
# translates packets back and forth to the Teensy and its stdin/stdout, as well
# as to files with a little setup.
#
# Not licensed. Internal development only!
#
########################################################


from PyQt4 import uic, QtCore, QtGui
import sys, time


class Rawhid() :
    
    def __init__(self) :
        
        self.open = False
        self.buf = ''
        self.portlist = []
        
    
    def Init(self) :
        self.proc = QtCore.QProcess() 
        self.proc.start("rawhid_listener.exe")
        self.proc.setProcessChannelMode(QtCore.QProcess.MergedChannels);
        self.proc.readyReadStandardOutput.connect(self.readStdOutput)
        # wait for the program to boot
        print self.ReadBlocking(300)
        print "rawhid_listener.exe interface active."
        
        
        #self.GetComPorts()
        
    #Slot that handles new data from the listener, buffering it internally.
    def readStdOutput(self):
        self.buf = self.buf + str(self.proc.readAllStandardOutput())
        #print "StdOut hook.\n"# '" + self.buf + "'"
    
    
    # Returns a list of serial ports as a list of touples
    # Touples contain (<port name>, <description>, <location>)
    def GetComPorts(self) :
        self.portlist = []
        self.DumpToConsole()
        self.proc.writeData('i\n')
        for i in range(0, 10) :
            txt = str(self.ReadLn())
            if len(txt) == 2 :
                self.portlist.append(txt)
            elif len(txt) > 2 :
                break;
        return self.portlist
    
    
    # port here refers to the index in the list returned by GetComPorts to open.
    # speed, extra and extra2 are retained for backwards-compatibility
    def Open(self, port='0', speed='n/a', extra='', extra2='') :
        self.proc.writeData('n ' + port + '\n')
        self.port = port
        print 'n ' + port + '\n'
        # we don't actually check that it opened...at least not for now.
        self.open = True
    
    def Close(self) :
        self.proc.writeData('c\n')
        self.open = False
    
    def Quit(self) :
        self.proc.writeData('q\n')
        time.sleep(0.1)
        self.proc.close()
    
    def IsOpen(self) :
        return self.open
    
    # Dumps all serial input waiting on the buffer to the console.
    def DumpToConsole(self) :
        #print self.proc.bytesAvailable()
        #print "DumpToConsole: '" + self.buf + "'"
        txt = self.ReadBlocking(50) #self.buf #self.proc.readAll()#
        if len(txt) > 0 :
            print txt,
        #self.buf = ''
            
                
    
    # Sends <data> to the device (if open)
    def Write(self, data) :
        if self.open :
            self.proc.writeData(">" + data + "\n")
    
    # Reads everything on the current buffer to the console
    def Read(self) :
        txt = self.buf + str(self.proc.readAllStandardOutput())
        self.buf = ''
        return txt
    
    # a version of read that blocks until there is at least *something* to read.
    def ReadBlocking(self, msec) :
        #if self.buf != '' :
        self.proc.waitForReadyRead(msec)
        return self.Read()
    
    # Reads until the next newline
    def ReadLn(self) :
        txt = ''
        # look through buf until we find a readline
        for i in range(0, 50) :
            #txt = self.proc.readLine()
            #print '"' + txt + '"',
            #if txt != "" :
            #    break
            self.buf = self.buf + str(self.proc.readAllStandardOutput())
            if self.buf.find('\n') >= 0 :
                txt = self.buf[:self.buf.find('\n')]
                self.buf = self.buf[self.buf.find('\n')+1:]
                #print "Readline: '" + txt + "'"
                return txt
            #time.sleep(0.05)     # more text will buffer automatically
            self.proc.waitForReadyRead(50)
        else :
            print "Timeout waiting for readline!"
        return txt
            
    # scans a string for ads escape sequences and removes them. Not relevent for comm_rawhid.py
    def AdsScan(self, str) :
        return str
    
    # not relevant here.
    def GetAds(self) :
        return []
    
    # start saving a data stream to a given file. This only applies to the RawHID
    # operation mode. ds_id is 0, 1, or 2 and corresponds to the packet_type in
    # rawhid_msg.h
    def DataStreamStartSave(self, ds_id, fname) :
        if self.open :
            self.proc.writeData("p " + `ds_id` + " " + fname + "\n")
    
    # stops saving a data stream to a file. Only applies to RawHID operating mode.
    # ds_id is 0, 1, or 2 and corresponds to packet_type in rawhid_msg
    def DataStreamStopSave(self, ds_id) :
        if self.open :
            self.proc.writeData("p " + `ds_id` + "\n")
            
    # Writes data stream packets to the console. Only applies to RawHID operating mode.
    # ds_id is 0, 1, or 2 and corresponds to packet_type in rawhid_msg
    def DataStreamToConsole(self, ds_id, enable) :
        if self.open :
            if enable :
                self.proc.writeData("d " + `ds_id` + " on\n")
            else :
                self.proc.writeData("d " + `ds_id` + " off\n")
                
