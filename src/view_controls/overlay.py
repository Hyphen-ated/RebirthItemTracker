"""
This module deals with everything related to the overlay text generated,
as well as formating how to display stats
"""
from game_objects.item  import ItemInfo

class Overlay(object):
    """The main class to handle output to overlay text files"""
    def __init__(self, prefix, tracker_state):
        self.state = tracker_state
        self.prefix = prefix

    @staticmethod
    def format_value(value):
        """Format a float value for displaying"""
        # NOTE this is not only used in this class
        # Round to 2 decimal places then ignore trailing zeros and trailing periods
        # Doing just 'rstrip("0.")' breaks on "0.00"
        display = format(value, ".2f").rstrip("0").rstrip(".")

        # For example, set "0.6" to ".6"
        if abs(value) < 1 and value != 0:
            display = display.lstrip("0")

        if value > -0.00001:
            display = "+" + display
        return display

    @staticmethod
    def format_transformation(guppy_set):
        """Format a guppy_set for displaying"""
        # NOTE this is not only used in this class
        if len(guppy_set) >= 3:
            return "yes"
        else:
            return str(len(guppy_set))		

    def update_stats(self, stat_list=None):
        """
        Update file content for a subset (or all) the player's stats.
        stat_list provide the subset of stats to update, if None it will update everything
        """
        if stat_list is None:
            stat_list = ItemInfo.stat_list + ["guppy"]
        for stat in stat_list:
            display = ""
            if stat == "guppy":
                display = Overlay.format_transformation(self.state.guppy_set)
            elif stat == "beelzebub":
				display = Overlay.format_transformation(self.state.beelzebub_set)
            elif stat == "bob":
				display = Overlay.format_transformation(self.state.bob_set)
            elif stat == "conjoined":
				display = Overlay.format_transformation(self.state.conjoined_set)
            elif stat == "funguy":
				display = Overlay.format_transformation(self.state.funguy_set)
            elif stat == "leviathan":
				display = Overlay.format_transformation(self.state.leviathan_set)
            elif stat == "ohcrap":
				display = Overlay.format_transformation(self.state.ohcrap_set)
            elif stat == "seraphim":
				display = Overlay.format_transformation(self.state.seraphim_set)
            elif stat == "spun":
				display = Overlay.format_transformation(self.state.spun_set)
            elif stat == "yesmother":
				display = Overlay.format_transformation(self.state.yesmother_set)
            elif stat == "superbum":
				display = Overlay.format_transformation(self.state.superbum_set)
            else:
                display = Overlay.format_value(self.state.player_stats[stat])
            with open(self.prefix + "overlay text/" + stat + ".txt", "w+") as sfile:
                sfile.write(display)

    def update_last_item_description(self):
        """Update the overlay file for item pickup description"""
        item = self.state.last_item
        desc = item.info.name
        desc += ": " + item.generate_item_description()
        with open(self.prefix + "overlay text/itemInfo.txt", "w+") as sfile:
            sfile.write(desc)

    def update_seed(self):
        """Update the overlay file the seed"""
        with open(self.prefix + "overlay text/seed.txt", "w+") as sfile:
            sfile.write(self.state.seed)


