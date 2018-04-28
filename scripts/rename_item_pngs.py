# this is a script to add new item pngs to the repository in the form the tracker expects
# basically we're going from "collectibles_440_kidneystone.png" to "collectibles_440.png"
# this is not part of the tracker itself

import os, re, shutil

files = []
incoming_files_directory = 'brand_new_images'
outgoing_files_directory = 'renamed_images'

for f in os.listdir(incoming_files_directory):
    file = os.path.join(incoming_files_directory, f)
    if os.path.isfile(file):
        m = re.match('collectibles_(\d\d\d)_.*\.png', f)
        if m:
            itemid = m.group(1)
            finalname = 'collectibles_' + itemid + '.png'
            finalpath = os.path.join(outgoing_files_directory, finalname)
            shutil.copy(file, finalpath)
            print(file + " copied to " + finalpath)
