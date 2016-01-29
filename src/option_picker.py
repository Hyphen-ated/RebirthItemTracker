from Tkinter import *
from tkColorChooser import askcolor
import json
from string import maketrans, lower
import re
import ttk
import pygame.sysfont
from options import Options
import logging
import urllib2
import webbrowser

class OptionsMenu(object):
    """
    These are the standard save and load options functions.
    """
    def __init__(self):
        self.options = Options()
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
            log = logging.getLogger("tracker")
            log.error("There may have been an error detecting system fonts.")
            import traceback
            log.error(traceback.print_exc())


    """
    Callbacks
    """
    def color_callback(self, source):
        # Prompt a color picker, set the options and the background/foreground of the button
        nums, hex_color = askcolor(color=getattr(self.options, source), title="Color Chooser")
        if hex_color:
            opposite = self.opposite_color(hex_color)
            setattr(self.options, source, hex_color.upper())
            self.buttons[source].configure(bg=hex_color, fg=opposite)

    def checkbox_callback(self):
        # Just for the "show decription" checkbox -- to disable the message duration entry
        if not self.checks.get("show_description").get():
            self.entries["message_duration"].configure(state=DISABLED)
        else:
            self.entries["message_duration"].configure(state=NORMAL)

        # Disable custom message if we don't have to show it
        if not self.checks.get("show_status_message").get():
            self.entries["status_message"].configure(state=DISABLED)
        else:
            self.entries["status_message"].configure(state=NORMAL)

    # Writing to server occurs when state changes, so enable read delay iff we are reading
        if self.checks.get("read_from_server").get():
            self.entries["read_delay"].grid()
            self.entries["twitch_name"].grid()
            self.labels["read_delay"].grid()
            self.labels["twitch_name"].grid()
        else:
            self.entries["read_delay"].grid_remove()
            self.entries["twitch_name"].grid_remove()
            self.labels["read_delay"].grid_remove()
            self.labels["twitch_name"].grid_remove()

        # Disable authkey if we don't write to server
        if self.checks.get("write_to_server").get():
            self.entries["trackerserver_authkey"].grid()
            self.labels["trackerserver_authkey"].grid()
            self.buttons["authkey_button"].grid()
        else:
            self.entries["trackerserver_authkey"].grid_remove()
            self.labels["trackerserver_authkey"].grid_remove()
            self.buttons["authkey_button"].grid_remove()

    def read_callback(self):
        if self.checks.get("read_from_server").get():
            self.checks.get("write_to_server").set(0)
            self.update_twitch_name_combobox_from_server()
        self.checkbox_callback()

    def write_callback(self):
        if self.checks.get("write_to_server").get():
            self.checks.get("read_from_server").set(0)
        self.checkbox_callback()

    def save_callback(self):
        # Callback for the "save" option -- rejiggers options and saves to options.json, then quits
        for key, value in self.entries.iteritems():
            if key in self.integer_keys:
                # Cast this as a float first to avoid errors if the user puts a value of 1.0 in an options, for example
                setattr(self.options, key, int(float(value.get())))
            elif key in self.float_keys:
                setattr(self.options, key, float(value.get()))
            elif hasattr(value, "get"):
                setattr(self.options, key, value.get())
        for key, value in self.checks.iteritems():
            setattr(self.options, key, True if value.get() else False)
        self.root.destroy()

    def seconds_to_text(self, seconds):
        if seconds < 60:
            return str(seconds) + " second" + ("s" if seconds > 1 else "")
        minutes = seconds / 60
        if minutes < 60:
            return str(minutes) + " minute" + ("s" if minutes > 1 else "")
        hours = minutes / 60
        if hours < 24:
            return str(hours) + " hour" + ("s" if hours > 1 else "")
        days = hours / 24
        return str(days) + " day" + ("s" if days > 1 else "")

    def update_twitch_name_combobox_from_server(self):
        try:
            url = self.entries['trackerserver_url'].get() + "/tracker/api/userlist/"
            json_state = urllib2.urlopen(url).read()
            users = json.loads(json_state)
            users_combobox_list = []
            for user in users:
                formatted_time_ago = self.seconds_to_text(user["seconds"])
                list_entry = user["name"] + " (updated " + formatted_time_ago + " ago)"
                users_combobox_list.append(list_entry)
            self.entries['twitch_name']['values'] = users_combobox_list
        except Exception:
            import traceback
            errmsg = traceback.format_exc()
            #print it to stdout for dev troubleshooting, log it to a file for production
            print(errmsg)
            logging.getLogger("tracker").error(errmsg)

    def trim_name(self, event):
        name = self.entries['twitch_name'].get()
        name = name.partition(" (")[0]
        self.entries['twitch_name'].set(name)


    # Taken from http://code.activestate.com/recipes/527747-invert-css-hex-colors/
    def opposite_color(self, color):
        # Get the opposite color of a hex color, just to make text on buttons readable
        color = color.lower()
        table = maketrans('0123456789abcdef', 'fedcba9876543210')
        return str(color).translate(table).upper()

    pretty_name_map = {"read_from_server": "Watch Someone Else",
                       "write_to_server": "Let Others Watch Me",
                       "twitch_name": "Their Twitch Name",
                       "bold_font": "Bold",
                       "blck_cndl_mode": "BLCK CNDL mode"}
    label_after_text = {"message_duration":"seconds",
                        "framerate_limit":"fps"}
    def pretty_name(self, s):
        # Change from a var name to something you'd show the users
        if self.pretty_name_map.has_key(s):
            return self.pretty_name_map.get(s)
        return " ".join(s.split("_")).title()

    # From http://stackoverflow.com/questions/4140437/interactively-validating-entry-widget-content-in-tkinter
    def OnValidate(self, d, i, P, s, S, v, V, W):
        # This validation is a biiit janky, just some crazy regex that checks P (value of entry after modification)
        return P == "" or re.search("^\d+(\.\d*)?$", P) is not None

    def run(self):
        # Create root
        self.root = Tk()
        self.root.attributes("-topmost", True)
        self.root.wm_title("Item Tracker Options")
        self.root.resizable(False, False)

        # Generate numeric options by looping over option types
        self.integer_keys = ["message_duration", "framerate_limit", "read_delay"]
        self.float_keys   = ["size_multiplier"]
        self.entries = {}
        self.labels = {}
        self.checks = {}
        self.buttons = {}

        textframe = LabelFrame(self.root, text="Text Options", padx=20, pady=20)
        textframe.grid(row=0, column=0, padx=5, pady=5)
        vcmd = (self.root.register(self.OnValidate), '%d', '%i', '%P', '%s', '%S', '%v', '%V', '%W')
        nextrow = 0
        for index, opt in enumerate(["message_duration"]):
            Label(textframe, text=self.pretty_name(opt)).grid(row=nextrow)
            self.entries[opt] = Entry(textframe, validate="key", validatecommand=vcmd)
            self.entries[opt].grid(row=nextrow, column=1)
            self.entries[opt].insert(0, getattr(self.options, opt))
            if opt in self.label_after_text:
                Label(textframe, text=self.label_after_text[opt]).grid(row=nextrow, column=2)
            nextrow += 1

        for index, opt in enumerate(["show_font"]):
            Label(textframe, text=self.pretty_name(opt)).grid(row=nextrow)
            initialvar = StringVar()
            initialvar.set(getattr(self.options, opt))
            self.entries[opt] = ttk.Combobox(textframe, values=sorted(self.fonts), textvariable=initialvar, state='readonly')
            self.entries[opt].grid(row=nextrow, column=1)

        for index, opt in enumerate(["bold_font"]):
            self.checks[opt] = IntVar()
            c = Checkbutton(textframe, text=self.pretty_name(opt), variable=self.checks[opt])
            c.grid(row=nextrow, column=2)
            nextrow += 1
            if getattr(self.options, opt):
                c.select()

        for index, opt in enumerate(["status_message"]):
            Label(textframe, text=self.pretty_name(opt)).grid(row=nextrow)
            self.entries[opt] = Entry(textframe)
            self.entries[opt].grid(row=nextrow, column=1)
            self.entries[opt].insert(0, getattr(self.options, opt))
            nextrow += 1

        text_checkboxes = ["show_description", "show_status_message", "word_wrap"]
        for index, opt in enumerate(text_checkboxes):
            self.checks[opt] = IntVar()
            c = Checkbutton(textframe, text=self.pretty_name(opt), variable=self.checks[opt])
            c.grid(row=len(text_checkboxes) + 1 + index / 2, column=index % 2)  # 2 checkboxes per row
            if getattr(self.options, opt):
                c.select()

            # Disable letting the user set the message duration if the show description option is disabled.
            if opt == "show_description" or opt == "show_status_message":
                c.configure(command=self.checkbox_callback)


        mainframe = LabelFrame(self.root, text="Display Options", padx=20, pady=20)
        # mainframe.pack(fill="both", expand="yes")
        mainframe.grid(row=1, column=0, padx=5, pady=5)
        nextrow = 0

        for index, opt in enumerate(["framerate_limit", "size_multiplier"]):
            Label(mainframe, text=self.pretty_name(opt)).grid(row=nextrow)
            self.entries[opt] = Entry(mainframe, validate="key", validatecommand=vcmd)
            self.entries[opt].grid(row=nextrow, column=1)
            self.entries[opt].insert(0, getattr(self.options, opt))
            if opt in self.label_after_text:
                Label(mainframe, text=self.label_after_text[opt]).grid(row=nextrow, column=2)
            nextrow += 1

        # Generate text options by looping over option types
        for index, opt in enumerate(["item_details_link"]):
            Label(mainframe, text=self.pretty_name(opt)).grid(row=nextrow)
            self.entries[opt] = Entry(mainframe)
            self.entries[opt].grid(row=nextrow, column=1)
            self.entries[opt].insert(0, getattr(self.options, opt))
            nextrow += 1

        # Generate buttons by looping over option types
        for index, opt in enumerate(["background_color", "text_color"]):
            self.buttons[opt] = Button(
                mainframe,
                text=self.pretty_name(opt),
                bg=getattr(self.options, opt),
                fg=self.opposite_color(getattr(self.options, opt)),
                command=lambda opt=opt: self.color_callback(opt)
            )
            self.buttons[opt].grid(row=len(self.entries), column=index)

        # Generate checkboxes, with special exception for show_description for message duration
        for index, opt in enumerate(
                ["show_floors", "show_rerolled_items", "show_health_ups",
                 "show_space_items", "show_blind_icon", "make_items_glow","blck_cndl_mode"]):
            self.checks[opt] = IntVar()
            c = Checkbutton(mainframe, text=self.pretty_name(opt), variable=self.checks[opt])
            c.grid(row=len(self.entries) + 1 + index / 2, column=index % 2)  # 2 checkboxes per row
            if getattr(self.options, opt):
                c.select()

        serverframe = LabelFrame(self.root, text="Tournament Settings", padx=20, pady=20)
        serverframe.grid(row=0, column=1)
        next_row = 0


        # Generate text options by looping over option types
        for index, opt in enumerate(["trackerserver_url", "trackerserver_twitch_id"]):
            self.labels[opt] = Label(serverframe, text=self.pretty_name(opt))
            self.labels[opt].grid(row=next_row, pady=2)
            self.entries[opt] = Entry(serverframe)
            self.entries[opt].grid(row=next_row, column=1, pady=2)
            self.entries[opt].insert(0, getattr(self.options, opt, ""))
            next_row += 1

        paddings = {"read_from_server": 5, "write_to_server": 120}
        callbacks = {"read_from_server":self.read_callback, "write_to_server":self.write_callback}
        for index, opt in enumerate(["read_from_server", "write_to_server"]):
            self.checks[opt] = IntVar()
            c = Checkbutton(serverframe, text=self.pretty_name(opt), variable=self.checks[opt], indicatoron=False)
            c.grid(row=next_row, column=index, pady=2, padx=paddings[opt])
            c.configure(command=callbacks[opt])
            if getattr(self.options, opt, False):
                c.select()
        next_row += 1


        for index, opt in enumerate(["twitch_name"]):
            self.labels[opt] = Label(serverframe, text=self.pretty_name(opt))
            self.labels[opt].grid(row=next_row, pady=2)
            self.entries[opt] = ttk.Combobox(serverframe, width=40)
            self.entries[opt].set(getattr(self.options, opt, ""))
            self.entries[opt].bind("<<ComboboxSelected>>", self.trim_name)
            self.entries[opt].grid(row=next_row, column=1)
            next_row += 1


        # Generate text options by looping over option types
        for index, opt in enumerate(["read_delay", "trackerserver_authkey"]):
            self.labels[opt] = Label(serverframe, text=self.pretty_name(opt))
            self.labels[opt].grid(row=next_row, pady=2)
            self.entries[opt] = Entry(serverframe)
            self.entries[opt].grid(row=next_row, column=1, pady=2)
            self.entries[opt].insert(0, getattr(self.options, opt, ""))
            next_row += 1

        def authkey_fn():
            webbrowser.open("https://api.twitch.tv/kraken/oauth2/authorize?response_type=token&client_id=" + self.entries["trackerserver_twitch_id"].get() + "&redirect_uri=" +
                            self.entries['trackerserver_url'].get() + "/tracker/setup&scope=", autoraise=True)
            self.entries["trackerserver_authkey"].delete(0, last=END)


        self.buttons["authkey_button"] = Button(
            serverframe,
            text="Get an authkey",
            command=authkey_fn
        )

        self.buttons["authkey_button"].grid(row=next_row, column=1, pady=5)

        # Check for coherency in options with priority to read
        self.read_callback()
        # Disable some textboxes if needed
        self.checkbox_callback()


        buttonframe = LabelFrame(self.root, bd=0, padx=5, pady=5)
        buttonframe.grid(row=2, column=1)
        # Save and cancel buttons
        save = Button(
            buttonframe,
            text="Save",
            command=self.save_callback
        )
        save.grid(row=0, column=0, padx=5)
        cancel = Button(
            buttonframe,
            text="Cancel",
            command=self.root.destroy
        )
        cancel.grid(row=0, column=1, padx=5)

        # Start the main loop
        mainloop()

