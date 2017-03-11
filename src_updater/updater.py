#checks for updates, then runs the actual tracker
import json
import os, shutil
import urllib2
import logging
from Tkinter import *

wdir_prefix = "./"
latest_version = ""
update_option_name = "automatically_update"
run_the_tracker = True

error_log = logging.getLogger("tracker")
error_log.addHandler(logging.FileHandler(wdir_prefix + "tracker_log.txt", mode='a'))
error_log.setLevel(logging.INFO)

def log_error(msg):
    # Print it to stdout for dev troubleshooting, log it to a file for production
    print(msg)
    error_log.error(msg)


options_file = wdir_prefix + "options.json"
if not os.path.isfile(options_file):
    shutil.copy(wdir_prefix + "options_default.json", options_file)

with open(options_file, "r") as options_json:
    options = json.load(options_json)

with open(wdir_prefix + 'version.txt', 'r') as f:
    current_version = f.read()

def check_if_update_possible():
    try:
        if update_option_name not in options or options[update_option_name]:
            # check if github has a newer version than us
            latest = "https://api.github.com/repos/Hyphen-ated/RebirthItemTracker/releases/latest"
            github_info_json = urllib2.urlopen(latest).read()
            info = json.loads(github_info_json)
            global latest_version
            latest_version = info["name"]
            if latest_version != current_version:
                global run_the_tracker
                run_the_tracker = False
                run_update_window()
    except Exception:
        import traceback
        errmsg = traceback.format_exc()
        log_error(errmsg)

root = None
def run_update_window():
    global root
    root = Tk()
    root.wm_title("Update Item Tracker")
    root.resizable(False, False)
    root.minsize(300, 100)
    label = Label(root, text="Your current version is " + current_version + "\nThe latest version is " + latest_version)
    label.pack()

    update = Button(root, text="Update Now", command=do_update)
    update.pack()

    ignore = Button(root, text="Ignore Updates", command=ignore_updates)
    ignore.pack()
    mainloop()

def do_update():
    print("hey")
    global run_the_tracker
    run_the_tracker = True
    root.destroy()

def ignore_updates():
    options[update_option_name] = False
    with open(options_file, "w") as json_file:
        json.dump(options, json_file, indent=3, sort_keys=True)
    global run_the_tracker
    run_the_tracker = True
    root.destroy()

def main():
    check_if_update_possible()

    # launch the real tracker
    if run_the_tracker:
        os.chdir("dist/")
        os.execl("item_tracker.exe", "Rebirth Item Tracker")

main()



