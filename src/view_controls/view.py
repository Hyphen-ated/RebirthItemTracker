""" This module handles everything related to the tracker's window """
import json
import logging
import os
import platform # For determining what operating system the script is being run on
import pygame   # This is the main graphics library used for the item tracker
import webbrowser
import string
from Tkinter import Tk # For clipboard functionality
from collections import defaultdict
from options import Options
from game_objects.floor import Curse
from game_objects.item import ItemInfo
from view_controls.overlay import Overlay
from pygame.locals import RESIZABLE
from game_objects.state import TrackerState, TrackerStateEncoder
from math import floor
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

    def draw(self, selected=False):
        raise NotImplementedError("This object needs to implement draw()")

class Clicakble(object):
    def on_click(self):
        pass

class Event(object):
    DONE = 1
    OPTIONS_UPDATE = 2

class DrawingTool(object):
    def __init__(self, prefix):
        self.file_prefix = prefix
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
        # Reference to the previous state drawn
        self.state = None
        self.clock = None
        self.win_info = None
        self.screen = None
        self.window_title_info = WindowTitleInfo()
        self.start_pygame()

    def start_pygame(self):
        """ Initialize pygame system stuff and draw empty window """
        pygame.init()
        pygame.display.set_icon(self.get_image("collectibles_333.png", disable_glow=True))
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
        self.reset_options()

        if platform.system() == "Windows":
            self.win_info = pygameWindowInfo.PygameWindowInfo()
        del os.environ['SDL_VIDEO_WINDOW_POS']

        self.screen.fill(DrawingTool.color(opt.background_color))

    def tick(self):
        """ Tick the clock. """
        self.clock.tick(int(Options().framerate_limit))

    def save_window_position(self):
        if platform.system() == "Windows":
            win_pos = self.win_info.getScreenPosition()
            Options().x_position = win_pos["left"]
            Options().y_position = win_pos["top"]

    def handle_events(self):
        """ Handle any pygame event """
        opt = Options()
        # pygame logic
        for event in pygame.event.get():
            if event.type == QUIT:
                return Event.DONE

            elif event.type == VIDEORESIZE:
                self.screen = pygame.display.set_mode(event.dict['size'], RESIZABLE)
                opt.width = event.dict["w"]
                opt.height = event.dict["h"]
                self.__reflow()
                pygame.display.flip()

            elif event.type == MOUSEMOTION:
                if pygame.mouse.get_focused():
                    pos = pygame.mouse.get_pos()
                    self.select_item_on_hover(*pos)

            elif event.type == KEYDOWN:
                if event.key == K_UP and pygame.key.get_mods() & KMOD_CTRL and opt.read_from_server:
                    opt.read_delay += 1
                    self.update_window_title()
                elif event.key == K_DOWN and pygame.key.get_mods() & KMOD_CTRL and opt.read_from_server:
                    opt.read_delay = max(0, opt.read_delay - 1)
                    self.update_window_title()
                elif event.key == K_RETURN:
                    self.load_selected_detail_page()
                elif event.key == K_F4 and pygame.key.get_mods() & KMOD_ALT:
                    return Event.DONE
                elif event.key == K_c and pygame.key.get_mods() & KMOD_CTRL:
                    # Debug function to write the state to a json file
                    #with open("../export_state.json", "w") as state_file:
                    #    state_file.write(json.dumps(self.state, cls=TrackerStateEncoder, sort_keys=True))

                    # Write the seed to the clipboard
                    # (from http://stackoverflow.com/questions/579687/how-do-i-copy-a-string-to-the-clipboard-on-windows-using-python)
                    r = Tk()
                    r.withdraw()
                    r.clipboard_clear()
                    r.clipboard_append(self.state.seed)
                    r.destroy()

                #self.generate_run_summary() # This is commented out because run summaries are broken with the new "state" model rewrite of the item tracker

            elif event.type == MOUSEBUTTONDOWN:
                if event.button == 1:
                    self.load_selected_detail_page()
                if event.button == 3:
                    self.save_window_position()
                    import option_picker
                    self.screen.fill(DrawingTool.color(opt.background_color))
                    self.write_message("Editing options...", flip=True)
                    pygame.event.set_blocked([QUIT, MOUSEBUTTONDOWN, KEYDOWN, MOUSEMOTION])
                    option_picker.OptionsMenu().run()
                    pygame.event.set_allowed([QUIT, MOUSEBUTTONDOWN, KEYDOWN, MOUSEMOTION])
                    self.reset_options()
                    self.reset()
                    if self.state is not None:
                        self.__reflow()
                    return Event.OPTIONS_UPDATE

        return None

    def draw_state(self, state):
        """
        Draws the state
        :param state:
        """
        if self.state != state:
            self.reset()
            self.state = state

        opt = Options()
        # Clear the screen
        self.screen.fill(DrawingTool.color(opt.background_color))

        # If state is None we just want to clear the screen
        if self.state is None:
            return

        # If items were added, or removed (run restarted) regenerate items
        if self.state.modified:
            # We picked up an item, start the counter
            self.item_picked_up()
            overlay = Overlay(self.file_prefix, self.state)
            overlay.update_seed()
            if len(self.drawn_items) > 0:
                overlay.update_stats()
                overlay.update_last_item_description()
        current_floor = self.state.last_floor


        # Draw item pickup text, if applicable
        # Save the previous text_height to know if we need to reflow the items
        text_height_before = self.text_height
        text_written = False
        if opt.show_description and self.item_message_countdown_in_progress():
            text_written = self.write_item_text()
        if not text_written and opt.show_status_message:
            # Draw seed/guppy text:
            seed = self.state.seed

            dic = defaultdict(str, seed=seed)
            # Update this dic with player stats

            for stat in ItemInfo.stat_list:
                dic[stat] = Overlay.format_value(self.state.player_stats[stat])
            for transform in ItemInfo.transform_list:
                dic[transform] = Overlay.format_transform(self.state.player_transforms[transform])

            # Use vformat to handle the case where the user adds an
            # undefined placeholder in default_message
            message = string.Formatter().vformat(
                opt.status_message,
                (),
                dic
            )
            self.text_height = self.write_message(message)
        elif not text_written:
            self.text_height = 0

        # We want to reflow if the state has been modified or if the text
        # height has changed
        if self.state.modified or self.text_height != text_height_before:
            self.__reflow()

        floor_to_draw = None

        idx = 0
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
                floor_to_draw.draw()
            drawable_item.draw(selected=(idx == self.selected_item_index))

            idx += 1

        # Also draw the floor if we hit the end or if the list is empty,
        # so the current floor is visible
        if opt.show_floors and current_floor is not None:
            if floor_to_draw is None or (floor_to_draw is not None and
                                         floor_to_draw.floor != current_floor):
                x, y = self.next_item
                DrawableFloor(current_floor, x, y, self).draw()

        self.state.drawn()
        pygame.display.flip()
        self.framecount += 1

    def __reflow(self):
        '''
        Regenerate the displayed item list
        '''
        opt = Options()
        size_multiplier = opt.size_multiplier

        # Empty the previous drawn items list
        self.drawn_items[:] = []
        # Build the list of items to display
        items_to_flow = [x for x in self.state.item_list if self.show_item(x)] if self.state is not None else []
        n_items_to_flow = len(items_to_flow)

        if n_items_to_flow == 0:
            self.next_item = (0, self.text_height + self.text_margin_size)
            return

        # Check for trailing floor and consider we'll have to draw it
        if items_to_flow[-1].floor != self.state.last_floor:
            n_items_to_flow += 1

        # Compute the icon size according to user's multiplier, as well as
        # the minimum size that we want to display (the "footprint")
        icon_size = int(opt.default_spacing * size_multiplier)
        min_icon_footprint = int(opt.min_spacing * size_multiplier)

        # Declare these variables here so that we can reuse it after the loop
        max_col = 0
        available_width = 0

        # Find the biggest possible footprint while displaying every items,
        chosen_icon_footprint = icon_size
        while chosen_icon_footprint >= min_icon_footprint:
            # Compute the maximum number of columns, taking into account the
            # last item's width
            available_width = opt.width - (icon_size - chosen_icon_footprint)
            if opt.enable_mouseover:
                # Boxes have a line width of 2px, so we need to substract them
                available_width -= 2
            max_col = floor(available_width/chosen_icon_footprint)
            row_height = chosen_icon_footprint
            if opt.show_floors:
                row_height += self.text_margin_size
            # height also has to take into account the size of the items on the edges, so they never flow off the bottom
            available_height = opt.height - self.text_height - (icon_size - chosen_icon_footprint)
            max_row = floor(available_height/row_height)
            # We have our maximum number of columns and rows visible, we can
            # check if everything will fit, or if we reached the minimal size
            if (n_items_to_flow <= max_col * max_row or
                chosen_icon_footprint == min_icon_footprint):
                break
            chosen_icon_footprint -= 1

        unused_pixels = 0
        # If we fully filled the row, and the number of items per line doesn't
        # match the exact windows width, then we have some pixels left to use
        # to perfectly "stretch" the items
        if n_items_to_flow > max_col or chosen_icon_footprint != icon_size:
            unused_pixels = available_width % chosen_icon_footprint

        # Compute the strech needed per item, and the possible stretch remaining
        # We use max_col - 1 because we want the first item to be left-aligned
        stretch_per_item = 0
        stretch_remaining = 0
        if max_col > 1:
            stretch_per_item = int(unused_pixels/(max_col-1))
            if stretch_per_item == 0:
                stretch_remaining = unused_pixels
            else:
                stretch_remaining = unused_pixels % stretch_per_item

        # Compute x,y positions for each items
        cur_col = 0
        cur_row = 0
        xpos = 0
        ypos = self.text_height + self.text_margin_size
        for item in items_to_flow:
            # Deal with drawable items
            self.drawn_items.append(DrawableItem(item, xpos, ypos, self))
            cur_col += 1
            if (cur_col%max_col == 0):
                cur_col = 0
                cur_row += 1
                xpos = 0
                ypos += self.text_margin_size + chosen_icon_footprint
            else:
                xpos += chosen_icon_footprint + stretch_per_item
                # If some stretch is remaining, add 1 px per item until we reach
                # the maximum stretch remaining
                if cur_col <= stretch_remaining:
                    xpos += 1

        # Set coordinates for trailing floor, in case it would be needed
        self.next_item = (xpos, ypos)
        self.build_position_index()


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
        size_multiplier = 64 * opt.size_multiplier
        for item in self.drawn_items:
            if self.show_item(item.item):
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
        if not Options().enable_mouseover:
            return

        if y < len(self.item_position_index):
            selected_row = self.item_position_index[y]
            if x < len(selected_row):
                self.selected_item_index = selected_row[x]

                if self.selected_item_index is not None \
                and self.selected_item_index < len(self.drawn_items):
                    self.item_message_start_time = self.framecount

    def load_selected_detail_page(self):
        if self.selected_item_index is None:
            return
        self.drawn_items[self.selected_item_index].load_detail_page()

    def get_scaled_icon(self, path, scale):
        return pygame.transform.scale(self.get_image(path), (scale, scale))

    def get_image(self, imagename, disable_glow=False):
        image = self._image_library.get(imagename)
        if image is None:
            path = self.file_prefix + "/collectibles/"
            if Options().make_items_glow and not disable_glow:
                path += "glow/"
            path += imagename
            canonicalized_path = path.replace('/', os.sep).replace('\\', os.sep)
            image = pygame.image.load(canonicalized_path)
            size_multiplier = Options().size_multiplier
            scaled_image = image
            # Resize image iff we need to
            if size_multiplier != 1:
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
        if item_index_to_display is None or item_index_to_display >= len(self.drawn_items):
            return False
        item = self.drawn_items[item_index_to_display].item
        desc = item.generate_item_description()
        self.text_height = self.write_message("%s%s" % (item.name, desc))
        return True

    def write_error_message(self, message):
        opt = Options()
        # Clear the screen
        self.screen.fill(DrawingTool.color(opt.background_color))
        self.write_message(message, flip=True)

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
        size_multiplier = int(64 * Options().size_multiplier)
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
        font_size = int(16 * opt.size_multiplier)

        # Anything that gets calculated and cached based on something in options
        # now needs to be flushed
        self.text_margin_size = font_size
        try:
            self.font = pygame.font.SysFont(
                opt.show_font,
                font_size,
                bold=opt.bold_font
            )
        except Exception:
            import traceback
            errmsg = traceback.format_exc()
            log = logging.getLogger("tracker")
            log.error("ERROR: Couldn't load font \"" + opt.show_font +"\", falling back to Arial")
            log.error(errmsg)
            self.font = pygame.font.SysFont(
                    "arial",
                    font_size,
                    bold=opt.bold_font
            )

        self._image_library = {}
        self.roll_icon = self.get_scaled_icon(self.id_to_image("284"), font_size * 2)
        self.blind_icon = self.get_scaled_icon("questionmark.png", font_size * 2)
        if opt.show_description or opt.show_status_message:
            self.text_height = self.write_message(" ")
        else:
            self.text_height = 0

    def reset(self):
        self.selected_item_index = None
        self.drawn_items = []
        self.item_position_index = []

    def set_window_title_info(self, watching=None, uploading=None, watching_player=None, update_notifier=None, updates_queued=None ):
        if watching is not None:
            self.window_title_info.watching = watching
        if uploading is not None:
            self.window_title_info.uploading = uploading
        if watching_player is not None:
            self.window_title_info.watching_player = watching_player
        if update_notifier is not None:
            self.window_title_info.update_notifier = update_notifier
        if updates_queued is not None:
            self.window_title_info.updates_queued = updates_queued

        self.update_window_title()

    def update_window_title(self):
        title = ""
        # The user wants a hard-coded window title
        if Options().custom_title_enabled:
            title = Options().custom_title
        else:
            title = "Rebirth Item Tracker"
            if self.window_title_info.update_notifier:
                title += self.window_title_info.update_notifier

            if self.window_title_info.watching:
                title += ", spectating " + self.window_title_info.watching_player + ". Delay: " + str(Options().read_delay) + ". Updates queued: " + str(self.window_title_info.updates_queued)
            elif self.window_title_info.uploading:
                title += ", uploading to server"

        # Set the title on the actual window
        pygame.display.set_caption(title)

    def show_item(self, item):
        """
            The highest priority is info.shown, because that way a user can override our logic and stop from seeing an
            item they don't want to see.

            Next is: we always show guppy items. Even if it's a space guppy item and space items are turned off. Because
            guppy is that important. TODO: look into applying this treatment to a few other space items? like nail?

            Finally, check any configurable conditions that might make us not want to show the item, and default to
            showing it if none of those are met.
        """
        opt = Options()
        if not item.info.shown:
            return False
        elif item.info.guppy:
            return True
        elif item.info.health_only and \
                not opt.show_health_ups:
                    return False
        elif item.info.space and \
                not opt.show_space_items:
                    return False
        elif item.was_rerolled and \
                not opt.show_rerolled_items:
                    return False
        return True




class DrawableItem(Drawable):
    def __init__(self, item, x, y, tool):
        super(DrawableItem, self).__init__(x, y, tool)
        self.item = item
        self.is_drawn = False

    def show_blind_icon(self):
        """
            We only show the curse of the blind icon if we're showing blind
            icons, the floor it was found on was a blind floor AND
            it's not one of our starting items
        """
        return Options().show_blind_icon and \
            not Options().blck_cndl_mode and \
            self.item.blind and \
            not self.item.starting_item

    def draw(self, selected=False):
        image = self.tool.get_image(DrawingTool.id_to_image(self.item.item_id))
        self.tool.screen.blit(image, (self.x, self.y))
        # If we're a re-rolled item, draw a little d4 near us
        if self.item.was_rerolled:
            self.tool.screen.blit(self.tool.roll_icon, (self.x, self.y))
        # If we're showing blind icons, draw a little blind icon
        if self.show_blind_icon():
            self.tool.screen.blit(
                self.tool.blind_icon,
                (self.x, self.y + Options().size_multiplier * 24)
            )
        # If we're selected, draw a box to highlight us
        if selected:
            self.tool.draw_selected_box(self.x, self.y)

    def load_detail_page(self):
        url = Options().item_details_link
        if not url:
            return
        url = url.replace("$ID", self.item.item_id)
        webbrowser.open(url, autoraise=True)

class WindowTitleInfo:
    def __init__(self, uploading, watching, update_notifier, watching_player, updates_queued):
        self.uploading = uploading
        self.watching = watching
        self.watching_player = watching_player
        self.updates_queued = updates_queued
        self.update_notifier = update_notifier
    def __init__(self):
        self.uploading = False
        self.watching = False
        self.watching_player = None
        self.updates_queued = None
        self.update_notifier = None


class DrawableFloor(Drawable):
    def __init__(self, floor, x, y, tool):
        super(DrawableFloor, self).__init__(x, y, tool)
        self.floor = floor
        self.is_drawn = False

    def draw(self, selected=False):
        text_color = DrawingTool.color(Options().text_color)
        size_multiplier = Options().size_multiplier
        pygame.draw.lines(
            self.tool.screen,
            text_color,
            False,
            ((self.x + 2, int(self.y + 48 * size_multiplier)),
             (self.x + 2, self.y),
             (int(self.x + 32 * size_multiplier), self.y))
        )
        image = self.tool.font.render(self.floor.name(Options().blck_cndl_mode), True, text_color)
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
