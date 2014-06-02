########################################################
# Control Design GUI machine.py
# Reads and sets up datastructures for the machine's commands
# and parameters, and abstracts serial communication with the device.
#
# Ben Weiss, University of Washington
# Spring 2014
#
# NOTE: Machine.xml contains "Action" fields which are directly
# executed in the current Python context with exec. If this is evern
# used in a situation in which security matters, this practice should
# be changed!
#
# XML parsing tutorial used:
# http://www.blog.pythonlibrary.org/2013/04/30/python-101-intro-to-xml-parsing-with-elementtree/
#
# Other code snipped from:
# http://stackoverflow.com/questions/2175080/sscanf-in-python
#
# Not licensed. Internal development only!
#
########################################################

import xml.etree.cElementTree as ET
import comm
import time
import re
import scripts


machine = None


# Machine can't currently create or delete params or cmds and have
# the results propigate back to the xml file.
class Machine :
    
    

    # load a machine from an xml ElementTree root
    def __init__(self, fname) :
        self.name = ''
        self.debugstr = ''
        self.get_cmd = ''
        self.set_cmd = ''
        self.cmds = []
        self.params = []
        self.tabs = []
    
        self.xmltree = ET.ElementTree(file=fname)
        
        root = self.xmltree.getroot()
        
        if root.tag != 'Machine' :
            print("Could not parse XML. Root is not a 'Machine'")
            return
        if root.attrib.has_key('name') :
            self.name = root.attrib['name']
        if root.attrib.has_key('debugstr') :
            self.debugstr = root.attrib['debugstr']
        if root.attrib.has_key('getparam') :
            self.get_cmd = root.attrib['getparam']
        if root.attrib.has_key('setparam') :
            self.set_cmd = root.attrib['setparam']

        for child in root :
            if child.tag == 'Commands' :
                for cmd in child :
                    self.cmds.append(Command(cmd))
            elif child.tag == 'Parameters' :
                for param in child :
                    p = Param(param)
                    self.params.append(p)
                    try :
                        self.tabs.index(p.tab)
                    except ValueError :
                        self.tabs.append(p.tab)

    # loads only settings from an xml file, not structure!
    def loadSettings(self, fname) :
        valuetree = ET.ElementTree(file=fname)

        vroot = valuetree.getroot()

        if vroot.tag != 'Machine' :
            print('Invalid settings file!')
            return
        for child in vroot :
            if child.tag == 'Parameters' :
                for vparam in child :
                    if vparam.attrib.has_key('name') :
                        for param in self.params :
                            if param.name.lower() == vparam.attrib['name'].lower() :
                                param.value = vparam.text
                                param.default_value = vparam.text

    # saves back the Machine structure to the xml file
    def save(self, fname) :
        root = self.xmltree.getroot()
        root.set('name', self.name)
        root.set('debugstr', self.debugstr)
        root.set('getparam', self.get_cmd)
        root.set('setparam', self.set_cmd)
        for cmd in self.cmds :
            cmd.updatexml()
        for param in self.params :
            param.updatexml()

        self.xmltree.write(fname)



class Command :
    

    def __init__(self) :
        self.name = ''
        self.cmd = ''
        self.action = ''
        self.xmlnode = None
    
    def __init__(self, xmlnode) :
        self.xmlnode = xmlnode
        if xmlnode.tag != "Command" :
            print("XML syntax error!")
            return
            
        if xmlnode.attrib.has_key('name') :
            self.name = xmlnode.attrib['name']
        if xmlnode.attrib.has_key('cmd') :
            self.cmd = xmlnode.attrib['cmd']
        self.action = xmlnode.text

    # updates the xml object linked to this class in the hierarchy.
    def updatexml(self) :
        if self.xmlnode != None :
            self.xmlnode.set('name', self.name)
            self.xmlnode.set('cmd', self.cmd)
            self.xmlnode.text = self.action

    # Performs the action by sending the serial command
    # to the device, then performing whatever action is desired.
    def doAction(self) :
        if comm.IsOpen() :
            print ">" + self.cmd
            comm.Write(self.cmd)
            if self.action != '' and self.action != None :
                exec self.action



class Param :
    

    def __init__(self) :
        self.name = ''
        self.cmd = ''
        self.readOnly = False
        self.datatype = 'Int'
        self.value = 0
        self.default_value = 0
        self.tab = ''
        self.xmlnode = None

    def __init__(self, xmlnode) :
        self.xmlnode = xmlnode
        if xmlnode.tag != 'Parameter' :
            print("XML syntax error!")
            return

        if xmlnode.attrib.has_key('name') :
            self.name = xmlnode.attrib['name']
        if xmlnode.attrib.has_key('cmd') :
            self.cmd = xmlnode.attrib['cmd']
        if xmlnode.attrib.has_key('readonly') :
            self.readOnly = xmlnode.attrib['readonly']
        if xmlnode.attrib.has_key('type') :
            self.datatype = xmlnode.attrib['type']
        if xmlnode.attrib.has_key('tab') :
            self.tab = xmlnode.attrib['tab']
        self.value = xmlnode.text
        self.default_value = xmlnode.text

    def updatexml(self) :
        if self.xmlnode != None :
            self.xmlnode.set('name', self.name)
            self.xmlnode.set('cmd', self.cmd)
            self.xmlnode.set('readonly', str(self.readOnly))
            self.xmlnode.set('type', self.datatype)
            self.xmlnode.set('tab', self.tab)
            self.xmlnode.text = str(self.value)

    # Queries the device for the value of this parameter and updates self.value
    def getFromDevice(self, quiet=False) :
        if comm.IsOpen() :
            if not quiet :
                print ">" + machine.get_cmd + self.cmd
            comm.Write(machine.get_cmd + self.cmd)
            for i in range(0,5) :   # read a few lines in case there's other dribble
                line = comm.ReadLn()
                #print '"' + line + '"'
                if '' == line :
                   print "No return!"
                   return True
                if line[0] != machine.debugstr :
                    r = re.compile("[ \t\n\r]+")
                    data = r.split(line)[0]
                    # cast data to the right form
                    try :
                        if self.datatype.lower() == "int" :
                            self.value = int(data)
                        elif self.datatype.lower() == "uint" :
                            self.value = int(data)
                        elif self.datatype.lower() == "float" :
                            self.value = float(data)
                        else :  # assumed to be string, keep the whole line
                            self.value = data
                        return True
                    except ValueError :
                        if not quiet :
                            print("Error parseing response from chip! Tried to parse '%s' and failed. Whole line: %s" % (data, line))
                        return False
                else :
                    print line + ";"
        return False

    # Sets the value to the device
    def setToDevice(self) :
        if comm.IsOpen() :
            print ">" + machine.set_cmd + self.cmd + ' ' + str(self.value)
            comm.Write(machine.set_cmd + self.cmd + ' ' + str(self.value))
    
    # Restores the value to default and sets the value to the device.
    def restoreDefault(self) :
        self.value = self.default_value
        if comm.IsOpen() :
            print ">" + machine.set_cmd + self.cmd + ' ' + str(self.value)
            comm.Write(machine.set_cmd + self.cmd + ' ' + str(self.value))

    # Validates the value newvalue, and if it is OK, stores it locally.
    # Returns True for successful parse and store, False otherwise
    def setValidValue(self, newvalue) :
        try :
            if self.datatype.lower() == "uint" :
                self.value = abs(int(newvalue))
            elif self.datatype.lower() == "int" :
                self.value = int(newvalue)
            elif self.datatype.lower() == "float" :
                self.value = float(newvalue)
            else :
                self.value = newvalue
            return True
        except ValueError :
            return False


        
# Loads a machine from a file
def loadMachine(fname) :
    global machine
    machine = Machine(fname)

if __name__ == "__main__" :
    loadMachine('machine.xml')
