import logging  # For logging to a flat file
import time


# this logging stuff has to be outside of the IsaacTracker class so we can use it when it fails to instantiate
log_dir = "../"
error_log = logging.getLogger("tracker")
error_log.addHandler(logging.FileHandler(log_dir + "tracker_log.txt", mode='a'))
error_log.setLevel(logging.INFO)

def log_error(msg):
    # Print it to stdout for dev troubleshooting, log it to a file for production
    msg = time.strftime("%Y-%m-%d %H:%M:%S ") + msg
    print(msg)
    error_log.error(msg)