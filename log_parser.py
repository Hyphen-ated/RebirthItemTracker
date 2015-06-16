import os
import time


class RunHistory:
    def __init__(self, seed):
        self.seed = seed
        self.items = []
        self.bosses = []


class LogParser:
    def __init__(self, verbose=False, debug=False):
        self.verbose = verbose
        self.debug = debug
        self.raw_input = ''

        # Store each run as a separate list element
        self.runs = []

        self.paths = ("../log.txt", os.environ['USERPROFILE'] + "/Documents/My Games/Binding of Isaac Rebirth/log.txt")

    # Checks if the log file has changed and appends new lines to raw_input, or replaces it if a new log is detected.
    def read_log(self):
        for path in self.paths:
            if os.path.isfile(path):
                self.path = path
                break
        if path == None:
            self.log_msg("log.txt not found", 'D')
            return

        length = len(self.raw_input)
        size = os.path.getsize(path)
        if length > size or length == 0:  # New log file
            self.raw_input = open(path, 'rb').read()
        elif length < size:
            f = open(path, 'r')
            f.seek(length+1)
            self.raw_input += f.read()

    # debugging method
    def get_raw(self):
        return self.raw_input

    # debugging method
    def log_msg(self, msg, level):
        if level=="V" and self.verbose: print msg
        if level=="D" and self.debug: print msg

# Internal testing code

testParser = LogParser(verbose=True, debug=True)
testParser.read_log()

while True:
    time.sleep(1)
    testParser.read_log()
    curr = testParser.get_raw().splitlines()
    print curr

# ---------------------------
# junk code stash
# ---------------------------

def load_log_file(self, path, content):
    length = len(content)
    size = os.path.getsize(path)
    if length > size or length == 0:  # New log file
        content = open(path, 'rb').read()
    elif length < size:
        f = open(path, 'r')
        f.seek(length+1)
        content += f.read()
