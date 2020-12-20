import os, sys, shutil, subprocess, time

# Here is where you can set the name for the release zip file and for the install dir inside it.
# version.txt is the sole source of truth about what version this is. the version string shouldnt be hardcoded anywhere
with open('version.txt', 'r') as f:
    version = f.read()
installName = 'Rebirth Item Tracker'

# target is where we assemble our final install.
if os.path.isdir('target/'):
    shutil.rmtree('target/')
    #windows takes time to delete things, wait until it's done
    while os.path.isdir('target/'):
        time.sleep(0.3)
installDir = 'target/' + installName + '/'
os.mkdir('target/')
#os.mkdir(installDir)

localpy = sys.executable

os.chdir("src_bootstrapper")
subprocess.call(localpy + " cxfreeze.py bootstrapper.py --base-name=Win32GUI --target-dir dist --icon ../mind.ico", shell=False, stdout=sys.stdout, stderr=sys.stderr)
os.chdir("..")

shutil.move('src_bootstrapper/dist/bootstrapper.exe', 'src_bootstrapper/dist/Rebirth Item Tracker.exe') # Move the dist files to our target directory
shutil.move('src_bootstrapper/dist/', installDir)

# Run the tracker build script. The results are placed in ./dist/
os.chdir("src_updater")
subprocess.call(localpy + " cxfreeze.py updater.py --base-name=Win32GUI --target-dir dist --icon ../mind.ico", shell=False, stdout=sys.stdout, stderr=sys.stderr)
os.chdir("..")
shutil.move('src_updater/dist/', installDir + "updater-lib/")

os.chdir("src")
subprocess.call(localpy + " cxfreeze.py item_tracker.py --base-name=Win32GUI --target-dir dist --icon ../mind.ico", shell=False, stdout=sys.stdout, stderr=sys.stderr)
os.chdir("..")
shutil.copy('src/options.ico', 'src/dist/options.ico')
shutil.move('src/dist/', installDir + 'tracker-lib/')



# Then copy over all the data files
shutil.copytree('collectibles/', installDir + 'collectibles/')
shutil.copytree('overlay text reference/', installDir + 'overlay text/')
# do NOT include "options.json" in a release. when it's missing, the tracker itself will generate it based on options_default
# if options.json goes into a release, it will completely overwrite users' options when they autoupdate
shutil.copy('options_default.json', installDir + "tracker-lib/")
shutil.copy('items_abplus.json', installDir)
shutil.copy('items.json', installDir)
shutil.copy('items_custom.json', installDir)
shutil.copy('LICENSE.txt', installDir)
shutil.copy('README.md', installDir + 'README.txt')
shutil.copy('version.txt', installDir)
shutil.make_archive("target/" + installName + "-" + version, "zip", 'target', installName + "/")

exit()