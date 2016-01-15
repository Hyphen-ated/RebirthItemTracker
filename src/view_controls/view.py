# Imports
import json
import os
import platform # For determining what operating system the script is being run on
import pygame   # This is the main graphics library used for the item tracker
import webbrowser
import string
from collections import defaultdict
from options import Options
from game_objects.floor import Curse
from game_objects.item import ItemProperty, Stat
from view_controls.overlay import Overlay
from pygame.locals import RESIZABLE
# FIXME I don't know what to do with that, I don't use the release script
#import pygame._view # Uncomment this if you are trying to run release.py and you get: "ImportError: No module named _view"

# Additional pygame imports
if platform.system() == "Windows":
    import pygameWindowInfo
from pygame.locals import *

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

class DrawingTool(object):
    def __init__(self, title):
        # FIXME this is the second time I see this, make this global/static
        self.file_prefix = "../"
        self.next_item = (0, 0)
        self.item_position_index = []
        self.drawn_items = []
        self._image_library = {}
        self.blind_icon = None
        self.roll_icon = None
        self.font = None
        self.text_margin_size = None
        self.framecount = 0
        self.selected_item_index = None
        self.item_message_start_time = self.framecount
        self.item_pickup_time = self.framecount
        # Reference to IsaacTracker's state
        self.state = None
        self.clock = None
        self.win_info = None
        self.screen = None
        self.start_pygame(title)

    def start_pygame(self, title):
        # Initialize pygame system stuff
        pygame.init()
        self.reset_options()
        pygame.display.set_caption(title)
        pygame.display.set_icon(self.get_image("collectibles_333.png"))
        self.clock = pygame.time.Clock()


        opt = Options()
        # figure out where we should put our window.
        xpos = opt.x_position
        ypos = opt.y_position
        # it can go negative when weird problems happen, so put it in a default location in that case
        if xpos < 0:
            xpos = 100
        if ypos < 0:
            ypos = 100

        os.environ['SDL_VIDEO_WINDOW_POS'] = "%d, %d" % (xpos, ypos)

        if self.screen is None: # If screen is none, we make our own
            self.screen = pygame.display.set_mode((opt.width, opt.height), RESIZABLE)
        if opt.show_description or opt.show_custom_message:
            self.text_height = self.write_message(" ")
        else:
            self.text_height = 0

        if platform.system() == "Windows":
            self.win_info = pygameWindowInfo.PygameWindowInfo()
        del os.environ['SDL_VIDEO_WINDOW_POS']

        self.screen.fill(DrawingTool.color(opt.background_color))

    def tick(self):
        # Drawing logic
        self.clock.tick(int(Options().framerate_limit))


    def handle_events(self):
        opt = Options()
        # pygame logic
        for event in pygame.event.get():
            if event.type == QUIT:
                if platform.system() == "Windows":
                    win_pos = self.win_info.getScreenPosition()
                    opt.x_position = win_pos["left"]
                    opt.y_position = win_pos["top"]
                return True
            elif event.type == VIDEORESIZE:
                self.screen = pygame.display.set_mode(event.dict['size'], RESIZABLE)
                opt.width = event.dict["w"]
                opt.height = event.dict["h"]
                self.reflow()
                pygame.display.flip()
            elif event.type == MOUSEMOTION:
                if pygame.mouse.get_focused():
                    pos = pygame.mouse.get_pos()
                    self.select_item_on_hover(*pos)
            elif event.type == KEYDOWN:
                if len(self.state.item_list) > 0:
                    if event.key == K_RIGHT:
                        self.adjust_select_item_on_keypress(1)
                    elif event.key == K_LEFT:
                        self.adjust_select_item_on_keypress(-1)
                    elif event.key == K_RETURN:
                        self.load_selected_detail_page()
                    elif event.key == K_c and pygame.key.get_mods() & KMOD_CTRL:
                        pass
                    #self.generate_run_summary() # This is commented out because run summaries are broken with the new "state" model rewrite of the item tracker
            elif event.type == MOUSEBUTTONDOWN:
                if event.button == 1:
                    self.load_selected_detail_page()
                if event.button == 3:
                    import option_picker
                    pygame.event.set_blocked([QUIT, MOUSEBUTTONDOWN, KEYDOWN, MOUSEMOTION])
                    option_picker.OptionsMenu().run()
                    pygame.event.set_allowed([QUIT, MOUSEBUTTONDOWN, KEYDOWN, MOUSEMOTION])
                    self.reset()
                    self.reset_options()
                    self.reflow()
        return False


    def draw_items(self):
        '''
        Draws all the items in current_tracker
        :param current_tracker:
        '''
        current_floor = self.state.last_floor
        opt = Options()
        # Clear the screen
        self.screen.fill(DrawingTool.color(opt.background_color))

        # 19 pixels is the default line height, but we don't know what the
        # line height is with respect to the user's particular size_multiplier.
        # Thus, we can just draw a single space to ensure that the spacing is consistent
        # whether text happens to be showing or not.
        if opt.show_description or opt.show_custom_message:
            self.text_height = self.write_message(" ")
        else:
            self.text_height = 0

        # Draw item pickup text, if applicable
        text_written = False
        if opt.show_description and self.item_message_countdown_in_progress():
            text_written = self.write_item_text()
        if not text_written and opt.show_custom_message:
            # Draw seed/guppy text:
            seed = self.state.seed

            dic = defaultdict(str, seed=seed)
            # Update this dic with player stats

            for stat in Stat.LIST:
                dic[stat] = Overlay.format_value(self.state.player_stats[stat])
            dic[Stat.IS_GUPPY] = Overlay.format_guppy(self.state.guppy_set)

            # Use vformat to handle the case where the user adds an
            # undefined placeholder in default_message
            message = string.Formatter().vformat(
                opt.custom_message,
                (),
                dic
            )
            self.text_height = self.write_message(message)

        floor_to_draw = None

        # Draw items on screen, excluding filtered items:
        for drawable_item in self.drawn_items:
            if floor_to_draw is None or floor_to_draw.floor != drawable_item.item.floor:
                floor_to_draw = DrawableFloor(
                    drawable_item.item.floor,
                    drawable_item.x,
                    drawable_item.y,
                    self
                )
            if not floor_to_draw.is_drawn and opt.show_floors:
                self.draw(floor_to_draw)
            self.draw(drawable_item)

        # Also draw the floor if we hit the end, so the current floor is visible
        # FIXME investigate the current_floor is not None stuff, as we should always have a b/b1
        if opt.show_floors and floor_to_draw is not None:
            if floor_to_draw.floor != current_floor and current_floor is not None:
                x, y = self.next_item
                self.draw(DrawableFloor(current_floor, x, y, self))

        pygame.display.flip()
        self.framecount += 1

    def draw(self, drawable):
        if isinstance(drawable, Drawable):
            drawable.draw()
            drawable.is_drawn = True


    def reflow(self):
        '''
        Changes the position of the items so they all fit on the screen
        :param item_collection: Collection of items to display
        '''
        opt = Options()
        item_collection = self.state.item_list
        size_multiplier = opt.size_multiplier * .5
        item_icon_size = int(opt.default_spacing * size_multiplier)
        item_icon_footprint = item_icon_size
        result = self.try_layout(item_icon_footprint, item_icon_size, False)
        while result is None:
            item_icon_footprint -= 1
            if (item_icon_footprint < opt.min_spacing or
                    item_icon_footprint < 4):
                result = self.try_layout(item_icon_footprint, item_icon_size,
                                         True)
            else:
                result = self.try_layout(item_icon_footprint, item_icon_size,
                                         False)

        self.drawn_items = result
        self.build_position_index()

    def try_layout(self, icon_footprint, icon_size, force_layout):
        new_drawable_items = []
        cur_row = 0
        cur_column = 0
        vert_padding = 0
        opt = Options()
        if opt.show_floors:
            vert_padding = self.text_margin_size
        collected_items = self.state.item_list
        for item in collected_items:
            initial_x = icon_footprint * cur_column
            initial_y = self.text_height + (icon_footprint * cur_row) + (
                vert_padding * (cur_row + 1))

            # Deal with drawable items
            new_drawable = DrawableItem(item, initial_x, initial_y, self)

            # Only bother adding anything if we're going to show it
            if new_drawable.shown():
                # Check to see if we are about to go off the right edge
                cur_column += 1
                size_multiplier = 32 * opt.size_multiplier
                new_width = icon_footprint * cur_column + size_multiplier
                new_height = (self.text_height + (icon_footprint + vert_padding) * (cur_row + 1)
                              + icon_size + vert_padding)
                if new_width > opt.width:
                    if (not force_layout) and new_height > opt.height:
                        return None
                    cur_row += 1
                    cur_column = 0
                new_drawable_items.append(new_drawable)

        # Finally, we set next_item so that if we have an empty floor,
        # we can use those coordinates to place it
        initial_x = icon_footprint * cur_column
        initial_y = self.text_height + (icon_footprint * cur_row) + (vert_padding * (cur_row + 1))
        self.next_item = (initial_x, initial_y)
        return new_drawable_items

    def build_position_index(self):
        '''
        Builds an array covering the entire visible screen and fills it
        with references to the index items where appropriate so we can show
        select boxes on hover
        '''
        opt = Options()
        w = opt.width
        h = opt.height
        # 2d array of size h, w
        self.item_position_index = [[None for x in xrange(w)] for y in xrange(h)]
        num_displayed_items = 0
        size_multiplier = 32 * opt.size_multiplier
        for item in self.drawn_items:
            if item.shown():
                for y in range(int(item.y), int(item.y + size_multiplier)):
                    if y >= h:
                        continue
                    row = self.item_position_index[y]
                    for x in range(int(item.x), int(item.x + size_multiplier)):
                        if x >= w:
                            continue
                        row[x] = num_displayed_items  # Set the row to the index of the item
                num_displayed_items += 1

    def select_item_on_hover(self, x, y):
        if y < len(self.item_position_index):
            selected_row = self.item_position_index[y]
            if x < len(selected_row):
                if self.selected_item_index is not None:
                    self.drawn_items[self.selected_item_index].selected = False
                self.selected_item_index = selected_row[x]
                if self.selected_item_index is not None:
                    self.item_message_start_time = self.framecount
                    self.drawn_items[self.selected_item_index].selected = True

    def adjust_select_item_on_keypress(self, adjust_by):
        # TODO: Rename this method to something better
        if self.selected_item_index is None:
            return
        self.drawn_items[self.selected_item_index].selected = False
        self.selected_item_index += adjust_by
        self.selected_item_index = max(0, min(self.selected_item_index, len(self.drawn_items) - 1))
        self.drawn_items[self.selected_item_index].selected = True

    def load_selected_detail_page(self):
        if self.selected_item_index is None:
            return
        self.drawn_items[self.selected_item_index].load_detail_page()

    def get_scaled_icon(self, path, scale):
        return pygame.transform.scale(self.get_image(path), (scale, scale))

    def get_image(self, imagename):
        image = self._image_library.get(imagename)
        if image is None:
            path = self.file_prefix + "/collectibles/" + imagename
            canonicalized_path = path.replace('/', os.sep).replace('\\', os.sep)
            image = pygame.image.load(canonicalized_path)
            size_multiplier = Options().size_multiplier
            scaled_image = pygame.transform.scale(image, (
                int(image.get_size()[0] * size_multiplier),
                int(image.get_size()[1] * size_multiplier)))
            self._image_library[imagename] = scaled_image
        return image

    def get_message_duration(self):
        return Options().message_duration * Options().framerate_limit

    def item_message_countdown_in_progress(self):
        return self.item_message_start_time + self.get_message_duration() > self.framecount

    def item_pickup_countdown_in_progress(self):
        return self.item_pickup_time + self.get_message_duration() > self.framecount

    def item_picked_up(self):
        self.item_message_start_time = self.framecount
        self.item_pickup_time = self.framecount

    def write_item_text(self):
        if len(self.drawn_items) <= 0:
            # No items, nothing to show
            return False
        item_index_to_display = self.selected_item_index
        if item_index_to_display is None and self.item_pickup_countdown_in_progress():
            # We want to be showing an item but they haven't selected one,
            # that means show the newest item
            item_index_to_display = len(self.drawn_items) - 1
        if item_index_to_display is None:
            return False
        item = self.drawn_items[item_index_to_display].item
        desc = item.generate_item_description()
        self.text_height = self.write_message("%s%s" % (item.name, desc))
        return True

    def write_message(self, message, flip=False):
        opt = Options()
        height = draw_text(
            self.screen,
            message,
            self.color(opt.text_color),
            pygame.Rect(2, 2, opt.width - 2, opt.height - 2),
            self.font,
            aa=True,
            wrap=opt.word_wrap
        )
        if flip:
            pygame.display.flip()
        return height

    def draw_selected_box(self, x, y):
        size_multiplier = int(32 * Options().size_multiplier)
        pygame.draw.rect(
            self.screen,
            DrawingTool.color(Options().text_color),
            (x, y, size_multiplier, size_multiplier),
            2
        )

    @staticmethod
    def color(stringcolor):
        return Color(str(stringcolor))

    @staticmethod
    def id_to_image(id):
        return 'collectibles_%s.png' % id.zfill(3)

    def reset_options(self):
        """ Reset state variables affected by options """
        opt = Options()
        size_multiplier = int(8 * opt.size_multiplier)

        # Anything that gets calculated and cached based on something in options
        # now needs to be flushed
        self.text_margin_size = size_multiplier
        self.font = pygame.font.SysFont(
            opt.show_font,
            size_multiplier,
            bold=opt.bold_font
        )
        self._image_library = {}
        self.roll_icon = self.get_scaled_icon(self.id_to_image("284"), size_multiplier * 2)
        self.blind_icon = self.get_scaled_icon("questionmark.png", size_multiplier * 2)

    def reset(self):
        self.selected_item_index = None
        self.drawn_items = []

class DrawableItem(Drawable):
    def __init__(self, item, x, y, tool):
        super(DrawableItem, self).__init__(x, y, tool)
        self.item = item
        self.is_drawn = False
        self.selected = False

    def show_blind_icon(self):
        """
            We only show the curse of the blind icon if we're showing blind
            icons, the floor it was found on was a blind floor AND
            it's not one of our starting items
        """
        return Options().show_blind_icon and \
            self.item.floor.floor_has_curse(Curse.Blind) and \
            not self.item.starting_item

    def shown(self):
        """
            We should show if the following is true:
                1. We are showable
                2. We are guppy
                3. We are health pickup AND we want to see health pickups
                4. We are rerolled AND we want to see rerolls
                5. We are a spacebar AND we want to see spacebars
        """
        opt = Options()
        if not self.item.info.get(ItemProperty.SHOWN, False):
            return False
        elif self.item.info.get(ItemProperty.GUPPY, False):
            return True
        elif self.item.info.get(ItemProperty.HEALTH_ONLY, False) and \
                not opt.show_health_ups:
            return False
        elif self.item.info.get(ItemProperty.SPACE, False) and \
                not opt.show_space_items:
            return False
        elif self.item.was_rerolled and \
                not opt.show_rerolled_items:
            return False
        return True

    def draw(self):
        image = self.tool.get_image(DrawingTool.id_to_image(self.item.item_id))
        self.tool.screen.blit(image, (self.x, self.y))
        # If we're a re-rolled item, draw a little d4 near us
        if self.item.was_rerolled:
            self.tool.screen.blit(self.tool.roll_icon, (self.x, self.y))
        # If we're showing blind icons, draw a little blind icon
        if self.show_blind_icon():
            self.tool.screen.blit(
                self.tool.blind_icon,
                (self.x, self.y + Options().size_multiplier * 12)
            )
        # If we're selected, draw a box to highlight us
        if self.selected:
            self.tool.draw_selected_box(self.x, self.y)

    def load_detail_page(self):
        url = Options().item_details_link
        if not url:
            return
        url = url.replace("$ID", self.item.item_id)
        webbrowser.open(url, autoraise=True)

class DrawableFloor(Drawable):
    def __init__(self, floor, x, y, tool):
        super(DrawableFloor, self).__init__(x, y, tool)
        self.floor = floor
        self.is_drawn = False

    def draw(self):
        text_color = DrawingTool.color(Options().text_color)
        size_multiplier = Options().size_multiplier
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


# Taken from pygame_helpers.py
def draw_text(surface, text, color, rect, font, aa=False, bkg=None, wrap=False):
    rect = pygame.Rect(rect)
    y = rect.top
    lineSpacing = -2

    # Get the height of the font
    fontHeight = font.size("Tg")[1]

    if wrap is False:
        rect = pygame.Rect(rect.left, rect.top, rect.width, fontHeight)

    while text:
        i = 1

        # Determine if the row of text will be outside our area
        if y + fontHeight > rect.bottom:
            break

        # Determine maximum width of line
        while font.size(text[:i])[0] < rect.width and i < len(text):
            i += 1

        # If we've wrapped the text, then adjust the wrap to the last word
        if i < len(text):
            i = text.rfind(" ", 0, i) + 1

        # Render the line and blit it to the surface
        if bkg:
            image = font.render(text[:i], 1, color, bkg)
            image.set_colorkey(bkg)
        else:
            image = font.render(text[:i], aa, color)

        surface.blit(image, (rect.left, y))
        y += fontHeight + lineSpacing

        # Remove the text we just blitted
        text = text[i:]

    return y
