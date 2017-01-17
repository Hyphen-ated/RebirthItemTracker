""" This module handles everything related to log parsing """
import platform # For determining what operating system the script is being run on
import re       # For parsing the log file (regular expressions)
import os       # For working with files on the operating system
import logging  # For logging
from game_objects.item  import Item
from game_objects.floor import Floor, Curse
from game_objects.state  import TrackerState
from options import Options

class LogParser(object):
    """
    This class load Isaac's log file, and incrementally modify a state representing this log
    """
    def __init__(self, prefix, tracker_version):
        self.state = TrackerState("", tracker_version, Options().game_version)
        self.log = logging.getLogger("tracker")
        self.file_prefix = prefix

        self.reset()

    def reset(self):
        """Reset variable specific to the log file/run"""
        # Variables describing the parser state
        self.getting_start_items = False
        self.current_room = ""
        self.current_seed = ""
        # Cached contents of log
        self.content = ""
        # Log split into lines
        self.splitfile = []
        self.run_start_line = 0
        self.seek = 0
        self.spawned_coop_baby = 0
        self.state.reset(self.current_seed, Options().game_version)

    def parse(self):
        """
        Parse the log file and return a TrackerState object,
        or None if the log file couldn't be found
        """

        self.opt = Options()
        # Attempt to load log_file
        if not self.__load_log_file():
            return None
        self.splitfile = self.content.splitlines()

        # This will become true if we are getting starting items
        self.getting_start_items = False

        # Process log's new output
        for current_line_number, line in enumerate(self.splitfile[self.seek:]):
            self.__parse_line(current_line_number, line)


        self.seek = len(self.splitfile)
        return self.state

    def __parse_line(self, line_number, line):
        """
        Parse a line using the (line_number, line) tuple
        """
        # In Afterbirth+, nearly all lines start with this.
        # We want to slice it off.
        info_prefix = '[INFO] - '
        if line.startswith(info_prefix):
            line = line[len(info_prefix):]

        #TODO: also parse version number for non-AB+
        if line.startswith('Binding of Isaac: Afterbirth+'):
            self.__parse_version_number(line)
        if line.startswith('RNG Start Seed:'):
            self.__parse_seed(line, line_number)
        if line.startswith('Room'):
            self.__parse_room(line)
        if line.startswith('Level::Init'):
            self.__parse_floor(line, line_number)
        if line.startswith("Curse"):
            self.__parse_curse(line)
        if line.startswith("Spawn co-player!"):
            self.spawned_coop_baby = line_number + self.seek
        if re.search(r"Added \d+ Collectibles", line):
            self.log.debug("Reroll detected!")
            self.state.reroll()
        if line.startswith('Adding collectible'):
            self.__parse_item_add(line_number, line)
        if line.startswith('Lua Debug: Removing collectible'):
            self.__parse_item_remove(line_number, line)

    def __trigger_new_run(self, line_number):
        self.log.debug("Starting new run, seed: %s", self.current_seed)
        self.run_start_line = line_number + self.seek
        self.state.reset(self.current_seed, Options().game_version)

    def __parse_version_number(self, line):
        offset = len('Binding of Isaac: Afterbirth+')
        self.state.version_number = line[offset:]

    def __parse_seed(self, line, line_number):
        """ Parse a seed line """
        # This assumes a fixed width, but from what I see it seems safe
        self.current_seed = line[16:25]

        # Antibirth doesn't have a proper way to detect run resets
        # it will wipe the tracker when doing a "continue"
        if self.opt.game_version == "Antibirth":
            self.__trigger_new_run(line_number)

    def __parse_room(self, line):
        """ Parse a room line """
        if 'Start Room' not in line:
            self.getting_start_items = False

    def __parse_floor(self, line, line_number):
        """ Parse the floor in line and push it to the state """
        # Create a floor tuple with the floor id and the alternate id
        if self.opt.game_version == "Afterbirth" or self.opt.game_version == "Afterbirth+":
            regexp_str = r"Level::Init m_Stage (\d+), m_StageType (\d+)"
        elif self.opt.game_version == "Rebirth" or self.opt.game_version == "Antibirth":
            regexp_str = r"Level::Init m_Stage (\d+), m_AltStage (\d+)"
        else:
            return
        floor_tuple = tuple([re.search(regexp_str, line).group(x) for x in [1, 2]])

        self.getting_start_items = True

        # Assume floors aren't cursed until we see they are
        floor = int(floor_tuple[0])
        alt = floor_tuple[1]

        if floor == 1 and self.opt.game_version != "Antibirth":
            self.__trigger_new_run(line_number)

        # Special handling for the Cathedral and The Chest and Afterbirth
        if self.opt.game_version == "Afterbirth" or self.opt.game_version == "Afterbirth+":
            # In Afterbirth, Cath is an alternate of Sheol (which is 10)
            # and Chest is an alternate of Dark Room (which is 11)
            if floor == 10 and alt == '0':
                floor -= 1
            elif floor == 11 and alt == '1':
                floor += 1
        else:
            # In Rebirth, floors have different numbers
            if alt == '1' and (floor == 9 or floor == 11):
                floor += 1
        floor_id = 'f' + str(floor)

        # Greed mode
        if alt == '3':
            floor_id += 'g'

        self.state.add_floor(Floor(floor_id))
        return True

    def __parse_curse(self, line):
        """ Parse the curse and add it to the last floor """
        if line.startswith("Curse of the Labyrinth!"):
            self.state.add_curse(Curse.Labyrinth)
        if line.startswith("Curse of Blind"):
            self.state.add_curse(Curse.Blind)
        if line.startswith("Curse of the Lost!"):
            self.state.add_curse(Curse.Lost)

    def __parse_item_add(self, line_number, line):
        """ Parse an item and push it to the state """
        if len(self.splitfile) > 1 and self.splitfile[line_number + self.seek - 1] == line:
            self.log.debug("Skipped duplicate item line from baby presence")
            return False
        space_split = line.split(" ") # Hacky string manipulation
        item_id = space_split[2] # When you pick up an item, this has the form: "Adding collectible 105 (The D6)"

        # Check if the item ID exists
        if not Item.contains_info(item_id):
            item_id = "NEW"

        item_name = " ".join(space_split[3:])[1:-1]
        self.log.debug("Picked up item. id: %s, name: %s", item_id, item_name)
        if ((line_number + self.seek) - self.spawned_coop_baby) < (len(self.state.item_list) + 10) \
                and self.state.contains_item(item_id):
            self.log.debug("Skipped duplicate item line from baby entry")
            return False

        # It's a blind pickup if we're on a blind floor and we don't have the Black Candle
        blind_pickup = self.state.last_floor.floor_has_curse(Curse.Blind) and not self.state.contains_item('260')
        added = self.state.add_item(Item(item_id, self.state.last_floor, self.getting_start_items, blind=blind_pickup))
        if not added:
            self.log.debug("Skipped adding item %s to avoid space-bar duplicate", item_id)
        return True

    def __parse_item_remove(self, line_number, line):
        """ Parse an item and remove it from the state """
        space_split = line.split(" ") # Hacky string manipulation
        item_id = space_split[4] # When you lose an item, this has the form: "Lua Debug: Removing collectible 105"

        # Check if the item ID exists
        if not Item.contains_info(item_id):
            return False

        self.log.debug("Removed item. id: %s", item_id)

        # A check will be made inside the remove_item function
        # to see if this item is actually in our inventory or not.
        return self.state.remove_item(item_id)

    def __load_log_file(self):
        """
        Attempt to load log file from common location.
        Return true if successfully loaded, false otherwise
        """
        path = None
        logfile_location = ""
        version_path_fragment = self.opt.game_version
        if version_path_fragment == "Antibirth":
            version_path_fragment = "Rebirth"

        if platform.system() == "Windows":
            logfile_location = os.environ['USERPROFILE'] + '/Documents/My Games/Binding of Isaac {}/'
        elif platform.system() == "Linux":
            logfile_location = os.getenv('XDG_DATA_HOME',
                os.path.expanduser('~') + '/.local/share') + '/binding of isaac {}/'
            version_path_fragment = version_path_fragment.lower()
        elif platform.system() == "Darwin":
            logfile_location = os.path.expanduser('~') + '/Library/Application Support/Binding of Isaac {}/'


        logfile_location = logfile_location.format(version_path_fragment)

        for check in (self.file_prefix + '../log.txt', logfile_location + 'log.txt'):
            if os.path.isfile(check):
                path = check
                break
        if path is None:
            return False

        cached_length = len(self.content)
        file_size = os.path.getsize(path)
        if cached_length > file_size or cached_length == 0: # New log file or first time loading the log
            self.reset()
            self.content = open(path, 'rb').read()
        elif cached_length < file_size:  # Append existing content
            f = open(path, 'rb')
            f.seek(cached_length + 1)
            self.content += f.read()
        return True

