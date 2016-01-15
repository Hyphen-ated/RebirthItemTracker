""" This module handles everything that is floor-related"""

class Curse(object):
    """Curse enumaration"""
    No_Curse, Blind, Darkness, Lost, Maze, Unknown, Labyrinth, Cursed = range(8)

class Floor(object):
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

    def __init__(self, floor_id, is_alternate, curse=Curse.No_Curse):
        self.floor_id = floor_id
        self.curse = curse
        self.is_alt_floor = is_alternate

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

    def name(self):
        """Return the floor name"""
        return Floor.__floor_id_to_label[self.floor_id]

    def __eq__(self, other):
        if not isinstance(other, Floor):
            return False
        return other is not None and self.floor_id == other.floor_id

    def __ne__(self, other):
        if not isinstance(other, Floor):
            return True
        return other is None or self.floor_id != other.floor_id
