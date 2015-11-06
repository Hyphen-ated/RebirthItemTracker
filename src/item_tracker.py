# Imports
import StringIO # For writing out the log to the "run_logs" folder
import time     # For getting the current timestamp
import os       # For working with files on the operating system
import platform # For determining what operating system the script is being run on
import zipfile  # For compressing the log files of past runs
import pygame   # This is the main graphics library used for the item tracker
import re       # For parsing the log file (regular expressions)
import json     # For importing the items and options
import urllib2  # For checking for updates to the item tracker
import string   # Used in generating a run summary
#import pygame._view # Uncomment this if you are trying to run release.py and you get: "ImportError: No module named _view"

# Import item tracker specific code
from view_controls.view import DrawingTool, Option
from game_objects.floor import Floor, Curse
from game_objects.item  import Item, Stat, ItemProperty

# Additional pygame imports
if platform.system() == "Windows":
    import pygameWindowInfo
from pygame.locals import *

tracker_log_path = "../tracker_log.txt"

# The main class of the program
class IsaacTracker:
    def __init__(self, verbose=False, debug=False, read_delay=1):
        # Class variables
        self.verbose          = verbose
        self.debug            = debug
        self.text_height      = 0
        self.text_margin_size = None  # Will be changed in load_options
        self.font             = None  # Will be changed in load_options
        self.seek             = 0
        self.framecount       = 0
        self.read_delay       = read_delay
        self.run_ended        = True
        self.log_not_found    = False
        self.content          = ""  # Cached contents of log
        self.splitfile        = []  # Log split into lines
        self.drawing_tool     = None
        self.file_prefix      = "../"

        # Initialize isaac stuff
        self.collected_items         = [] # List of items collected this run
        self.collected_item_info     = [] # List of "immutable" ItemInfo objects used for determining the layout to draw
        self.guppy_set               = set() # Used to keep track of whether we're guppy or not
        self.num_displayed_items     = 0
        self.selected_item_idx       = None
        self.seed                    = ""
        self.current_room            = ""
        self.blind_floor             = False
        self.getting_start_items     = False
        self.run_start_line          = 0
        self.run_start_frame         = 0
        self.bosses                  = []
        self.last_run                = {}
        self._image_library          = {}
        self.in_summary_list         = []
        self.summary_condition_list  = []
        self.items_info              = {}
        self.floors                  = []
        self.player_stats            = {}
        self.player_stats_display    = {}
        self.reset_player_stats()
        self.item_message_start_time = 0
        self.item_pickup_time        = 0
        self.item_position_index     = []
        self.current_floor           = None
        self.floor_tuple             = () # Tuple with first value being floor number, second value being alt stage value (0 or 1, r.n.)
        self.spawned_coop_baby       = 0  # The last spawn of a co-op baby
        self.roll_icon               = None
        self.blind_icon              = None

        self.GAME_VERSION = "" # I KNOW THIS IS WRONG BUT I DON'T KNOW WHAT ELSE TO DO

        # Load items info
        with open(self.file_prefix + "items.json", "r") as items_file:
            self.items_info = json.load(items_file)

    def save_options(self):
        with open(self.file_prefix + "options.json", "w") as json_file:
            json.dump(self.options, json_file, indent=3, sort_keys=True)

    # write a message to the logfile for the tracker itself. debug messages and stacktraces and stuff should go here
    def log_msg(self, msg, level=""):
        def log(m):
            with open(tracker_log_path, "a") as log:
                log.write(m)

        if level == "V":
            if self.verbose: log(msg)
        elif level == "D":
            if self.debug: log(msg)
        else: log(msg)

    # This is just for the suffix of the boss kill number
    def suffix(self, d):
        return 'th' if 11 <= d <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(d % 10, 'th')

    def check_end_run(self, line, cur_line_num):
        if not self.run_ended:
            died_to  = ""
            end_type = ""
            if self.bosses and self.bosses[-1][0] in ['???', 'The Lamb', 'Mega Satan']:
                end_type = "Won"
            elif (self.seed != '') and line.startswith('RNG Start Seed:'):
                end_type = "Reset"
            elif line.startswith('Game Over.'):
                end_type = "Death"
                died_to = re.search('(?i)Killed by \((.*)\) spawned', line).group(1)
            if end_type:
                self.last_run = {
                    "bosses":   self.bosses,
                    "items":    self.collected_items,
                    "seed":     self.seed,
                    "died_to":  died_to,
                    "end_type": end_type
                }
                self.run_ended = True
                self.log_msg("End of Run! %s" % self.last_run, "D")
                if end_type != "Reset":
                    self.save_file(self.run_start_line, cur_line_num, self.seed)

    def save_file(self, start, end, seed):
        self.mkdir(self.file_prefix + "run_logs")
        timestamp = int(time.time())
        seed = seed.replace(" ", "")
        data = "\n".join(self.splitfile[start:end + 1])
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

    def add_stats_for_item(self, item, item_id):
        item_info = item.info
        for stat in Stat.LIST:
            if stat not in item_info:
                continue
            change = float(item_info.get(stat))
            self.player_stats[stat] += change
            value = self.player_stats[stat]

            # Round to 2 decimal places then ignore trailing zeros and trailing periods
            display = format(value, ".2f").rstrip("0").rstrip(".") # Doing just 'rstrip("0.")' breaks on "0.00"

            # For example, set "0.6" to ".6"
            if abs(value) < 1:
                display = display.lstrip("0")

            if value > -0.00001:
                display = "+" + display
            self.player_stats_display[stat] = display
            with open(self.file_prefix + "overlay text/" + stat + ".txt", "w+") as f:
                f.write(display)

        # If this can make us guppy, check if we're guppy
        if Stat.IS_GUPPY in item_info and item_info.get(Stat.IS_GUPPY):
            self.guppy_set.add(item)
            display = ""
            if len(self.guppy_set) >= 3:
                display = "yes"
            else:
                display = str(len(self.guppy_set))
            with open(self.file_prefix + "overlay text/" + stat + ".txt", "w+") as f:
                f.write(display)
            self.player_stats_display[Stat.IS_GUPPY] = display

    def reset_player_stats(self):
        for stat in Stat.LIST:
            self.player_stats[stat] = 0.0
            self.player_stats_display[stat] = "+0"
        self.player_stats_display[Stat.IS_GUPPY] = "0"

    # TODO: take SRL .comment length limit of 140 chars into account? would require some form of weighting
    # TODO: space bar items (Undefined, Teleport...) - a bit tricky because a simple "touch" shouldn't count
    def generate_run_summary(self):
        components = []
        floors = self.get_items_per_floor()
        for floor_id, items in floors.iteritems():
            floor_summary = self.generate_floor_summary(floor_id, items)
            floor = self.get_floor(floor_id)
            if floor_summary:
                components.append(floor_summary)

        components.insert(0, self.seed)
        components.append(self.generate_run_summary_stats())
        summary = string.join(components, ", ")

        if len(self.collected_guppy_items) is 2:
            two_thirds_text = ", 2/3 Guppy"
            if len(summary) <= (140 - len(two_thirds_text)):
                summary += two_thirds_text

        pygame.scrap.init()
        pygame.scrap.put(SCRAP_TEXT, summary)

    # TODO: this should be configurable with a string like the overlay
    def generate_run_summary_stats(self):
        return string.join(
            [("D:" + self.get_stat(Stat.DMG)),
             ("T:" + self.get_stat(Stat.TEARS)),
             ("S:" + self.get_stat(Stat.SPEED))], "/")

    def get_stat(self, stat):
        return self.player_stats_display[stat]

    def get_floor_label(self, floor_id):
        # TODO: Broken - fix
        floor = self.get_floor(floor_id) # A floor can't be lost _and_ blind (with Amnesia it could be, but we can't tell from log.txt)
        return self.get_floor_name(floor_id)

    def generate_floor_summary(self, floor_id, items):
        # TODO: Broken - fix
        floor_label = self.get_floor_label(floor_id)
        floor = self.get_floor(floor_id)

        if floor is None:
            # This should not happen
            return ""
        if not items:
            # Lost floors are still relevant even without items
            return floor_label if floor.lost else None
        return floor_label + " " + string.join(items, "/")

    def get_floor_name(self, floor_id):
        # TODO: Broken - fix
        return self.floor_id_to_label[floor_id]

    def get_floor(self, floor_id):
        # TODO: Broken - fix
        for floor in self.floors:
            if floor.id is floor_id:
                return floor
        return None

    def get_items_per_floor(self):
        # TODO: Make this work again using state model
        # TODO: Redo this using new state model
        floors = {}
        current_floor_id = None
        # A counter is necessary to find out *when* we became Guppy
        guppy_count = 0

        for item in self.collected_item_info:
            # TODO: why are the ids in the collected_item_info list not lstripped?
            short_id = item.id.lstrip("0")
            if item.floor:  # This is actually a floor, not an item
                floors[item.id] = []
                current_floor_id = item.id
            elif short_id in self.in_summary_list:
                item_info = self.get_item_info(item.id)
                floors[current_floor_id].append(self.get_summary_name(item_info))

            if short_id in self.guppy_list:
                guppy_count += 1
                if guppy_count >= 3:
                    floors[current_floor_id].append(u"Guppy")

        summary_condition_list_copy = list(self.summary_condition_list)
        return self.process_summary_conditions(floors, summary_condition_list_copy, [])

    def process_summary_conditions(self, floors, summary_conditions_left, keep_list):
        if len(summary_conditions_left) <= 0:
            return self.remove_items_not_in_list(floors, keep_list)
        item_id = summary_conditions_left.pop()
        condition = self.items_info[item_id][ItemProperty.SUMMARY_CONDITION]
        for floor in floors.itervalues():
            for item in floor:
                if item == condition:
                    keep_list.append(self.get_summary_name(self.items_info[item_id]))
        return self.process_summary_conditions(floors, summary_conditions_left, keep_list)

    def remove_items_not_in_list(self, floors, keep_list):
        new_floors = {}
        for floor_id in floors:
            new_floors[floor_id] = []
            for item_name in floors[floor_id]:
                if not self.in_summary_condition_list(item_name):
                    new_floors[floor_id].append(item_name)
                elif item_name in keep_list:
                    new_floors[floor_id].append(item_name)
        return new_floors

    def in_summary_condition_list(self, item_summary_name):
        for item_id in self.summary_condition_list:
            name = self.get_summary_name(self.items_info[item_id])
            if name is item_summary_name:
                return True
        return False

    def get_summary_name(self, item_info):
        if ItemProperty.SUMMARY_NAME in item_info:
            return item_info.get(ItemProperty.SUMMARY_NAME)
        return item_info.get(ItemProperty.NAME)

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
            self.log_msg("Failed to find update info: " + e.message, "D")
        return ""

    def get_item_info(self, item_id):
        id_padded = item_id.zfill(3)
        return self.items_info[id_padded]

    def start_new_run(self, current_line_number):
        self.run_start_line = current_line_number + self.seek
        self.log_msg("Starting new run, seed: %s" % self.seed, "D")
        self.run_start_frame = self.framecount
        self.collected_items = []
        self.log_msg("Emptied item array", "D")
        self.bosses = []
        self.log_msg("Emptied boss array", "D")
        self.run_ended = False
        self.reset_player_stats()
        self.current_floor = None
        self.drawing_tool.reset()
        self.guppy_set=set()
        self.log_msg("Reset drawing tool", "D")
        with open(self.file_prefix + "overlay text/seed.txt", "w+") as f:
            f.write(self.seed)

    def run(self):
        self.current_floor = None

        # Initialize pygame system stuff
        pygame.init()
        update_notifier = self.check_for_update()
        pygame.display.set_caption("Rebirth Item Tracker" + update_notifier)

        # Create drawing tool to use to draw everything - it'll create its own screen
        self.drawing_tool = DrawingTool()
        os.environ['SDL_VIDEO_WINDOW_POS'] = "%d, %d" % (
            self.drawing_tool.options[Option.X_POSITION],
            self.drawing_tool.options[Option.Y_POSITION])
        self.drawing_tool.start_pygame()
        pygame.display.set_icon(self.drawing_tool.get_image("collectibles_333.png"))
        done = False
        clock = pygame.time.Clock()
        winInfo = None
        if platform.system() == "Windows":
            winInfo = pygameWindowInfo.PygameWindowInfo()

        del os.environ['SDL_VIDEO_WINDOW_POS']
        while not done:
            # pygame logic
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    if platform.system() == "Windows":
                        winPos = winInfo.getScreenPosition()
                        self.drawing_tool.options[Option.X_POSITION] = winPos["left"]
                        self.drawing_tool.options[Option.Y_POSITION] = winPos["top"]
                        self.drawing_tool.save_options()
                    done = True
                elif event.type == VIDEORESIZE:
                    screen = pygame.display.set_mode(event.dict['size'], RESIZABLE)
                    self.drawing_tool.options[Option.WIDTH] = event.dict["w"]
                    self.drawing_tool.options[Option.HEIGHT] = event.dict["h"]
                    self.drawing_tool.save_options()
                    self.drawing_tool.reflow(self.collected_items)
                    pygame.display.flip()
                elif event.type == MOUSEMOTION:
                    if pygame.mouse.get_focused():
                        pos = pygame.mouse.get_pos()
                        self.drawing_tool.select_item_on_hover(*pos)
                elif event.type == KEYDOWN:
                    if len(self.collected_items) > 0:
                        if event.key == pygame.K_RIGHT:
                            self.drawing_tool.adjust_select_item_on_keypress(1)
                        elif event.key == pygame.K_LEFT:
                            self.drawing_tool.adjust_select_item_on_keypress(-1)
                        elif event.key == pygame.K_RETURN:
                            self.drawing_tool.load_selected_detail_page()
                        elif event.key == pygame.K_c and pygame.key.get_mods() & pygame.KMOD_CTRL:
                            pass
                            #self.generate_run_summary() # This is commented out because run summaries are broken with the new "state" model rewrite of the item tracker
                elif event.type == MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self.drawing_tool.load_selected_detail_page()
                    if event.button == 3:
                        import option_picker
                        pygame.event.set_blocked([QUIT, MOUSEBUTTONDOWN, KEYDOWN, MOUSEMOTION])
                        option_picker.options_menu(self.file_prefix + "options.json").run()
                        pygame.event.set_allowed([QUIT, MOUSEBUTTONDOWN, KEYDOWN, MOUSEMOTION])
                        self.drawing_tool.reset()
                        self.drawing_tool.load_options()
                        self.drawing_tool.reflow(self.collected_items)

            # Drawing logic
            clock.tick(int(self.drawing_tool.options[Option.FRAMERATE_LIMIT]))

            if self.log_not_found:
                self.drawing_tool.write_message("log.txt not found. Put the RebirthItemTracker folder inside the isaac folder, next to log.txt")

            self.drawing_tool.draw_items(self)
            self.framecount += 1

            # Now we re-process the log file to get anything that might have loaded; do it every read_delay seconds (making sure to truncate to an integer or else it might never mod to 0)
            if self.framecount % int(self.drawing_tool.options[Option.FRAMERATE_LIMIT] * self.read_delay) == 0:
                self.load_log_file()
                self.splitfile = self.content.splitlines()

                # Return to start if seek passes the end of the file (usually because the log file restarted)
                if self.seek > len(self.splitfile):
                    self.log_msg("Current line number longer than lines in file, returning to start of file", "D")
                    self.seek = 0

                should_reflow = False
                getting_start_items = False # This will become true if we are getting starting items

                # Process log's new output
                for current_line_number, line in enumerate(self.splitfile[self.seek:]):
                    self.log_msg(line, "V")

                    # The end floor boss should be defeated now
                    if line.startswith('Mom clear time:'):
                        kill_time = int(line.split(" ")[-1])

                        # If you re-enter a room you get a "mom clear time" again, check for that (can you fight the same boss twice?)
                        if self.current_room not in [x[0] for x in self.bosses]:
                            self.bosses.append((self.current_room, kill_time))
                            self.log_msg(
                                "Defeated %s%s boss %s at time %s" % (len(self.bosses),
                                self.suffix(len(self.bosses)), self.current_room, kill_time), "D")

                    # Check and handle the end of the run; the order is important - we want it after boss kill but before "RNG Start Seed"
                    self.check_end_run(line, current_line_number + self.seek)

                    if line.startswith('RNG Start Seed:'): # The start of a run
                        self.seed = line[16:25] # This assumes a fixed width, but from what I see it seems safe

                    if line.startswith('Room'):
                        self.current_room = re.search('\((.*)\)', line).group(1)
                        if 'Start Room' not in line:
                            getting_start_items = False
                        self.log_msg("Entered room: %s" % self.current_room,"D")
                    if line.startswith('Level::Init'):
                        if self.GAME_VERSION == "Afterbirth":
                            floor_tuple = tuple([re.search("Level::Init m_Stage (\d+), m_StageType (\d+)",line).group(x) for x in [1, 2]])
                        else:
                            floor_tuple = tuple([re.search("Level::Init m_Stage (\d+), m_AltStage (\d+)",line).group(x) for x in [1, 2]])

                        # Assume floors aren't cursed until we see they are
                        self.blind_floor = False
                        getting_start_items = True
                        floor = int(floor_tuple[0])
                        alt = floor_tuple[1]


                        # Special handling for cath and chest
                        if alt == '1' and (floor == 9 or floor == 11):
                            floor += 1
                        floor_id = 'f' + str(floor)

                        # when we see a new floor 1, that means a new run has started
                        if floor == 1:
                            self.start_new_run(current_line_number)

                        self.current_floor=Floor(floor_id,self,(alt=='1'))
                        should_reflow = True



                    if line.startswith("Curse of the Labyrinth!"):
                        # It SHOULD always begin with f (that is, it's a floor) because this line only comes right after the floor line
                        self.current_floor.add_curse(Curse.Labyrinth)
                    if line.startswith("Curse of Blind"):
                        self.current_floor.add_curse(Curse.Blind)
                    if line.startswith("Curse of the Lost!"):
                        self.current_floor.add_curse(Curse.Lost)
                    if line.startswith("Spawn co-player!"):
                        self.spawned_coop_baby = current_line_number + self.seek
                    if re.search("Added \d+ Collectibles", line):
                        self.log_msg("Reroll detected!", "D")
                        map(lambda item: item.rerolled(),self.collected_items)
                    if line.startswith('Adding collectible'):
                        if len(self.splitfile) > 1 and self.splitfile[current_line_number + self.seek - 1] == line:
                            self.log_msg("Skipped duplicate item line from baby presence", "D")
                            continue
                        space_split = line.split(" ") # Hacky string manipulation
                        item_id = space_split[2] # A string has the form of "Adding collectible 105 (The D6)"

                        # Check if the item ID exists
                        if item_id.zfill(3) not in self.items_info:
                            item_id = "NEW"
                        item_info = self.get_item_info(item_id)

                        # Default current floor to basement 1 if none
                        if self.current_floor is None:
                            self.current_floor = Floor("f1", self, False)
                        # If the item IDs are equal, it should say this item already exists
                        temp_item = Item(item_id,self.current_floor,item_info,getting_start_items)
                        if ((current_line_number + self.seek) - self.spawned_coop_baby) < (len(self.collected_items) + 10) \
                                and temp_item in self.collected_items:
                            self.log_msg("Skipped duplicate item line from baby entry","D")
                            continue
                        item_name = " ".join(space_split[3:])[1:-1]
                        self.log_msg("Picked up item. id: %s, name: %s" % (item_id, item_name), "D")
                        with open(self.file_prefix + "overlay text/itemInfo.txt", "w+") as f:
                            desc = temp_item.generate_item_description()
                            f.write(item_info[ItemProperty.NAME] + ":" + desc)

                        # Ignore repeated pickups of space bar items
                        if not (item_info.get(ItemProperty.SPACE,False) and temp_item in self.collected_items):
                            self.collected_items.append(temp_item)
                            self.item_message_start_time = self.framecount
                            self.item_pickup_time = self.framecount
                            self.drawing_tool.item_picked_up()
                        else:
                            self.log_msg("Skipped adding item %s to avoid space-bar duplicate" % item_id, "D")
                        self.add_stats_for_item(temp_item, item_id)
                        should_reflow = True

                self.seek = len(self.splitfile)
                if should_reflow:
                    self.drawing_tool.reflow(self.collected_items)

# Main
def main():
    # erase our tracker log file from previous runs
    open(tracker_log_path, 'w').close()
    try:
        rt = IsaacTracker(verbose=False, debug=False)
        rt.run()
    except Exception as e:
        import traceback
        with open(tracker_log_path, "a") as log:
            log.write(traceback.format_exc())

if __name__ == "__main__":
    main()
