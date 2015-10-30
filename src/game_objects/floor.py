# Imports
import pygame

class Curse:
    No_Curse, Blind, Darkness, Lost, Maze, Unknown, Labyrinth, Cursed = range(8)

class Floor(object):
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
        }

    def __init__(self, id, tracker, is_alternate, curse=Curse.No_Curse):
        self.id           = id
        self.curse        = curse
        self.items        = []
        self.tracker      = tracker
        self.is_alt_floor = is_alternate
    
    def add_curse(self, curse):
        if curse is None:
            curse = Curse.No_Curse # None is the same as no curse
        self.curse = curse
        if self.curse == Curse.Labyrinth:
            self.id += 'x' # If we are Curse of the Labyrinth, then we are XL

    def add_item(self, item):
        self.items.append(item)

    def floor_has_curse(self, curse):
        return curse == self.curse

    def name(self):
        return Floor.__floor_id_to_label[self.id]

    def __eq__(self,other):
        if not isinstance(other, Floor):
            return False
        return other is not None and self.id == other.id

    def __ne__(self,other):
        if not isinstance(other, Floor):
            return True
        return other is None or self.id != other.id
