from view import Drawable, Option, DrawingTool
import pygame

class Curse:
    No_Curse, Blind, Darkness, Lost, Maze, Unknown, Labyrinth, Cursed = range(8)

class Floor(Drawable):
    '''
    Stolen from item_tracker - used as an easy way to convert floors into
    shortened names
    '''
    __floor_id_to_label = {
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
    
    def __init__(self, id, tracker, curse=Curse.No_Curse):
        self.id = id
        self.curse = curse
        self.items = []
        self.tracker = tracker
    
    def addCurse(self, curse):
        raise NotImplementedError("This is unimplemented due to only one curse per floor.")
    
    def addItem(self, item):
        self.items.append(item)
    
    def draw(self, x, y, screen, options):
        text_color = options[Option.TEXT_COLOR]
        size_multiplier = options[Option.SIZE_MULTIPLIER]
        font = options[Option.SHOW_FONT]
        pygame.draw.lines(
            screen,
            self.color(text_color),
            False,
            ((x + 2, int(y + 24 * size_multiplier)),
             (x + 2, y),
             (int(x + 16 * size_multiplier), y))
        )
        image = font.render(self.name(), True, DrawingTool.color(text_color))
        screen.blit(image, (x + 4, y - self.text_margin_size))
    
    def name(self):
        return Floor.__floor_id_to_label[self.id]
    
