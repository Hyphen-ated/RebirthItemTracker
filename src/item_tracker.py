# Imports
import StringIO # For writing out the log to the "run_logs" folder
import time     # For getting the current timestamp
import os       # For working with files on the operating system
import platform # For determining what operating system the script is being run on
import zipfile  # For compressing the log files of past runs
import re       # For parsing the log file (regular expressions)
import json     # For importing the items and options
import urllib2  # For checking for updates to the item tracker
import logging  # For logging

# Import item tracker specific code
from view_controls.view import DrawingTool, Option
from view_controls.overlay import Overlay
from game_objects.floor import Curse
from game_objects.item  import Item
from game_objects.state  import TrackerState


tracker_log_path = "../tracker_log.txt"

# The main class of the program
class IsaacTracker(object):
    def __init__(self, logging_level=logging.INFO, read_delay=1):
        # Class variables
        self.seek             = 0
        self.framecount       = 0
        self.read_delay       = read_delay
        self.run_ended        = True
        self.log_not_found    = False
        self.content          = ""  # Cached contents of log
        self.splitfile        = []  # Log split into lines
        self.drawing_tool     = None
        self.file_prefix      = "../"
        self.state            = TrackerState("")
        self.overlay          = Overlay(self.file_prefix, self.state)

        # Initialize isaac stuff
        self.current_room            = ""
        self.getting_start_items     = False
        self.run_start_line          = 0
        # FIXME This is used for log purpose, improve when restoring run summaries
        self.last_run                = {}
        self.spawned_coop_baby       = 0  # The last spawn of a co-op baby

        self.GAME_VERSION = "" # I KNOW THIS IS WRONG BUT I DON'T KNOW WHAT ELSE TO DO

        self.log = logging.getLogger("tracker")
        self.log.addHandler(logging.FileHandler(tracker_log_path))
        self.log.setLevel(logging_level)

        # Load items info
        with open(self.file_prefix + "items.json", "r") as items_file:
            Item.items_info = json.load(items_file)

    def check_end_run(self, line, cur_line_num):
        if not self.run_ended:
            died_to  = ""
            end_type = ""
            # FIXME right now I don't think boss detection in the log is working properly
            if self.state.last_boss and self.state.last_boss[0] in ['???', 'The Lamb', 'Mega Satan']:
                end_type = "Won"
            elif (self.state.seed != '') and line.startswith('RNG Start Seed:'):
                end_type = "Reset"
            elif line.startswith('Game Over.'):
                end_type = "Death"
                died_to = re.search(r'(?i)Killed by \((.*)\) spawned', line).group(1)
            if end_type:
                self.last_run = {
                    "bosses":   self.state.bosses,
                    "items":    self.state.item_list,
                    "seed":     self.state.seed,
                    "died_to":  died_to,
                    "end_type": end_type
                }
                self.run_ended = True
                self.log.debug("End of Run! %s" % self.last_run)
                if end_type != "Reset":
                    self.save_file(self.run_start_line, cur_line_num, self.state.seed)

    def save_file(self, start, end, seed):
        self.mkdir(self.file_prefix + "run_logs")
        timestamp = int(time.time())
        seed = seed.replace(" ", "")
        data = "\n".join(self.splitfile[start:end + 1])
        # FIXME improve
        data = "%s\nRUN_OVER_LINE\n%s" % (data, self.last_run)
        run_name = "%s%s.log" % (seed, timestamp)
        in_memory_file = StringIO.StringIO()
        with zipfile.ZipFile(in_memory_file, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(run_name, data)
        with open(self.file_prefix + "run_logs/" + run_name + ".zip", "wb") as f:
            f.write(in_memory_file.getvalue())

    def mkdir(self, dn):
        if not os.path.isdir(dn):
            os.mkdir(dn)


    def load_log_file(self):
        self.log_not_found = False
        path = None
        logfile_location = ""
        game_names = ("Afterbirth", "Rebirth")
        if platform.system() == "Windows":
            logfile_location = os.environ['USERPROFILE'] + '/Documents/My Games/Binding of Isaac {}/'
        elif platform.system() == "Linux":
            logfile_location = os.getenv('XDG_DATA_HOME',
                os.path.expanduser('~') + '/.local/share') + '/binding of isaac {}/'
            game_names = ("afterbirth", "rebirth")
        elif platform.system() == "Darwin":
            logfile_location = os.path.expanduser('~') + '/Library/Application Support/Binding of Isaac {}/'
        if os.path.exists(logfile_location.format(game_names[0])):
            logfile_location = logfile_location.format(game_names[0])
            self.GAME_VERSION = "Afterbirth"
        else:
            logfile_location = logfile_location.format(game_names[1])
            self.GAME_VERSION = "Rebirth"

        for check in (self.file_prefix + '../log.txt', logfile_location + 'log.txt'):
            if os.path.isfile(check):
                path = check
                break
        if path is None:
            self.log_not_found = True
            return

        cached_length = len(self.content)
        file_size = os.path.getsize(path)
        if cached_length > file_size or cached_length == 0: # New log file or first time loading the log
            self.content = open(path, 'rb').read()
        elif cached_length < file_size:  # Append existing content
            f = open(path, 'rb')
            f.seek(cached_length + 1)
            self.content += f.read()

    # Returns text to put in the title bar
    def check_for_update(self):
        try:
            github_info_json = urllib2.urlopen("https://api.github.com/repos/Hyphen-ated/RebirthItemTracker/releases/latest").read()
            info = json.loads(github_info_json)
            latest_version = info["name"]

            with open(self.file_prefix + 'version.txt', 'r') as f:
                current_version = f.read()
                title_text = " v" + current_version
                if latest_version != current_version:
                    title_text += " (new version available)"
                return title_text
        except Exception as e:
            self.log.debug("Failed to find update info: " + e.message)
        return ""

    def start_new_run(self, current_line_number, seed):
        self.run_start_line = current_line_number + self.seek
        self.log.debug("Starting new run, seed: %s" % seed)
        self.log.debug("Starting new state")
        self.state.reset(seed)
        self.run_ended = False
        self.drawing_tool.reset()
        self.log.debug("Reset drawing tool")
        # Update seed and reset all stats
        # NOTE we can't update last item description as nothing has been picked up yet
        self.overlay.update_seed()
        self.overlay.update_stats()

    def run(self):

        update_notifier = self.check_for_update()

        # Create drawing tool to use to draw everything - it'll create its own screen
        self.drawing_tool = DrawingTool("Rebirth Item Tracker" + update_notifier, self.state)

        done = False
        # This is the last seed 'seen' by the log reader
        current_seed = ""

        while not done:

            # Check for events and handle them
            done = self.drawing_tool.handle_events()
            self.drawing_tool.tick()

            if self.log_not_found:
                self.drawing_tool.write_message("log.txt not found. Put the RebirthItemTracker "
                                                "folder inside the isaac folder, next to log.txt")

            self.drawing_tool.draw_items()
            self.framecount += 1

            # Now we re-process the log file to get anything that might have loaded; do it every read_delay seconds (making sure to truncate to an integer or else it might never mod to 0)
            if self.framecount % int(self.drawing_tool.options[Option.FRAMERATE_LIMIT] * self.read_delay) == 0:
                self.load_log_file()
                self.splitfile = self.content.splitlines()

                # Return to start if seek passes the end of the file (usually because the log file restarted)
                if self.seek > len(self.splitfile):
                    self.log.debug("Current line number longer than lines in file, returning to start of file")
                    self.seek = 0

                should_reflow = False
                getting_start_items = False # This will become true if we are getting starting items

                # Process log's new output
                for current_line_number, line in enumerate(self.splitfile[self.seek:]):

                    # The end floor boss should be defeated now
                    if line.startswith('Mom clear time:'):
                        kill_time = int(line.split(" ")[-1])

                        # If you re-enter a room you get a "mom clear time" again, check for that (can you fight the same boss twice?)
                        self.state.add_boss(self.current_room, kill_time)

                    # Check and handle the end of the run; the order is important
                    # - we want it after boss kill but before "RNG Start Seed"
                    self.check_end_run(line, current_line_number + self.seek)

                    if line.startswith('RNG Start Seed:'):
                        # We have a seed. If it's a new seed it's a new run, else it's a quit/continue
                        current_seed = line[16:25] # This assumes a fixed width, but from what I see it seems safe

                    if line.startswith('Room'):
                        self.current_room = re.search(r'\((.*)\)', line).group(1)
                        if 'Start Room' not in line:
                            getting_start_items = False
                        self.log.debug("Entered room: %s" % self.current_room)
                    if line.startswith('Level::Init'):
                        # Create a floor tuple with the floor id and the alternate id
                        if self.GAME_VERSION == "Afterbirth":
                            floor_tuple = tuple([re.search(r"Level::Init m_Stage (\d+), m_StageType (\d+)", line).group(x) for x in [1, 2]])
                        else:
                            floor_tuple = tuple([re.search(r"Level::Init m_Stage (\d+), m_AltStage (\d+)", line).group(x) for x in [1, 2]])

                        # Assume floors aren't cursed until we see they are
                        getting_start_items = True
                        floor = int(floor_tuple[0])
                        alt = floor_tuple[1]


                        # Special handling for cath and chest and Afterbirth
                        if self.GAME_VERSION == "Afterbirth":
                            # In Afterbirth Cath is an alternate of Sheol (which is 10)
                            # and Chest is an alternate of Dark room (which is 11)
                            if floor == 10 and alt == '0':
                                floor -= 1
                            elif floor == 11 and alt == '1':
                                floor += 1
                        else:
                            # In Rebirth floors have different numbers
                            if alt == '1' and (floor == 9 or floor == 11):
                                floor += 1
                        floor_id = 'f' + str(floor)
                        # Greed mode
                        if alt == '3':
                            floor_id += 'g'

                        # when we see a new floor 1, that means a new run has started
                        if floor == 1:
                            self.start_new_run(current_line_number, current_seed)

                        self.state.add_floor(floor_id, (alt == '1'))
                        should_reflow = True



                    if line.startswith("Curse of the Labyrinth!"):
                        # It SHOULD always begin with f (that is, it's a floor) because this line only comes right after the floor line
                        self.state.add_curse(Curse.Labyrinth)
                    if line.startswith("Curse of Blind"):
                        self.state.add_curse(Curse.Blind)
                    if line.startswith("Curse of the Lost!"):
                        self.state.add_curse(Curse.Lost)
                    if line.startswith("Spawn co-player!"):
                        self.spawned_coop_baby = current_line_number + self.seek
                    if re.search(r"Added \d+ Collectibles", line):
                        self.log.debug("Reroll detected!")
                        self.state.reroll()
                    if line.startswith('Adding collectible'):
                        if len(self.splitfile) > 1 and self.splitfile[current_line_number + self.seek - 1] == line:
                            self.log.debug("Skipped duplicate item line from baby presence")
                            continue
                        space_split = line.split(" ") # Hacky string manipulation
                        item_id = space_split[2] # A string has the form of "Adding collectible 105 (The D6)"

                        # Check if the item ID exists
                        if item_id.zfill(3) not in Item.items_info:
                            item_id = "NEW"

                        item_name = " ".join(space_split[3:])[1:-1]
                        self.log.debug("Picked up item. id: %s, name: %s" % (item_id, item_name))
                        if ((current_line_number + self.seek) - self.spawned_coop_baby) < (len(self.state.item_list) + 10) \
                                and self.state.contains_item(item_id):
                            self.log.debug("Skipped duplicate item line from baby entry")
                            continue
                        result_tuple = self.state.add_item(item_id, getting_start_items)
                        # First element is true if the item has been added
                        if result_tuple[0]:
                            self.overlay.update_stats(result_tuple[1])
                            # NOTE with the current implementation, a spacebar item will
                            # have its description only once
                            self.overlay.update_last_item_description()
                            self.drawing_tool.item_picked_up()
                        else:
                            self.log.debug("Skipped adding item %s to avoid space-bar duplicate" % item_id)

                        should_reflow = True

                self.seek = len(self.splitfile)
                if should_reflow:
                    self.drawing_tool.reflow()

# Main
def main():
    # erase our tracker log file from previous runs
    open(tracker_log_path, 'w').close()
    try:
        # Pass "logging.DEBUG" in debug mode
        rt = IsaacTracker()
        rt.run()
    except Exception:
        import traceback
        # FIXME restore the traceback to file
        print traceback.format_exc()
        # with open(tracker_log_path, "a") as log:
            # log.write(traceback.format_exc())

if __name__ == "__main__":
    main()
