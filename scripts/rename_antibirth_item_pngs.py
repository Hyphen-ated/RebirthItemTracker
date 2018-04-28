# Antibirth images come with an x at the end, but the log prints them with a 1 at the front
# So we make copies of the images that have a 1 at the front.

import os, re, shutil

incoming_files_directory = 'brand_new_images'
outgoing_files_directory = 'renamed_images'

for f in os.listdir(incoming_files_directory):
    file = os.path.join(incoming_files_directory, f)
    if os.path.isfile(file):
        m = re.match('collectibles_(\d\d\d)x_.*\.png', f)
        if m:
            itemid = m.group(1)
            finalname = 'collectibles_1' + itemid + '.png'
            finalpath = os.path.join(outgoing_files_directory, finalname)
            shutil.copy(file, finalpath)
            print(file + " copied to " + finalpath)
