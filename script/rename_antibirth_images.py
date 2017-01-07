#antibirth images come with an x at the end, but the log prints them with a 1 at the front
import os, re, shutil
for f in os.listdir('.'):
    if os.path.isfile(f):
        m = re.match("collectibles_(\d\d\d)x_.*\.png", f)
        if m:
            id = m.group(1)
            shutil.move(f, "collectibles_1" + id + ".png")

