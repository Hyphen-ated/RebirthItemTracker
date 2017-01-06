# this is a script to add new item pngs to the repository in the form the tracker expects
# basically we're going from "collectibles_440_kidneystone.png" to "collectibles_440.png"
# this is not part of the tracker itself
import os, re, shutil

files = []
dir_with_new_files = "newitems/"

for file in os.listdir(dir_with_new_files):
    if file.startswith("collectibles_"):
        files.append(file)

for file in files:
    m = re.match("collectibles_(\d\d\d|\d\d\dx)_.*\.png", file)
    newname = "collectibles_" + m.group(1) + ".png"

    shutil.copyfile(dir_with_new_files + file, "collectibles/" + newname)
    print newname