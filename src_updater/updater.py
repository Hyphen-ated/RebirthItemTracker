#checks for updates, then runs the actual tracker
import json
import os, shutil
import urllib2
import logging
from Tkinter import *

wdir_prefix = "./"
update_option_name = "automatically_update"

error_log = logging.getLogger("tracker")
error_log.addHandler(logging.FileHandler(wdir_prefix + "tracker_log.txt", mode='a'))
error_log.setLevel(logging.INFO)

def log_error(msg):
    # Print it to stdout for dev troubleshooting, log it to a file for production
    print(msg)
    error_log.error(msg)

class Updater(object):
    def __init__(self):
        self.latest_version = ""

        self.run_the_tracker = True
        self.root = None

        self.options_file = wdir_prefix + "options.json"
        if not os.path.isfile(self.options_file):
            shutil.copy(wdir_prefix + "options_default.json", self.options_file)

        with open(self.options_file, "r") as options_json:
            self.options = json.load(options_json)

        with open(wdir_prefix + 'version.txt', 'r') as f:
            self.current_version = f.read()

    def check_if_update_possible(self):
        try:
            if update_option_name not in self.options or self.options[update_option_name]:
                # check if github has a newer version than us
                latest = "https://api.github.com/repos/Hyphen-ated/RebirthItemTracker/releases/latest"
                github_info_json = urllib2.urlopen(latest).read()
                info = json.loads(github_info_json)
                self.latest_version = info["name"]
                if self.latest_version != self.current_version:
                    self.run_the_tracker = False
                    self.run_update_window()
        except Exception:
            import traceback
            errmsg = traceback.format_exc()
            log_error(errmsg)


    def run_update_window(self):
        self.root = Tk()
        self.root.wm_title("Update Item Tracker")
        self.root.resizable(False, False)
        self.root.minsize(300, 100)
        label = Label(self.root, text="Your current version is " + self.current_version + "\nThe latest version is " + self.latest_version)
        label.pack()

        update = Button(self.root, text="Update Now", command=self.do_update)
        update.pack()

        ignore = Button(self.root, text="Ignore Updates", command=self.ignore_updates)
        ignore.pack()
        mainloop()

    def do_update(self):



        self.run_the_tracker = True
        self.root.destroy()

    def ignore_updates(self):
        self.options[update_option_name] = False
        with open(self.options_file, "w") as json_file:
            json.dump(self.options, json_file, indent=3, sort_keys=True)
        self.run_the_tracker = True
        self.root.destroy()

def main():
    updater = Updater()
    updater.check_if_update_possible()

    # launch the real tracker
    if updater.run_the_tracker:
        os.chdir("dist/")
        os.execl("item_tracker.exe", "Rebirth Item Tracker")

main()



