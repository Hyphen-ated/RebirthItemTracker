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

if platform.system() == "Windows":
    import pygameWindowInfo
from pygame.locals import *
from pygame.scrap import *
from pygame_helpers import *
from collections import defaultdict
import string

# TODO: can actually  be a floor as well now, not just an item - should be changed in the future
class ItemInfo:
    def __init__(self, id, x, y, index, shown, floor):
        self.id = id
        self.x = x
        self.y = y
        self.shown = shown
        self.index = index
        self.floor = floor


# TODO: keep track of all curses
class Floor:
    def __init__(self, id):
        self.id = id
        self.blind = False
        self.lost = False


# Player stat constants (keys to player_stats and player_stats_display)
# This is a subset of all available ItemPropertys
class Stat:
    DMG = "dmg"
    DMG_X = "dmgx"
    DELAY = "delay"
    DELAY_X = "delayx"
    HEALTH = "health"
    SPEED = "speed"
    SHOT_SPEED = "shotspeed"
    TEAR_RANGE = "range"
    HEIGHT = "height"
    TEARS = "tears"
    SOUL_HEARTS = "soulhearts"
    SIN_HEARTS = "sinhearts"
    IS_GUPPY = "guppy"
    # used for init and reset - does not have all stats yet
    LIST = [DMG, DELAY, SPEED, SHOT_SPEED, TEAR_RANGE, HEIGHT, TEARS]


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
        self.drawingTool = None

        # initialize isaac stuff
        self.collected_items = []  # list of string item ids with no leading zeros. can also contain "f1" through "f12" for floor markers
        self.collected_guppy_items = []  # list of guppy items collected, probably redundant, oh well
        self.collected_blind_item_indices = []  # list of indexes into the collected_items array for items that were picked up blind
        self.rolled_item_indices = []  # list of indexes into the collected_items array for items that were rerolled
        self.collected_item_info = []  # list of "immutable" ItemInfo objects used for determining the layout to draw
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
        self.filter_list = []  # list of string item ids with zeros stripped, they are items we don't want to see
        self.guppy_list = []
        self.space_list = []
        self.healthonly_list = []
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
        self.current_floor = ()  # 2-tuple with first value being floor number, second value being alt stage value (0 or 1, r.n.)
        self.spawned_coop_baby = 0  # last spawn of a co op baby
        self.roll_icon = None
        self.blind_icon = None
        # Load all of the settings from the "options.json" file
        self.load_options()
        

        with open("items.json", "r") as items_file:
            self.items_info = json.load(items_file)
        for item_id, item in self.items_info.iteritems():
            short_id = item_id.lstrip("0")
            if not item[ItemProperty.SHOWN]:
                self.filter_list.append(short_id)
            if ItemProperty.GUPPY in item and item[ItemProperty.GUPPY]:
                self.guppy_list.append(short_id)
            if ItemProperty.SPACE in item and item[ItemProperty.SPACE]:
                self.space_list.append(short_id)
            if ItemProperty.HEALTH_ONLY in item and item[ItemProperty.HEALTH_ONLY]:
                self.healthonly_list.append(short_id)
            if ItemProperty.IN_SUMMARY in item and item[ItemProperty.IN_SUMMARY]:
                self.in_summary_list.append(short_id)
            if ItemProperty.SUMMARY_CONDITION in item and item[ItemProperty.SUMMARY_CONDITION]:
                self.summary_condition_list.append(short_id)

        self.floor_id_to_label = {
            "f1": "B1",
            "f2": "B2",
            "f3": "C1",
            "f4": "C2",
            "f5": "D1",
            "f6": "D2",
            "f7": "W1",
            "f8": "W2",
            "f9": "SHEOL",
            "f10": "CATH",
            "f11": "DARK",
            "f12": "CHEST",
            "f1x": "BXL",
            "f3x": "CXL",
            "f5x": "DXL",
            "f7x": "WXL",
        }

    def load_options(self):
        with open("options.json", "r") as json_file:
            self.options = json.load(json_file)

        size_multiplier = int(8 * self.options[Option.SIZE_MULTIPLIER])

        # anything that gets calculated and cached based on something in options now needs to be flushed
        self.text_margin_size = size_multiplier
        # font can only be initialized after pygame is set up
        if self.font:
            self.font = pygame.font.SysFont(self.options[Option.SHOW_FONT],
                                            size_multiplier,
                                            bold=self.options[Option.BOLD_FONT])
        self._image_library = {}
        self.roll_icon = self.get_scaled_icon(self.id_to_image("284"),
                                              size_multiplier * 2)
        self.blind_icon = self.get_scaled_icon("collectibles/questionmark.png",
                                               size_multiplier * 2)

    def get_scaled_icon(self, path, scale):
        return pygame.transform.scale(self.get_image(path), (scale, scale))

    def save_options(self):
        with open("options.json", "w") as json_file:
            json.dump(self.options, json_file, indent=3, sort_keys=True)

    # just for debugging
    def log_msg(self, msg, level):
        if level == "V" and self.verbose: print msg
        if level == "D" and self.debug: print msg

    # just for the suffix of boss kill number lol
    def suffix(self, d):
        return 'th' if 11 <= d <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(
            d % 10, 'th')

    def check_end_run(self, line, cur_line_num):
        if not self.run_ended:
            died_to = ""
            end_type = ""
            if self.bosses and self.bosses[-1][0] in ['???', 'The Lamb',
                                                      'Mega Satan']:
                end_type = "Won"
            elif (self.seed != '') and line.startswith('RNG Start Seed:'):
                end_type = "Reset"
            elif line.startswith('Game Over.'):
                end_type = "Death"
                died_to = re.search('(?i)Killed by \((.*)\) spawned',
                                    line).group(1)
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

    # image library stuff, from openbookproject.net
    def get_image(self, path):
        image = self._image_library.get(path)
        if image is None:
            canonicalized_path = path.replace('/', os.sep).replace('\\', os.sep)
            image = pygame.image.load(canonicalized_path)
            size_multiplier = self.options[Option.SIZE_MULTIPLIER]
            scaled_image = pygame.transform.scale(image, (
                int(image.get_size()[0] * size_multiplier),
                int(image.get_size()[1] * size_multiplier)))
            self._image_library[path] = scaled_image
        return image

    def build_position_index(self):
        w = self.options[Option.WIDTH]
        h = self.options[Option.HEIGHT]
        # 2d array of size h, w
        self.item_position_index = [[None for x in xrange(w)] for y in
                                    xrange(h)]
        self.num_displayed_items = 0
        size_multiplier = 32 * self.options[Option.SIZE_MULTIPLIER]
        for item in self.collected_item_info:
            if item.shown and not item.floor:
                self.num_displayed_items += 1
                for y in range(int(item.y), int(item.y + size_multiplier)):
                    if y >= h:
                        continue
                    row = self.item_position_index[y]
                    for x in range(int(item.x), int(item.x + size_multiplier)):
                        if x >= w:
                            continue
                        row[x] = item.index

    def reflow(self):
        size_multiplier = self.options[Option.SIZE_MULTIPLIER] * .5
        item_icon_size = int(
            self.options[Option.DEFAULT_SPACING] * size_multiplier)
        item_icon_footprint = item_icon_size
        result = self.try_layout(item_icon_footprint, item_icon_size, False)
        while result is None:
            item_icon_footprint -= 1
            if item_icon_footprint < self.options[
                Option.MIN_SPACING] or item_icon_footprint < 4:
                result = self.try_layout(item_icon_footprint, item_icon_size,
                                         True)
            else:
                result = self.try_layout(item_icon_footprint, item_icon_size,
                                         False)

        self.collected_item_info = result
        self.build_position_index()

    def try_layout(self, icon_footprint, icon_size, force_layout):
        new_item_info = []
        cur_row = 0
        cur_column = 0
        index = 0
        vert_padding = 0
        if self.options[Option.SHOW_FLOORS]:
            vert_padding = self.text_margin_size
        for item_id in self.collected_items:
            item_x = icon_footprint * cur_column
            item_y = self.text_height + (icon_footprint * cur_row) + (
                vert_padding * (cur_row + 1))
            floor = False
            shown = True
            if item_id not in self.filter_list \
                    and (not item_id in self.healthonly_list or self.options[
                        Option.SHOW_HEALTH_UPS]) \
                    and (not item_id in self.space_list or item_id in self.guppy_list or
                                self.options[Option.SHOW_SPACE_ITEMS]) \
                    and (not index in self.rolled_item_indices or self.options[
                        Option.SHOW_REROLLED_ITEMS]):

                # check to see if we are about to go off the right edge
                size_multiplier = 32 * self.options[Option.SIZE_MULTIPLIER]
                if icon_footprint * cur_column + size_multiplier > self.options[
                    Option.WIDTH]:
                    if (not force_layout) \
                            and self.text_height + (
                                        icon_footprint + vert_padding) * (
                                        cur_row + 1) + icon_size + vert_padding \
                                    > self.options[Option.HEIGHT]:
                        return None
                    cur_row += 1
                    cur_column = 0

                floor = item_id.startswith('f')
                if not floor:
                    cur_column += 1
            else:
                shown = False

            new_item_info.append(
                ItemInfo(item_id, item_x, item_y, index, shown, floor))
            index += 1
        return new_item_info

    def add_stats_for_item(self, item_info, item_id):
        for stat in [Stat.DMG, Stat.DELAY, Stat.SPEED, Stat.SHOT_SPEED,
                     Stat.TEAR_RANGE, Stat.HEIGHT, Stat.TEARS]:
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

        if Stat.IS_GUPPY in item_info and item_info.get(Stat.IS_GUPPY) \
                and item_id not in self.collected_guppy_items:
            self.collected_guppy_items.append(item_id)
            display = ""
            if len(self.collected_guppy_items) >= 3:
                display = "yes"
            else:
                display = str(len(self.collected_guppy_items))
            with open("overlay text/" + stat + ".txt", "w+") as f:
                f.write(display)
            self.player_stats_display[Stat.IS_GUPPY] = display

    def reset_player_stats(self):
        for stat in Stat.LIST:
            self.player_stats[stat] = 0.0
            self.player_stats_display[stat] = "+0"

    def generate_item_description(self, item_info):
        desc = ""
        text = item_info.get("text")
        dmg = item_info.get(Stat.DMG)
        dmgx = item_info.get(Stat.DMG_X)
        delay = item_info.get(Stat.DELAY)
        delayx = item_info.get(Stat.DELAY_X)
        health = item_info.get(Stat.HEALTH)
        speed = item_info.get(Stat.SPEED)
        shotspeed = item_info.get(Stat.SHOT_SPEED)
        tearrange = item_info.get(Stat.TEAR_RANGE)
        height = item_info.get(Stat.HEIGHT)
        tears = item_info.get(Stat.TEARS)
        soulhearts = item_info.get(Stat.SOUL_HEARTS)
        sinhearts = item_info.get(Stat.SIN_HEARTS)
        if dmg:
            desc += dmg + " dmg, "
        if dmgx:
            desc += "x" + dmgx + " dmg, "
        if tears:
            desc += tears + " tears, "
        if delay:
            desc += delay + " tear delay, "
        if delayx:
            desc += "x" + delayx + " tear delay, "
        if shotspeed:
            desc += shotspeed + " shotspeed, "
        if tearrange:
            desc += tearrange + " range, "
        if height:
            desc += height + " height, "
        if speed:
            desc += speed + " speed, "
        if health:
            desc += health + " health, "
        if soulhearts:
            desc += soulhearts + " soul hearts, "
        if sinhearts:
            desc += sinhearts + " sin hearts, "
        if text:
            desc += text
        if desc.endswith(", "):
            desc = desc[:-2]
        if len(desc) > 0:
            desc = ": " + desc
        return desc

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
        floor = self.get_floor(floor_id)
        # a floor can't be lost _and_ blind
        # (with amnesia it could be, but we can't tell from log.txt)
        return self.get_floor_name(floor_id) + \
            ("(bld)" if floor.blind else "") + \
            ("(lst)" if floor.lost else "")

    def generate_floor_summary(self, floor_id, items):
        floor_label = self.get_floor_label(floor_id)
        floor = self.get_floor(floor_id)
        if floor is None:
            return "Error - could not find floor " + floor_id
        if not items:
            # lost floors are still relevant even without items
            return floor_label if floor.lost else None
        return floor_label + " " + string.join(items, "/")

    def get_floor_name(self, floor_id):
        return self.floor_id_to_label[floor_id]

    def get_floor(self, floor_id):
        for floor in self.floors:
            if floor.id is floor_id:
                return floor
        # Should not happen
        return None

    def get_items_per_floor(self):
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

    def color(self, string):
        return pygame.color.Color(str(string))

    def load_selected_detail_page(self):
        # TODO open browser if this is not None
        if not self.selected_item_idx:
            return
        url = self.options[Option.ITEM_DETAILS_LINK]
        if not url:
            return
        item_id = self.collected_item_info[self.selected_item_idx].id
        url = url.replace("$ID", item_id)
        webbrowser.open(url, autoraise=True)
        return

    def adjust_selected_item(self, amount):
        item_length = len(self.collected_item_info)
        if self.num_displayed_items < 1:
            return
        if self.selected_item_idx is None and amount > 0:
            self.selected_item_idx = 0
        elif self.selected_item_idx is None and amount < 0:
            self.selected_item_idx = item_length - 1
        else:
            done = False
            while not done:
                self.selected_item_idx += amount
                # clamp it to the range (0, length)
                self.selected_item_idx = (
                                             self.selected_item_idx + item_length) % item_length
                selected_type = self.collected_item_info[self.selected_item_idx]
                done = selected_type.shown and not selected_type.floor

        self.item_message_start_time = self.framecount

    def item_message_countdown_in_progress(self):
        return self.item_message_start_time + self.get_message_duration() > self.framecount

    def item_pickup_countdown_in_progress(self):
        return self.item_pickup_time + self.get_message_duration() > self.framecount

    def get_message_duration(self):
        return (self.options[Option.MESSAGE_DURATION] *
                self.options[Option.FRAMERATE_LIMIT])

    def write_item_text(self, my_font, screen):
        item_idx = self.selected_item_idx
        if len(self.collected_items) < 0:
            # no items, nothing to show
            return False
        if item_idx is None and self.item_pickup_countdown_in_progress():
            # we want to be showing an item but they haven't selected one, that means show the newest item
            item_idx = -1
        if item_idx is None or len(self.collected_items) < item_idx:
            # we got into a weird state where we think we should be showing something unshowable, bail out
            return False
        item = self.collected_items[item_idx]
        if item.startswith('f'):
            return False
        item_info = self.get_item_info(item)
        desc = self.generate_item_description(item_info)
        self.text_height = draw_text(
            screen,
            "%s%s" % (item_info[ItemProperty.NAME], desc),
            self.color(self.options[Option.TEXT_COLOR]),
            pygame.Rect(2, 2, self.options[Option.WIDTH] - 2,
                        self.options[Option.HEIGHT] - 2),
            my_font,
            aa=True,
            wrap=self.options[Option.WORD_WRAP]
        )
        return True

    def load_log_file(self):
        self.log_not_found = False
        path = None
        logfile_location = ""
        if platform.system() == "Windows":
            logfile_location = os.environ[
                                   'USERPROFILE'] + '/Documents/My Games/Binding of Isaac Rebirth/'
        elif platform.system() == "Linux":
            logfile_location = os.getenv('XDG_DATA_HOME',
                os.path.expanduser('~') + '/.local/share') + '/binding of isaac rebirth/'
        elif platform.system() == "Darwin":
            logfile_location = os.path.expanduser(
                '~') + '/Library/Application Support/Binding of Isaac Rebirth/'
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
            github_info_json = urllib2.urlopen(
                "https://api.github.com/repos/Hyphen-ated/RebirthItemTracker/releases/latest").read()
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

    def id_to_image(self, id):
        return 'collectibles/collectibles_%s.png' % id.zfill(3)

    def draw_floor(self, f, screen, my_font):
        text_color = self.options[Option.TEXT_COLOR]
        size_multiplier = self.options[Option.SIZE_MULTIPLIER]
        pygame.draw.lines(
            screen,
            self.color(text_color),
            False,
            ((f.x + 2, int(f.y + 24 * size_multiplier)),
             (f.x + 2, f.y),
             (int(f.x + 16 * size_multiplier), f.y))
        )
        image = my_font.render(self.get_floor_name(f.id), True,
                               self.color(text_color))
        screen.blit(image, (f.x + 4, f.y - self.text_margin_size))

    def draw_item(self, item, screen):
        image = self.get_image(self.id_to_image(item.id))
        screen.blit(image, (item.x, item.y))
        if item.index in self.rolled_item_indices:
            screen.blit(self.roll_icon, (item.x, item.y))
        if self.options[Option.SHOW_BLIND_ICON] and item.index in self.collected_blind_item_indices:
            screen.blit(self.blind_icon,
                        (item.x, item.y + self.options[Option.SIZE_MULTIPLIER] * 12))

    def run(self):
        os.environ['SDL_VIDEO_WINDOW_POS'] = "%d, %d" % (
            self.options[Option.X_POSITION], self.options[Option.Y_POSITION])
        # initialize pygame system stuff
        pygame.init()
        update_notifier = self.check_for_update()
        pygame.display.set_caption("Rebirth Item Tracker v0.8" + update_notifier)
        screen = pygame.display.set_mode(
            (self.options[Option.WIDTH], self.options[Option.HEIGHT]), RESIZABLE)
        self.drawingTool = DrawingTool(screen)
        self.font = pygame.font.SysFont(self.options[Option.SHOW_FONT], int(
            8 * self.options[Option.SIZE_MULTIPLIER]), bold=self.options[Option.BOLD_FONT])
        pygame.display.set_icon(
            self.get_image("collectibles/collectibles_333.png"))
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
                        self.options[Option.X_POSITION] = winPos["left"]
                        self.options[Option.Y_POSITION] = winPos["top"]
                        self.save_options()
                    done = True
                elif event.type == VIDEORESIZE:
                    screen = pygame.display.set_mode(event.dict['size'],
                                                     RESIZABLE)
                    self.options[Option.WIDTH] = event.dict["w"]
                    self.options[Option.HEIGHT] = event.dict["h"]
                    self.save_options()
                    self.reflow()
                    pygame.display.flip()
                elif event.type == MOUSEMOTION:
                    if pygame.mouse.get_focused():
                        x, y = pygame.mouse.get_pos()
                        if y < len(self.item_position_index):
                            selected_row = self.item_position_index[y]
                            if x < len(selected_row):
                                self.selected_item_idx = selected_row[x]
                                if self.selected_item_idx:
                                    self.item_message_start_time = self.framecount
                elif event.type == KEYDOWN:
                    if len(self.collected_items) > 0:
                        if event.key == pygame.K_RIGHT:
                            self.adjust_selected_item(1)
                        elif event.key == pygame.K_LEFT:
                            self.adjust_selected_item(-1)
                        elif event.key == pygame.K_RETURN:
                            self.load_selected_detail_page()
                        elif event.key == pygame.K_c and pygame.key.get_mods() & pygame.KMOD_CTRL:
                            self.generate_run_summary()
                elif event.type == MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self.load_selected_detail_page()
                    if event.button == 3:
                        if os.path.isfile("optionpicker/option_picker.exe"):
                            self.log_msg("Starting option picker from .exe",
                                         "D")
                            subprocess.call(os.path.join('optionpicker',
                                                         "option_picker.exe"),
                                            shell=True)
                        elif os.path.isfile("option_picker.py"):
                            self.log_msg("Starting option picker from .py", "D")
                            subprocess.call("python option_picker.py",
                                            shell=True)
                        else:
                            self.log_msg("No option_picker found!", "D")
                        self.load_options()
                        self.selected_item_idx = None  # Clear this to avoid overlapping an item that may have been hidden
                        self.reflow()

            screen.fill(self.color(self.options[Option.BACKGROUND_COLOR]))
            clock.tick(int(self.options[Option.FRAMERATE_LIMIT]))

            if self.log_not_found:
                draw_text(
                    screen,
                    "log.txt not found. Put the RebirthItemTracker folder inside the isaac folder, next to log.txt",
                    self.color(self.options[Option.TEXT_COLOR]),
                    pygame.Rect(2, 2, self.options[Option.WIDTH] - 2,
                                self.options[Option.HEIGHT] - 2),
                    self.font,
                    aa=True,
                    wrap=True
                )

            # 19 pixels is the default line height, but we don't know what the line height is with respect to the user's particular size_multiplier.
            # Thus, we can just draw a single space to ensure that the spacing is consistent whether text happens to be showing or not.
            if self.options[Option.SHOW_DESCRIPTION] or self.options[
                Option.SHOW_CUSTOM_MESSAGE]:
                self.text_height = draw_text(
                    screen,
                    " ",
                    self.color(self.options[Option.TEXT_COLOR]),
                    pygame.Rect(2, 2, self.options[Option.WIDTH] - 2,
                                self.options[Option.HEIGHT] - 2),
                    self.font,
                    aa=True,
                    wrap=self.options[Option.WORD_WRAP]
                )
            else:
                self.text_height = 0

            text_written = False
            # draw item pickup text, if applicable
            if (len(self.collected_items) > 0
                and self.options[Option.SHOW_DESCRIPTION]
                and self.run_start_frame + 120 < self.framecount
                and self.item_message_countdown_in_progress()):
                text_written = self.write_item_text(self.font, screen)
            if not text_written and self.options[
                Option.SHOW_CUSTOM_MESSAGE] and not self.log_not_found:
                # draw seed/guppy text:
                seed = self.seed

                dic = defaultdict(str, seed=seed)
                dic.update(self.player_stats_display)

                # Use vformat to handle the case where the user adds an undefined
                # placeholder in default_message
                message = string.Formatter().vformat(
                    self.options[Option.CUSTOM_MESSAGE],
                    (),
                    dic
                )
                self.text_height = draw_text(
                    screen,
                    message,
                    self.color(self.options[Option.TEXT_COLOR]),
                    pygame.Rect(2, 2, self.options[Option.WIDTH] - 2,
                                self.options[Option.HEIGHT] - 2),
                    self.font,
                    aa=True, wrap=self.options[Option.WORD_WRAP]
                )
            self.reflow()

            if not self.item_message_countdown_in_progress():
                self.selected_item_idx = None

            floor_to_draw = None
            # draw items on screen, excluding filtered items:
            for item in self.collected_item_info:
                if item.shown:
                    if item.floor:
                        floor_to_draw = item
                    else:
                        self.draw_item(item, screen)
                        # don't draw a floor until we hit the next item (this way multiple floors in a row collapse)
                        if floor_to_draw and self.options[Option.SHOW_FLOORS]:
                            self.draw_floor(floor_to_draw, screen, self.font)

            # also draw the floor if we hit the end, so the current floor is visible
            if floor_to_draw and self.options[Option.SHOW_FLOORS]:
                self.draw_floor(floor_to_draw, screen, self.font)

            if (self.selected_item_idx
                and self.selected_item_idx < len(self.collected_item_info)
                and self.item_message_countdown_in_progress()):
                item = self.collected_item_info[self.selected_item_idx]
                if item.id not in self.floor_id_to_label:
                    screen.blit(self.get_image(self.id_to_image(item.id)),
                                (item.x, item.y))
                    size_multiplier = int(32 * self.options[Option.SIZE_MULTIPLIER])
                    pygame.draw.rect(
                        screen,
                        self.color(self.options[Option.TEXT_COLOR]),
                        (item.x,
                         item.y,
                         size_multiplier,
                         size_multiplier),
                        2
                    )

            pygame.display.flip()
            self.framecount += 1

            # process log stuff every read_delay seconds. making sure to truncate to an integer or else it might never mod to 0
            if self.framecount % int(self.options[Option.FRAMERATE_LIMIT] * self.read_delay) == 0:
                self.load_log_file()
                self.splitfile = self.content.splitlines()
                # return to start if seek passes the end of the file (usually b/c log file restarted)
                if self.seek > len(self.splitfile):
                    self.log_msg(
                        "Current line number longer than lines in file, returning to start of file",
                        "D")
                    self.seek = 0

                should_reflow = False
                # process log's new output
                for current_line_number, line in enumerate(
                        self.splitfile[self.seek:]):
                    self.log_msg(line, "V")
                    # end floor boss defeated, hopefully?
                    if line.startswith('Mom clear time:'):
                        kill_time = int(line.split(" ")[-1])
                        # if you re-enter a room you get a "mom clear time" again, check for that.
                        # can you fight the same boss twice?
                        if self.current_room not in [x[0] for x in self.bosses]:
                            self.bosses.append((self.current_room, kill_time))
                            self.log_msg("Defeated %s%s boss %s at time %s" % (
                                len(self.bosses), self.suffix(len(self.bosses)),
                                self.current_room, kill_time), "D")
                    # check + handle the end of the run (order important here!)
                    # we want it after boss kill (so we have that handled) but before RNG Start Seed (so we can handle that)
                    self.check_end_run(line, current_line_number + self.seek)
                    # start of a run
                    if line.startswith('RNG Start Seed:'):
                        # this assumes a fixed width, but from what I see it seems safe
                        self.seed = line[16:25]
                        self.log_msg("Starting new run, seed: %s" % self.seed,
                                     "D")
                        self.run_start_frame = self.framecount
                        self.rolled_item_indices = []
                        self.collected_items = []
                        self.collected_guppy_items = []
                        self.collected_blind_item_indices = []
                        self.log_msg("Emptied item array", "D")
                        self.bosses = []
                        self.log_msg("Emptied boss array", "D")
                        self.run_start_line = current_line_number + self.seek
                        self.run_ended = False
                        self.reset_player_stats()
                        with open("overlay text/seed.txt", "w+") as f:
                            f.write(self.seed)

                    # entered a room, use to keep track of bosses
                    if line.startswith('Room'):
                        self.current_room = re.search('\((.*)\)', line).group(1)
                        if 'Start Room' not in line:
                            self.getting_start_items = False
                        self.log_msg("Entered room: %s" % self.current_room,
                                     "D")
                    if line.startswith('Level::Init'):
                        self.current_floor = tuple(
                            [re.search(
                                "Level::Init m_Stage (\d+), m_AltStage (\d+)",
                                line).group(x) for x in [1, 2]])
                        # assume floors aren't cursed until we see they are
                        self.blind_floor = False
                        self.getting_start_items = True
                        floor = int(self.current_floor[0])
                        alt = self.current_floor[1]
                        # special handling for cath and chest
                        if alt == '1' and (floor == 9 or floor == 11):
                            floor += 1
                        floor_id = 'f' + str(floor)
                        self.collected_items.append(floor_id) # TODO: remove this line - items are not floors
                        self.floors.append(Floor(floor_id))
                        should_reflow = True
                    last_collected = self.collected_items[-1] if self.collected_items else None
                    if line.startswith("Curse of the Labyrinth!"):
                        # it SHOULD always begin with f (that is, it's a floor) because this line only comes right after the floor line
                        if last_collected.startswith('f'):
                            self.collected_items[-1] += 'x'
                    if line.startswith("Curse of Blind"):
                        self.floors[-1].blind = True
                        self.blind_floor = True
                    if line.startswith("Curse of the Lost!"):
                        self.floors[-1].lost = True
                    if line.startswith("Spawn co-player!"):
                        self.spawned_coop_baby = current_line_number + self.seek
                    if re.search("Added \d+ Collectibles", line):
                        self.log_msg("Reroll detected!", "D")
                        self.rolled_item_indices = [index for index, item in
                                                    enumerate(
                                                        self.collected_items) if
                                                    item[0] != 'f']
                    if line.startswith('Adding collectible'):
                        if len(self.splitfile) > 1 and self.splitfile[
                                            current_line_number + self.seek - 1] == line:
                            self.log_msg(
                                "Skipped duplicate item line from baby presence",
                                "D")
                            continue
                        # hacky string manip, idgaf
                        space_split = line.split(" ")
                        # string has the form "Adding collectible 105 (The D6)"
                        item_id = space_split[2]
                        if ((
                                        current_line_number + self.seek) - self.spawned_coop_baby) < (
                                    len(self.collected_items) + 10) \
                                and item_id in self.collected_items:
                            self.log_msg(
                                "Skipped duplicate item line from baby entry",
                                "D")
                            continue
                        item_name = " ".join(space_split[3:])[1:-1]
                        self.log_msg("Picked up item. id: %s, name: %s" % (
                            item_id, item_name), "D")
                        item_info = self.get_item_info(item_id)
                        with open("overlay text/itemInfo.txt", "w+") as f:
                            desc = self.generate_item_description(item_info)
                            f.write(item_info[ItemProperty.NAME] + ":" + desc)

                        # ignore repeated pickups of space bar items
                        if not (item_info.get(
                                ItemProperty.SPACE) and item_id in self.collected_items):
                            self.collected_items.append(item_id)
                            self.item_message_start_time = self.framecount
                            self.item_pickup_time = self.framecount
                        else:
                            self.log_msg(
                                "Skipped adding item %s to avoid space-bar duplicate" % item_id,
                                "D")
                        self.add_stats_for_item(item_info, item_id)
                        if self.blind_floor and not self.getting_start_items:
                            # the item we just picked up was picked up blind, so add its index here to track that fact
                            self.collected_blind_item_indices.append(
                                len(self.collected_items) - 1)
                        should_reflow = True

                self.seek = len(self.splitfile)
                if should_reflow:
                    self.reflow()


try:
    rt = IsaacTracker(verbose=False, debug=False)
    rt.run()
except Exception as e:
    import traceback

    traceback.print_exc()
