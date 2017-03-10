# Run this to add glow versions of any item images that don't currently have glow versions.
# requires imagemagick

import os

def add_glow_to_dir(dirname):
    glows = {}
    for file in os.listdir(dirname + "/glow"):
        if file.endswith(".png"):
            glows[file] = True

    for file in os.listdir(dirname):
        if file not in glows:
            if file.endswith(".png"):
                cmd = 'convert "' + dirname + '/' + file +\
                        '" ( +clone -channel A -blur 0x2.5 -level 0,80% +channel +level-colors white ) -compose DstOver -composite "' +\
                        dirname + '/glow/' + file + '"'
                print(cmd)
                os.system(cmd)

add_glow_to_dir("../collectibles/")
add_glow_to_dir("../collectibles/antibirth")
add_glow_to_dir("../collectibles/custom")