""" This module handles everything that is floor-related"""
from game_objects.serializable import Serializable
import logging

class Curse(object):
    """Curse enumaration"""
    No_Curse, Blind, Darkness, Lost, Maze, Unknown, Labyrinth, Cursed = range(8)

class Floor(Serializable):
    """ This class represent a floor and handles everything related to its properties"""
    __floor_id_to_label = {
        "f1":  "B1",
        "f2":  "B2",
        "f3":  "C1",
        "f4":  "C2",
        "f5":  "D1",
        "f6":  "D2",
        "f7":  "W1",
        "f8":  "W2",
        "f9":  "SHEOL",
        "f10": "CATH",
        "f11": "DARK",
        "f12": "CHEST",
        "f1x": "BXL",
        "f3x": "CXL",
        "f5x": "DXL",
        "f7x": "WXL",
        "f1g": "B",
        "f2g": "C",
        "f3g": "D",
        "f4g": "W",
        "f5g": "SHEOL",
        "f6g": "SHOP",
        "f7g": "GREED",
        }
    serialize = [('floor_id', basestring), ('curse', int)]
    def __init__(self, floor_id, curse=Curse.No_Curse):
        self.floor_id = floor_id
        self.curse = curse

    def add_curse(self, curse):
        """Add a curse to this floor"""
        if curse is None:
            curse = Curse.No_Curse # None is the same as no curse
        self.curse = curse
        if self.curse == Curse.Labyrinth:
            self.floor_id += 'x' # If we are Curse of the Labyrinth, then we are XL

    def floor_has_curse(self, curse):
        """Return true if the floor has the curse"""
        return curse == self.curse

    def name(self, xl_disabled=False):
        """Return the floor name"""
        id = self.floor_id
        if xl_disabled and id.endswith('x'):
            id = id[:-1]
        return Floor.__floor_id_to_label[id]

    def __eq__(self, other):
        if not isinstance(other, Floor):
            return False
        return other is not None and self.floor_id == other.floor_id

    def __ne__(self, other):
        if not isinstance(other, Floor):
            return True
        return other is None or self.floor_id != other.floor_id

    @staticmethod
    def from_valid_json(json_dic, *args):
        """ Create a Floor from a type-checked dic """
        floor_id = json_dic['floor_id']
        curse = json_dic['curse']
        if (floor_id not in Floor.__floor_id_to_label or
                curse < Curse.No_Curse or
                curse > Curse.Labyrinth):
            logging.getLogger("tracker").error("ERROR: Invalid foor_id or curse")
            return None
        return Floor(floor_id, curse)
