"""Utility functions for navigating the filesystem
"""

import os
import glob


def search(root):
    """Generator function to crawl all files in directory"""
    for f in glob.glob(os.path.join(root, "*")):
        if os.path.isdir(f):
            for result in search(f):
                yield result
        else:
            yield f
