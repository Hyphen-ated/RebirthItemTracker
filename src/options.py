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

    def load_missing_defaults(self, filename):
        with open(filename, "r") as json_file:
            defaults = json.load(json_file)
            for k,v in defaults.items():
                if k not in self._shared_state:
                    self._shared_state[k] = v
