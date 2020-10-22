# This script takes png files from a directory and makes a copy that is twice the size.
# The workflow is:
# 1) Put new file images in the incoming_files_directory
# 2) Run this script
# 3) Put the files in the outgoing_files_directory in the appropriate place in collectibles/
# 4) Run add_missing_glow_images.py

# This script uses the "convert" command, which is part of ImageMagick:
# https://www.imagemagick.org/script/download.php
# You must use an old version of ImageMagick for the convert command to work properly.
# Version 6.9.3-7 Q16 x64 is confirmed to work

import os
import sys

incoming_files_directory = 'renamed_images'
outgoing_files_directory = 'resized_images'

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
