""" This module handles everything related to (De)serialization. """
import logging

from error_stuff import log_error


class Serializable(object):
    """
    Base class for a serializable object.
    Derived class must define a class variable 'serialize' containing a list of
    (member, type) tuple to (de)serialize.
    """
    serialize = []

    def to_json(self):
        """ Export the class to json, according to the derived 'serialize' informations """
        result = dict()
        for key, value_type in type(self).serialize:
            if issubclass(value_type, Serializable):
                result[key] = getattr(self, key).to_json()
            else:
                result[key] = getattr(self, key)
        return result

    @staticmethod
    def from_valid_json(json_dic, *args):
        """
        This function has to be implemented by derived class,
        which can assumes that keys in dictionary exist and have the right type
        """
        raise NotImplementedError

    @classmethod
    def from_json(cls, json_dic, *args):
        """
        This function does some type checking on expected attributes,
        and then calls the derived factory method
        """
        log = logging.getLogger("tracker")
        if not isinstance(json_dic, dict):
            log_error("ERROR: json_dic is not a dictionary")
            return None
        # Basic type check
        for key, value_type in cls.serialize:
            if key not in json_dic:
                log_error("ERROR: key "+ key + " not found in dictionary")
                return None
            if not isinstance(json_dic[key], value_type):
                log_error("ERROR: key " + key + " is not a " + value_type.__name__ + " as expected")
                return None
        return cls.from_valid_json(json_dic, *args)
