########################################################
# Control Design GUI: serial.py
# Interfaces with serial COM port and handles communicating
# with the microcontroller.
#
# Ben Weiss, University of Washington
# Spring 2014
#
# This module creates a common comm object that impelements either comm_rawhid.py
# or comm_serial.py. This would be a good place for some subclassing when I 
# next rewrite things...
#
# Not licensed. Internal development only!
#
########################################################

from comm_serial import *
from comm_rawhid import *


CM_SERIAL = 1
CM_RAWHID = 2
COMM_MODE = CM_RAWHID      # or CM_SERIAL

if COMM_MODE == CM_SERIAL :
    comm = Serobj()
elif COMM_MODE == CM_RAWHID :
    comm = Rawhid()
else :
    comm = None