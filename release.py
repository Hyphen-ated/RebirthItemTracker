import os, sys, shutil, subprocess, py2exe
from distutils.core import setup

# Here is where you can set the name for the release zip file and for the install dir inside it.
installName = 'RebirthItemTracker-0.5'

# target is where we assemble our final install. dist is where py2exe produces exes and their dependencies
if os.path.isdir('target/'):
    shutil.rmtree('target/')
installDir = 'target/' + installName + '/'

shutil.copytree('collectibles/', installDir + 'collectibles/')

# first build the main tracker using the horrible ugly pygame2exe script
subprocess.call("pygame2exe.py item_tracker.py", shell=True, stdout=sys.stdout, stderr=sys.stderr)
shutil.copy('dist/item_tracker.exe', installDir)

# then build the option builder using normal py2exe
sys.argv.append('py2exe')
setup(console=['option_picker.py'])

# unfortunately i cant figure out how to make it bundle all the optionpicker's dlls inside the exe like pygame2exe does
# so let's copy all this junk into the install dir
shutil.copytree('dist/', installDir + 'optionpicker/', ignore=shutil.ignore_patterns("item_tracker.exe"))

shutil.copy('options.json', installDir)
shutil.copy('items.txt', installDir)
shutil.copy('README.md', installDir + 'README.txt')
shutil.make_archive("target/" + installName, "zip", 'target', installName + "/")
