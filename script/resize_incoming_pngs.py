# this takes png files it finds in scripts/incoming and makes copies of each one in scripts/resized that are double size
# the workflow is: put new files in incoming, run this, put the new files in the appropriate place in collectibles/
# then run add_missing_glow_images.py

# This script uses the "convert" command, which is part of ImageMagick: https://www.imagemagick.org/script/download.php

import os

for file in os.listdir('in'):
    if file.endswith('.png'):
        in_file = os.path.join('in', file)
        out_file = os.path.join('out', file)
        cmd = 'convert "' + in_file + '" ' +\
              '-scale 200% "' + out_file + '"'
        print(cmd)
        os.system(cmd)
