# this takes png files it finds in scripts/incoming and makes copies of each one in scripts/resized that are double size
# the workflow is: put new files in incoming, run this, put the new files in the appropriate place in collectibles/
# then run add_missing_glow_images.py

# requires imagemagick

import os

for file in os.listdir("incoming"):
    if file.endswith(".png"):
        cmd = 'convert "incoming/' + file + '" -scale 200% "resized/' + file + '"'
        print(cmd)
        os.system(cmd)