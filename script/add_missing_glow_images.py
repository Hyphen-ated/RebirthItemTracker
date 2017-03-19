# Run this to add glow versions of any item images that don't currently have glow versions.
# This script uses the "convert" command, which is part of ImageMagick: https://www.imagemagick.org/script/download.php

import os

def add_glow_to_dir(dirname):
    glows = {}
    for file in os.listdir(os.path.join(dirname, 'glow')):
        if file.endswith('.png'):
            glows[file] = True

    for file in os.listdir(dirname):
        if file not in glows:
            if file.endswith('.png'):
                file_path = os.path.join(dirname, file)
                file_glow_path = os.path.join(dirname, 'glow', file)
                cmd = 'convert "' + file_path + '" ' +\
                      '( +clone -channel A -blur 0x2.5 -level 0,80% +channel +level-colors white ) ' +\
                      '-compose DstOver ' +\
                      '-composite "' + file_glow_path + '"'
                print(cmd)
                os.system(cmd)

add_glow_to_dir(os.path.join('..', 'collectibles'))
#add_glow_to_dir(os.path.join('..', 'collectibles', 'antibirth'))
add_glow_to_dir(os.path.join('..', 'collectibles', 'custom'))
