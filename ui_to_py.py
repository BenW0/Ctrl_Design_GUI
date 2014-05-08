# Converts a QtDesigner .ui file into a Python sourcecode file.

from PyQt4 import uic

fout = open("ui_gui.py",'w')
uic.compileUi('gui.ui', fout, True)
fout.close()
