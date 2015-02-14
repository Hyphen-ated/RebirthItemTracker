import time
import glob
import os
import pygame
import re
import json
from pygame.locals import *


#convenience class that lets you basically have dictionaries that you access with dot notation
# (copy pasted from the internet, i have no idea how this works)
class Bunch:
    __init__ = lambda self, **kw: setattr(self, '__dict__', kw)


class IsaacTracker:


  def __init__(self, verbose=False, debug=False, read_delay=60):
    # some general variable stuff, i guess
    self.verbose = verbose
    self.debug = debug
    self.seek = 0
    self.framecount = 0
    self.read_delay = read_delay
    self.run_ended = True
    # initialize isaac stuff
    self.collected_items = []
    self.collected_item_info = []
    self.seed = ""
    # filter_list = {"105"}
    self.current_room = ""
    self.run_start_line = 0
    self.bosses = []
    self.last_run = {}
    self._image_library = {}
    self.filter_list = []
    self.items_info = {}
    with open("items.txt", "r") as items_file:
      self.items_info = json.load(items_file)

    for itemid, item in self.items_info.iteritems():
      if not item["shown"]:
        self.filter_list.append(itemid.lstrip("0"))

    self.options = self.load_options()


  def load_options(self):
    with open("options.json", "r") as json_file:
      options = json.load(json_file)
    return options


  def save_options(self):
    with open("options.json", "w") as json_file:
      json.dump(self.options, json_file)


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
    if image == None:
      canonicalized_path = path.replace('/', os.sep).replace('\\', os.sep)
      image = pygame.image.load(canonicalized_path)
      scaled_image = pygame.transform.scale(image,(image.get_size()[0] * 2,image.get_size()[1] * 2))
      self._image_library[path] = scaled_image
    return image


  def reflow(self):
    item_icon_size = self.options["default_spacing"]
    result = self.try_layout(item_icon_size, False)
    while result is False:
      item_icon_size -= 1
      if item_icon_size < self.options["min_spacing"] or item_icon_size < 4:
        result = self.try_layout(item_icon_size, True)
      else:
        result = self.try_layout(item_icon_size, False)

    self.collected_item_info = result


  def try_layout(self, icon_width, force_layout):
    new_item_info = []
    cur_row = 0
    cur_column = 0
    for index,item in enumerate([x for x in self.collected_items if x not in self.filter_list]):
      #check to see if we are about to go off the right edge
      if icon_width * (cur_column) + 64 > self.options["width"]:
        if (not force_layout) and 16 + icon_width * (cur_row + 1) + 64 > self.options["height"]:
          return False
        cur_row += 1
        cur_column = 0

      item_info = Bunch(id = item,
                        x = icon_width * cur_column,
                        y =  16 + icon_width * cur_row)
      new_item_info.append(item_info)
      cur_column += 1
    return new_item_info


  def run(self):
    # initialize pygame system stuff
    pygame.init()
    pygame.display.set_caption("Rebirth Item Tracker")
    screen = pygame.display.set_mode((self.options["width"], self.options["height"]), RESIZABLE)
    done = False
    clock = pygame.time.Clock()
    my_font = pygame.font.SysFont("Arial", 16,bold=True)


    while not done:
      # pygame logic
      for event in pygame.event.get():
        if event.type == pygame.QUIT:
          done = True
        elif event.type==VIDEORESIZE:
          screen=pygame.display.set_mode(event.dict['size'], RESIZABLE)
          self.options["width"] = event.dict["w"]
          self.options["height"] = event.dict["h"]
          self.save_options()
          self.reflow()
          pygame.display.flip()


      screen.fill((25,25,25))
      clock.tick(60)

      # draw seed text:
      seed_text = my_font.render("Seed: %s" % self.seed, True, (255,255,255))
      screen.blit(seed_text,(2,2))

      # draw items on screen, excluding filtered items:
      for item in self.collected_item_info:
        screen.blit(self.get_image('collectibles/collectibles_%s.png' % item.id.zfill(3)), (item.x, item.y))

      pygame.display.flip()

      self.framecount += 1

      # process log stuff every read_delay frames
      if self.framecount % self.read_delay == 0:
        # entire thing loaded into memory each loop -- see if maybe pruning log is possible for long sessions?
        content = ""
        try:
          with open('../log.txt', 'r') as f:
            content = f.read()
        except Exception:
          self.log_msg("log.txt not found, is the RebirthItemTracker directory in 'my games/Binding of Isaac Rebirth'?","D")
          continue


        self.splitfile = content.splitlines()
        # return to start if seek passes the end of the file (usually b/c log file restarted)
        if self.seek > len(self.splitfile):
          self.log_msg("Current line number longer than lines in file, returning to start of file","D")
          self.seek = 0


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
            self.collected_items = []
            self.log_msg("Emptied item array","D")
            self.bosses = []
            self.log_msg("Emptied boss array","D")
            self.run_start_line = current_line_number + self.seek
            self.run_ended = False
          # entered a room, use to keep track of bosses
          if line.startswith('Room'):
            self.current_room = re.search('\((.*)\)',line).group(1)
            self.log_msg("Entered room: %s" % self.current_room,"D")
          if line.startswith('Adding collectible'):
            # hacky string manip, idgaf
            space_split = line.split(" ")
            # string has the form "Adding collectible 105 (The D6)"
            item_id = space_split[2]
            item_name = " ".join(space_split[3:])[1:-1]
            self.log_msg("Picked up item. id: %s, name: %s" % (item_id, item_name),"D")
            self.collected_items.append(item_id)
            self.reflow()
            pass

        self.seek = len(self.splitfile)


rt = IsaacTracker(verbose=False, debug=False)
rt.run()