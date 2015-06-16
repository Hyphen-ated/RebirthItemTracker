import time
import glob
import os
import platform
import webbrowser
import pygame
import re
import json
import subprocess
import urllib2
if platform.system() == "Windows":
  import pygameWindowInfo
from pygame.locals import *
from pygame_helpers import *

class ItemInfo:
  def __init__(self, id, x, y, index, shown=True, floor=False):
    self.id = id
    self.x = x
    self.y = y
    self.shown = shown
    self.index = index
    self.floor = floor
    self.rerolled = False


class IsaacTracker:


  def __init__(self, verbose=False, debug=False, read_delay=1):
    # some general variable stuff, i guess
    self.verbose = verbose
    self.debug = debug
    self.text_height = 0
    self.text_margin_size = 16
    self.seek = 0
    self.framecount = 0
    self.read_delay = read_delay
    self.run_ended = True
    self.log_not_found = False
    self.content = ""
    # initialize isaac stuff
    self.collected_items = [] #list of string item ids with no leading zeros. can also contain "f1" through "f12" for floor markers
    self.collected_item_info = [] #list of iteminfo dicts
    self.num_displayed_items = 0
    self.selected_item_idx = None
    self.seed = ""
    self.current_room = ""
    self.run_start_line = 0
    self.run_start_frame = 0
    self.bosses = []
    self.last_run = {}
    self._image_library = {}
    self.filter_list = [] #list of string item ids with zeros stripped, they are items we don't want to see
    self.items_info = {}
    self.item_message_start_time = 0
    self.item_pickup_time = 0
    self.item_position_index = []
    self.current_floor = () # 2-tuple with first value being floor number, second value being alt stage value (0 or 1, r.n.)
    self.spawned_coop_baby = 0 # last spawn of a co op baby
    with open("items.txt", "r") as items_file:
      self.items_info = json.load(items_file)

    for itemid, item in self.items_info.iteritems():
      if not item["shown"]:
        self.filter_list.append(itemid.lstrip("0"))

    self.options = self.load_options()

    self.floor_id_to_label = {
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


  def load_options(self):
    with open("options.json", "r") as json_file:
      options = json.load(json_file)
    return options


  def save_options(self):
    with open("options.json", "w") as json_file:
      json.dump(self.options, json_file, indent=3, sort_keys=True)


  # just for debugging
  def log_msg(self, msg, level):
    if level=="V" and self.verbose: print msg
    if level=="D" and self.debug: print msg


  # just for the suffix of boss kill number lol
  def suffix(self, d):
    return 'th' if 11<=d<=13 else {1:'st',2:'nd',3:'rd'}.get(d%10, 'th')


  def check_end_run(self,line,cur_line_num):
    if not self.run_ended:
      died_to = ""
      end_type = ""
      if self.bosses and self.bosses[-1][0] in ['???','The Lamb','Mega Satan']:
        end_type = "Won"
      elif (self.seed != '') and line.startswith('RNG Start Seed:'):
        end_type = "Reset"
      elif line.startswith('Game Over.'):
        end_type = "Death"
        died_to = re.search('(?i)Killed by \((.*)\) spawned',line).group(1)
      if end_type:
        self.last_run = {
          "bosses":self.bosses
          , "items":self.collected_items
          , "seed":self.seed
          , "died_to":died_to
          , "end_type":end_type
        }
        self.run_ended = True
        self.log_msg("End of Run! %s" % self.last_run,"D")
        if end_type != "Reset":
          self.save_file(self.run_start_line,cur_line_num, self.seed)


  def save_file(self, start, end, seed):
    self.mkdir("run_logs")
    timestamp = int(time.time())
    seed = seed.replace(" ","")
    data = "\n".join(self.splitfile[start:end+1])
    data = "%s\nRUN_OVER_LINE\n%s" % (data, self.last_run)
    with open("run_logs/%s%s.log" % (seed,timestamp),'wb') as f:
      f.write(data)


  def mkdir(self, dn):
    import os
    if not os.path.isdir(dn):
      os.mkdir(dn)


  # image library stuff, from openbookproject.net
  def get_image(self, path):
    image = self._image_library.get(path)
    if image is None:
      canonicalized_path = path.replace('/', os.sep).replace('\\', os.sep)
      image = pygame.image.load(canonicalized_path)
      scaled_image = pygame.transform.scale(image,(image.get_size()[0] * 2,image.get_size()[1] * 2))
      self._image_library[path] = scaled_image
    return image


  def build_position_index(self):
    w = self.options["width"]
    h = self.options["height"]
    # 2d array of size h, w
    self.item_position_index = [[None for x in xrange(w)] for y in xrange(h)]
    self.num_displayed_items = 0
    for item in self.collected_item_info:
      if item.shown and not item.floor:
        self.num_displayed_items += 1
        for y in range(item.y, item.y + 64):
          if y >= h:
            continue
          row = self.item_position_index[y]
          for x in range(item.x, item.x + 64):
            if x >= w:
              continue
            row[x] = item.index

  def reflow(self):
    item_icon_size = self.options["default_spacing"]
    result = self.try_layout(item_icon_size, False)
    while result is None:
      item_icon_size -= 1
      if item_icon_size < self.options["min_spacing"] or item_icon_size < 4:
        result = self.try_layout(item_icon_size, True)
      else:
        result = self.try_layout(item_icon_size, False)

    self.collected_item_info = result

    self.build_position_index()


  def try_layout(self, icon_width, force_layout):
    icon_height = icon_width
    new_item_info = []
    cur_row = 0
    cur_column = 0
    index = 0
    vert_padding = 0
    if self.options['show_floors']:
      vert_padding = self.text_margin_size
    for item_id in self.collected_items:

      if item_id not in self.filter_list:

        #check to see if we are about to go off the right edge
        if icon_width * (cur_column) + icon_width > self.options["width"]:
          if (not force_layout) and self.text_height + (icon_height + vert_padding) * (cur_row + 1) + icon_height > self.options["height"]:
            return None
          cur_row += 1
          cur_column = 0

        if item_id.startswith('f'):
          item_info = ItemInfo(id = item_id,
                               x = icon_width * cur_column,
                               y =  self.text_height + (icon_height * cur_row) + (vert_padding * (cur_row + 1)),
                               shown = True,
                               index = index,
                               floor = True)
          new_item_info.append(item_info)
        else:
          item_info = ItemInfo(id = item_id,
                            x = icon_width * cur_column,
                            y =  self.text_height + (icon_height * cur_row) + (vert_padding * (cur_row + 1)),
                            shown = True,
                            index = index)
          new_item_info.append(item_info)
          cur_column += 1
      else:
        item_info = ItemInfo(id = item_id,
                          x = icon_width * cur_column,
                          y =  self.text_height +  (icon_height * cur_row) + (vert_padding * (cur_row + 1)),
                          shown = False,
                          index = index)
        new_item_info.append(item_info)
      index += 1
    return new_item_info


  def generateItemDescription(self, item_info):
    desc = ""
    text = item_info.get("text")
    dmg = item_info.get("dmg")
    dmgx = item_info.get("dmgx")
    delay = item_info.get("delay")
    delayx = item_info.get("delayx")
    health = item_info.get("health")
    speed = item_info.get("speed")
    shotspeed = item_info.get("shotspeed")
    tearrange = item_info.get("range")
    height = item_info.get("height")
    tears = item_info.get("tears")
    soulhearts = item_info.get("soulhearts")
    sinhearts = item_info.get("sinhearts")
    if dmg:
      desc += dmg + " dmg, "
    if dmgx:
      desc += "x" + dmgx + " dmg, "
    if tears:
      desc += tears + " tears, "
    if delay:
      desc += delay + " tear delay, "
    if delayx:
      desc += "x" + delayx + " tear delay, "
    if shotspeed:
      desc += shotspeed + " shotspeed, "
    if tearrange:
      desc += tearrange + " range, "
    if height:
      desc += height + " height, "
    if speed:
      desc += speed + " speed, "
    if health:
      desc += health + " health, "
    if soulhearts:
      desc += soulhearts + " soul hearts, "
    if sinhearts:
      desc += sinhearts + " sin hearts, "
    if text:
      desc += text
    if desc.endswith(", "):
      desc = desc[:-2]
    if len(desc) > 0:
      desc = ": " + desc
    return desc


  def color(self, string):
    return pygame.color.Color(str(string))

  def load_selected_detail_page(self):
    #todo open browser if this is not None
    if not self.selected_item_idx:
      return
    url = self.options.get("item_details_link")
    if not url:
      return
    item_id = self.collected_item_info[self.selected_item_idx].id
    url = url.replace("$ID", item_id)
    webbrowser.open(url, autoraise=True)
    return

  def adjust_selected_item(self, amount):
    itemlength = len(self.collected_item_info)
    if self.num_displayed_items < 1:
      return
    if self.selected_item_idx is None and amount > 0:
      self.selected_item_idx = 0
    elif self.selected_item_idx is None and amount < 0:
      self.selected_item_idx = itemlength - 1
    else:
      done = False
      while not done:
        self.selected_item_idx += amount
        # clamp it to the range (0, length)
        self.selected_item_idx = (self.selected_item_idx + itemlength) % itemlength
        done = self.collected_item_info[self.selected_item_idx].shown

    self.item_message_start_time = self.framecount

  def item_message_countdown_in_progress(self):
    return self.item_message_start_time + (self.options["message_duration"] * self.options["framerate"]) > self.framecount

  def item_pickup_countdown_in_progress(self):
    return self.item_pickup_time + (self.options["message_duration"] * self.options["framerate"]) > self.framecount

  def write_item_text(self, my_font, screen):
    item_idx = self.selected_item_idx
    if item_idx is None and self.item_pickup_countdown_in_progress():
      item_idx = -1
    if item_idx is None or len(self.collected_items) < item_idx :
      self.text_height = 19
      self.reflow()
      return
    item = self.collected_items[item_idx]
    if item.startswith('f'):
      return
    id_padded = item.zfill(3)
    item_info = self.items_info[id_padded]
    desc = self.generateItemDescription(item_info)
    self.text_height = draw_text(screen,"%s%s" % (item_info["name"], desc), self.color(self.options["text_color"]), pygame.Rect(2,2,self.options["width"]-2,self.options["height"]-2), my_font, aa=True, wrap=self.options["word_wrap"])
    self.reflow()
    # item_text = my_font.render("%s%s" % (item_info["name"], desc), True, self.color(self.options["text_color"]))
    # screen.blit(item_text, (2, 2))

  def load_log_file(self):
    self.log_not_found = False
    path = None
    for check in ('../log.txt', os.environ['USERPROFILE'] + '/Documents/My Games/Binding of Isaac Rebirth/log.txt'):
      if os.path.isfile(check):
        path = check
        break
    if path == None:
      self.log_not_found = True
      return

    length = len(self.content)
    size = os.path.getsize(path)
    if length > size or length == 0:  # New log file or first time loading the log
      self.content = open(path, 'rb').read()
    elif length < size:  # append existing content
      f = open(path, 'rb')
      f.seek(length + 1)
      self.content += f.read()

  #returns text to put in the titlebar
  def check_for_update(self):
    try:
      github_info_json = urllib2.urlopen("https://api.github.com/repos/Hyphen-ated/RebirthItemTracker/releases/latest").read()
      info = json.loads(github_info_json)
      latest_version = info["name"]
      with open('version.txt', 'r') as f:

        if(latest_version != f.read()):
          return " (new version available)"
    except Exception as e:
      pass
    return ""

  def id_to_image(self, id):
    return 'collectibles/collectibles_%s.png' % id.zfill(3)


  def draw_floor(self, f, screen, my_font):
    pygame.draw.lines(screen, self.color(self.options["text_color"]), False, ((f.x + 2, f.y + 48), (f.x + 2, f.y), (f.x + 32, f.y)))
    image = my_font.render(self.floor_id_to_label[f.id], True, self.color(self.options["text_color"]))
    screen.blit(image, (f.x + 4, f.y - self.text_margin_size))
    floor_to_draw = None

  def run(self):
    os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (self.options["xposition"],self.options["yposition"])
    # initialize pygame system stuff
    pygame.init()
    update_notifier = self.check_for_update()
    pygame.display.set_caption("Rebirth Item Tracker" + update_notifier)
    screen = pygame.display.set_mode((self.options["width"], self.options["height"]), RESIZABLE)
    done = False
    clock = pygame.time.Clock()
    my_font = pygame.font.SysFont("Arial", 16,bold=True)
    winInfo = None
    if platform.system() == "Windows":
      winInfo = pygameWindowInfo.PygameWindowInfo()
    userprofile_dir = os.environ['USERPROFILE']

    del os.environ['SDL_VIDEO_WINDOW_POS']
    while not done:
      # pygame logic
      for event in pygame.event.get():
        if event.type == pygame.QUIT:
          if platform.system() == "Windows":
            winPos = winInfo.getWindowPosition()
            self.options["xposition"] = winPos["left"]
            self.options["yposition"] = winPos["top"]
            self.save_options()
          done = True
        elif event.type==VIDEORESIZE:
          screen=pygame.display.set_mode(event.dict['size'], RESIZABLE)
          self.options["width"] = event.dict["w"]
          self.options["height"] = event.dict["h"]
          self.save_options()
          self.reflow()
          pygame.display.flip()
        elif event.type==MOUSEMOTION:
          if pygame.mouse.get_focused():
            x, y = pygame.mouse.get_pos()
            if y < len(self.item_position_index):
              selected_row = self.item_position_index[y]
              if x < len(selected_row):
                self.selected_item_idx = selected_row[x]
                if self.selected_item_idx:
                  self.item_message_start_time = self.framecount
        elif event.type==KEYDOWN:
          if len(self.collected_items) > 0:
            if event.key == pygame.K_RIGHT:
              self.adjust_selected_item(1)
            elif event.key == pygame.K_LEFT:
              self.adjust_selected_item(-1)
            elif event.key == pygame.K_RETURN:
              self.load_selected_detail_page()
        elif event.type==MOUSEBUTTONDOWN:
          if event.button==1:
            self.load_selected_detail_page()
          if event.button==3:
            if os.path.isfile("optionpicker/option_picker.exe"):
              self.log_msg("Starting option picker from .exe","D")
              subprocess.call(os.path.join('optionpicker',"option_picker.exe"),shell=True)
            elif os.path.isfile("option_picker.py"):
              self.log_msg("Starting option picker from .py","D")
              subprocess.call("python option_picker.py",shell=True)
            else:
              self.log_msg("No option_picker found!","D")
            self.options = self.load_options()
            self.reflow()


      screen.fill(self.color(self.options["background_color"]))
      clock.tick(int(self.options["framerate"]))

      if self.log_not_found:
        draw_text(screen,"log.txt not found. Put the RebirthItemTracker folder inside the isaac folder, next to log.txt", self.color(self.options["text_color"]), pygame.Rect(2,2,self.options["width"]-2,self.options["height"]-2), my_font, aa=True, wrap=True)

      # draw item pickup text, if applicable
      if (len(self.collected_items) > 0
      and self.options["show_description"]
      and self.run_start_frame + 120 < self.framecount
      and self.item_message_countdown_in_progress()):
        self.write_item_text(my_font, screen)
      elif self.options["show_seed"] and not self.log_not_found:
        # draw seed text:
        self.text_height = draw_text(screen,"Seed: %s" % self.seed, self.color(self.options["text_color"]), pygame.Rect(2,2,self.options["width"]-2,self.options["height"]-2), my_font, aa=True)
        self.reflow()
      else:
        # can only happen if you turn seed + item descriptions off in options while its running
        if self.text_height != 0:
          self.text_height = 0
          self.reflow()

      if not self.item_message_countdown_in_progress():
        self.selected_item_idx = None

      floor_to_draw = None
      # draw items on screen, excluding filtered items:
      for item in self.collected_item_info:
        if item.shown:
          if item.floor:
            floor_to_draw = item
          else:
            screen.blit(self.get_image(self.id_to_image(item.id)), (item.x, item.y))
            #don't draw a floor until we hit the next item (this way multiple floors in a row collapse)
            if floor_to_draw and self.options["show_floors"]:
              self.draw_floor(floor_to_draw, screen, my_font)

      #also draw the floor if we hit the end, so the current floor is visible
      if floor_to_draw and self.options["show_floors"]:
        self.draw_floor(floor_to_draw, screen, my_font)

      if (self.selected_item_idx
      and self.selected_item_idx < len(self.collected_item_info)
      and self.item_message_countdown_in_progress()):
        item = self.collected_item_info[self.selected_item_idx]
        screen.blit(self.get_image(self.id_to_image(item.id)), (item.x, item.y))
        pygame.draw.rect(screen, self.color(self.options["text_color"]), (item.x, item.y, 64,64), 2)


      pygame.display.flip()

      self.framecount += 1

      # process log stuff every read_delay frames
      if self.framecount % (int(self.options["framerate"])*self.read_delay) == 0:
        self.load_log_file()
        self.splitfile = self.content.splitlines()
        # return to start if seek passes the end of the file (usually b/c log file restarted)
        if self.seek > len(self.splitfile):
          self.log_msg("Current line number longer than lines in file, returning to start of file","D")
          self.seek = 0

        should_reflow = False
        # process log's new output
        for current_line_number,line in enumerate(self.splitfile[self.seek:]):
          self.log_msg(line,"V")
          # end floor boss defeated, hopefully?
          if line.startswith('Mom clear time:'):
            kill_time = int(line.split(" ")[-1])
            # if you re-enter a room you get a "mom clear time" again, check for that.
            # can you fight the same boss twice?
            if self.current_room not in [x[0] for x in self.bosses]:
              self.bosses.append((self.current_room, kill_time))
              self.log_msg("Defeated %s%s boss %s at time %s" % (len(self.bosses),self.suffix(len(self.bosses)),self.current_room,kill_time),"D")
          # check + handle the end of the run (order important here!)
          # we want it after boss kill (so we have that handled) but before RNG Start Seed (so we can handle that)
          self.check_end_run(line, current_line_number + self.seek)
          # start of a run
          if line.startswith('RNG Start Seed:'):
            # this assumes a fixed width, but from what i see it seems safe
            self.seed = line[16:25]
            self.log_msg("Starting new run, seed: %s" % self.seed,"D")
            self.run_start_frame = self.framecount
            self.collected_items = []
            self.log_msg("Emptied item array","D")
            self.bosses = []
            self.log_msg("Emptied boss array","D")
            self.run_start_line = current_line_number + self.seek
            self.run_ended = False
            with open("seed.txt", "w") as f:
              f.write(self.seed)

          # entered a room, use to keep track of bosses
          if line.startswith('Room'):
            self.current_room = re.search('\((.*)\)',line).group(1)
            self.log_msg("Entered room: %s" % self.current_room,"D")
          if line.startswith('Level::Init'):
            self.current_floor = tuple([re.search("Level::Init m_Stage (\d+), m_AltStage (\d+)",line).group(x) for x in [1,2]])
            floor = int(self.current_floor[0])
            alt = self.current_floor[1]
            # special handling for cath and chest
            if alt == '1' and (floor == 9 or  floor == 11):
              floor += 1
            self.collected_items.append('f' + str(floor))
            should_reflow = True
          if line.startswith('Curse of the Labyrinth!'):
            #it SHOULD always begin with f (that is, it's a floor) because this line only comes right after the floor line
            if self.collected_items[-1].startswith('f'):
              self.collected_items[-1] += 'x'
          if line.startswith('Spawn co-player!'):
            self.spawned_coop_baby = current_line_number + self.seek
          if re.search("Added \d+ Collectibles", line):
            self.log_msg("Reroll detected!","D")
            for item in self.collected_item_info:
              if not item.floor:
                item.rerolled = True
          if line.startswith('Adding collectible'):
            if len(self.splitfile) > 1 and self.splitfile[current_line_number + self.seek - 1] == line:
              self.log_msg("Skipped duplicate item line from baby presence","D")
              continue
            # hacky string manip, idgaf
            space_split = line.split(" ")
            # string has the form "Adding collectible 105 (The D6)"
            item_id = space_split[2]
            if ((current_line_number + self.seek) - self.spawned_coop_baby) < (len(self.collected_items) + 10) and item_id in self.collected_items:
              self.log_msg("Skipped duplicate item line from baby entry","D")
              continue
            item_name = " ".join(space_split[3:])[1:-1]
            self.log_msg("Picked up item. id: %s, name: %s" % (item_id, item_name),"D")
            id_padded = item_id.zfill(3)
            item_info = self.items_info[id_padded]
            with open("itemInfo.txt", "w") as f:
              desc = self.generateItemDescription(item_info)
              f.write(item_info["name"] + ":" + desc)

            # ignore repeated pickups of space bar items, or starting items (too early)
            if not (item_info.get("space") and item_id in self.collected_items):
              self.collected_items.append(item_id)
              self.item_message_start_time = self.framecount
              self.item_pickup_time = self.framecount
            else:
              self.log_msg("Skipped adding item %s to avoid space-bar duplicate" % item_id,"D")
            should_reflow = True

        self.seek = len(self.splitfile)
        if should_reflow:
          self.reflow()

try:
  rt = IsaacTracker(verbose=False, debug=False)
  rt.run()
except Exception as e:
  import traceback
  traceback.print_exc()