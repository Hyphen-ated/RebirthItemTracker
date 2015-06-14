from Tkinter import *
from tkColorChooser import askcolor  
import json
from string import maketrans
import re


"""
  standard save + load options functions, from item_tracker.py. save_options modified a bit to take a parameter
"""
def load_options():
  with open("options.json", "r") as json_file:
    options = json.load(json_file)
  return options


def save_options(options):
  with open("options.json", "w") as json_file:
    json.dump(options, json_file, indent=3, sort_keys=True)


"""
  callbacks
"""
def color_callback(source):
  # prompt a color picker, set the options and the background/foreground of the button
  global buttons
  global options
  nums, hex_color = askcolor(color=options.get(source), 
                    title = "Color Chooser")
  if hex_color:
    opposite = opposite_color(hex_color)
    options[source] = hex_color.upper()
    buttons[source].configure(bg=hex_color, fg=opposite)


def checkbox_callback():
  # just for the "show decription" checkbox -- to disable the message duration entry
  global checks
  global entries
  if not checks.get("show_description").get():
    entries["message_duration"].configure(state=DISABLED)
  else:
    entries["message_duration"].configure(state=NORMAL)


def save():
  # callback for the "save" option -- rejiggers options and saves to options.json, then quits
  global root
  global options
  global numeric_entry_keys
  for key, value in entries.iteritems():
    if key in numeric_entry_keys:
      options[key] = int(value.get())
    else:
      options[key] = value.get()
  for key, value in checks.iteritems():
    options[key] = True if value.get() else False
  save_options(options)
  root.quit()


# taken from http://code.activestate.com/recipes/527747-invert-css-hex-colors/
def opposite_color(color):
  # get the opposite color of a hex color, just to make text on buttons readable
  color = color.lower()
  table = maketrans(
      '0123456789abcdef',
      'fedcba9876543210')
  return str(color).translate(table).upper()


def pretty_name(s):
  # change from a var name to something you'd show the users
  return " ".join(s.split("_")).title()


# from http://stackoverflow.com/questions/4140437/interactively-validating-entry-widget-content-in-tkinter
def OnValidate(d, i, P, s, S, v, V, W):
  # this validation is a biiit janky, just some crazy regex that checks P (value of entry after modification)
  return P=="" or re.search("^\d+(\.\d*)?$",P) is not None


# load options, create root
options = load_options()
root = Tk()
root.wm_title("Item Tracker Options")

# generate numeric options by looping over option types
numeric_entry_keys = ["message_duration","min_spacing","default_spacing"]
entries = {}
nextrow = 0
vcmd = (root.register(OnValidate), 
        '%d', '%i', '%P', '%s', '%S', '%v', '%V', '%W')
for index, opt in enumerate(["message_duration","min_spacing","default_spacing"]):
  Label(root, text=pretty_name(opt)).grid(row=nextrow)
  entries[opt] = Entry(root,validate="key",validatecommand=vcmd)
  entries[opt].grid(row=nextrow,column=1)
  entries[opt].insert(0,options.get(opt))
  nextrow += 1

# generate text options by looping over option types
for index, opt in enumerate(["item_details_link"]):
  Label(root, text=pretty_name(opt)).grid(row=nextrow)
  entries[opt] = Entry(root)
  entries[opt].grid(row=nextrow,column=1)
  entries[opt].insert(0,options.get(opt))
  nextrow += 1

# generate buttons by looping over option types
buttons = {}
for index, opt in enumerate(["background_color","text_color"]):
  buttons[opt] = Button(root, 
         text=pretty_name(opt), 
         bg=options.get(opt),
         fg=opposite_color(options.get(opt)),
         # command=lambda: color_callback(opt))
         command=lambda opt=opt: color_callback(opt))
  buttons[opt].grid(row=len(entries),column=index)


# generate checkboxes, with special exception for show_description for message duration
checks = {}
for index, opt in enumerate(["show_description", "show_seed", "show_floors", "word_wrap"]):
  checks[opt] = IntVar()
  c = Checkbutton(root, text=pretty_name(opt), variable=checks[opt])
  c.grid(row=len(entries)+len(buttons),column=index)
  if options.get(opt):
    c.select()
  # for greying out the thing ugh
  if opt=="show_description":
    c.configure(command=checkbox_callback)
    if not options.get("show_description"):
      entries["message_duration"].configure(state=DISABLED)


# save and cancel buttons
cancel = Button(root, 
         text="Cancel",
         command=root.quit)


save = Button(root, 
         text="Save",
         command=save)


cancel.grid(row=len(entries)+len(buttons)+len(checks),column=1)
save.grid(row=len(entries)+len(buttons)+len(checks),column=0)


# start the main loop eyyy
mainloop()