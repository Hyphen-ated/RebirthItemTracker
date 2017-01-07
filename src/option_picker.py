from Tkinter import *
from multiprocessing import Queue
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
import platform
import threading

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
        self.game_versions = ['Rebirth', 'Afterbirth', 'Afterbirth+', 'Antibirth']
        self.network_queue = Queue()

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

    pretty_name_map = {"read_from_server": "Watch Someone Else",
                       "write_to_server": "Let Others Watch Me",
                       "twitch_name": "Their Twitch Name",
                       "bold_font": "Bold",
                       "blck_cndl_mode": "BLCK CNDL mode",
                       "custom_title_enabled": "Change Window Title"}
    label_after_text = {"message_duration":"seconds",
                        "framerate_limit":"fps"}
    connection_labels = {"starting":"Connecting to server for player list...",
                         "done": "Connecting to server for player list... Done",
                         "fail": "Connecting to server for player list... Failed"}

    def pretty_name(self, s):
        # Change from a var name to something you'd show the users
        if self.pretty_name_map.has_key(s):
            return self.pretty_name_map.get(s)
        return " ".join(s.split("_")).title()

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

        # Just for the "Custom Title Enabled" checkbox -- to disable the "Custom Title" entry
        if not self.checks.get("custom_title_enabled").get():
            self.entries["custom_title"].configure(state=DISABLED)
        else:
            self.entries["custom_title"].configure(state=NORMAL)

        # Writing to server occurs when state changes, so enable read delay if we are reading
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
            self.labels["server_connect_label"].config(text="")

        if self.checks.get("change_server").get():
            self.entries["trackerserver_url"].grid()
            self.labels["trackerserver_url"].grid()
        else:
            self.entries["trackerserver_url"].grid_remove()
            self.labels["trackerserver_url"].grid_remove()


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
            self.labels["server_connect_label"].config(text=self.connection_labels["starting"])
            t = threading.Thread(target=self.get_server_userlist_and_enqueue)
            t.start()
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

    def get_server_userlist_and_enqueue(self):
        try:
            url = self.entries['trackerserver_url'].get() + "/tracker/api/userlist/"
            json_state = urllib2.urlopen(url).read()
            users = json.loads(json_state)
            success = True
        except Exception:
            import traceback
            errmsg = traceback.format_exc()
            #print it to stdout for dev troubleshooting, log it to a file for production
            print(errmsg)
            logging.getLogger("tracker").error(errmsg)
            users = []
            success = False
        network_result = {"users": users, "success": success}
        self.network_queue.put(network_result)

    def get_server_twitch_client_id(self):
        try:
            url = self.entries['trackerserver_url'].get() + "/tracker/api/twitchclientid/"
            return urllib2.urlopen(url).read()
        except Exception:
            import traceback
            errmsg = traceback.format_exc()
            #print it to stdout for dev troubleshooting, log it to a file for production
            print(errmsg)
            logging.getLogger("tracker").error(errmsg)
            return None


    def process_network_results(self):
        while self.network_queue.qsize():
            try:
                network_result = self.network_queue.get(0)
                users_combobox_list = []
                for user in network_result["users"]:
                    formatted_time_ago = self.seconds_to_text(user["seconds"])
                    list_entry = user["name"] + " (updated " + formatted_time_ago + " ago)"
                    users_combobox_list.append(list_entry)
                self.entries['twitch_name']['values'] = users_combobox_list
                label = "done" if network_result["success"] else "fail"
                self.labels["server_connect_label"].config(text=self.connection_labels[label])
            except Queue.Empty:
                pass
        self.root.after(100, self.process_network_results)


    def trim_name(self, event):
        name = self.entries['twitch_name'].get()
        name = name.partition(" (")[0]
        self.entries['twitch_name'].set(name)

    # From: http://code.activestate.com/recipes/527747-invert-css-hex-colors/
    def opposite_color(self, color):
        # Get the opposite color of a hex color, just to make text on buttons readable
        color = color.lower()
        table = maketrans('0123456789abcdef', 'fedcba9876543210')
        return str(color).translate(table).upper()

    # From: http://stackoverflow.com/questions/4140437/interactively-validating-entry-widget-content-in-tkinter
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

        # Draw the "Text Options" box
        text_options_frame = LabelFrame(self.root, text="Text Options", padx=20, pady=20)
        text_options_frame.grid(row=0, column=0, padx=5, pady=5)
        vcmd = (self.root.register(self.OnValidate), '%d', '%i', '%P', '%s', '%S', '%v', '%V', '%W')
        next_row = 0
        for index, opt in enumerate(["message_duration"]):
            Label(text_options_frame, text=self.pretty_name(opt)).grid(row=next_row)
            self.entries[opt] = Entry(text_options_frame, validate="key", validatecommand=vcmd)
            self.entries[opt].grid(row=next_row, column=1)
            self.entries[opt].insert(0, getattr(self.options, opt))
            if opt in self.label_after_text:
                Label(text_options_frame, text=self.label_after_text[opt]).grid(row=next_row, column=2)
            next_row += 1

        for index, opt in enumerate(["show_font"]):
            Label(text_options_frame, text=self.pretty_name(opt)).grid(row=next_row)
            initialfont = StringVar()
            initialfont.set(getattr(self.options, opt))
            self.entries[opt] = ttk.Combobox(text_options_frame, values=sorted(self.fonts), textvariable=initialfont, state='readonly')
            self.entries[opt].grid(row=next_row, column=1)

        for index, opt in enumerate(["bold_font"]):
            self.checks[opt] = IntVar()
            c = Checkbutton(text_options_frame, text=self.pretty_name(opt), variable=self.checks[opt])
            c.grid(row=next_row, column=2)
            next_row += 1
            if getattr(self.options, opt):
                c.select()

        for index, opt in enumerate(["status_message"]):
            Label(text_options_frame, text=self.pretty_name(opt)).grid(row=next_row)
            self.entries[opt] = Entry(text_options_frame)
            self.entries[opt].grid(row=next_row, column=1)
            self.entries[opt].insert(0, getattr(self.options, opt))
            next_row += 1

        text_checkboxes = ["show_description", "show_status_message", "word_wrap"]
        for index, opt in enumerate(text_checkboxes):
            self.checks[opt] = IntVar()
            c = Checkbutton(text_options_frame, text=self.pretty_name(opt), variable=self.checks[opt])
            c.grid(row=len(text_checkboxes) + 1 + index / 2, column=index % 2)  # 2 checkboxes per row
            if getattr(self.options, opt):
                c.select()

            # Disable letting the user set the message duration if the show description option is disabled
            if opt == "show_description" or opt == "show_status_message":
                c.configure(command=self.checkbox_callback)

        # Draw the other options box
        display_options_frame = LabelFrame(self.root, text="", padx=20, pady=20)
        display_options_frame.grid(row=1, column=0, padx=5, pady=5)
        next_row = 0

        for index, opt in enumerate(["game_version"]):
            Label(display_options_frame, text=self.pretty_name(opt)).grid(row=next_row)
            initialversion = StringVar()
            initialversion.set(getattr(self.options, opt))
            self.entries[opt] = ttk.Combobox(display_options_frame, values=self.game_versions, textvariable=initialversion, state='readonly')
            self.entries[opt].grid(row=next_row, column=1)
            next_row += 1

        for index, opt in enumerate(["framerate_limit", "size_multiplier"]):
            Label(display_options_frame, text=self.pretty_name(opt)).grid(row=next_row)
            self.entries[opt] = Entry(display_options_frame, validate="key", validatecommand=vcmd)
            self.entries[opt].grid(row=next_row, column=1)
            self.entries[opt].insert(0, getattr(self.options, opt))
            if opt in self.label_after_text:
                Label(display_options_frame, text=self.label_after_text[opt]).grid(row=next_row, column=2)
            next_row += 1

        # Generate text options by looping over option types
        for index, opt in enumerate(["item_details_link"]):
            Label(display_options_frame, text=self.pretty_name(opt)).grid(row=next_row)
            self.entries[opt] = Entry(display_options_frame)
            self.entries[opt].grid(row=next_row, column=1)
            self.entries[opt].insert(0, getattr(self.options, opt))
            next_row += 1

        # Generate buttons by looping over option types
        for index, opt in enumerate(["background_color", "text_color"]):
            self.buttons[opt] = Button(
                display_options_frame,
                text=self.pretty_name(opt),
                bg=getattr(self.options, opt),
                fg=self.opposite_color(getattr(self.options, opt)),
                command=lambda opt=opt: self.color_callback(opt)
            )
            self.buttons[opt].grid(row=len(self.entries), column=index)

        # Generate checkboxes, with special exception for show_description for message duration
        for index, opt in enumerate(
                ["enable_mouseover", "show_floors", "show_rerolled_items", "show_health_ups",
                 "show_space_items", "show_blind_icon", "make_items_glow", "blck_cndl_mode",
                 "custom_title_enabled"]):
            self.checks[opt] = IntVar()
            c = Checkbutton(display_options_frame, text=self.pretty_name(opt), variable=self.checks[opt])
            c.grid(row=len(self.entries) + 1 + index / 2, column=index % 2) # 2 checkboxes per row
            if getattr(self.options, opt):
                c.select()
            if opt == "custom_title_enabled":
                c.configure(command=self.checkbox_callback)
            next_row += len(self.entries) / 2 + 1

        # Generate label for custom title
        Label(display_options_frame, text=self.pretty_name("custom_title")).grid(row=next_row)
        self.entries["custom_title"] = Entry(display_options_frame)
        self.entries["custom_title"].grid(row=next_row, column=1)
        self.entries["custom_title"].insert(0, getattr(self.options, "custom_title"))
        next_row += 1

        # Draw the "Tournament Settings" box
        tournament_settings_frame = LabelFrame(self.root, text="Tournament Settings", padx=20, pady=20)
        tournament_settings_frame.grid(row=0, column=1, rowspan=2, sticky=N)
        next_row = 0

        for index, opt in enumerate(["change_server"]):
            self.checks[opt] = IntVar()
            c = Checkbutton(tournament_settings_frame, text=self.pretty_name(opt), variable=self.checks[opt], indicatoron=False)
            c.grid(row=next_row, column=0, pady=2)
            c.configure(command=self.checkbox_callback)
            if getattr(self.options, opt, False):
                c.select()
        next_row += 1

        # Generate text options by looping over option types
        for index, opt in enumerate(["trackerserver_url"]):
            self.labels[opt] = Label(tournament_settings_frame, text=self.pretty_name(opt))
            self.labels[opt].grid(row=next_row, pady=2)
            self.entries[opt] = Entry(tournament_settings_frame)
            self.entries[opt].grid(row=next_row, column=1, pady=2)
            self.entries[opt].insert(0, getattr(self.options, opt, ""))
            next_row += 1

        paddings = {"read_from_server": 5, "write_to_server": 120}
        callbacks = {"read_from_server":self.read_callback, "write_to_server":self.write_callback}
        for index, opt in enumerate(["read_from_server", "write_to_server"]):
            self.checks[opt] = IntVar()
            c = Checkbutton(tournament_settings_frame, text=self.pretty_name(opt), variable=self.checks[opt], indicatoron=False)
            c.grid(row=next_row, column=index, pady=2, padx=paddings[opt])
            c.configure(command=callbacks[opt])
            if getattr(self.options, opt, False):
                c.select()
        next_row += 1

        for index, opt in enumerate(["server_connect_label"]):
            self.labels[opt] = Label(self.root, text="", width=len(self.connection_labels["fail"]))
            self.labels[opt].grid(row=next_row, pady=2, columnspan=2, in_=tournament_settings_frame)
            next_row += 1

        for index, opt in enumerate(["twitch_name"]):
            self.labels[opt] = Label(tournament_settings_frame, text=self.pretty_name(opt))
            self.labels[opt].grid(row=next_row, pady=2)
            self.entries[opt] = ttk.Combobox(tournament_settings_frame, width=40)
            self.entries[opt].set(getattr(self.options, opt, ""))
            self.entries[opt].bind("<<ComboboxSelected>>", self.trim_name)
            self.entries[opt].grid(row=next_row, column=1)
            next_row += 1


        # Generate text options by looping over option types
        for index, opt in enumerate(["read_delay", "trackerserver_authkey"]):
            self.labels[opt] = Label(tournament_settings_frame, text=self.pretty_name(opt))
            self.labels[opt].grid(row=next_row, pady=2)
            self.entries[opt] = Entry(tournament_settings_frame)
            self.entries[opt].grid(row=next_row, column=1, pady=2)
            self.entries[opt].insert(0, getattr(self.options, opt, ""))
            next_row += 1

        def authkey_fn():
            self.entries["trackerserver_authkey"].delete(0, last=END)
            twitch_client_id = self.get_server_twitch_client_id()
            if twitch_client_id is not None:
                webbrowser.open("https://api.twitch.tv/kraken/oauth2/authorize?response_type=token&client_id=" + twitch_client_id + "&redirect_uri=" +
                                self.entries['trackerserver_url'].get() + "/tracker/setup&scope=", autoraise=True)
            else:
                # TODO: show an error
                pass

        self.buttons["authkey_button"] = Button(
            tournament_settings_frame,
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

        # We're going to jump through a lot of hoops so we can position the options window on top of the tracker...
        # ... WITHOUT going off the edge of the screen

        # First we start out placing ourselves at the tracker's position
        x_pos = getattr(self.options, "x_position")
        y_pos = getattr(self.options, "y_position")

        # Now we make ourselves invisible and fullscreen (this is a hack to measure the size and position of the monitor)
        # We can't use the "screenwidth" and "screenheight" functions because they only give info on the primary display!
        self.root.geometry('+%d+%d' % (x_pos, y_pos))
        self.root.attributes("-alpha", 00)
        if platform.system() == "Windows":
            self.root.state("zoomed")
            self.root.update()
        else:
            self.root.attributes("-fullscreen", True)
            # For some reason using 'update' here affects the actual window height we want to get later
            self.root.update_idletasks()

        # Our current width and height are now our display's width and height
        screen_width = self.root.winfo_width()
        screen_height = self.root.winfo_height()

        # Get the upper left corner of the monitor
        origin_x = self.root.winfo_x()
        origin_y = self.root.winfo_y()

        # Now we get out of invisible fullscreen mode
        self.root.attributes("-alpha", 0xFF)
        if platform.system() == "Windows":
            self.root.state("normal")
        else:
            self.root.attributes("-fullscreen", False)
            self.root.update()

        # Here's the actual size of the window we're drawing
        window_width = self.root.winfo_width()
        window_height = self.root.winfo_height()

        # Now we can make sure we don't go off the sides
        max_x = origin_x + screen_width - window_width - 50
        max_y = origin_y + screen_height - window_height - 50

        x_pos = min(x_pos, max_x)
        y_pos = min(y_pos, max_y)

        # Clamp origin after clamping the other side, so that if our window is too big we lose the bottom/right instead of top/left
        x_pos = max(x_pos, origin_x)
        y_pos = max(y_pos, origin_y)

        self.root.geometry('+%d+%d' % (x_pos, y_pos))
        self.root.update()

        self.root.focus_force()

        # We're polling this queue for network results 10 times per second. This avoids blocking the main thread when we talk to the server
        self.root.after(100, self.process_network_results())

        # Start the main loop
        mainloop()

