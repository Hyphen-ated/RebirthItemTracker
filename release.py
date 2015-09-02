import os, sys, shutil, subprocess

# Here is where you can set the name for the release zip file and for the install dir inside it.
version = "0.8"
installName = 'RebirthItemTracker-' + version

# target is where we assemble our final install.
if os.path.isdir('target/'):
    shutil.rmtree('target/')
installDir = 'target/' + installName + '/'

# Run the tracker build script. The results are placed in ./dist/
subprocess.call("pygame2exe.py item_tracker.py", shell=True, stdout=sys.stdout, stderr=sys.stderr)

# Remove the Tk demo files, this should always be safe
shutil.rmtree('dist/library/tcl/tk8.5/demos')
shutil.rmtree('dist/library/tcl/tk8.5/images')
shutil.rmtree('dist/library/tcl/tk8.5/msgs')

# Remove localization encoding files, this might cause compatibility issues in obscure scenarios
'''
for root, dirs, files in os.walk('dist/library/tcl/tcl8.5/', topdown=False):
    for name in files:
        if name not in ['auto.tcl', 'init.tcl', 'tclIndex']:
            os.remove(os.path.join(root, name))
    for name in dirs:
        os.rmdir(os.path.join(root,name))
'''

shutil.move('dist/', installDir) # Move the dist files to our target directory

# Then copy over all the data files
shutil.copytree('collectibles/', installDir + 'collectibles/')
shutil.copytree('overlay text reference/', installDir + 'overlay text/')
shutil.copy('options.json', installDir)
shutil.copy('items.json', installDir)
shutil.copy('LICENSE.txt', installDir)
shutil.copy('README.md', installDir + 'README.txt')
with open(installDir + "version.txt", 'w') as f:
    f.write(version)
shutil.make_archive("target/" + installName, "zip", 'target', installName + "/")