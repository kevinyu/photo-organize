"""
When searching through photos, detect related photos by datetime

Detect days where more photos are taken than normal, photos are taken close together in time,
and taken in similar locations. Also, even though movies don't have exif data (not sure if
this is true or not, see if we can figure out a good way to group these too)
"""

import datetime
import os
import pickle
import subprocess
import sys
from collections import defaultdict

import matplotlib.pyplot as plt
import numpy as np
import PyQt5.QtWidgets as widgets
import PyQt5.QtGui as gui
from PyQt5.QtCore import Qt, pyqtSignal
from mpl_toolkits import mplot3d
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg

import config
from cmdline_utils import yes_no
from date_utils import CalendarMonthGrid
from plotting_utils import line2d_seg_dist


def load_creation_times(root):
    """Loads the saved timestamp data or prompts to run
    """
    if not os.path.exists(config.FILE_METADATA_PICKLE_FILE):
        if yes_no("The creation time analyzer has not been run yet. Run it?"
                " This might take a bit. (y/n) : "):
            subprocess.call(["python", "code/get_creation_times.py", root])
        else:
            sys.exit(0)

    with open(config.FILE_METADATA_PICKLE_FILE, "rb") as picklefile:
        results = pickle.load(picklefile)

    results, lone_aae, aae_img_map = results
    return results, lone_aae, aae_img_map


class Thumbnail(widgets.QWidget):
    """Panel for a single image and exif data"""
    def __init__(self, path):
        super().__init__()
        self.path = path
        self.init_ui()

    def init_ui(self):
        self.layout = widgets.QVBoxLayout()
        self.setLayout(self.layout)
        im = gui.QImage(self.path)
        pixmap = gui.QPixmap.fromImage(im.scaled(128, 128, Qt.KeepAspectRatio))
        label = widgets.QLabel(self)
        label.setPixmap(pixmap)
        self.layout.addWidget(label)


class PreviewWidget(widgets.QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.layout = widgets.QVBoxLayout()
        self.setLayout(self.layout)

    def clear(self):
        for i in reversed(range(self.layout.count())):
            w = self.layout.itemAt(i).widget()
            if isinstance(w, Thumbnail):
                w.deleteLater()

    def set_images(self, paths):
        self.clear()
        for path in paths:
            thumb = Thumbnail(path)
            self.layout.addWidget(Thumbnail(path))


class PlotWindow(widgets.QWidget):

    coordClicked = pyqtSignal(int, int)

    def __init__(self, width, height):
        super().__init__()
        self.width = width
        self.height = height
        self.init_ui()

    def init_ui(self):
        self.fig = plt.Figure(figsize=(self.width, self.height))
        self.ax = self.fig.add_axes([0, 0, 1, 1], projection="3d")
        self.canvas = FigureCanvasQTAgg(self.fig)

        self.layout = widgets.QHBoxLayout()
        self.layout.addWidget(self.canvas)
        self.setLayout(self.layout)

        self.canvas.mpl_connect('button_press_event', self.on_click)

    def _get_xyz(self, event):
        """
        Get coordinates clicked by user

        Rescued from: https://stackoverflow.com/a/51522454
        """
        if self.ax.M is None:
            return {}

        xd, yd = event.xdata, event.ydata
        p = (xd, yd)
        edges = self.ax.tunit_edges()

        ldists = [(line2d_seg_dist(p0, p1, p), i) for \
                    i, (p0, p1) in enumerate(edges)]
        ldists.sort()

        # nearest edge
        edgei = ldists[0][1]

        p0, p1 = edges[edgei]

        # scale the z value to match
        x0, y0, z0 = p0
        x1, y1, z1 = p1
        d0 = np.hypot(x0-xd, y0-yd)
        d1 = np.hypot(x1-xd, y1-yd)
        dt = d0+d1
        z = d1/dt * z0 + d0/dt * z1

        x, y, z = mplot3d.proj3d.inv_transform(xd, yd, z, self.ax.M)
        return x, y, z

    def on_click(self, event):
        if event.inaxes != self.ax:
            return
        x, y, z = self._get_xyz(event)
        x = int(np.floor(x))
        y = int(np.floor(y))
        self.coordClicked.emit(x, y)


class MainWindow(widgets.QWidget):
    def __init__(self, dataset):
        super().__init__()

        # The dataset is a list where each element is 5:
        # (datetime, month, year, containing folder, image path)
        self.dataset = dataset

        month_sets = defaultdict(list)
        for result in results:
            if result[0] is None:
                continue
            month_sets[result[1]].append(result)
        self.month_sets = sorted(month_sets.items())

        self.init_ui()

        self.plotWindow.coordClicked.connect(
            self.on_click
        )

        self.show()
        self.choose_index(0)

    def get_dataset_months(self):
        return sorted(np.unique([x[1] for x in self.dataset]))

    def init_ui(self):
        self.setWindowTitle("Photo Date Viewer")
        self.layout = widgets.QVBoxLayout()

        self.topBar = widgets.QHBoxLayout()
        self.mainPanel = widgets.QHBoxLayout()
       
        dropdown = widgets.QComboBox(self)
        dropdown.setStyleSheet("combobox-popup: 0;")
        # dropdown.setMaxVisibleItems(5)
        for i in range(len(self.month_sets)):
            dropdown.addItem("{1}/{0}".format(*self.month_sets[i][0]))
        dropdown.activated.connect(self.choose_index)

        self.plotWindow = PlotWindow(6, 6)
        self.plotWindow.ax.set_axis_off()

        self.previewWidget = PreviewWidget()

        self.topBar.addWidget(dropdown)
        self.topBar.addStretch()
        self.mainPanel.addWidget(self.plotWindow)
        self.mainPanel.addWidget(self.previewWidget)
        self.layout.addLayout(self.topBar)
        self.layout.addLayout(self.mainPanel)
        self.setLayout(self.layout)

    def choose_index(self, idx):
        self.current_idx = idx
        self.plotWindow.ax.cla()
        files_in_month = self.month_sets[idx][1]
        dates = [x[0] for x in files_in_month]

        self.draw_calendar(dates)

    def draw_calendar(self, dates):
        self.calendar = CalendarMonthGrid(
            dates[0].month,
            dates[0].year,
            default=0,
            null=-1,
            dtype=np.int
        )
        for date in dates:
            curr = self.calendar.get(date.day)
            self.calendar.set(date.day, curr + 1)

        X, Y, Z = self.calendar.prepare_3d()

        self.plotWindow.ax.bar3d(X, Y, 0, 0.9, 0.9, Z, shade=True)
        self.plotWindow.ax.view_init(85, 2)
        self.plotWindow.ax.grid(False)
        self.plotWindow.ax.set_zlim(0, max(40, np.max(Z)))

        # Turn off z axis labels
        self.plotWindow.ax.set_axis_off()

        # Draw Title
        self.plotWindow.ax.text(-1, 3.5, 0,
            "{} {}".format(dates[0].strftime("%b"), dates[0].year),
            verticalalignment="bottom",
            horizontalalignment="center",
            color="black",
            fontsize=24
        )

        # Draw dates and numbers
        for i, (x, y, z) in enumerate(zip(X, Y, Z)):
            self.plotWindow.ax.text(x + 0.1, y + 0.1, z,
                "{}/{}".format(self.calendar.month, i + 1),
                verticalalignment="top",
                horizontalalignment="left",
                color="white",
                fontsize=6,
            )
            self.plotWindow.ax.text(x + 0.5, y + 0.5, z,
                z,
                verticalalignment="center",
                horizontalalignment="center",
                fontsize=10,
                color="white"
            )

        self.plotWindow.canvas.draw()

    def on_click(self, row, col):
        day = self.calendar.reverse(row, col)
        if day is None:
            return
        self.preview_day(day)

    def preview_day(self, day):
        files_in_month = self.month_sets[self.current_idx][1]
        dates = [x[0] for x in files_in_month]

        files_in_day = [x for x in files_in_month if x[0].day == day]
        self.previewWidget.set_images([
            x[-1] for x in files_in_day[:4]
        ])


if __name__ == "__main__":
    impath = sys.argv[1]
    results, lone_aae, aae_img_map = load_creation_times(impath)
    results = sorted([r for r in results if r[0] is not None])

    # Plot some summaries of the data
    dates = [x[0] for x in results if x[0]]
    dates = [x for x in dates if x.year > 1980]

    app = widgets.QApplication(sys.argv)
    ex = MainWindow(results)
    sys.exit(app.exec_())
