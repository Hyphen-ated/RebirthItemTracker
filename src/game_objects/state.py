"""This module handles anything related to the item tracker's state"""
from game_objects.item  import Item, Stat, ItemProperty
from game_objects.floor import Floor

class TrackerState(object):
    """This class represents a tracker state, and handle the logic to
    modify it while keeping it coherent
    """

    def __init__(self, seed):
        self.reset(seed)
        # FIXME move this else where
        self.file_prefix = "../"

    def reset(self, seed):
        """
        Reset a run to a given string
        This should be enough to enable the GC to clean everything from the previous run
        """
        self.seed = seed
        self.floor_list = []
        self.item_list = []
        self.bosses = []
        # NOTE do not serialize that
        self.player_stats = {}
        self.guppy_set = set()
        for stat in Stat.LIST:
            self.player_stats[stat] = 0.0

    def add_floor(self, floor, is_alternate):
        """ Add a floor to the current run """
        self.floor_list.append(Floor(floor, is_alternate))

    def last_floor(self):
        """
        Get current floor
        If no floor is in the floor list, create a default one
        """
        if len(self.floor_list) == 0:
            self.add_floor("f1", False)
        return self.floor_list[-1]

    def add_item(self, item_id, is_starting_item, picked_up_floor=None):
        """
        Add an item to the current run, and update player's stats accordingly
        Return true if it has been added false otherwise
        """
        current_floor = picked_up_floor
        # If the item IDs are equal, it should say this item already exists
        if current_floor == None:
            current_floor = self.last_floor()
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

    def contains_item(self, item_id):
        """ Looks for the given item_id in our item_list """
        return len([x for x in self.item_list if x.item_id == item_id]) >= 1

    # In a dict/displayable format
    def get_player_stats(self):
        """ Get player stats in a readable format """
        # FIXME move this logic to the view !
        display_stat = {}
        for stat in Stat.LIST:
            value = self.player_stats[stat]

            # Round to 2 decimal places then ignore trailing zeros and trailing periods
            # Doing just 'rstrip("0.")' breaks on "0.00"
            display = format(value, ".2f").rstrip("0").rstrip(".")

            # For example, set "0.6" to ".6"
            if abs(value) < 1 and value != 0:
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
        """ Update player's stats with the given item """
        item_info = item.info
        for stat in Stat.LIST:
            if stat not in item_info:
                continue
            change = float(item_info.get(stat))
            self.player_stats[stat] += change
            value = self.player_stats[stat]

            # FIXME move this logic to the view !
            # Round to 2 decimal places then ignore trailing zeros and trailing periods
            # Doing just 'rstrip("0.")' breaks on "0.00"
            display = format(value, ".2f").rstrip("0").rstrip(".")

            # For example, set "0.6" to ".6"
            if abs(value) < 1:
                display = display.lstrip("0")

            if value > -0.00001:
                display = "+" + display
            # self.player_stats_display[stat] = display
            # FIXME move this elsewhere ?
            with open(self.file_prefix + "overlay text/" + stat + ".txt", "w+") as sfile:
                sfile.write(display)

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
            with open(self.file_prefix + "overlay text/" + Stat.IS_GUPPY + ".txt", "w+") as sfile:
                sfile.write(display)
            # self.player_stats_display[Stat.IS_GUPPY] = display

    # Add curse to last floor
    def add_curse(self, curse):
        """ Add a curse to current floor """
        self.last_floor().add_curse(curse)


    def add_boss(self, room, kill_time):
        """ Add boss to seen boss """
        if room not in [x[0] for x in self.bosses]:
            self.bosses.append((room, kill_time))
            # self.log_msg("Defeated %s%s boss %s at time %s" % (len(self.bosses),
                         # self.suffix(len(self.bosses)), room, kill_time), "D")
            # FIXME restore the logging thing
            # print "Defeated %s%s boss %s at time %s" % (len(self.bosses),
                         # self.suffix(len(self.bosses)), room, kill_time)


# This is just for the suffix of the boss kill number
# def suffix(d):
    # return 'th' if 11 <= d <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(d % 10, 'th')
