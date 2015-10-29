from floor import Curse,Floor

class Item(object):
    def __init__(self,itemID,floor,item_info,starting_item):
        self.id=itemID
        self.floor=floor #floor item was found on
        self.was_rerolled=False
        self.info=item_info
        self.starting_item = starting_item
    
    def rerolled(self):
        #Space items can't be re-rolled that I know of
        if not self.info.get(ItemProperty.SPACE,False):
            self.was_rerolled = True
    
    @property
    def name(self):
        return self.info[ItemProperty.NAME]
            
    def generate_item_description(self):
        desc = ""
        text = self.info.get("text")
        dmg = self.info.get(Stat.DMG)
        dmgx = self.info.get(Stat.DMG_X)
        delay = self.info.get(Stat.DELAY)
        delayx = self.info.get(Stat.DELAY_X)
        health = self.info.get(Stat.HEALTH)
        speed = self.info.get(Stat.SPEED)
        shotspeed = self.info.get(Stat.SHOT_SPEED)
        tearrange = self.info.get(Stat.TEAR_RANGE)
        height = self.info.get(Stat.HEIGHT)
        tears = self.info.get(Stat.TEARS)
        soulhearts = self.info.get(Stat.SOUL_HEARTS)
        sinhearts = self.info.get(Stat.SIN_HEARTS)
        if dmg:
            desc += dmg + " dmg, "
        if dmgx:
            desc += "x" + dmgx + " dmg, "
        if tears:
            desc += tears + " tears, "
        if delay:
            desc += delay + " tear delay, "
        if delayx:
            desc += "x" + delayx + " tear delay, "
        if shotspeed:
            desc += shotspeed + " shotspeed, "
        if tearrange:
            desc += tearrange + " range, "
        if height:
            desc += height + " height, "
        if speed:
            desc += speed + " speed, "
        if health:
            desc += health + " health, "
        if soulhearts:
            desc += soulhearts + " soul hearts, "
        if sinhearts:
            desc += sinhearts + " sin hearts, "
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
        return other is not None and self.id==other.id
    
    def __ne__(self,other):
        if not isinstance(other, Item):
            return True
        return other is None or self.id!=other.id

# Player stat constants (keys to player_stats and player_stats_display)
# This is a subset of all available ItemPropertys
class Stat:
    DMG = "dmg"
    DMG_X = "dmgx"
    DELAY = "delay"
    DELAY_X = "delayx"
    HEALTH = "health"
    SPEED = "speed"
    SHOT_SPEED = "shotspeed"
    TEAR_RANGE = "range"
    HEIGHT = "height"
    TEARS = "tears"
    SOUL_HEARTS = "soulhearts"
    SIN_HEARTS = "sinhearts"
    IS_GUPPY = "guppy"
    # used for init and reset - does not have all stats yet
    LIST = [DMG, DELAY, SPEED, SHOT_SPEED, TEAR_RANGE, HEIGHT, TEARS]


# Properties that items from items.json can have
# additionally, those items can have any Stat
class ItemProperty:
    NAME = "name"
    SHOWN = "shown"
    GUPPY = "guppy"
    SPACE = "space"
    HEALTH_ONLY = "healthonly"
    IN_SUMMARY = "inSummary"
    SUMMARY_NAME = "summaryName"
    # an item that needs to be present for this item to be mentioned
    # in the summary. can only be one item right now.
    SUMMARY_CONDITION = "summaryCondition"
    