""" This module handles everything related to the tracker behaviour. """
import json     # For importing the items and options
import urllib2  # For checking for updates to the item tracker
import logging  # For logging

# Import item tracker specific code
from view_controls.view import DrawingTool
from game_objects.item  import Item
from game_objects.state  import TrackerState, TrackerStateEncoder
from log_parser import LogParser
from options import Options


class IsaacTracker(object):
    """ The main class of the program """
    def __init__(self, logging_level=logging.INFO, read_delay=1):
        self.read_delay = read_delay
        self.file_prefix = "../"


        self.log = logging.getLogger("tracker")
        # This will erase our tracker log file from previous runs
        self.log.addHandler(logging.FileHandler(self.file_prefix + "tracker_log.txt", mode='w'))
        self.log.setLevel(logging_level)

        # Load items info
        with open(self.file_prefix + "items.json", "r") as items_file:
            Item.items_info = json.load(items_file)
        # Load options
        Options().load_options(self.file_prefix + "options.json")

    def __del__(self):
        Options().save_options(self.file_prefix + "options.json")

    def check_for_update(self):
        """ Returns text to put in the title bar """
        try:
            latest = "https://api.github.com/repos/Hyphen-ated/RebirthItemTracker/releases/latest"
            github_info_json = urllib2.urlopen(latest).read()
            info = json.loads(github_info_json)
            latest_version = info["name"]

            with open(self.file_prefix + 'version.txt', 'r') as f:
                current_version = f.read()
                title_text = " v" + current_version
                if latest_version != current_version:
                    title_text += " (new version available)"
                return title_text
        except Exception as e:
            self.log.debug("Failed to find update info: " + e.message)
        return ""

    def run(self):
        """ The main routine which controls everything """

        update_notifier = self.check_for_update()
        framecount = 0

        # Create drawing tool to use to draw everything - it'll create its own screen
        drawing_tool = DrawingTool(self.file_prefix)
        drawing_tool.set_window_title(update_notifier, "")
        parser = LogParser(self.file_prefix)
        opt = Options()
        log = logging.getLogger("tracker")

        done = False
        log_found = False
        state = None
        read_from_server = opt.read_from_server
        write_to_server = opt.write_to_server
        delay = self.read_delay
        state_version = -1
        twitch_username = None

        while not done:

            # Check for events and handle them
            done = drawing_tool.handle_events()
            # A change means the user has (de)activated an option
            if opt.read_from_server != read_from_server\
            or opt.twitch_name != twitch_username:
                # By setting the framecount to 0 we ensure we'll refresh the state right away
                framecount = 0
                twitch_username = opt.twitch_name
                read_from_server = opt.read_from_server
                # Also restart version count if we go back and forth from log.txt to server
                if read_from_server:
                    state_version = -1
                    # show who we are watching in the title bar
                    drawing_tool.set_window_title(update_notifier, twitch_username)
                else:
                    drawing_tool.set_window_title(update_notifier, "")
            if opt.write_to_server and opt.write_to_server != write_to_server:
                framecount = 0
                write_to_server = True
                # Will force writing the correct state, as the parser uses the same
                # state during its lifetime
                if state != None:
                    state.modified = True
            if not opt.write_to_server:
                write_to_server = False

            if opt.read_from_server:
                # Change the delay for polling, as we probably don't want to fetch it every second
                delay = opt.read_delay
            else:
                delay = self.read_delay


            # Now we re-process the log file to get anything that might have loaded;
            # do it every read_delay seconds (making sure to truncate to an integer
            # or else it might never mod to 0)
            if (framecount % int(Options().framerate_limit * delay) == 0):
                # Let the parser do his thing and give us a state
                if opt.read_from_server:
                    base_url = opt.trackerserver_url + "/tracker/api/user/" + opt.twitch_name
                    try:
                        json_version = urllib2.urlopen(base_url + "/version").read()
                        if int(json_version) > state_version:
                            # FIXME better handling of 404 error ?
                            json_state = urllib2.urlopen(base_url).read()
                            json_dict = json.loads(json_state)
                            state = TrackerState.from_json(json_dict)
                            state_version = int(json_version)
                    except Exception:
                        state = None
                        log.error("Couldn't load state from server")
                        import traceback
                        log.error(traceback.format_exc())
                else:
                    state = parser.parse()
                    if state != None and write_to_server and state.modified:
                        opener = urllib2.build_opener(urllib2.HTTPHandler)
                        put_url = opt.trackerserver_url + "/tracker/api/update/" + opt.trackerserver_authkey
                        json_string = json.dumps(state, cls=TrackerStateEncoder, sort_keys=True)
                        request = urllib2.Request(put_url,
                                                  data=json_string)
                        request.add_header('Content-Type', 'application/json')
                        request.get_method = lambda: 'PUT'
                        try:
                            url = opener.open(request)
                        except Exception:
                            log.error("ERROR: Couldn't store state to server")

            # We got a state, now we draw it
            drawing_tool.draw_state(state)
            if state == None:
                if read_from_server:
                    drawing_tool.write_message("Unable to read state from server. Please verify "
                                               "your options setup and tracker_log.txt", True)
                else:
                    drawing_tool.write_message("log.txt not found. Put the RebirthItemTracker "
                                               "folder inside the isaac folder, next to log.txt", True)


            drawing_tool.tick()
            framecount += 1


def main():
    """ Main """
    try:
        # Pass "logging.DEBUG" in debug mode
        rt = IsaacTracker()
        rt.run()
    except Exception:
        import traceback
        errmsg = traceback.format_exc()
        #print it to stdout for dev troubleshooting, log it to a file for production
        print(errmsg)
        logging.getLogger("tracker").error(errmsg)

if __name__ == "__main__":
    main()
