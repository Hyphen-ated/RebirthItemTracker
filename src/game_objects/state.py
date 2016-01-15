"""This module handles anything related to the item tracker's state"""
import logging
from game_objects.item  import Item, ItemInfo
from game_objects.floor import Floor

class TrackerState(object):
    """This class represents a tracker state, and handle the logic to
    modify it while keeping it coherent
    """

    def __init__(self, seed):
        self.reset(seed)


    def reset(self, seed):
        """
        Reset a run to a given string
        This should be enough to enable the GC to clean everything from the previous run
        """
        # When the tracker state has been restarted, put this to True
        # The view can then put it to false once it's been rendered
        self.modified = True
        self.seed = seed
        self.floor_list = []
        self.item_list = []
        self.bosses = []
        # NOTE do not serialize that
        self.player_stats = {}
        self.guppy_set = set()
        for stat in ItemInfo.stat_list:
            self.player_stats[stat] = 0.0

    def add_floor(self, floor, is_alternate):
        """ Add a floor to the current run """
        self.floor_list.append(Floor(floor, is_alternate))

    @property
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
        Return a tuple (boolean, list).
        The boolean is true if the item has been added, false otherwise.
        The list contains all the stats that has been modified by this pickup
        """
        current_floor = picked_up_floor
        # If the item IDs are equal, it should say this item already exists
        if current_floor == None:
            current_floor = self.last_floor
        temp_item = Item(item_id, current_floor, is_starting_item)

        # Ignore repeated pickups of space bar items
        if not (temp_item.info.space and temp_item in self.item_list):
            self.item_list.append(temp_item)
            self.__add_stats_for_item(temp_item)
            return True
        else:
            return False

    @property
    def last_item(self):
        """
        Get last item picked up
        Can return None !
        """
        if len(self.item_list) > 0:
            return self.item_list[-1]
        else:
            return None

    def contains_item(self, item_id):
        """ Looks for the given item_id in our item_list """
        return len([x for x in self.item_list if x.item_id == item_id]) >= 1

    def reroll(self):
        """ Tag every (non-spacebar) items as rerolled """
        [item.rerolled() for item in self.item_list]



    # Add curse to last floor
    def add_curse(self, curse):
        """ Add a curse to current floor """
        self.last_floor.add_curse(curse)


    def add_boss(self, room, kill_time):
        """ Add boss to seen boss """
        if room not in [x[0] for x in self.bosses]:
            self.bosses.append((room, kill_time))
            nbosses = len(self.bosses)
            if 11 <= nbosses <= 13:
                suffix = 'th'
            else:
                suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(nbosses % 10, 'th')
            logging.getLogger("tracker").debug("Defeated %s%s boss %s at time %s",
                                               len(self.bosses),
                                               suffix,
                                               room,
                                               kill_time)

    @property
    def last_boss(self):
        """
        Get last boss encountered
        Can return None !
        """
        if len(self.bosses) > 0:
            return self.bosses[-1]
        else:
            return None

    def drawn(self):
        self.modified = False


    def __add_stats_for_item(self, item):
        """
        Update player's stats with the given item.
        """
        item_info = item.info
        for stat in ItemInfo.stat_list:
            if not item_info[stat]:
                continue
            change = float(item_info[stat])
            self.player_stats[stat] += change

        # If this can make us guppy, check if we're guppy
        # Can the .get thing be actually false ?!
        if item_info.guppy:
            self.guppy_set.add(item)

