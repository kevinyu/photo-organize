"""
Collect the datetimes of all photos

This script is expanded to not just get datetimes but also when there are AAE files and
find their actual image pairs
"""

import datetime
import glob
import io
import os
import pickle
import pprint
import time
from collections import defaultdict

from PIL import Image, UnidentifiedImageError
import exifread
import ffmpeg
import pyheif
import tqdm

import config
from filesystem import search

pp = pprint.PrettyPrinter(indent=4)


def _time_parser(time_string):
    try:
        return datetime.datetime.strptime(time_string, '%Y:%m:%d %H:%M:%S')
    except ValueError:
        pass

    try:
        return datetime.datetime.strptime(time_string, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        pass

    try:
        return datetime.datetime.strptime(time_string, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError:
        pass

    raise ValueError("Could not find a time parser for time {}".format(time_string))


def detect_by_date_taken(root):
    results = []
    progressbar = tqdm.tqdm(search(root))

    time1 = 0
    time2 = 0
    time3 = 0

    lone_aae = []
    aae_img_map = {}

    for filename in progressbar:
        progressbar.set_description("Looking in {}".format(os.path.dirname(filename)))

        name, ext = os.path.splitext(filename)
        if ext.lower() == ".aae":
            corresponding_images = [f for f in glob.glob("{}*".format(name)) if f != filename]
            if not len(corresponding_images):
                lone_aae.append(filename)
                print("AAE has no corresponding image(s)")
            else:
                for i in corresponding_images:
                    aae_img_map[i] = name
            continue

        date_taken = None
        _start = time.time()
        try:
            with Image.open(filename) as imagefile:
                exif = imagefile.getexif()
            date_taken = exif.get(36867, exif.get(36868))
        except UnidentifiedImageError:
            pass
        else:
            if date_taken is not None:
                date_taken = datetime.datetime.strptime(date_taken, '%Y:%m:%d %H:%M:%S')
        time1 += time.time() - _start

        _start = time.time()
        if date_taken is None:
            try:
                date_taken = ffmpeg.probe(filename)["format"]["tags"]["creation_time"]
            except:
                pass
            else:
                if date_taken is not None:
                    date_taken = _time_parser(date_taken)
        time2 += time.time() - _start

        _start = time.time()
        if date_taken is None:
            try:
                with open(filename, "rb") as imagefile:
                    exifdata = pyheif.read_heif(imagefile).metadata[0]["data"][6:]
                exifdata = exifread.process_file(io.BytesIO(exifdata))
                _date_taken = exifdata.get("EXIF DateTimeOriginal")
            except ValueError:
                pass
            except:
                raise
            else:
                if _date_taken is not None:
                    date_taken = _time_parser(str(_date_taken))
        time3 += time.time() - _start

        if date_taken:
            results.append((
                date_taken,
                (date_taken.year, date_taken.month),
                (date_taken.year, date_taken.month, date_taken.day),
                os.path.dirname(filename),
                filename
            ))
        else:
            results.append((
                None,
                None,
                None,
                os.path.dirname(filename),
                filename
            ))

    print("FinisheD")
    print("""
    time1: {:.2f}
    time2: {:.2f}
    time3: {:.2f}
    """.format(time1, time2, time3))

    return results, lone_aae, aae_img_map


if __name__ == "__main__":
    import sys
    impath = sys.argv[1]

    if os.path.exists(config.FILE_METADATA_PICKLE_FILE):
        with open(config.FILE_METADATA_PICKLE_FILE, "rb") as picklefile:
            results = pickle.load(picklefile)
    else:
        results = detect_by_date_taken(impath)
        with open(config.FILE_METADATA_PICKLE_FILE, "wb") as picklefile:
            pickle.dump(results, picklefile)

    results, lone_aae, aae_img_map = results

    month_sets = defaultdict(list)
    year_sets = defaultdict(list)
    for result in results:
        if result[0] is None:
            continue
        month_sets[result[1]].append(result[4])
        year_sets[result[0].year].append(result[4])

    no_timestamp_results = [r for r in results if r[0] is None]
    pp.pprint([r[4] for r in no_timestamp_results])

    print("""
    Found {} lone AAE files.
    {} had corresponding image files.
    """.format(len(lone_aae), len(aae_img_map)))

    print("""
    Found {} images.
    {} did not have timestamps.
    """.format(
        len(results),
        len(no_timestamp_results)
    ))

    sorted_month_sets = sorted(month_sets.items())
    for month, val in sorted_month_sets:
        print("{}: {}".format(month, len(val)))

