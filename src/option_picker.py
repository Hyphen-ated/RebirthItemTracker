from Tkinter import *
from tkColorChooser import askcolor
import json
from string import maketrans, lower
import re
import ttk
import pygame.sysfont

class options_menu():
    """
    These are the standard save and load options functions.
    """
    def __init__(self):
        # Our 'safe' list of fonts that should work in pygame
        self.fonts = ['Andalus', 'Angsana New', 'AngsanaUPC', 'Arial', 'Arial Black', 'Browallia New', 'BrowalliaUPC',
                      'Comic Sans MS', 'Cordia New', 'CordiaUPC', 'Courier New', 'DFKai-SB', 'David', 'DilleniaUPC',
                      'Estrangelo Edessa', 'FrankRuehl', 'Franklin Gothic Medium', 'Gautami', 'Georgia', 'Impact',
                      'IrisUPC', 'JasmineUPC', 'KodchiangUPC', 'Latha', 'LilyUPC', 'Lucida Console', 'MV Boli',
                      'Mangal', 'Microsoft Sans Serif', 'Miriam', 'Miriam Fixed', 'Narkisim', 'Raavi', 'Rod', 'Shruti',
                      'SimHei', 'Simplified Arabic', 'Simplified Arabic Fixed', 'Sylfaen', 'Tahoma', 'Times New Roman',
                      'Traditional Arabic', 'Trebuchet MS', 'Tunga', 'Verdana']

        # Check if the system has the fonts installed, and remove them from the list if it doesn't
        try:
            valid_pygame_fonts = [lower(x.replace(" ", "")) for x in self.fonts]
            system_fonts = pygame.sysfont.get_fonts()
            to_delete = []
            for index, font in enumerate(valid_pygame_fonts):
                if font not in system_fonts:
                    to_delete += [index]
            for index in to_delete[::-1]:
                del self.fonts[index]
        except:
            print "There may have been an error detecting system fonts."
            import traceback
            traceback.print_exc()

    def load_options(self):
        with open("options.json", "r") as json_file:
            options = json.load(json_file)
        return options


    def save_options(self, options):
        with open("options.json", "w") as json_file:
            json.dump(options, json_file, indent=3, sort_keys=True)

    """
    Callbacks
    """
    def color_callback(self, source):
        # Prompt a color picker, set the options and the background/foreground of the button
        nums, hex_color = askcolor(color=self.options.get(source),
                                   title="Color Chooser")
        if hex_color:
            opposite = self.opposite_color(hex_color)
            self.options[source] = hex_color.upper()
            self.buttons[source].configure(bg=hex_color, fg=opposite)

    def checkbox_callback(self):
        # Just for the "show decription" checkbox -- to disable the message duration entry
        if not self.checks.get("show_description").get():
            self.entries["message_duration"].configure(state=DISABLED)
        else:
            self.entries["message_duration"].configure(state=NORMAL)

    def save_callback(self):
        # Callback for the "save" option -- rejiggers options and saves to options.json, then quits
        for key, value in self.entries.iteritems():
            if key in self.numeric_entry_keys:
                self.options[key] = int(value.get())
            else:
                self.options[key] = value.get()
        for key, value in self.checks.iteritems():
            self.options[key] = True if value.get() else False
        self.save_options(self.options)
        self.root.destroy()


    # Taken from http://code.activestate.com/recipes/527747-invert-css-hex-colors/
    def opposite_color(self,color):
        # Get the opposite color of a hex color, just to make text on buttons readable
        color = color.lower()
        table = maketrans(
            '0123456789abcdef',
            'fedcba9876543210')
        return str(color).translate(table).upper()


    def pretty_name(self, s):
        # Change from a var name to something you'd show the users
        return " ".join(s.split("_")).title()


    # From http://stackoverflow.com/questions/4140437/interactively-validating-entry-widget-content-in-tkinter
    def OnValidate(self, d, i, P, s, S, v, V, W):
        # This validation is a biiit janky, just some crazy regex that checks P (value of entry after modification)
        return P == "" or re.search("^\d+(\.\d*)?$", P) is not None

    def run(self):
        # Load options, create root
        self.options = self.load_options()
        self.root = Tk()
        self.root.wm_title("Item Tracker Options")
        self.root.resizable(False, False)

        # Generate numeric options by looping over option types
        self.numeric_entry_keys = ["message_duration", "min_spacing", "default_spacing", "framerate_limit", "size_multiplier"]
        self.entries = {}
        nextrow = 0
        vcmd = (self.root.register(self.OnValidate), '%d', '%i', '%P', '%s', '%S', '%v', '%V', '%W')
        for index, opt in enumerate(["message_duration", "min_spacing", "default_spacing", "framerate_limit", "size_multiplier"]):
            Label(self.root, text=self.pretty_name(opt)).grid(row=nextrow)
            self.entries[opt] = Entry(self.root, validate="key", validatecommand=vcmd)
            self.entries[opt].grid(row=nextrow, column=1)
            self.entries[opt].insert(0, self.options.get(opt))
            nextrow += 1

        for index, opt in enumerate(["show_font"]):
            Label(self.root, text=self.pretty_name(opt)).grid(row=nextrow)
            initialvar = StringVar()
            initialvar.set(self.options.get(opt))
            self.entries[opt] = ttk.Combobox(self.root, values=sorted(self.fonts), textvariable=initialvar, state='readonly')
            self.entries[opt].grid(row=nextrow, column=1)
            nextrow += 1

        # Generate text options by looping over option types
        for index, opt in enumerate(["item_details_link", "custom_message"]):
            Label(self.root, text=self.pretty_name(opt)).grid(row=nextrow)
            self.entries[opt] = Entry(self.root)
            self.entries[opt].grid(row=nextrow, column=1)
            self.entries[opt].insert(0, self.options.get(opt))
            nextrow += 1

        # Generate buttons by looping over option types
        self.buttons = {}
        for index, opt in enumerate(["background_color", "text_color"]):
            self.buttons[opt] = Button(
                self.root,
                text=self.pretty_name(opt),
                bg=self.options.get(opt),
                fg=self.opposite_color(self.options.get(opt)),
                command=lambda opt=opt: self.color_callback(opt)
            )
            self.buttons[opt].grid(row=len(self.entries), column=index)

        # Generate checkboxes, with special exception for show_description for message duration
        self.checks = {}
        for index, opt in enumerate(
                ["show_description", "show_custom_message", "show_floors", "show_rerolled_items", "show_health_ups",
                 "show_space_items", "show_blind_icon", "word_wrap", "bold_font"]):
            self.checks[opt] = IntVar()
            c = Checkbutton(self.root, text=self.pretty_name(opt), variable=self.checks[opt])
            c.grid(row=len(self.entries) + 1 + index / 2, column=index % 2)  # 2 checkboxes per row
            if self.options.get(opt):
                c.select()

            # Disable letting the user set the message duration if the show description option is disabled.
            if opt == "show_description":
                c.configure(command=self.checkbox_callback)
                if not self.options.get("show_description"):
                    self.entries["message_duration"].configure(state=DISABLED)

        # Save and cancel buttons
        save = Button(self.root,
                      text="Save",
                      command=self.save_callback)
        save.grid(row=len(self.entries) + len(self.buttons) + len(self.checks), column=0)
        cancel = Button(self.root,
                        text="Cancel",
                        command=self.root.destroy)
        cancel.grid(row=len(self.entries) + len(self.buttons) + len(self.checks), column=1)

        # Start the main loop
        mainloop()

if __name__ == '__main__':
    options_menu().run()
