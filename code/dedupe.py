"""
Search for potentially duplicate files by date taken and size
"""

from collections import defaultdict
import os
import glob

from PIL import Image, ImageQt
import tqdm

import PyQt5.QtWidgets as widgets
import PyQt5.QtGui as gui
from PyQt5.QtCore import Qt



def get_info(impath):
    with Image.open(impath) as imagefile:
        result = {
            "filesize": os.stat(impath).st_size,
            "size": imagefile.size,
            "creation_time": imagefile.getexif().get(36867),
            "format": imagefile.format,
            "exif": imagefile.getexif()
        }
    result["hash"] = "{filesize}:{size}:{format}".format(**result)
    return result


def superhash(impath):
    with Image.open(impath) as imagefile:
        result = {
            "filesize": os.stat(impath).st_size,
            "size": imagefile.size,
            "format": imagefile.format,
            "pixel0": imagefile.getpixel((0, 0)),
            "pixel1": imagefile.getpixel((imagefile.size[0]//2, imagefile.size[1]//2)),
            "exif": imagefile.getexif()
        }
    result["hash"] = "{filesize}:{size}:{pixel0}:{pixel1}:{format}".format(**result)
    return result


def search(root):
    for f in glob.glob(os.path.join(root, "*")):
        if os.path.isdir(f):
            for result in search(f):
                yield result
        else:
            yield f


def filter_duplicates(hashes):
    return {k: v for k, v in hashes.items() if len(v) > 1}


def pretty(info):
    string = """
    Taken: {}
    Source: {}
    """.format(info["exif"].get(36867), info["exif"].get(42036))
    return string


class SelectionWindow(widgets.QWidget):
    def __init__(self, path):
        super().__init__()
        self.path = path
        self.init_ui()

    def init_ui(self):
        self.layout = widgets.QVBoxLayout()
        self.setLayout(self.layout)

        self.layout.addWidget(widgets.QLabel(self.path))
        self.layout.addWidget(widgets.QLabel(pretty(get_info(self.path))))

        im = gui.QImage(self.path)
        pixmap = gui.QPixmap.fromImage(im.scaled(500, 500, Qt.KeepAspectRatio))
        label = widgets.QLabel(self)
        label.setPixmap(pixmap)
        self.layout.addWidget(label)

        button = widgets.QPushButton("Remove")
        self.layout.addWidget(button)


class DuplicateFinder(widgets.QWidget):
    def __init__(self, hashes):
        super().__init__()
        self.hashes = hashes
        self.have_duplicates = list(filter_duplicates(self.hashes).keys())
        self.index = 0
        self.init_ui()
        self.render()
        self.show()

    def init_ui(self):
        self.setWindowTitle("DeDuper")
        self.layout = widgets.QVBoxLayout()
        dropdown = widgets.QComboBox(self)
        for i in range(len(self.have_duplicates)):
            dropdown.addItem("{} {}".format(
                i,
                ";".join([os.path.basename(f) for f in self.hashes[self.have_duplicates[i]]])
            ))
        dropdown.activated.connect(self.choose_index)

        self.selection_layout = widgets.QHBoxLayout()
        self.layout.addWidget(dropdown)
        self.layout.addLayout(self.selection_layout)
        self.setLayout(self.layout)

    def set_images(self, images):
        for path in images:
            self.selection_layout.addWidget(SelectionWindow(path))

    def choose_index(self, idx):
        for i in reversed(range(self.selection_layout.count())):
            w = self.selection_layout.itemAt(i).widget()
            if isinstance(w, SelectionWindow):
                w.deleteLater()
        self.index = idx % len(self.have_duplicates)
        self.render()

    def render(self):
        k = self.have_duplicates[self.index]
        v = self.hashes[k]
        self.set_images(v)


if __name__ == "__main__":
    import sys
    impath = sys.argv[1]

    print("Searching for duplicates")

    hashes = defaultdict(list)
    duplicates_found = 0

    progressbar = tqdm.tqdm(search(impath))
    for filename in progressbar:
        progressbar.set_description("Duplicates Found: {}. Looking in {}".format(duplicates_found, os.path.dirname(filename)))
        try:
            info = get_info(filename)
        except:
            hashes[filename].append(filename)
        else:
            if info["hash"] in hashes:
                duplicates_found += 1
            hashes[info["hash"]].append(filename)

    hashes = filter_duplicates(hashes)
    print("Validating {} potential duplicates".format(len(hashes)))
    superhashes = defaultdict(list)
    for k, v in tqdm.tqdm(list(filter_duplicates(hashes).items())):
        # If all the filenames in v have the same creation date, we're good
        if len(set([get_info(filename)["creation_time"] for filename in v])) == 1:
            superhashes[k] = v
            continue

        ## If not, we include some pixel info in the hash (excluded before because its much slower)
        for filename in v:
            try:
                info = superhash(filename)
            except:
                superhashes[filename].append(filename)
            else:
                superhashes[info["hash"]].append(filename)

    superhashes = filter_duplicates(superhashes)
    print("Identified {} duplicates".format(len(superhashes)))
    print("Launching GUI...")

    app = widgets.QApplication(sys.argv)
    ex = DuplicateFinder(superhashes)
    sys.exit(app.exec_())
