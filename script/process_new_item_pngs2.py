# this is a script to add new item pngs to the repository in the form the tracker expects
# basically we're going from "1.png" to "collectibles_2001.png"
# this is not part of the tracker itself

import os, re, shutil

files = []
dir_with_new_files = 'in'

for file in os.listdir(dir_with_new_files):
    files.append(file)

for file in files:
    m = re.match('(\d+)\.png', file)
    newname = 'collectibles_2' + m.group(1).zfill(3) + '.png'

    shutil.copyfile(os.path.join(dir_with_new_files, file), os.path.join("out", newname))
    print newname
