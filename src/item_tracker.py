""" This module handles everything related to the tracker behaviour. """
import json     # For importing the items and options
import os
import shutil
import time     # For referencing the "state" timestamp that we get from the server
import urllib2  # For checking for updates to the item tracker
import traceback

# Import item tracker specific code
from view_controls.view import DrawingTool, Event
from game_objects.item  import Item, ItemInfo
from game_objects.state  import TrackerState, TrackerStateEncoder
from log_parser import LogParser
from log_finder import LogFinder
from options import Options
from error_stuff import log_error, log_dir

wdir_prefix = log_dir # this is "../". doing it this way to avoid import cycle

class IsaacTracker(object):
    """ The main class of the program """
    def __init__(self):

        new_updater_dir = wdir_prefix + "update_scratchdir/updater-lib"
        if os.path.exists(new_updater_dir):
            # We found a new version of the updater, from when the updater presumably just ran
            old_updater_dir = wdir_prefix + "updater-lib"
            if os.path.exists(old_updater_dir):
                shutil.rmtree(old_updater_dir)
            shutil.copytree(new_updater_dir, old_updater_dir)
            shutil.rmtree(wdir_prefix + "update_scratchdir")

        # Load items/trinkets info
        with open(wdir_prefix + "items.json", "r") as items_file:
            Item.items_info = json.load(items_file)
        ItemInfo.check_item_keys(Item.items_info, "items.json")

        with open(wdir_prefix + "items_abplus.json", "r") as abplus_items_file:
            Item.abplus_items_info = json.load(abplus_items_file)
        ItemInfo.check_item_keys(Item.abplus_items_info, "items_abplus.json")    
        
        with open(wdir_prefix + "items_custom.json", "r") as custom_items_file:
            Item.custom_items_info = json.load(custom_items_file)
        Item.determine_custom_item_names()
        ItemInfo.check_item_keys(Item.custom_items_info, "items_custom.json")


    # Load version
        with open(wdir_prefix + 'version.txt', 'r') as f:
            self.tracker_version = f.read()

        # Load options
        Options().load_options(wdir_prefix + "options.json")
        defaults_path = "options_default.json"
        # If we're running in production, this file will be in our dir.
        # If we're running from source, it will be up a level
        if not os.path.exists(defaults_path):
            defaults_path = wdir_prefix + defaults_path
        Options().load_missing_defaults(defaults_path)


    def run(self):
        """ The main routine which controls everything """
        framecount = 0

        # Create drawing tool to use to draw everything - it'll create its own screen
        drawing_tool = DrawingTool(wdir_prefix)
        drawing_tool.set_window_title_info(update_notifier=(" v" + self.tracker_version))
        opt = Options()

        parser = LogParser(wdir_prefix, self.tracker_version, LogFinder())

        event_result = None
        state = None
        custom_title_enabled = opt.custom_title_enabled
        read_from_server = opt.read_from_server
        write_to_server = opt.write_to_server
        game_version = opt.game_version
        state_version = -1
        twitch_username = None
        new_states_queue = []
        screen_error_message = None
        retry_in = 0
        update_timer = opt.log_file_check_seconds
        last_game_version = None

        while event_result != Event.DONE:
            # Check for events and handle them
            event_result = drawing_tool.handle_events()

            # The user checked or unchecked the "Custom Title Enabled" checkbox
            if opt.custom_title_enabled != custom_title_enabled:
                custom_title_enabled = opt.custom_title_enabled
                drawing_tool.update_window_title()

            # The user started or stopped watching someone from the server (or they started watching a new person from the server)
            if opt.read_from_server != read_from_server or opt.twitch_name != twitch_username:
                twitch_username = opt.twitch_name
                read_from_server = opt.read_from_server
                new_states_queue = []
                # Also restart version count if we go back and forth from log.txt to server
                if read_from_server:
                    state_version = -1
                    state = None
                    # Change the delay for polling, as we probably don't want to fetch it every second
                    update_timer_override = 2
                    # Show who we are watching in the title bar
                    drawing_tool.set_window_title_info(watching=True, watching_player=twitch_username, updates_queued=len(new_states_queue))
                else:
                    drawing_tool.set_window_title_info(watching=False)
                    update_timer_override = 0

            # The user started or stopped broadcasting to the server
            if opt.write_to_server != write_to_server:
                write_to_server = opt.write_to_server
                drawing_tool.set_window_title_info(uploading=opt.write_to_server)

            if opt.game_version != game_version:
                parser.reset()
                game_version = opt.game_version

            # Force refresh state if we updated options or if we need to retry
            # to contact the server.
            if (event_result == Event.OPTIONS_UPDATE or
                (screen_error_message is not None and retry_in == 0)):
                # By setting the framecount to 0 we ensure we'll refresh the state right away
                framecount = 0
                screen_error_message = None
                retry_in = 0
                # Force updates after changing options
                if state is not None:
                    state.modified = True

            # normally we check for updates based on how the option is set
            # when doing network stuff, this can be overridden
            update_delay = opt.log_file_check_seconds
            if update_timer_override != 0:
                update_delay = update_timer_override
                
            # Now we re-process the log file to get anything that might have loaded;
            # do it every update_timer seconds (making sure to truncate to an integer
            # or else it might never mod to 0)
            frames_between_checks = int(Options().framerate_limit * update_delay)
            if frames_between_checks <= 0:
                frames_between_checks = 1
            
            if framecount % frames_between_checks == 0:
                if retry_in != 0:
                    retry_in -= 1
                # Let the parser do his thing and give us a state
                if opt.read_from_server:
                    base_url = opt.trackerserver_url + "/tracker/api/user/" + opt.twitch_name
                    json_dict = None
                    try:
                        json_version = urllib2.urlopen(base_url + "/version").read()
                        if int(json_version) > state_version:
                            # FIXME better handling of 404 error ?
                            json_state = urllib2.urlopen(base_url).read()
                            json_dict = json.loads(json_state, "utf-8")
                            new_state = TrackerState.from_json(json_dict)
                            if new_state is None:
                                raise Exception("server gave us empty state")
                            state_version = int(json_version)
                            new_states_queue.append((state_version, new_state))
                            drawing_tool.set_window_title_info(updates_queued=len(new_states_queue))
                    except Exception:
                        state = None
                        log_error("Couldn't load state from server\n" + traceback.format_exc())
                        if json_dict is not None:
                            if "tracker_version" in json_dict:
                                their_version = json_dict["tracker_version"]
                            else:
                                # This is the only version that can upload to the server but doesn't include a version string
                                their_version = "0.10-beta1"

                            if their_version != self.tracker_version:
                                screen_error_message = "They are using tracker version " + their_version + " but you have " + self.tracker_version
                else:
                    force_draw = state and state.modified
                    state = parser.parse()
                    if force_draw and state is not None:
                        state.modified = True
                    if write_to_server and not opt.trackerserver_authkey:
                        screen_error_message = "Your authkey is blank. Get a new authkey in the options menu and paste it into the authkey text field."
                    if state is not None and write_to_server and state.modified and screen_error_message is None:
                        opener = urllib2.build_opener(urllib2.HTTPHandler)
                        put_url = opt.trackerserver_url + "/tracker/api/update/" + opt.trackerserver_authkey
                        json_string = json.dumps(state, cls=TrackerStateEncoder, sort_keys=True)
                        request = urllib2.Request(put_url,
                                                  data=json_string)
                        request.add_header('Content-Type', 'application/json')
                        request.get_method = lambda: 'PUT'
                        try:
                            result = opener.open(request)
                            result_json = json.loads(result.read())
                            updated_user = result_json["updated_user"]
                            if updated_user is None:
                                screen_error_message = "The server didn't recognize you. Try getting a new authkey in the options menu."
                            else:
                                screen_error_message = None
                        except Exception as e:
                            log_error("ERROR: Couldn't send item info to server\n" + traceback.format_exc())
                            screen_error_message = "ERROR: Couldn't send item info to server, check tracker_log.txt"
                            # Retry to write the state in 10*update_timer (aka 10 sec in write mode)
                            retry_in = 10

            # Check the new state at the front of the queue to see if it's time to use it
            if len(new_states_queue) > 0:
                (state_timestamp, new_state) = new_states_queue[0]
                current_timestamp = int(time.time())
                if current_timestamp - state_timestamp >= opt.read_delay or opt.read_delay == 0 or state is None:
                    state = new_state
                    new_states_queue.pop(0)
                    drawing_tool.set_window_title_info(updates_queued=len(new_states_queue))

            if state is None and screen_error_message is None:
                if read_from_server:
                    screen_error_message = "Unable to read state from server. Please verify your options setup and tracker_log.txt"
                    # Retry to read the state in 5*update_timer (aka 10 sec in read mode)
                    retry_in = 5
                else:
                    screen_error_message = "log.txt for " + opt.game_version + " not found. Make sure you have the right game selected in the options."

            if screen_error_message is not None:
                drawing_tool.write_error_message(screen_error_message)
            else:
                # We got a state, now we draw it
                drawing_tool.draw_state(state,framecount)

            # if we're watching someone and they change their game version, it can require us to reset
            if state and last_game_version != state.game_version:
                drawing_tool.reset_options()
                last_game_version = state.game_version

            drawing_tool.tick()
            framecount += 1

        # Main loop finished; program is exiting
        drawing_tool.save_window_position()
        Options().save_options(wdir_prefix + "options.json")

def main():
    """ Main """
    try:
        # Pass "logging.DEBUG" in debug mode
        rt = IsaacTracker()
        rt.run()
    except Exception:
        log_error(traceback.format_exc())

if __name__ == "__main__":
    main()
