import json
import os

import pygame


class Drawable:
    def draw(self, x, y, screen):
        raise NotImplementedError("This object needs drawing implemented")

class DrawingTool:
    def __init__(self, screen):
        self.screen = screen
        self.load_options()
    
    def draw(self, drawable, x, y):
        if issubclass(drawable, Drawable):
            drawable.draw(x, y, self.screen, self.options)
            
    def load_options(self):
        with open("options.json", "r") as json_file:
            self.options = json.load(json_file)

        size_multiplier = int(8 * self.options[Option.SIZE_MULTIPLIER])

        # anything that gets calculated and cached based on something in options now needs to be flushed
        self.text_margin_size = size_multiplier
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
    def get_image(self,path):
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
    
    @staticmethod
    def color(string):
        return pygame.color.Color(str(string))
    @staticmethod
    def roll_icon():
        pass
    @staticmethod
    def id_to_image(id):
        return 'collectibles/collectibles_%s.png' % id.zfill(3)

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
