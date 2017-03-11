#checks for updates, then runs the actual tracker
import json
import os, shutil

wdir_prefix = "./"
options_file = wdir_prefix + "options.json"
if not os.path.isfile(options_file):
    shutil.copy(wdir_prefix + "options_default.json", options_file)

options = {}
with open(options_file, "r") as options_json:
    options = json.load(options_json)

#check for updates if we should be doing that
auto_str = "automatically_update"
if auto_str not in options or not options[auto_str]:
    print "i would be updating now"

#launch the real tracker
os.chdir("dist/")
os.execl("item_tracker.exe", "item_tracker")




