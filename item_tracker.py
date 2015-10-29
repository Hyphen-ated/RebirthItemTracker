import time
import glob
import os
import platform
import webbrowser
import pygame
import re
import json
import subprocess
import urllib2
from view_controls.view import DrawingTool
from game_objects.floor import Floor,Curse
from game_objects.item import Item,Stat

if platform.system() == "Windows":
    import pygameWindowInfo
from pygame.locals import *
from pygame.scrap import *
from pygame_helpers import *
from collections import defaultdict
import string


# Properties that items from items.json can have
# additionally, those items can have any Stat
class ItemProperty:
    NAME = "name"
    SHOWN = "shown"
    GUPPY = "guppy"
    SPACE = "space"
    HEALTH_ONLY = "healthonly"
    IN_SUMMARY = "inSummary"
    SUMMARY_NAME = "summaryName"
    # an item that needs to be present for this item to be mentioned
    # in the summary. can only be one item right now.
    SUMMARY_CONDITION = "summaryCondition"

# Keys to the options dict
class Option:
    X_POSITION = "xposition"
    Y_POSITION = "yposition"
    WIDTH = "width"
    HEIGHT = "height"
    BACKGROUND_COLOR = "background_color"
    FRAMERATE_LIMIT = "framerate_limit"
    #
    SIZE_MULTIPLIER = "size_multiplier"
    DEFAULT_SPACING = "default_spacing"
    MIN_SPACING = "min_spacing"
    #
    SHOW_FONT = "show_font"
    BOLD_FONT = "bold_font"
    TEXT_COLOR = "text_color"
    WORD_WRAP = "word_wrap"
    #
    SHOW_FLOORS = "show_floors"
    SHOW_HEALTH_UPS = "show_health_ups"
    SHOW_SPACE_ITEMS = "show_space_items"
    SHOW_REROLLED_ITEMS = "show_rerolled_items"
    SHOW_BLIND_ICON = "show_blind_icon"
    SHOW_DESCRIPTION = "show_description"
    #
    SHOW_CUSTOM_MESSAGE = "show_custom_message"
    MESSAGE_DURATION = "message_duration"
    CUSTOM_MESSAGE = "custom_message"
    ITEM_DETAILS_LINK = "item_details_link"

class IsaacTracker:
    def __init__(self, verbose=False, debug=False, read_delay=1):

        # Class variables
        self.verbose = verbose
        self.debug = debug
        self.text_height = 0
        self.text_margin_size = None  # will be changed in load_options
        self.font = None  # will be changed in load_options
        self.seek = 0
        self.framecount = 0
        self.read_delay = read_delay
        self.run_ended = True
        self.log_not_found = False
        self.content = ""  # cached contents of log
        self.splitfile = []  # log split into lines
        self.drawing_tool = None

        # initialize isaac stuff
        self.collected_items = []   #List of items collected this run
        self.collected_item_info = []  # list of "immutable" ItemInfo objects used for determining the layout to draw
        self.guppy_set = set() # Used to keep track of whether we're guppy or not
        self.num_displayed_items = 0
        self.selected_item_idx = None
        self.seed = ""
        self.current_room = ""
        self.blind_floor = False
        self.getting_start_items = False
        self.run_start_line = 0
        self.run_start_frame = 0
        self.bosses = []
        self.last_run = {}
        self._image_library = {}
        self.in_summary_list = []
        self.summary_condition_list = []
        self.items_info = {}
        self.floors = []
        self.player_stats = {}
        self.player_stats_display = {}
        self.reset_player_stats()
        self.item_message_start_time = 0
        self.item_pickup_time = 0
        self.item_position_index = []
        self.current_floor = None
        self.floor_tuple = ()  # 2-tuple with first value being floor number, second value being alt stage value (0 or 1, r.n.)
        self.spawned_coop_baby = 0  # last spawn of a co op baby
        self.roll_icon = None
        self.blind_icon = None
        
        #load items info
        with open("items.json", "r") as items_file:
            self.items_info = json.load(items_file)

    def save_options(self):
        with open("options.json", "w") as json_file:
            json.dump(self.options, json_file, indent=3, sort_keys=True)

    # just for debugging
    def log_msg(self, msg, level):
        if level == "V" and self.verbose: print msg
        if level == "D" and self.debug: print msg

    # just for the suffix of boss kill number lol
    def suffix(self, d):
        return 'th' if 11 <= d <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(d % 10, 'th')

    def check_end_run(self, line, cur_line_num):
        if not self.run_ended:
            died_to = ""
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
                    "bosses": self.bosses,
                    "items": self.collected_items,
                    "seed": self.seed,
                    "died_to": died_to,
                    "end_type": end_type
                }
                self.run_ended = True
                self.log_msg("End of Run! %s" % self.last_run, "D")
                if end_type != "Reset":
                    self.save_file(self.run_start_line, cur_line_num, self.seed)

    def save_file(self, start, end, seed):
        self.mkdir("run_logs")
        timestamp = int(time.time())
        seed = seed.replace(" ", "")
        data = "\n".join(self.splitfile[start:end + 1])
        data = "%s\nRUN_OVER_LINE\n%s" % (data, self.last_run)
        with open("run_logs/%s%s.log" % (seed, timestamp), 'wb') as f:
            f.write(data)

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

            # round to 2 decimal places then ignore trailing zeros and trailing periods
            # doing rstrip("0.") breaks on "0.00"
            display = format(value, ".2f").rstrip("0").rstrip(".")
            # 0.6 -> .6
            if abs(value) < 1:
                display = display.lstrip("0")

            if value > -0.00001:
                display = "+" + display
            self.player_stats_display[stat] = display
            with open("overlay text/" + stat + ".txt", "w+") as f:
                f.write(display)
        #If this can make us guppy, check if we're guppy
        if Stat.IS_GUPPY in item_info and item_info.get(Stat.IS_GUPPY):
            self.guppy_set.add(item)
            display = ""
            if len(self.guppy_set) >= 3:
                display = "yes"
            else:
                display = str(len(self.guppy_set))
            with open("overlay text/" + stat + ".txt", "w+") as f:
                f.write(display)
            self.player_stats_display[Stat.IS_GUPPY] = display

    def reset_player_stats(self):
        for stat in Stat.LIST:
            self.player_stats[stat] = 0.0
            self.player_stats_display[stat] = "+0"

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
        #TODO: Broken - fix
        floor = self.get_floor(floor_id)
        # a floor can't be lost _and_ blind
        # (with amnesia it could be, but we can't tell from log.txt)
        return self.get_floor_name(floor_id)

    def generate_floor_summary(self, floor_id, items):
        #TODO: Broken - fix
        floor_label = self.get_floor_label(floor_id)
        floor = self.get_floor(floor_id)
        # Should not happen
        if floor is None:
            return ""
        if not items:
            # lost floors are still relevant even without items
            return floor_label if floor.lost else None
        return floor_label + " " + string.join(items, "/")

    def get_floor_name(self, floor_id):
        #TODO: Broken - fix
        return self.floor_id_to_label[floor_id]

    def get_floor(self, floor_id):
        #TODO: Broken - fix
        for floor in self.floors:
            if floor.id is floor_id:
                return floor
        return None

    def get_items_per_floor(self):
        #TODO: Make this work again using state model
        #TODO: Redo this using new state model
        floors = {}
        current_floor_id = None
        # counter is necessary to find out *when* we became Guppy
        guppy_count = 0

        for item in self.collected_item_info:
            # TODO: why are the ids in the collected_item_info list not lstripped?
            short_id = item.id.lstrip("0")
            if item.floor:  # this is actually a floor, not an item
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
        if platform.system() == "Windows":
            logfile_location = os.environ['USERPROFILE'] + '/Documents/My Games/Binding of Isaac Rebirth/'
        elif platform.system() == "Linux":
            logfile_location = os.getenv('XDG_DATA_HOME',
                os.path.expanduser('~') + '/.local/share') + '/binding of isaac rebirth/'
        elif platform.system() == "Darwin":
            logfile_location = os.path.expanduser('~') + '/Library/Application Support/Binding of Isaac Rebirth/'
        for check in ('../log.txt', logfile_location + 'log.txt'):
            if os.path.isfile(check):
                path = check
                break
        if path is None:
            self.log_not_found = True
            return

        cached_length = len(self.content)
        file_size = os.path.getsize(path)
        if cached_length > file_size or cached_length == 0:  # New log file or first time loading the log
            self.content = open(path, 'rb').read()
        elif cached_length < file_size:  # append existing content
            f = open(path, 'rb')
            f.seek(cached_length + 1)
            self.content += f.read()

    # returns text to put in the title bar
    def check_for_update(self):
        try:
            github_info_json = urllib2.urlopen("https://api.github.com/repos/Hyphen-ated/RebirthItemTracker/releases/latest").read()
            info = json.loads(github_info_json)
            latest_version = info["name"]
            with open('version.txt', 'r') as f:

                if latest_version != f.read():
                    return " (new version available)"
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
        with open("overlay text/seed.txt", "w+") as f:
            f.write(self.seed)

    def run(self):
        self.current_floor = None
        # initialize pygame system stuff
        pygame.init()
        update_notifier = self.check_for_update()
        pygame.display.set_caption("Rebirth Item Tracker v0.8" + update_notifier)
        #Create drawing tool to use to draw everything - it'll create its own screen
        self.drawing_tool = DrawingTool()
        os.environ['SDL_VIDEO_WINDOW_POS'] = "%d, %d" % (
            self.drawing_tool.options[Option.X_POSITION], 
            self.drawing_tool.options[Option.Y_POSITION])
        pygame.display.set_icon(self.drawing_tool.get_image("collectibles/collectibles_333.png"))
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
                    screen = pygame.display.set_mode(event.dict['size'],
                                                     RESIZABLE)
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
                            #self.generate_run_summary()
                elif event.type == MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self.drawing_tool.load_selected_detail_page()
                    if event.button == 3:
                        import option_picker
                        pygame.event.set_blocked([QUIT, MOUSEBUTTONDOWN, KEYDOWN, MOUSEMOTION])
                        option_picker.options_menu().run()
                        pygame.event.set_allowed([QUIT, MOUSEBUTTONDOWN, KEYDOWN, MOUSEMOTION])
                        self.drawing_tool.reset()
                        self.drawing_tool.load_options()
                        self.drawing_tool.reflow(self.collected_items)
            #End Pygame Logic
            
            #Drawing Logic
            clock.tick(int(self.drawing_tool.options[Option.FRAMERATE_LIMIT]))

            if self.log_not_found:
                self.drawing_tool.write_message("log.txt not found. Put the RebirthItemTracker folder inside the isaac folder, next to log.txt")
            
            self.drawing_tool.draw_items(self)
            self.framecount += 1
            #end drawing logic
            
            #Now we re-process the log file to get anything that might've loaded
            # process log stuff every read_delay seconds. making sure to truncate to an integer or else it might never mod to 0
            if self.framecount % int(self.drawing_tool.options[Option.FRAMERATE_LIMIT] * self.read_delay) == 0:
                self.load_log_file()
                self.splitfile = self.content.splitlines()
                # return to start if seek passes the end of the file (usually b/c log file restarted)
                if self.seek > len(self.splitfile):
                    self.log_msg("Current line number longer than lines in file, returning to start of file", "D")
                    self.seek = 0

                should_reflow = False
                getting_start_items = False #This will become true if we're getting starting items
                # process log's new output
                for current_line_number, line in enumerate(self.splitfile[self.seek:]):
                    self.log_msg(line, "V")
                    # end floor boss defeated, hopefully?
                    if line.startswith('Mom clear time:'):
                        kill_time = int(line.split(" ")[-1])
                        # if you re-enter a room you get a "mom clear time" again, check for that.
                        # can you fight the same boss twice?
                        if self.current_room not in [x[0] for x in self.bosses]:
                            self.bosses.append((self.current_room, kill_time))
                            self.log_msg(
                                "Defeated %s%s boss %s at time %s" % (len(self.bosses),
                                self.suffix(len(self.bosses)), self.current_room, kill_time), "D")
                    # check + handle the end of the run (order important here!)
                    # we want it after boss kill (so we have that handled) but before RNG Start Seed (so we can handle that)
                    self.check_end_run(line, current_line_number + self.seek)
                    # start of a run
                    if line.startswith('RNG Start Seed:'):
                        # this assumes a fixed width, but from what I see it seems safe
                        self.seed = line[16:25]
                        self.start_new_run(current_line_number)
                    if line.startswith('Room'):
                        self.current_room = re.search('\((.*)\)', line).group(1)
                        if 'Start Room' not in line:
                            getting_start_items = False
                        self.log_msg("Entered room: %s" % self.current_room,"D")
                    if line.startswith('Level::Init'):
                        floor_tuple = tuple([re.search("Level::Init m_Stage (\d+), m_AltStage (\d+)",line).group(x) for x in [1, 2]])
                        # assume floors aren't cursed until we see they are
                        self.blind_floor = False
                        getting_start_items = True
                        floor = int(floor_tuple[0])
                        alt = floor_tuple[1]
                        # special handling for cath and chest
                        if alt == '1' and (floor == 9 or floor == 11):
                            floor += 1
                        floor_id = 'f' + str(floor)
                        self.current_floor=Floor(floor_id,self,(alt=='1'))
                        should_reflow = True
                    if line.startswith("Curse of the Labyrinth!"):
                        # it SHOULD always begin with f (that is, it's a floor) because this line only comes right after the floor line
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
                        # hacky string manip, idgaf
                        space_split = line.split(" ")
                        # string has the form "Adding collectible 105 (The D6)"
                        item_id = space_split[2]
                        item_info = self.get_item_info(item_id)
                        #If Item IDs are equal, it should say this item already exists
                        temp_item = Item(item_id,self.current_floor,item_info,getting_start_items)
                        if ((current_line_number + self.seek) - self.spawned_coop_baby) < (len(self.collected_items) + 10) \
                                and temp_item in self.collected_items:
                            self.log_msg("Skipped duplicate item line from baby entry","D")
                            continue
                        item_name = " ".join(space_split[3:])[1:-1]
                        self.log_msg("Picked up item. id: %s, name: %s" % (item_id, item_name), "D")
                        with open("overlay text/itemInfo.txt", "w+") as f:
                            desc = temp_item.generate_item_description()
                            f.write(item_info[ItemProperty.NAME] + ":" + desc)

                        # ignore repeated pickups of space bar items
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


try:
    rt = IsaacTracker(verbose=False, debug=False)
    rt.run()
except Exception as e:
    import traceback

    traceback.print_exc()
