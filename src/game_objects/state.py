"""This module handles anything related to the item tracker's state"""
import logging
import json
from game_objects.item  import Item, ItemInfo
from game_objects.floor import Floor
from game_objects.serializable import Serializable

class TrackerState(Serializable):
    """This class represents a tracker state, and handle the logic to
    modify it while keeping it coherent
    """
    serialize = [('seed', basestring), ('floor_list', list),
                 ('item_list', list), ('bosses', list), ('tracker_version', basestring), ('game_version', basestring)]
    def __init__(self, seed, tracker_version, game_version):
        self.reset(seed, game_version)
        self.tracker_version = tracker_version

    def reset(self, seed, game_version):
        """
        Reset a run to a given string
        This should be enough to enable the GC to clean everything from the previous run
        """
        # When the tracker state has been restarted, put this to True
        # The view can then put it to false once it's been rendered
        self.modified = True
        self.seed = seed
        self.game_version = game_version
        self.floor_list = []
        self.item_list = []
        self.bosses = []
        self.player_stats = {}
        self.player_transforms = {}
        for stat in ItemInfo.stat_list:
            self.player_stats[stat] = 0.0
        for transform in ItemInfo.transform_list:
            self.player_transforms[transform] = set()

    def add_floor(self, floor):
        """ Add a floor to the current run """
        self.floor_list.append(floor)
        self.modified = True

    @property
    def last_floor(self):
        """
        Get current floor
        If no floor is in the floor list, create a default one
        """
        if len(self.floor_list) == 0:
            self.add_floor(Floor("f1"))
        return self.floor_list[-1]

    def add_item(self, item):
        """
        Add an item to the current run, and update player's stats accordingly
        Return a tuple (boolean, list).
        The boolean is true if the item has been added, false otherwise.
        """

        # Ignore repeated pickups of space bar items
        if not (item.info.space and item in self.item_list):
            self.item_list.append(item)
            self.__add_stats_for_item(item)
            self.modified = True
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


    def add_boss(self, bossid):
        """ Add boss to seen boss """
        if bossid not in self.bosses:
            self.bosses.append(bossid)
            nbosses = len(self.bosses)
            if 11 <= nbosses <= 13:
                suffix = 'th'
            else:
                suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(nbosses % 10, 'th')
            logging.getLogger("tracker").debug("Defeated %s%s boss %s",
                                               len(self.bosses),
                                               suffix,
                                               bossid)

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
        """ Tag this state as rendered """
        self.modified = False

    @staticmethod
    def from_valid_json(json_dic, *args):
        """ Create a state from a type-checked dic """
        state = TrackerState(json_dic['seed'], json_dic['tracker_version'], json_dic['game_version'])
        # The order is important, we want a list of legal floors the item can
        # be picked up on before parsing items
        for floor_dic in json_dic['floor_list']:
            floor = Floor.from_json(floor_dic)
            if not floor:
                return None
            state.add_floor(floor)
        for bossstr in json_dic['bosses']:
            # TODO create a serializable boss class that would create
            # a boss object with description from a bossid
            # In any case it's sufficient to (de)serialize only bossids
            if not isinstance(bossstr, basestring):
                return None
            state.add_boss(bossstr)
        for item_dic in json_dic['item_list']:
            item = Item.from_json(item_dic, state.floor_list)
            if not item:
                return None
            state.add_item(item)

        return state

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
        for transform in ItemInfo.transform_list:
            if not item_info[transform]:
                continue
            self.player_transforms[transform].add(item)


class TrackerStateEncoder(json.JSONEncoder):
    """ An encoder to provide to the json.load method, which handle game objects """
    def default(self, obj):
        if isinstance(obj, Serializable):
            return obj.to_json()
        return obj.__dict__
