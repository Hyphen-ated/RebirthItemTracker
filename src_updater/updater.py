#checks for updates, then runs the actual tracker
import json
import os, shutil
import threading
import urllib2
import logging
import webbrowser
import zipfile
from StringIO import StringIO
from Tkinter import *
import errno
import traceback

import time

import subprocess
from enum import Enum


class UpdateStep(Enum):
    PROMPTING = "Asking about update"
    PRE_DOWNLOAD = "Preparing for update"
    DOWNLOAD = "Downloading update zip"
    EXTRACT = "Extracting update zip"
    PERFORMING = "Performing update"
    DONE = "Update finished"
    ERROR = "Error"
    SKIP = "Skipping update"

# specific kinds of errors where we can actionably tell the user what to do to fix it, not just "please report"
class UpdateError(Enum):
    TRACKER_RUNNING = 1

wdir_prefix = "../"
update_option_name = "check_for_updates"

error_log = logging.getLogger("tracker")
error_log.addHandler(logging.FileHandler(wdir_prefix + "tracker_log.txt", mode='a'))
error_log.setLevel(logging.INFO)

def log_error(msg):
    # Print it to stdout for dev troubleshooting, log it to a file for production
    msg = time.strftime("%Y-%m-%d %H:%M:%S ") + msg
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

        self.root = None
        self.update_thread = None
        self.update_step = None
        self.update_error = None

        self.options_file = wdir_prefix + "options.json"
        if not os.path.isfile(self.options_file):
            shutil.copy(wdir_prefix + "tracker-lib/options_default.json", self.options_file)

        with open(self.options_file, "r") as options_json:
            self.options = json.load(options_json)

        with open(wdir_prefix + 'version.txt', 'r') as f:
            self.current_version = f.read()

    # creates tk window and blocks until it goes away
    def check_if_update_possible(self):
        try:
            #if the update option isn't present, the default is to do updates.
            if update_option_name not in self.options or self.options[update_option_name]:
                # check if github has a newer version than us
                latest = "https://api.github.com/repos/rchardon/RebirthItemTracker/releases/latest"
                github_info_json = urllib2.urlopen(latest).read()
                info = json.loads(github_info_json)
                self.latest_version = info["name"]
                if self.latest_version != self.current_version:
                    return True
        except Exception:
            log_error("Error while checking whether there's a new version:\n" + traceback.format_exc())
        return False


    def create_update_window(self):
        self.update_step = UpdateStep.PROMPTING
        self.root = Tk()
        self.root.wm_title("Update Item Tracker")
        self.root.resizable(False, False)
        self.root.minsize(500, 300)
        self.label = Label(self.root, text="Your current version is " + self.current_version + "\nThe latest version is " + self.latest_version)
        self.label.pack()

        self.update = Button(self.root, text="Update Now", command=self.trigger_update_thread)
        self.update.pack()

        self.justlaunchit = Button(self.root, text="Ignore Update This Time", command=self.just_launch_it)
        self.justlaunchit.pack()

        self.ignore = Button(self.root, text="Ignore Updates Forever", command=self.ignore_updates)
        self.ignore.pack()
        mainloop()

    def trigger_update_thread(self):
        self.update_step = UpdateStep.PRE_DOWNLOAD
        self.update.pack_forget()
        self.justlaunchit.pack_forget()
        self.ignore.pack_forget()


        self.update_thread = threading.Thread(target=self.do_update)
        self.update_thread.start()
        self.check_update_status()

    def check_update_status(self):
        self.label['text'] = "Updating, please wait...\n" + self.update_step.value
        if self.update_step == UpdateStep.DONE:
            self.root.destroy()
            return

        if self.update_step == UpdateStep.ERROR:
            self.handle_error()
        else:
            self.root.after(200, self.check_update_status)

    def handle_error(self):
        reportbtn = Button(self.root, text="Open bug report page", command=self.open_report_page)
        ignorebtn = Button(self.root, text="Ignore Updates Forever", command=self.ignore_updates)
        closebtn = Button(self.root, text="OK", command=self.dont_launch)

        if self.update_error == UpdateError.TRACKER_RUNNING:
            self.label['text']="Another copy of the tracker seems to be running already, close it and retry.\n"+ \
                               "If that doesn't work, please report this bug and include your tracker_log.txt"
            reportbtn.pack()
            closebtn.pack()
        else:
            # generic problem we don't have special handling for
            self.label['text'] = "Sorry, there was an error during the update.\n"+ \
                                 "You might need to just manually download the new version\n"+ \
                                 "and copy in your old options.json (if you care about your settings.)\n"+ \
                                 "Please report this bug and include your tracker_log.txt, as well as what version you had."
            reportbtn.pack()
            ignorebtn.pack()
            closebtn.pack()


    def open_report_page(self):
        webbrowser.open("https://github.com/rchardon/RebirthItemTracker/issues", autoraise=True)
        self.root.destroy()

    def do_update(self):
        try:
            tasklist = subprocess.check_output('tasklist', shell=True)
            if "item_tracker.exe" in tasklist:
                self.update_step = UpdateStep.ERROR
                self.update_error = UpdateError.TRACKER_RUNNING
                return

            backupdir = wdir_prefix + "options backups/" + self.current_version
            mkdir_p(backupdir)
            shutil.copy(wdir_prefix + "options.json", backupdir)

            scratch = wdir_prefix + "update_scratchdir/"
            if os.path.exists(scratch):
                shutil.rmtree(scratch)

            mkdir_p(scratch)
            try:
                self.update_step = UpdateStep.DOWNLOAD
                url = 'https://github.com/rchardon/RebirthItemTracker/releases/download/' + self.latest_version + '/Rebirth.Item.Tracker-' + self.latest_version + ".zip"
                urlstream = urllib2.urlopen(url)
                myzip = zipfile.ZipFile(StringIO(urlstream.read()))
                self.update_step = UpdateStep.EXTRACT
                myzip.extractall(scratch)
            except Exception as e:
                log_error("Failed to download and extract latest version from GitHub ( url was :" + url + " )\n" + traceback.format_exc())
                self.update_step = UpdateStep.ERROR
                return

            self.update_step = UpdateStep.PERFORMING
            innerdir = scratch + "Rebirth Item Tracker/"

            with open(wdir_prefix + "tracker-lib/options_default.json", "r") as old_defaults_json:
                old_defaults = json.load(old_defaults_json)

            with open(innerdir + "tracker-lib/options_default.json", "r") as new_defaults_json:
                new_defaults = json.load(new_defaults_json)

            for k,v in old_defaults.iteritems():
                # for each default option they left unchanged, if the default changed in the new version, give them the new default
                if k in self.options and self.options[k] == v and new_defaults[k] != v:
                    self.options[k] = new_defaults[k]

            self.write_options()

            path_to_exe = wdir_prefix + "tracker-lib/item_tracker.exe"
            # the exe might not exist if we're trying to recover from a previous botched update, that's okay
            if os.path.exists(path_to_exe):
                try:
                   os.remove(path_to_exe)
                except Exception:
                    # failing to remove the exe means very likely it's currently running
                    self.update_step = UpdateStep.ERROR
                    self.update_error = UpdateError.TRACKER_RUNNING
                    log_error(traceback.format_exc())
                    return

            for subdir in ["collectibles", "overlay text", "tracker-lib"]:
                dir_to_remove = wdir_prefix + subdir
                if os.path.isdir(dir_to_remove):
                    shutil.rmtree(dir_to_remove)

            shutil.move(innerdir + "updater-lib", scratch)
            recursive_overwrite(innerdir, "..")
            self.update_step = UpdateStep.DONE
        except Exception:
            log_error("Error while attempting tracker update\n" + traceback.format_exc())
            self.update_step = UpdateStep.ERROR

    def just_launch_it(self):
        self.update_step = UpdateStep.SKIP
        self.root.destroy()

    def ignore_updates(self):
        self.options[update_option_name] = False
        self.write_options()
        self.update_step = UpdateStep.SKIP
        self.root.destroy()

    def dont_launch(self):
        self.update_step = UpdateStep.ERROR
        self.root.destroy()

    def write_options(self):
        with open(self.options_file, "w") as json_file:
            json.dump(self.options, json_file, indent=3, sort_keys=True)


def main():
    try:
        updater = Updater()
        if updater.check_if_update_possible():
            #blocks until either an update is finished or they skip the update
            updater.create_update_window()

        if updater.update_step == UpdateStep.ERROR:
            return

        print("launching tracker")
        os.chdir(wdir_prefix + "tracker-lib/")
        os.execl("item_tracker.exe", "Rebirth Item Tracker")
    except Exception:
        log_error("Error with tracker updater outside of the actual update process\n" + traceback.format_exc())

main()



