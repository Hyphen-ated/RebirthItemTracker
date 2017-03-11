#checks for updates, then runs the actual tracker
import json
import os, shutil
import urllib2
import logging
import zipfile
from StringIO import StringIO
from Tkinter import *

import errno

wdir_prefix = "../"
update_option_name = "automatically_update"

error_log = logging.getLogger("tracker")
error_log.addHandler(logging.FileHandler(wdir_prefix + "tracker_log.txt", mode='a'))
error_log.setLevel(logging.INFO)

def log_error(msg):
    # Print it to stdout for dev troubleshooting, log it to a file for production
    print(msg)
    error_log.error(msg)

# got this from some guy on stackoverflow
def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise
# also got this from some guy on stackoverflow.
# I just want a version of shutil.copytree that can overwrite into an existing dest dir. that's what this is.
def recursive_overwrite(src, dest, ignore=None):
    if os.path.isdir(src):
        if not os.path.isdir(dest):
            os.makedirs(dest)
        files = os.listdir(src)
        if ignore is not None:
            ignored = ignore(src, files)
        else:
            ignored = set()
        for f in files:
            if f not in ignored:
                recursive_overwrite(os.path.join(src, f),
                                    os.path.join(dest, f),
                                    ignore)
    else:
        shutil.copyfile(src, dest)

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
        self.label = Label(self.root, text="Your current version is " + self.current_version + "\nThe latest version is " + self.latest_version)
        self.label.pack()

        self.update = Button(self.root, text="Update Now", command=self.do_update)
        self.update.pack()

        self.ignore = Button(self.root, text="Ignore Updates", command=self.ignore_updates)
        self.ignore.pack()
        mainloop()

    def do_update(self):
        self.update.pack_forget()
        self.ignore.pack_forget()
        self.label['text'] = "Updating, please wait..."
        self.root.update()
        backupdir = wdir_prefix + "options backups/" + self.current_version
        mkdir_p(backupdir)
        shutil.copy(wdir_prefix + "options.json", backupdir)

        scratch = wdir_prefix + "update_scratchdir/"
        if os.path.exists(scratch):
            shutil.rmtree(scratch)

        mkdir_p(scratch)
        try:
            url = 'https://github.com/Hyphen-ated/RebirthItemTracker/releases/download/' + self.latest_version + '/RebirthItemTracker-' + self.latest_version + ".zip"
            urlstream = urllib2.urlopen(url)
            myzip = zipfile.ZipFile(StringIO(urlstream.read()))
            myzip.extractall(scratch)
        except Exception as e:
            log_error('Failed to download and extract latest version from GitHub ( url was :' + url + " )")
            import traceback
            log_error(traceback.format_exc())

        shutil.rmtree(wdir_prefix + "collectibles")
        shutil.rmtree(wdir_prefix + "overlay text")
        shutil.rmtree(wdir_prefix + "tracker-lib")

        innerdir = scratch + "Rebirth Item Tracker/"
        shutil.move(innerdir + "updater-lib", scratch)
        recursive_overwrite(innerdir + "Rebirth Item Tracker/", "..")

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



