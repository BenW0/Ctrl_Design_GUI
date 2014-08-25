# Controller Configuration GUI
This repository contains the host-side code for configuring, offline-manipulation, and data collection for a Closed-Loop Intelligent Motor Controller platform.

Companion firmware, schamtics, etc: https://sites.google.com/site/benweisspublic/projects/imc-closed-loop-control

(c) 2014, Ben Weiss. See COPYING for licence agreement.

# Dependencies
The Python portion of this code is built on the Numpy/Scipy/Matplotlib stack, and additionally depends on PyQt4.

Some modules utilize PySerial, however this communication mode is deprecated in favor of RawHID.

# RawHID C++ Program
The RawHID C++ program is a small interface executable that reads and writes to the Teensy device over a connection substantially faster and more reliable than COM. It is compiled in Linux using the attached makefile. Linux dependencies are:

  apt-get install mingw32 mingw32-binutils mingw32-runtime

A compiled executable for the Windows platform is included in this repository. This program is used in background by the Python process to pass messages back and forth to the device, as well as to pipe data streams (for recording path tracking and control decision data) directly to files (Python can't handle the data rate very well).

# Using in Standalone Mode
The Control Design GUI can be used in conjunction with a single IMC node outside the context of an IMC network. This is the default behavior for closed loop IMC nodes based on the link cited above. Connect the Teensy to the computer via USB and open main.py. The GUI that appears enumerates the IMC nodes connected to the computer based on their I2C address pins and lists them next to the Port button. Select the device from the list and click Connect.

On the left hand side of the screen are actions that can be performed, either changing the operating mode of the device or executing some kind of script. On the right are a series of tabs which contain parameters stored on the device. These can be read back from the device, modified, written to the device, and reset (hold down Ctrl and click Set to reset the parameter to default). Whole sets of parameters can be loaded into the GUI using the Load Settings and Save Settings buttons. Apply Settings writes all the parameters currently shown to the device at once.

Parameters and commands are defined using the Machine.xml file. As more features are added, or to change the behavior of existing ones, this xml file can be modified to add new action buttons or parameters.

# Using in IMC Network Mode
Connect to the device as before. This time, enter the control mode desired (Unity for open loop, PID for closed loop PID control -- be sure to check the P, I, and D constants in the Ctrl Loop tab). Then, press the IMC mode button to enter IMC listening mode. Now the device will listen and respond to IMC commands sent over the I2C bus.


