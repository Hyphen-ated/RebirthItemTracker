import os, sys, shutil, subprocess

# Here is where you can set the name for the release zip file and for the install dir inside it.
# version.txt is the sole source of truth about what version this is. the version string shouldnt be hardcoded anywhere
with open('version.txt', 'r') as f:
    version = f.read()
installName = 'RebirthItemTracker-' + version

# target is where we assemble our final install.
if os.path.isdir('target/'):
    shutil.rmtree('target/')
installDir = 'target/' + installName + '/'

# Run the tracker build script. The results are placed in ./dist/
os.chdir("src")
subprocess.call("cxfreeze.py item_tracker.py --base-name=Win32GUI --target-dir dist ", shell=True, stdout=sys.stdout, stderr=sys.stderr)
os.chdir("..")

shutil.copy('src/options.ico', 'src/dist/options.ico')

shutil.move('src/dist/', installDir + "dist/") # Move the dist files to our target directory

# Then copy over all the data files
shutil.copytree('collectibles/', installDir + 'collectibles/')
shutil.copytree('overlay text reference/', installDir + 'overlay text/')
shutil.copy('shortcut_for_install_dir.lnk', installDir + "Launch Item Tracker.lnk")
shutil.copy('options_default.json', installDir + "options.json")
shutil.copy('items.json', installDir)
shutil.copy('LICENSE.txt', installDir)
shutil.copy('README.md', installDir + 'README.txt')
shutil.copy('version.txt', installDir)
shutil.make_archive("target/" + installName, "zip", 'target', installName + "/")