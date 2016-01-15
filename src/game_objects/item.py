"""This module handles anything related to items and their characteristics"""

class Item(object):
    """This class represent an Item in the game, and handles its properties"""

    # This will be needed by both the log reader and the serializer,
    # it should be static
    items_info = {}

    def __init__(self, item_id, floor, starting_item):
        self.item_id = item_id
        # The floor the item was found on
        self.floor = floor
        # Was this item rerolled ?
        self.was_rerolled = False
        # Is this a starting item ?
        self.starting_item = starting_item
        # ItemInfo for the current item
        self.info = Item.get_item_info(item_id)

    def rerolled(self):
        """Mark the item as rerolled"""
        # Spacebar items can't be re-rolled by a D4, dice room, etc.
        if not self.info.space:
            self.was_rerolled = True

    @property
    def name(self):
        """ Return Item's name"""
        return self.info.name

    def generate_item_description(self):
        """ Generate the item description from its stat"""
        desc = ""
        text = self.info.text
        dmg = self.info.dmg
        dmg_x = self.info.dmg_x
        delay = self.info.delay
        delay_x = self.info.delay_x
        health = self.info.health
        speed = self.info.speed
        shot_speed = self.info.shot_speed
        tear_range = self.info.range
        height = self.info.height
        tears = self.info.tears
        soul_hearts = self.info.soul_hearts
        sin_hearts = self.info.sin_hearts
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

    def __eq__(self, other):
        if not isinstance(other, Item):
            return False
        return other is not None and self.item_id == other.item_id

    def __ne__(self, other):
        if not isinstance(other, Item):
            return True
        return other is None or self.item_id != other.item_id

    def __hash__(self):
        return hash(self.item_id)

    @staticmethod
    def get_item_info(item_id):
        """Pad the id and look for its informations in the loaded dictionary"""
        id_padded = item_id.zfill(3)
        return ItemInfo(Item.items_info[id_padded])

    @staticmethod
    def contains_info(item_id):
        """ Return true if this item exists in items_info """
        return item_id.zfill(3) in Item.items_info

class ItemInfo(dict):
    """
    dict wrapper for item infos.
    Properties and stats can be accessed using instance.my_stat, if it does not
    exist, None is returned.

    Here is a list of properties that may be available :
        Stats :
        - dmg
        - dmg_x
        - delay
        - delay_x
        - health
        - speed
        - shot_speed
        - range
        - height
        - tears
        - soul_hearts
        - sin_hearts
        Properties
        - guppy
        - name
        - shown
        - space
        - health_only
        - in_summary
        - summary_name
        # An item that needs to be present for this item to be mentioned in the summary;
        # can only be one item right now
        - summary_condition
    """
    stat_list = ["dmg", "delay", "speed", "shot_speed", "range", "height", "tears"]
    def __init__(self, values):
        super(ItemInfo, self).__init__(values)
        self.__dict__ = self

    def __getattr__(self, name):
        return None

    def __missing__(self, name):
        return self.__getattr__(name)

