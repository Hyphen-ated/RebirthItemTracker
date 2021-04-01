""" This module handles everything related to log parsing """
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
    def __init__(self, prefix, tracker_version, log_finder):
        self.state = TrackerState("", tracker_version, Options().game_version)
        self.log = logging.getLogger("tracker")
        self.wdir_prefix = prefix
        self.log_finder = log_finder

        self.reset()

    def reset(self):
        """Reset variable specific to the log file/run"""
        # Variables describing the parser state
        self.getting_start_items = False
        self.reseeding_floor = False
        self.current_room = ""
        self.current_seed = ""
        # Cached contents of log
        self.content = ""
        # Log split into lines
        self.splitfile = []
        self.run_start_line = 0
        self.seek = 0
        self.spawned_coop_baby = 0
        self.log_file_handle = None
        # if they switched between rebirth and afterbirth, the log file we use could change
        self.log_file_path = self.log_finder.find_log_file(self.wdir_prefix)
        self.state.reset(self.current_seed, Options().game_version)
        self.lazarus = False
        self.greedmode = 0
        self.first_floor = None
        self.first_line = ""
        # Avoid tracker resetting on B1 for Backasswards challenge
        self.backasswards = False

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

        # Messages printed by mods have this prefix.
        # strip it, so mods can spoof actual game log messages to us if they want to
        luadebug_prefix ='Lua Debug: '
        if line.startswith(luadebug_prefix):
            line = line[len(luadebug_prefix):]

        # AB and AB+ version messages both start with this text (AB+ has a + at the end)
        if line.startswith('Binding of Isaac: Repentance') or line.startswith('Binding of Isaac: Afterbirth') or line.startswith('Binding of Isaac: Rebirth'):
            self.__parse_version_number(line)
        if line.startswith('RNG Start Seed:'):
            self.__parse_seed(line, line_number)
            self.greedmode = 0
        if self.opt.game_version == "Repentance" and line.startswith('Level::Init') and self.greedmode == 0: # Store the line of the first floor in Repentance because we can detect if we are in greed mode only after this line in the log
            self.first_line = line
        elif line.startswith('Level::Init'):
            self.__parse_floor(line, line_number)   
        if line.startswith('Room'):
            self.__parse_room(line)
            # Detect Greed mode floor on Repentance
            if self.opt.game_version == "Repentance":
                greed_mode_starting_rooms = ('1.1000','1.1010','1.1011','1.1012','1.1013','1.1014','1.1015','1.1016','1.1017','1.1018','1.2000','1.2001','1.2002','1.2003','1.2004','1.2005','1.2006','1.2007','1.2008','1.2009','1.3000','1.3001','1.3002','1.3003','1.3004','1.3005','1.3006','1.3007','1.3008','1.3009','1.3010','1.4000','1.4001','1.4002','1.4003','1.4004','1.4005','1.4006','1.4007','1.4008','1.4009','1.4010','1.5000','1.5001','1.5002','1.5003','1.5004','1.5005','1.5006','1.5007','1.5008','1.5009','1.5010','1.6000','1.6001','1.6002','1.6003','1.6004','1.6005','1.6006','1.6007','1.6008','1.6009')
                match = re.search(r"Room (.+?)\(", line)
                room_id = match.group(1)
                if room_id == '18.1000':
                    self.state.item_list = []
                elif room_id in greed_mode_starting_rooms and self.greedmode == 0:
                    self.greedmode = 2
                    self.__parse_floor(self.first_line, line_number)    
                elif self.greedmode == 0 or room_id == '5.50000': # 5.5000 is Mega Satan's Room in Challenge #31
                    if line.startswith('Room 5.5000'):
                        self.backasswards = True
                    else:
                        self.backasswards = False
                    self.greedmode = 1
                    self.__parse_floor(self.first_line, line_number)
        if line.endswith('Subtype 8'): # This is to detect if we play as Lazarus to avoid showing two Anemics in the tracker
            self.lazarus = True
        else: # To reset self.lazarus if we don't play it because it would never add Anemic again unless you close/re-open the game
            for i in range(20):
                if i != 8 and line.endswith("Subtype "+ str(i)):
                    self.lazarus = False
        if line.startswith("Curse"):
            self.__parse_curse(line)
        if line.startswith("Spawn co-player!"):
            self.spawned_coop_baby = line_number + self.seek
        if re.search(r"Added \d+ Collectibles", line):
            self.log.debug("Reroll detected!")
            self.state.reroll()
        if line.startswith('Adding collectible '):
            self.__parse_item_add(line_number, line)
        if line.startswith('Gulping trinket ') or line.startswith('Adding smelted trinket '):
            self.__parse_trinket_gulp(line)
        if line.startswith('Removing collectible ') or line.startswith('Removing voided collectible ') or line.startswith('Removing smelted trinket '):
            self.__parse_item_remove(line)            
        if line.startswith('Executing command: reseed'):
            # racing+ re-generates floors if they contain duplicate rooms. we need to track that this is happening
            # so we don't erroneously think the entire run is being restarted when it happens on b1.
            self.reseeding_floor = True


    def __trigger_new_run(self, line_number):
        self.log.debug("Starting new run, seed: %s", self.current_seed)
        self.run_start_line = line_number + self.seek
        self.state.reset(self.current_seed, Options().game_version)

    def __parse_version_number(self, line):
        words = line.split()
        self.state.version_number = words[-1]

    def __parse_seed(self, line, line_number):
        """ Parse a seed line """
        # This assumes a fixed width, but from what I see it seems safe
        self.current_seed = line[16:25]
        self.__trigger_new_run(line_number)

        # Antibirth doesn't have a proper way to detect run resets
        # it will wipe the tracker when doing a "continue"
        if self.opt.game_version == "Antibirth":
            self.__trigger_new_run(line_number)

    def __parse_room(self, line):
        """ Parse a room line """
        if 'Start Room' not in line:
            self.getting_start_items = False

        match = re.search(r"Room (.+?)\(", line)
        if match:
            room_id = match.group(1)
            self.state.change_room(room_id)

    def __parse_floor(self, line, line_number):
        """ Parse the floor in line and push it to the state """
        # Create a floor tuple with the floor id and the alternate id
        if self.opt.game_version == "Afterbirth" or self.opt.game_version == "Afterbirth+" or self.opt.game_version == "Repentance":
            regexp_str = r"Level::Init m_Stage (\d+), m_StageType (\d+)"
        elif self.opt.game_version == "Rebirth" or self.opt.game_version == "Antibirth":
            regexp_str = r"Level::Init m_Stage (\d+), m_AltStage (\d+)"
        else:
            return
        search_result = re.search(regexp_str, line)
        if search_result is None:
            self.log.debug("log.txt line doesn't match expected regex\nline: \"" + line+ "\"\nregex:\"" + regexp_str + "\"")
            return

        floor = int(search_result.group(1))
        alt = search_result.group(2)
        self.getting_start_items = True

        # we use generation of the first floor as our trigger that a new run started.
        # in racing+, it doesn't count if the game is currently in the process of "reseeding" that floor.
        # in antibirth, this doesn't work at all; instead we have to use the seed being printed as our trigger.
        # that means if you s+q in antibirth, it resets the tracker.
        # In Repentance, Downpour 1 and Dross 1 are considered Stage 1.
        # So we need to add a condition to avoid tracker reseting when entering those floors.
        # In Repentance, don't trigger a new run on floor 1 because of the R Key item
        if self.reseeding_floor:
            self.reseeding_floor = False
        elif floor == 1 and self.opt.game_version != "Antibirth" and self.opt.game_version != "Repentance" and self.backasswards == False:
            self.__trigger_new_run(line_number)

        # Special handling for the Cathedral and The Chest and Afterbirth
        if self.opt.game_version == "Afterbirth" or self.opt.game_version == "Afterbirth+" or self.opt.game_version == "Repentance":
            self.log.debug("floor")
            # In Afterbirth, Cath is an alternate of Sheol (which is 10)
            # and Chest is an alternate of Dark Room (which is 11)
            # In Repentance, alt paths are same stage as their counterparts (ex: Basement 1 = Downpour 1)
            if alt == '4' or alt == '5':
                floor += 15
            elif floor == 10 and alt == '0':
                floor -= 1
            elif floor == 11 and alt == '1':
                floor += 1
            elif floor == 9:
                floor = 13
            elif floor == 12:
                floor = 14
            elif floor == 13:
                floor = 15    
        else:
            # In Rebirth, floors have different numbers
            if alt == '1' and (floor == 9 or floor == 11):
                floor += 1
        floor_id = 'f' + str(floor)

        # Greed mode
        if (alt == '3' and self.opt.game_version != "Repentance") or (self.opt.game_version == "Repentance" and self.greedmode == 2):
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
        is_Jacob_item = line.endswith("(Jacob)") and self.opt.game_version == "Repentance" # The second part of the condition is to avoid showing Jacob's Head if you play on a modded char in AB+
        is_Esau_item = line.endswith("(Esau)") and self.opt.game_version == "Repentance" # The second part of the condition is to avoid showing Esau's Head if you play on a modded char in AB+  
        end_name = -15 if is_Jacob_item or is_Esau_item else -1
        space_split = line.split(" ")
        numeric_id = space_split[2] # When you pick up an item, this has the form: "Adding collectible 105 (The D6)"
        item_name = " ".join(space_split[3:])[1:end_name]
        item_id = ""

        if int(numeric_id) < 0:
            numeric_id = "-1"
        if int(numeric_id) == 577: # Damocles can't be rerolled by D4 so no need to show it twice
            numeric_id = "656"

        # Check if we recognize the numeric id
        if Item.contains_info(numeric_id):
            item_id = numeric_id
        else:
            # it might be a modded custom item. let's see if we recognize the name
            item_id = Item.modded_item_id_prefix + item_name
            if not Item.contains_info(item_id):
                item_id = "NEW"

        self.log.debug("Picked up item. id: %s, name: %s", item_id, item_name)
        if ((line_number + self.seek) - self.spawned_coop_baby) < (len(self.state.item_list) + 10) \
                and self.state.contains_item(item_id):
            self.log.debug("Skipped duplicate item line from baby entry")
            return False

        # It's a blind pickup if we're on a blind floor and we don't have the Black Candle
        blind_pickup = self.state.last_floor.floor_has_curse(Curse.Blind) and not self.state.contains_item('260')
        if not (numeric_id == "214" and ((self.state.contains_item('214') and self.state.contains_item('332')) or (self.lazarus and self.state.contains_item('214')))):
            added = self.state.add_item(Item(item_id, self.state.last_floor, self.getting_start_items, blind=blind_pickup, is_Jacob_item=is_Jacob_item, is_Esau_item=is_Esau_item))
            if not added:
                self.log.debug("Skipped adding item %s to avoid space-bar duplicate", item_id)
        else:
            self.log.debug("Skipped adding Anemic from Lazarus Rags because we already have Anemic")
        return True

    def __parse_trinket_gulp(self, line):
        """ Parse a (modded) trinket gulp and push it to the state """
        space_split = line.split(" ")
        # When using a mod like racing+ on AB+, a trinket gulp has the form: "Gulping trinket 10"
        # In Repentance, a gulped trinket has the form : "Adding smelted trinket 10"
        if self.opt.game_version == "Repentance":
            numeric_id = str(int(space_split[3]) + 2000) # the tracker hackily maps trinkets to items 2000 and up.
        else:
            numeric_id = str(int(space_split[2]) + 2000) # the tracker hackily maps trinkets to items 2000 and up.
        is_Jacob_item = line.endswith("(Jacob)") and self.opt.game_version == "Repentance"
        is_Esau_item = line.endswith("(Esau)") and self.opt.game_version == "Repentance"

        # Check if we recognize the numeric id
        if Item.contains_info(numeric_id):
            item_id = numeric_id
        else:
            item_id = "NEW"

        self.log.debug("Gulped trinket: %s", item_id)

        added = self.state.add_item(Item(item_id, self.state.last_floor, self.getting_start_items, is_Jacob_item=is_Jacob_item, is_Esau_item=is_Esau_item))
        if not added:
            self.log.debug("Skipped adding item %s to avoid space-bar duplicate", item_id)
        return True

    def __parse_item_remove(self, line):
        """ Parse an item and remove it from the state """
        space_split = line.split(" ") # Hacky string manipulation
        # When you lose an item, this has the form: "Removing collectible 105 (The D6)" or "Removing voided collectible 105 (The D6)"
        if self.opt.game_version == "Repentance":
            item_id = space_split[3]
            if space_split[2] == "trinket":
                item_id = str(int(space_split[3]) + 2000)
        else:
            item_id = space_split[2]
        item_name = " ".join(space_split[3:])[1:-1]
        # Check if the item ID exists
        if Item.contains_info(item_id):
            removal_id = item_id
        else:
            # that means it's probably a custom item
            removal_id = Item.modded_item_id_prefix + item_name

        self.log.debug("Removed item. id: %s", removal_id)

        # A check will be made inside the remove_item function
        # to see if this item is actually in our inventory or not.
        return self.state.remove_item(removal_id)



    def __load_log_file(self):
        if self.log_file_path is None:
            return False

        if self.log_file_handle is None:
            self.log_file_handle = open(self.log_file_path, 'rb')

        cached_length = len(self.content)
        file_size = os.path.getsize(self.log_file_path)

        if cached_length > file_size or cached_length == 0: # New log file or first time loading the log
            self.reset()
            self.content = open(self.log_file_path, 'rb').read()
        elif cached_length < file_size:  # Append existing content
            self.log_file_handle.seek(cached_length + 1)
            self.content += self.log_file_handle.read()
        return True
