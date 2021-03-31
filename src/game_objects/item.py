"""This module handles anything related to items and their characteristics"""
from game_objects.serializable import Serializable
import logging

from error_stuff import log_error
from options import Options


class Item(Serializable):
    """This class represent an Item in the game, and handles its properties"""

    # These will be needed by both the log reader and the serializer. They're set in ItemTracker.__init__
    # they shouldn't change after that.
    items_info = {}
    abplus_items_info = {}
    custom_items_info = {}

    serialize = [('item_id', basestring),
                 ('floor_id', basestring),
                 ('flags', basestring)]

    modded_item_id_prefix = "m"

    serialization_flags = {"blind":"b", "was_rerolled":"r", "starting_item":"s"}
    def __init__(self, item_id, floor, starting_item=False, was_rerolled=False, blind=False, flagstr=None, is_Jacob_item=False, is_Esau_item=False):
        # item_id is a string that identifies what kind of item it is.
        # If this is numeric, then it represents an item from the base game, an official expansion, or antibirth
        # If it's non-numeric, then it represents an item from a mod. numeric ids of modded items are unstable, so the
        # value we use is the name of the custom item as displayed in log.txt, prefixed with "m" (for "mod") in case someone makes
        # an item with a numeric name. (The "m" isn't shown in items_custom.json, because it's a hacky impl detail)
        # For example, the Racing+ mod has a custom version of the item "Betrayal". log.txt will display this:
        # [INFO] - Adding collectible 512 (Betrayal)
        # and the value of item_id would be "mBetrayal"
        self.item_id = item_id

        # The floor the item was found on
        self.floor = floor

        # If we get a flag string, use that to determine the values of those other variables
        if flagstr is not None:
            for varname,flag in Item.serialization_flags.iteritems():
                setattr(self, varname, flag in flagstr)
        else:
            # Is this an item the player has at the start of a run? like isaac's D6 or eden's things.
            self.starting_item = starting_item
            # Was it picked up while under the effect of curse of the blind?
            self.blind = blind
            # Was this item rerolled ?
            self.was_rerolled = was_rerolled
            # Does this item belong to Jacob ?
            self.is_Jacob_item = is_Jacob_item
            # Does this item belong to Esau ?
            self.is_Esau_item = is_Esau_item

        # ItemInfo for the current item
        self.info = Item.get_item_info(item_id)

    def rerolled(self):
        """Mark the item as rerolled"""

        # Passive items that can't be rerolled such as Key pieces or Knife pieces
        if Options().game_version != "Repentance":
            exceptions = ("10", "81", "238", "239", "258", "327", "328", "474")
        else:
            exceptions = ("238", "239", "258", "327", "328", "626", "627")

        trinket = False
        if self.item_id.startswith("2") and len(self.item_id) == 4:
            trinket = True

        # Spacebar items and gulped trinkets can't be re-rolled by a D4, dice room, etc.
        if not self.info.space and self.item_id not in exceptions and not trinket:
            self.was_rerolled = True

    @property
    def name(self):
        """ Return Item's name"""
        return self.info.name

    @property
    def floor_id(self):
        """ Return Item's floor_id """
        return self.floor.floor_id

    def generate_item_description(self):
        """ Generate the item description from its stat"""
        desc = ""
        text = self.info.text
        dmg = self.info.dmg
        dmg_x = self.info.dmg_x
        delay = self.info.delay
        delay_x = self.info.delay_x
        health = self.info.health
        speed = self.info.speed
        shot_speed = self.info.shot_speed
        tear_range = self.info.range
        height = self.info.height
        tears = self.info.tears
        soul_hearts = self.info.soul_hearts
        sin_hearts = self.info.sin_hearts
        if dmg:
            desc += dmg + " dmg, "
        if dmg_x:
            desc += "x" + dmg_x + " dmg, "
        if tears:
            desc += tears + " tears, "
        if delay:
            desc += delay + " tear delay, "
        if delay_x:
            desc += "x" + delay_x + " tear delay, "
        if shot_speed:
            desc += shot_speed + " shotspeed, "
        if tear_range:
            desc += tear_range + " range, "
        if height:
            desc += height + " height, "
        if speed:
            desc += speed + " speed, "
        if health:
            desc += health + " health, "
        if soul_hearts:
            desc += soul_hearts + " soul hearts, "
        if sin_hearts:
            desc += sin_hearts + " sin hearts, "  
        if text:
            desc += text
        if desc.endswith(", "):
            desc = desc[:-2]
        if len(desc) > 0:
            desc = ": " + desc
        return desc

    def __eq__(self, other):
        if not isinstance(other, Item):
            return False
        return other is not None and self.item_id == other.item_id

    def __ne__(self, other):
        if not isinstance(other, Item):
            return True
        return other is None or self.item_id != other.item_id

    def __hash__(self):
        return hash(self.item_id)

    @staticmethod
    def get_item_info(item_id):
        """look for its informations in the loaded dictionary"""
        if item_id[0] == Item.modded_item_id_prefix:
            return ItemInfo(Item.custom_items_info[item_id[1:]])
        elif Options().game_version == "Repentance":
            return ItemInfo(Item.items_info[item_id])
        else:
            return ItemInfo(Item.abplus_items_info[item_id])

    @staticmethod
    def contains_info(item_id):
        """ Return true if we know an item with this id """
        if item_id[0] == Item.modded_item_id_prefix:
            return item_id[1:] in Item.custom_items_info
        elif Options().game_version == "Repentance":
            return item_id in Item.items_info
        else:
            return item_id in Item.abplus_items_info

    @staticmethod
    def determine_custom_item_names():
        """ For custom items that don't have a specific display name set, make the display name the same as the name id"""
        for k,v in Item.custom_items_info.iteritems():
            if "name" not in v:
                v["name"] = k

    @property
    def flags(self):
        """ Create a string containing single characters representing certain boolean member variables """
        flagstr = ""
        for varname,flag in Item.serialization_flags.iteritems():
            if getattr(self, varname):
                flagstr += flag
        return flagstr

    @staticmethod
    def from_valid_json(json_dic, *args):
        """ Create an Item from a type-checked dic and a floor_list """
        floor_list = args[0]
        floor = next((f for f in floor_list if f.floor_id == json_dic['floor_id']),
                     None)
        if not floor:
            log_error("ERROR: Floor id %s is not found in state list", json_dic['floor_id'])
            return None

        item_id = json_dic['item_id']
        if not Item.contains_info(item_id):
            item_id = "NEW"

        flagstr = json_dic['flags']

        return Item(item_id, floor, flagstr=flagstr)


class ItemInfo(dict):
    """
    dict wrapper for item infos.
    Properties and stats can be accessed using instance.my_stat, if it does not
    exist, None is returned.
    """
    transform_list = [
        "guppy",
        "bob",
        "conjoined",
        "funguy",
        "leviathan",
        "ohcrap",
        "seraphim",
        "spun",
        "yesmother",
        "superbum",
        "beelzebub",
        "bookworm",
        "spiderbaby"
    ]
    stat_list = [
        "dmg",
        "delay",
        "speed",
        "shot_speed",
        "range",
        "height",
        "tears"
    ]
    valid_key_list = [
        "delay_x",
        "dmg_x",
        "graphics_id",
        "health",
        "health_only",
        "in_summary",
        "introduced_in",
        "luck",
        "name",
        "shot_speed",
        "shown",
        "sin_hearts",
        "soul_hearts",
        "space",
        "summary_condition",
        "summary_name",
        "text",
        "comment"
    ]
    valid_key_list.extend(stat_list)
    valid_key_list.extend(transform_list)
    valid_key_set = set(valid_key_list)
    
    
    
    def __init__(self, values):
        super(ItemInfo, self).__init__(values)
        self.__dict__ = self

    def __getattr__(self, name):
        return None

    def __missing__(self, name):
        return self.__getattr__(name)

    @staticmethod
    def check_item_keys(items_dic, filename):
        """ 
        Check for unexpected keys in an item dict. if we find any, complain about them in the error log.
        This shouldn't actually stop the program though, because it just means some data won't be recognized,
        and that data is only of limited importance.
        """
        invalid_keys = set()
        for item_id in items_dic:
            for item_info_key in items_dic[item_id]:
                if item_info_key not in ItemInfo.valid_key_set:
                    invalid_keys.add(item_info_key)
        if len(invalid_keys) > 0:
            log_error("The file " + filename + " contains unexpected keys: " + ", ".join(invalid_keys))
        