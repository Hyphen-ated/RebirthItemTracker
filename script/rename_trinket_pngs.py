# this is a script to add new trinket pngs to the repository in the form the tracker expects
# basically we're going from "1.png" to "collectibles_2001.png"
# this is not part of the tracker itself

import os, re, shutil

incoming_files_directory = 'brand_new_images'
outgoing_files_directory = 'renamed_images'
for f in os.listdir(incoming_files_directory):
    file = os.path.join(incoming_files_directory, f)
    if os.path.isfile(file):
        m = re.match('trinket_(\d\d\d)_.*\.png', f)
        if m:
            itemid = m.group(1)
            finalname = 'collectibles_2' + itemid + '.png' # trinkets get a special 2000+ range in the tracker
            finalpath = os.path.join(outgoing_files_directory, finalname)
            shutil.copy(file, finalpath)
            print(f + " copied to " + finalpath)
