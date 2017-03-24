# this takes png files it finds in scripts/incoming and makes copies of each one in scripts/resized that are double size
# the workflow is: put new files in incoming, run this, put the new files in the appropriate place in collectibles/
# then run add_missing_glow_images.py

# This script uses the "convert" command, which is part of ImageMagick: https://www.imagemagick.org/script/download.php

import os
import sys

incoming_files_directory = 'in'
outgoing_files_directory = 'out'

if not os.path.isdir(incoming_files_directory):
    print('The incoming files directory of "' + incoming_files_directory + '" does not exist.')
    sys.exit(1)

if not os.path.isdir(outgoing_files_directory):
    os.makedirs(outgoing_files_directory)

for file in os.listdir(incoming_files_directory):
    if file.endswith('.png'):
        in_file = os.path.join(incoming_files_directory, file)
        out_file = os.path.join(outgoing_files_directory, file)
        cmd = 'convert "' + in_file + '" ' +\
              '-scale 200% "' + out_file + '"'
        print(cmd)
        os.system(cmd)
