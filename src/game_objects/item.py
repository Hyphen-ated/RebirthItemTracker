"""This module handles anything related to items and their characteristics"""

class Item(object):
    """This class represent an Item in the game, and handles its properties"""

    # This will be needed by both the log reader and the serializer,
    # it should be static
    items_info = {}

    @staticmethod
    def get_item_info(item_id):
        """Pad the id and look for its informations in the loaded dictionary"""
        id_padded = item_id.zfill(3)
        return Item.items_info[id_padded]

    def __init__(self, item_id, floor, starting_item):
        self.item_id       = item_id
        self.floor         = floor # The floor the item was found on
        self.was_rerolled  = False
        # Is this a starting item ?
        self.starting_item = starting_item
        # This shouldn't be serialized
        self.info          = Item.get_item_info(item_id)

    def rerolled(self):
        """Mark the item as rerolled"""
        # Spacebar items can't be re-rolled by a D4, dice room, etc.
        if not self.info.get(ItemProperty.SPACE, False):
            self.was_rerolled = True

    @property
    def name(self):
        """ Return Item's name"""
        return self.info[ItemProperty.NAME]

    def generate_item_description(self):
        """ Generate the item description from its stat"""
        desc        = ""
        text        = self.info.get("text")
        dmg         = self.info.get(Stat.DMG)
        dmg_x       = self.info.get(Stat.DMG_X)
        delay       = self.info.get(Stat.DELAY)
        delay_x     = self.info.get(Stat.DELAY_X)
        health      = self.info.get(Stat.HEALTH)
        speed       = self.info.get(Stat.SPEED)
        shot_speed  = self.info.get(Stat.SHOT_SPEED)
        tear_range  = self.info.get(Stat.TEAR_RANGE)
        height      = self.info.get(Stat.HEIGHT)
        tears       = self.info.get(Stat.TEARS)
        soul_hearts = self.info.get(Stat.SOUL_HEARTS)
        sin_hearts  = self.info.get(Stat.SIN_HEARTS)
        if dmg:
            desc += dmg + " dmg, "
        if dmg_x:
            desc += "x" + dmg_x + " dmg, "
        if tears:
            desc += tears + " tears, "
        if delay:
            desc += delay + " tear delay, "
        if delay_x:
            desc += "x" + delay_x + " tear delay, "
        if shot_speed:
            desc += shot_speed + " shotspeed, "
        if tear_range:
            desc += tear_range + " range, "
        if height:
            desc += height + " height, "
        if speed:
            desc += speed + " speed, "
        if health:
            desc += health + " health, "
        if soul_hearts:
            desc += soul_hearts + " soul hearts, "
        if sin_hearts:
            desc += sin_hearts + " sin hearts, "
        if text:
            desc += text
        if desc.endswith(", "):
            desc = desc[:-2]
        if len(desc) > 0:
            desc = ": " + desc
        return desc

    def __eq__(self,other):
        if not isinstance(other, Item):
            return False
        return other is not None and self.item_id == other.item_id

    def __ne__(self,other):
        if not isinstance(other, Item):
            return True
        return other is None or self.item_id != other.item_id

    def __hash__(self):
        return hash(self.item_id)

# FIXME a namedtuple is probably enough instead of a class
class Stat(object): # This is a subset of all available ItemProperty's
    """ Player stat constants (keys to player_stats and player_stats_display)"""
    DMG         = "dmg"
    DMG_X       = "dmg_x"
    DELAY       = "delay"
    DELAY_X     = "delay_x"
    HEALTH      = "health"
    SPEED       = "speed"
    SHOT_SPEED  = "shot_speed"
    TEAR_RANGE  = "range"
    HEIGHT      = "height"
    TEARS       = "tears"
    SOUL_HEARTS = "soul_hearts"
    SIN_HEARTS  = "sin_hearts"
    IS_GUPPY    = "guppy"
    LIST        = [DMG, DELAY, SPEED, SHOT_SPEED, TEAR_RANGE, HEIGHT, TEARS] # Used for init and reset - does not have all stats yet

class ItemProperty(object):
    """ Properties that items from items.json can have (these can have any stat)"""
    NAME              = "name"
    SHOWN             = "shown"
    GUPPY             = "guppy"
    SPACE             = "space"
    HEALTH_ONLY       = "health_only"
    IN_SUMMARY        = "in_summary"
    SUMMARY_NAME      = "summary_name"
    # An item that needs to be present for this item to be mentioned in the summary;
    # can only be one item right now
    SUMMARY_CONDITION = "summary_condition"
