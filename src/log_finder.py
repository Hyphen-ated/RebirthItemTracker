import logging
import os, platform
from options import Options


class LogFinder(object):
    def __init__(self):
        self.log = logging.getLogger("tracker")

    def find_log_file(self, wdir_prefix=".."):
        """
        Try to find the game log file
        Returns a string path, or None if we couldn't find it
        """
        logfile_location = ""
        version_path_fragment = Options().game_version
        if version_path_fragment == "Antibirth":
            version_path_fragment = "Rebirth"

        if platform.system() == "Windows":
            logfile_location = os.environ['USERPROFILE'] + '/Documents/My Games/Binding of Isaac {}/'
        elif platform.system() == "Linux":
            logfile_location = os.getenv('XDG_DATA_HOME', os.path.expanduser('~') + '/.local/share') + '/binding of isaac {}/'
            version_path_fragment = version_path_fragment.lower()
        elif platform.system() == "Darwin":
            logfile_location = os.path.expanduser('~') + '/Library/Application Support/Binding of Isaac {}/'

        logfile_location = logfile_location.format(version_path_fragment)

        for check in (wdir_prefix + '../log.txt', logfile_location + 'log.txt'):
            if os.path.isfile(check):
                return logfile_location + 'log.txt'

        self.log.error("Couldn't find log.txt in " + logfile_location)
        return None
