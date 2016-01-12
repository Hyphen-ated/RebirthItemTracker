# Imports
from game_objects.item  import Item, Stat, ItemProperty
from game_objects.floor import Floor

class TrackerState(object):
    def __init__(self, seed):
        self.reset(seed)
        # FIXME move this else where
        self.file_prefix      = "../"

    def reset(self, seed):
        self.seed = seed
        self.floor_list   = []
        self.item_list    = []
        self.bosses       = []
        # NOTE do not serialize that
        self.player_stats = {}
        self.guppy_set = set()
        for stat in Stat.LIST:
            self.player_stats[stat] = 0.0

    def add_floor(self, floor, is_alternate):
        self.floor_list.append(Floor(floor, is_alternate))

    def last_floor(self):
        if len(self.floor_list) > 0:
            return self.floor_list[-1]
        else:
            return None

    # Return true if added, false otherwise
    def add_item(self, item_id, is_starting_item, picked_up_floor = None):
        # Default current floor to basement 1 if none
        if len(self.floor_list) == 0:
            self.add_floor("f1", False)

        current_floor = picked_up_floor
        # If the item IDs are equal, it should say this item already exists
        if current_floor == None:
            current_floor = self.floor_list[-1]
        temp_item = Item(item_id, current_floor, is_starting_item)
        # space_split = line.split(" ") # Hacky string manipulation
        # item_name = " ".join(space_split[3:])[1:-1]

        # Ignore repeated pickups of space bar items
        if not (temp_item.info.get(ItemProperty.SPACE, False) and temp_item in self.item_list):
            self.item_list.append(temp_item)
            self.add_stats_for_item(temp_item)
            return True
        else:
            return False

    # In a dict/displayable format
    def get_player_stats(self):
        display_stat = {}
        for stat in Stat.LIST:
            value = self.player_stats[stat]

            # FIXME move this logic to the view !
            # Round to 2 decimal places then ignore trailing zeros and trailing periods
            display = format(value, ".2f").rstrip("0").rstrip(".") # Doing just 'rstrip("0.")' breaks on "0.00"

            # For example, set "0.6" to ".6"
            if abs(value) < 1:
                display = display.lstrip("0")

            if value > -0.00001:
                display = "+" + display
            display_stat[stat] = display

        if len(self.guppy_set) >= 3:
            display_stat[Stat.IS_GUPPY] = "yes"
        else:
            display_stat[Stat.IS_GUPPY] = str(len(self.guppy_set))
        return display_stat



    def add_stats_for_item(self, item):
        item_info = item.info
        for stat in Stat.LIST:
            if stat not in item_info:
                continue
            change = float(item_info.get(stat))
            self.player_stats[stat] += change
            value = self.player_stats[stat]

            # FIXME move this logic to the view !
            # Round to 2 decimal places then ignore trailing zeros and trailing periods
            display = format(value, ".2f").rstrip("0").rstrip(".") # Doing just 'rstrip("0.")' breaks on "0.00"

            # For example, set "0.6" to ".6"
            if abs(value) < 1:
                display = display.lstrip("0")

            if value > -0.00001:
                display = "+" + display
            # self.player_stats_display[stat] = display
            # FIXME move this elsewhere ?
            with open(self.file_prefix + "overlay text/" + stat + ".txt", "w+") as f:
                f.write(display)

        # If this can make us guppy, check if we're guppy
        if Stat.IS_GUPPY in item_info and item_info.get(Stat.IS_GUPPY):
            self.guppy_set.add(item)
            # FIXME to the view !
            display = ""
            if len(self.guppy_set) >= 3:
                display = "yes"
            else:
                display = str(len(self.guppy_set))
            # FIXME move this elsewhere ?
            with open(self.file_prefix + "overlay text/" + stat + ".txt", "w+") as f:
                f.write(display)
            # self.player_stats_display[Stat.IS_GUPPY] = display

    # Add curse to last floor
    def add_curse(self, curse):
        if len(self.floor_list) > 0:
            self.floor_list[-1].add_curse(curse)

    # This is just for the suffix of the boss kill number
    def suffix(self, d):
        return 'th' if 11 <= d <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(d % 10, 'th')

    def add_boss(self, room, kill_time):
        if room not in [x[0] for x in self.bosses]:
            self.bosses.append((room, kill_time))
            # self.log_msg("Defeated %s%s boss %s at time %s" % (len(self.bosses),
                         # self.suffix(len(self.bosses)), room, kill_time), "D")
            # FIXME restore the logging thing
            # print "Defeated %s%s boss %s at time %s" % (len(self.bosses),
                         # self.suffix(len(self.bosses)), room, kill_time)


