########################################################
# Control Design GUI plotgui.py
# Implements the GUI for separate matplotlib windows. The contents are defined
# elsewhere; this just gives a window with a matlab plot on it.
#
# Ben Weiss, University of Washington
# Spring 2014
#
# This code is modified only slightly from:
# http://matplotlib.org/examples/user_interfaces/embedding_in_qt4_wtoolbar.html
#
# Not licensed. Internal development only!
#
########################################################

from __future__ import print_function

import sys

import numpy as np
from matplotlib.figure import Figure
from matplotlib.backend_bases import key_press_handler
from matplotlib.backends.backend_qt4agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QTAgg as NavigationToolbar)
from PyQt4.QtCore import *
from PyQt4.QtGui import *


class PlotWindow(QMainWindow):
    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        #self.x, self.y = self.get_data()
        self.create_main_frame()
        #self.init_plot()

    def create_main_frame(self):
        self.main_frame = QWidget()

        self.fig = Figure((5.0, 4.0), dpi=82)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(self.main_frame)
        self.canvas.setFocusPolicy(Qt.StrongFocus)
        self.canvas.setFocus()

        self.mpl_toolbar = NavigationToolbar(self.canvas, self.main_frame)

        self.canvas.mpl_connect('key_press_event', self.on_key_press)

        vbox = QVBoxLayout()
        vbox.addWidget(self.canvas)  # the matplotlib canvas
        vbox.addWidget(self.mpl_toolbar)
        self.main_frame.setLayout(vbox)
        self.setCentralWidget(self.main_frame)

    # returns an axes object, from which we can call "plot" and all the normal figure stuff.
    def init_plot(self):
        self.fig.clear()
        self.axes = self.fig.add_subplot(111)
        
        return self.axes
        
    # renders the plot to the screen.
    def render_plot(self) :
        self.canvas.draw()

    def on_key_press(self, event):
        print('you pressed', event.key)
        # implement the default mpl key press events described at
        # http://matplotlib.org/users/navigation_toolbar.html#navigation-keyboard-shortcuts
        key_press_handler(event, self.canvas, self.mpl_toolbar)


def main():
    app = QApplication(sys.argv)
    form = PlotWindow()
    form.show()
    app.exec_()

if __name__ == "__main__":
    main()