# Imports
import json     # For importing the items and options
import urllib2  # For checking for updates to the item tracker
import logging  # For logging

# Import item tracker specific code
from view_controls.view import DrawingTool
from game_objects.item  import Item
from log_parser import LogParser
from options import Options


# The main class of the program
class IsaacTracker(object):
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




    # Returns text to put in the title bar
    def check_for_update(self):
        try:
            github_info_json = urllib2.urlopen("https://api.github.com/repos/Hyphen-ated/RebirthItemTracker/releases/latest").read()
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

        update_notifier = self.check_for_update()
        framecount = 0

        # Create drawing tool to use to draw everything - it'll create its own screen
        drawing_tool = DrawingTool("Rebirth Item Tracker" + update_notifier,
                                        self.file_prefix)
        parser = LogParser(self.file_prefix)

        done = False
        log_found = False


        while not done:

            # Check for events and handle them
            done = drawing_tool.handle_events()

            # Now we re-process the log file to get anything that might have loaded;
            # do it every read_delay seconds (making sure to truncate to an integer
            # or else it might never mod to 0)
            if framecount % int(Options().framerate_limit * self.read_delay) == 0:
                # Let the parser do his thing and give us a state
                state = parser.parse()
                if state != None:
                    log_found = True

            if not log_found:
                drawing_tool.write_message("log.txt not found. Put the RebirthItemTracker "
                                                "folder inside the isaac folder, next to log.txt", True)
            else:
                drawing_tool.draw_state(state)

            drawing_tool.tick()
            framecount += 1


# Main
def main():
    try:
        # Pass "logging.DEBUG" in debug mode
        rt = IsaacTracker()
        rt.run()
    except Exception:
        import traceback
        logging.getLogger("tracker").error(traceback.format_exc())

if __name__ == "__main__":
    main()
