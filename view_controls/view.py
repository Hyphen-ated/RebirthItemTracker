import json
import os

import pygame
import webbrowser

from collections import defaultdict

from game_objects.floor import Floor, Curse
from game_objects.item import Item, ItemProperty

class Drawable(object):
    def __init__(self, x, y, tool):
        self.x = x
        self.y = y
        self.tool = tool
        self.is_drawn = False
    
    def draw(self):
        raise NotImplementedError("This object needs to implement draw()")
    
class Clicakble(object):
    def on_click(self):
        pass

class DrawingTool:
    def __init__(self, screen):
        self.screen = screen
        self.blind_icon = None
        self.roll_icon = None
        self.font = None
        self.text_margin_size = None
        self.framecount = 0
        self.selected_item_index = None
        self.load_options()
        if self.options[Option.SHOW_DESCRIPTION] or self.options[
                Option.SHOW_CUSTOM_MESSAGE]:
                self.text_height = self.write_message(" ")
        else:
                self.text_height = 0
        self.item_message_start_time = self.framecount
        self.item_pickup_time = self.framecount
        self.drawn_items_cache = {}
        
    def write_message(self, message):
        return draw_text(
                    self.screen,
                    message,
                    self.color(self.options[Option.TEXT_COLOR]),
                    pygame.Rect(2, 2, self.options[Option.WIDTH] - 2,
                                self.options[Option.HEIGHT] - 2),
                    self.font,
                    aa=True, wrap=self.options[Option.WORD_WRAP]
                )
        
    def draw_items(self,current_floor):
        #Drawing Logic
        self.screen.fill(DrawingTool.color(self.options[Option.BACKGROUND_COLOR]))
        #clock.tick(int(self.drawing_tool.options[Option.FRAMERATE_LIMIT]))

        # 19 pixels is the default line height, but we don't know what the line height is with respect to the user's particular size_multiplier.
        # Thus, we can just draw a single space to ensure that the spacing is consistent whether text happens to be showing or not.
        if self.options[Option.SHOW_DESCRIPTION] or self.options[
            Option.SHOW_CUSTOM_MESSAGE]:
            self.text_height = self.write_message(" ")
        else:
            self.text_height = 0

        text_written = False
        #TODO: Deal with player stats here

        floor_to_draw = None
        # draw items on screen, excluding filtered items:
        for drawable_item in self.drawn_items:
            if floor_to_draw is None or \
                floor_to_draw.floor != drawable_item.item.floor:
                floor_to_draw = DrawableFloor(drawable_item.item.floor,
                                              drawable_item.x,
                                              drawable_item.y,self)
            if not floor_to_draw.is_drawn and self.options[Option.SHOW_FLOORS]:
                self.draw(floor_to_draw)
            self.draw(drawable_item)

        # also draw the floor if we hit the end, so the current floor is visible
        if self.options[Option.SHOW_FLOORS] and floor_to_draw is not None:
            if floor_to_draw.floor != current_floor:
                self.draw(DrawableFloor(current_floor,10,10,self))

        pygame.display.flip()
        self.framecount += 1
    
    def draw(self, drawable):
        if isinstance(drawable, Drawable):
            drawable.draw()
            drawable.is_drawn = True
    
    def draw_selected_box(self,x,y):
        size_multiplier = int(32 * self.options[Option.SIZE_MULTIPLIER])
        pygame.draw.rect(
            self.screen,
            DrawingTool.color(self.options[Option.TEXT_COLOR]),
            (x,
             y,
             size_multiplier,
             size_multiplier),
            2
        )
            
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
    
    def reflow(self, item_collection):
        size_multiplier = self.options[Option.SIZE_MULTIPLIER] * .5
        item_icon_size = int(self.options[Option.DEFAULT_SPACING] * size_multiplier)
        item_icon_footprint = item_icon_size
        result = self.try_layout(item_icon_footprint, item_icon_size, False, item_collection)
        while result is None:
            item_icon_footprint -= 1
            if item_icon_footprint < self.options[
                Option.MIN_SPACING] or item_icon_footprint < 4:
                result = self.try_layout(item_icon_footprint, item_icon_size,
                                         True, item_collection)
            else:
                result = self.try_layout(item_icon_footprint, item_icon_size,
                                         False, item_collection)

        self.drawn_items = result
        self.build_position_index()
        
    def try_layout(self, icon_footprint, icon_size, force_layout, collected_items):
        new_drawable_items = []
        cur_row = 0
        cur_column = 0
        cur_floor = None
        index = 0
        vert_padding = 0
        if self.options[Option.SHOW_FLOORS]:
            vert_padding = self.text_margin_size
        for item in collected_items:
            initial_x = icon_footprint * cur_column
            initial_y = self.text_height + (icon_footprint * cur_row) + (
                vert_padding * (cur_row + 1))
            #Deal with drawable items
            if self.drawn_items_cache.get(item) is not None:
                new_drawable = self.drawn_items_cache.get(item)
                new_drawable.x = initial_x
                new_drawable.y = initial_y
            else:
                new_drawable = DrawableItem(item, initial_x, initial_y, self)
                self.drawn_items_cache[item] = new_drawable
            if new_drawable.shown():
                # check to see if we are about to go off the right edge
                size_multiplier = 32 * self.options[Option.SIZE_MULTIPLIER]
                new_width = icon_footprint * cur_column + size_multiplier
                new_height = self.text_height  \
                             + (icon_footprint + vert_padding) \
                             * (cur_row + 1) + icon_size + vert_padding
                if new_width > self.options[Option.WIDTH]:
                    if (not force_layout) \
                            and new_height > self.options[Option.HEIGHT]:
                        return None
                    cur_row += 1
                    cur_column = 0
                new_drawable_items.append(new_drawable)
                cur_column += 1
        return new_drawable_items
    
    def build_position_index(self):
        w = self.options[Option.WIDTH]
        h = self.options[Option.HEIGHT]
        # 2d array of size h, w
        self.item_position_index = [[None for x in xrange(w)] for y in
                                    xrange(h)]
        num_displayed_items = 0
        size_multiplier = 32 * self.options[Option.SIZE_MULTIPLIER]
        for item in self.drawn_items:
            if item.shown():
                for y in range(int(item.y), int(item.y + size_multiplier)):
                    if y >= h:
                        continue
                    row = self.item_position_index[y]
                    for x in range(int(item.x), int(item.x + size_multiplier)):
                        if x >= w:
                            continue
                        row[x] = num_displayed_items #set the row to the index of the item
                num_displayed_items += 1        
    
    def select_item_on_hover(self,x,y):
        print "Hovering on: " + str((x,y))
        if y < len(self.item_position_index):
            selected_row = self.item_position_index[y]
            if x < len(selected_row):
                if self.selected_item_index is not None:
                    self.drawn_items[self.selected_item_index].selected=False
                self.selected_item_index = selected_row[x]
                print "Item is = " + str(self.selected_item_index)

                if self.selected_item_index is not None:
                    print " ID: " + str(self.drawn_items[self.selected_item_index].item.id)
                    self.item_message_start_time = self.framecount
                    self.drawn_items[self.selected_item_index].selected=True
                    
    def adjust_select_item_on_keypress(self,adjust_by):
        if self.selected_item_index is None:
            return
        self.drawn_items[self.selected_item_index].selected=False
        self.selected_item_index += adjust_by
        self.selected_item_index = max(0,min(self.selected_item_index,len(self.drawn_items)-1))
        self.drawn_items[self.selected_item_index].selected=True
        
    def load_selected_detail_page(self):
        if self.selected_item_index is None:
            return
        self.drawn_items[self.selected_item_index].load_detail_page()
        
    def get_scaled_icon(self, path, scale):
        return pygame.transform.scale(self.get_image(path), (scale, scale))
    
    def get_image(self, path):
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
    
    def get_message_duration(self):
        return (self.options[Option.MESSAGE_DURATION] * 
                self.options[Option.FRAMERATE_LIMIT])
    
    def save_options(self):
        with open("options.json", "w") as json_file:
            json.dump(self.options, json_file, indent=3, sort_keys=True)
    
    def item_message_countdown_in_progress(self):
        return self.item_message_start_time + self.get_message_duration() > self.framecount

    def item_pickup_countdown_in_progress(self):
        return self.item_pickup_time + self.get_message_duration() > self.framecount
    
    def item_picked_up(self):
        self.item_message_start_time = self.framecount
        self.item_pickup_time = self.framecount
    
    @staticmethod
    def color(string):
        return pygame.color.Color(str(string))
    @staticmethod
    def id_to_image(id):
        return 'collectibles/collectibles_%s.png' % id.zfill(3)

class DrawableItem(Drawable):
    def __init__(self, item, x, y, tool):
        super(DrawableItem, self).__init__(x, y, tool)
        self.item = item
        self.is_drawn = False
        self.selected = False
    
    def show_blind_icon(self):
        return self.tool.options[Option.SHOW_BLIND_ICON] and \
            self.item.floor.floor_has_curse(Curse.Blind)
    
    def shown(self):
        """
            We should show if the following is true: 
                1. We are showable
                2. We are guppy
                3. We are health pickup AND we want to see health pickups
                4. We are rerolled AND we want to see rerolls
                5. We are a spacebar AND we want to see spacebars
        """
        if not self.item.info.get(ItemProperty.SHOWN,False):
            return False
        elif self.item.info.get(ItemProperty.GUPPY,False):
            return True
        elif self.item.info.get(ItemProperty.HEALTH_ONLY,False) and \
            not self.tool.option[Option.SHOW_HEALTH_UPS]:
            return False
        elif self.item.info.get(ItemProperty.SPACE,False) and \
             not self.tool.option[Option.SHOW_SPACE_ITEMS]:
            return False
        elif self.item.was_rerolled and \
              not self.tool.option[Option.SHOW_REROLLED_ITEMS]:
            return False
        return True
                    
    def draw(self):
        image = self.tool.get_image(DrawingTool.id_to_image(self.item.id))
        self.tool.screen.blit(image, (self.x, self.y))
        if self.item.was_rerolled:
            self.tool.screen.blit(self.tool.roll_icon, (self.x, self.y))
        if self.show_blind_icon():
            self.tool.screen.blit(self.tool.blind_icon,
                        (self.x, self.y + self.tool.options[Option.SIZE_MULTIPLIER] * 12))
        if self.selected:
            self.tool.draw_selected_box(self.x,self.y)
    
    def load_detail_page(self):
        url = self.tool.options[Option.ITEM_DETAILS_LINK]
        if not url:
            return
        url = url.replace("$ID", self.item.id)
        webbrowser.open(url, autoraise=True)
            
class DrawableFloor(Drawable):
    def __init__(self, floor, x, y, tool):
        super(DrawableFloor, self).__init__(x, y, tool)
        self.floor = floor
        self.is_drawn = False
        
    def draw(self):
        text_color = DrawingTool.color(self.tool.options[Option.TEXT_COLOR])
        size_multiplier = self.tool.options[Option.SIZE_MULTIPLIER]
        pygame.draw.lines(
            self.tool.screen,
            text_color,
            False,
            ((self.x + 2, int(self.y + 24 * size_multiplier)),
             (self.x + 2, self.y),
             (int(self.x + 16 * size_multiplier), self.y))
        )
        image = self.tool.font.render(self.floor.name(), True, text_color)
        self.tool.screen.blit(image, (self.x + 4, self.y - self.tool.text_margin_size))
        
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
    
# taken from pygame_helpers.py    
def draw_text(surface, text, color, rect, font, aa=False, bkg=None, wrap=False):
    rect = pygame.Rect(rect)
    y = rect.top
    lineSpacing = -2

    # get the height of the font
    fontHeight = font.size("Tg")[1]

    if wrap is False:
        rect = pygame.Rect(rect.left, rect.top, rect.width, fontHeight)

    while text:
        i = 1

        # determine if the row of text will be outside our area
        if y + fontHeight > rect.bottom:
            break

        # determine maximum width of line
        while font.size(text[:i])[0] < rect.width and i < len(text):
            i += 1

        # if we've wrapped the text, then adjust the wrap to the last word
        if i < len(text):
            i = text.rfind(" ", 0, i) + 1

        # render the line and blit it to the surface
        if bkg:
            image = font.render(text[:i], 1, color, bkg)
            image.set_colorkey(bkg)
        else:
            image = font.render(text[:i], aa, color)

        surface.blit(image, (rect.left, y))
        y += fontHeight + lineSpacing

        # remove the text we just blitted
        text = text[i:]

    return y
