""" ItemTracker's option module """
import json

class Options(object):
    """ Options' singleton """
    _shared_state = {}
    def __init__(self):
        self.__dict__ = self._shared_state

    def load_options(self, filename):
        """ Load options from file """
        with open(filename, "r") as json_file:
            self._shared_state.update(json.load(json_file))

    def save_options(self, filename):
        """ Save current options to file """
        # Stop users from leaving the server options on
        self._shared_state['read_from_server'] = False
        self._shared_state['write_to_server'] = False
        with open(filename, "w") as json_file:
            json.dump(self._shared_state, json_file, indent=3, sort_keys=True)
