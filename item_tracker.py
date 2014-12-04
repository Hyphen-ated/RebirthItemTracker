import time
import glob
import os
import pygame


# some general variable stuff, i guess
verbose = False
debug = True
seek = 0
framecount = 0
read_delay = 60


# just for debugging
def log_msg(msg, level):
  if level=="V" and verbose: print msg
  if level=="D" and debug: print msg


# initialize isaac stuff
item_name_map = {"1":"The Sad Onion","2":"The Inner Eye","3":"Spoon Bender","4":"Cricket's Head","5":"My Reflection","6":"Number One","7":"Blood of the Martyr","8":"Brother Bobby","9":"Skatole","10":"Halo of Flies","11":"1UP","12":"Magic Mushroom","13":"The Virus","14":"Roid Rage","15":"<3","16":"Raw Liver","17":"Skeleton Key","18":"A Dollar","19":"Boom!","20":"Transcendence","21":"The Compass","22":"Lunch","23":"Dinner","24":"Dessert","25":"Breakfast","26":"Rotten Meat","27":"Wooden Spoon","28":"The Belt","29":"Mom's Underwear","30":"Mom's Heels","31":"Mom's Lipstick","32":"Wire Coat Hanger","33":"The Bible","34":"The Book of Belial","35":"The Necronomicon","36":"The Poop","37":"Mr. Boom","38":"Tammy's Head","39":"Mom's Bra","40":"Kamikaze","41":"Mom's Pad:","42":"Bob's Rotten Head","44":"Teleport","45":"Yum Heart","46":"Lucky Foot","47":"Doctor's Remote","48":"Cupid's Arrow","49":"Shoop Da Whoop","50":"Steven","51":"Pentagram","52":"Dr. Fetus","53":"Magneto","54":"Treasure Map","55":"Mom's Eye","56":"Lemon Mishap","57":"Distant Admiration","58":"Book of Shadows","60":"The Ladder","62":"Charm of the Vampire","63":"The Battery","64":"Steam Sale","65":"Anarchist's Cookbook","66":"The Hourglass","67":"Sister Maggy","68":"Technology","69":"Chocolate Milk","70":"Growth Hormones","71":"Mini Mush","72":"Rosary","73":"Cube of Meat","74":"A Quarter","75":"PhD","76":"X-Ray Vision","77":"My Little Unicorn","78":"Book of Revelations","79":"The Mark","80":"The Pact","81":"Dead Cat","82":"Lord of the Pit","83":"The Nail","84":"We Need To Go Deeper","85":"Deck of Cards","86":"Monstro's Tooth","87":"Loki's Horns","88":"Little Chubby","89":"Spider Bite","90":"The Small Rock","91":"Spelunker Hat","92":"Super Bandage","93":"The Gamekid","94":"Sack of Pennies","95":"Robo-Baby","96":"Little C.H.A.D.","97":"The Book of Sin","98":"The Relic","99":"Little Gish","100":"Little Steven","101":"The Halo","102":"Mom's Bottle of Pills","103":"The Common Cold","104":"The Parasite","105":"The D6","106":"Mr. Mega","107":"Pinking Shears","108":"The Wafer","109":"Money = Power","110":"Mom's Contacts","111":"The Bean","112":"Guardian Angel","113":"Demon Baby","114":"Mom's Knife","115":"Ouija Board","116":"9 Volt","117":"Dead Bird","118":"Brimstone","119":"Blood Bag","120":"Odd Mushroom (Thin)","121":"Odd Mushroom (Thick)","122":"Whore of Babylon","123":"Monster Manual","124":"Dead Sea Scrolls","125":"Bobby - Bomb","126":"Razor Blade","127":"Forget Me Now","128":"Forever Alone","129":"Bucket of Lard","130":"A Pony","131":"Bomb Bag","132":"A Lump of Coal","133":"Guppy's Paw","134":"Guppy's Tail","135":"IV Bag","136":"Best Friend","137":"Remote Detonator","138":"Stigmata","139":"Mom's Purse","140":"Bob's Curse","141":"Pageant Boy","142":"Scapular","143":"Speed Ball","144":"Bum Friend","145":"Guppy's Head","146":"Prayer Card","147":"Notched Axe","148":"Infestation","149":"Ipecac","150":"Tough Love","151":"The Mulligan","152":"Technology 2","153":"Mutant Spider","154":"Chemical Peel","155":"The Peeper","156":"Habit","157":"Bloody Lust","158":"Crystal Ball","159":"Spirit of the Night","160":"Crack The Sky","161":"Ankh","162":"Celtic Cross","163":"Ghost Baby","164":"The Candle","165":"Cat-O-Nine-Tails","166":"D20","167":"Harlequin Baby","168":"Epic Fetus","169":"Polyphemus","170":"Daddy Longlegs","171":"Spider Butt","172":"Sacrificial Dagger","173":"Mitre","174":"Rainbow Baby","175":"Dad's Key","176":"Stem Cells","177":"Portable Slot","178":"Holy Water","179":"Fate","180":"The Black Bean","181":"White Pony","182":"Sacred Heart","183":"Toothpicks","184":"Holy Grail","185":"Dead Dove","186":"Blood Rights","187":"Guppy's Hairball","188":"Abel","189":"SMB Super Fan","190":"Pyro","191":"3 Dollar Bill","192":"Telepathy for Dummies","193":"MEAT!","194":"Magic 8 Ball","195":"Mom's Coin Purse","196":"Squeezy","197":"Jesus Juice","198":"Box","199":"Mom's Key","200":"Mom's Eyeshadow","201":"Iron Bar","202":"Midas Touch","203":"Humbleing Bundle","204":"Fanny pack","205":"Sharp plug","206":"The Guillotine","207":"Ball of Bandages","208":"Champion Belt","209":"Butt Bombs","210":"Gnawed Leaf","211":"Spiderbaby","212":"Guppy's Collar","213":"Lost Contact","214":"Anemic","215":"Goat Head","216":"Ceremonial Robes","217":"Mom's Wig","218":"Placenta","219":"Old Bandage","220":"Sad Bombs","221":"Rubber Cement","222":"Anti-Gravity","223":"Pyromaniac","224":"Cricket's Body","225":"Gimpy","226":"Black Lotus","227":"Piggy Bank","228":"Mom's Perfume:","229":"Monstro's Lung","230":"Abaddon","231":"Ball of Tar","232":"Stop Watch","233":"Tiny Planet","234":"Infestation 2","236":"E. Coli","237":"Death's Touch","238":"Key Piece #1","239":"Key Piece #2","240":"Experimental Treatment","241":"Contract From Below","242":"Infamy","243":"Trinity Shield","244":"Tech.5","245":"20/20","246":"Blue Map","247":"BFFS!","248":"Hive Mind","249":"There's Options","250":"Bogo Bombs","251":"Starter Deck","252":"Little Baggy","253":"Magic Scab","254":"Blood Clot","255":"Screw","256":"Hot Bombs","257":"Fire Mind","258":"Missing No.","259":"Dark Matter","260":"Black Candle","261":"Proptosis","262":"Missing Page 2","264":"Smart Fly","265":"Dry Baby","266":"Juicy Sack","267":"Robo-Baby 2.0","268":"Rotten Baby","269":"Headless Baby","270":"Leech","271":"Mystery Sack","272":"BBF","273":"Bob's Brain","274":"Best Bud","275":"Lil' Brimstone","276":"Isaac's Heart","277":"Lil' Haunt","278":"Dark Bum","279":"Big Fan","280":"Sissy Long Legs","281":"Punching Bag","282":"How To Jump","283":"D100","284":"D4","285":"D10","286":"Blank Card","287":"Book of Secrets","288":"Box of Spiders","289":"Red Candle","290":"The Jar","291":"FLUSH!","292":"The Satanic Bible","293":"Head of Krampus","294":"Butter Bean","295":"Magic Fingers","296":"Converter","297":"Pandora's Box","298":"Unicorn Stump","299":"Taurus","300":"Aries","301":"Cancer","302":"Leo","303":"Virgo","304":"Libra","305":"Scorpio","306":"Sagittarius","307":"Capricorn","308":"Aquarius","309":"Pisces","310":"Eve's Mascara","311":"Judas' Shadow","312":"Maggy's Bow","313":"Holy Mantle","314":"Thunder Thighs","315":"Strange Attractor","316":"Cursed Eye","317":"Mysterious Liquid","318":"Gemini","319":"Cain's Other Eye","320":"???'s Only Friend","321":"Samson's Chains","322":"Mongo Baby","323":"Isaac's Tears","324":"Undefined","325":"Scissors","326":"Breath of Life","327":"The Polaroid","328":"The Negative","329":"The Ludovico Technique","330":"Soy Milk","331":"GodHead","332":"Lazarus' Rags","333":"The Mind","334":"The Body","335":"The Soul","336":"Dead Onion","337":"Broken Watch","338":"Boomerang","339":"Safety Pin","340":"Caffeine Pill","341":"Torn Photo","342":"Blue Cap","343":"Latch Key","344":"Match Book","345":"Synthoil","346":"A Snack"}
collected_items = []
seed = ""
# filter_list = {"105"}
use_items = {"65","111","136","33","286","186","42","34","78","287","58","97","338","288","326","294","164","296","160","158","284","285","283","166","105","175","124","85","47","291","127","93","145","133","293","66","282","323","135","290","40","56","295","102","39","41","123","86","37","77","83","35","147","297","107","130","36","177","146","126","289","137","292","325","49","171","38","192","44","324","298","84","181","45"}
guppy_use = {"133","148"}
health_ups = {"15","16","22","23","24","25","26","119","129","176","218","219","226","346"}
range_ups = {"29","30","31","339"}
filter_list = (use_items - guppy_use) | health_ups | range_ups

log_msg("Filtered items: %s" % ", ".join([item_name_map[id] for id in filter_list]),"D")

# image library stuff, from openbookproject.net
_image_library = {}
def get_image(path):
  global _image_library
  image = _image_library.get(path)
  if image == None:
    canonicalized_path = path.replace('/', os.sep).replace('\\', os.sep)
    image = pygame.image.load(canonicalized_path)
    scaled_image = pygame.transform.scale(image,(image.get_size()[0] * 2,image.get_size()[1] * 2))
    _image_library[path] = scaled_image
  return image


# initialize pygame system stuff
pygame.init()
screen = pygame.display.set_mode((800, 80))
done = False
clock = pygame.time.Clock()
my_font = pygame.font.SysFont("Arial", 16,bold=True)


while not done:
  # pygame logic
  for event in pygame.event.get():
    if event.type == pygame.QUIT:
      done = True

  screen.fill((25,25,25))
  clock.tick(60)

  # draw seed text:
  seed_text = my_font.render("Seed: %s" % seed, True, (255,255,255))
  screen.blit(seed_text,(2,2))

  # draw items on screen, excluding filtered items:
  for index,item in enumerate([x for x in collected_items if x not in filter_list]):
    screen.blit(get_image('collectibles/collectibles_%s.png' % item.zfill(3)), (64 * index,16))

  pygame.display.flip()

  framecount += 1

  # process log stuff every read_delay frames
  if framecount % read_delay == 0:
    # entire thing loaded into memory each loop -- see if maybe pruning log is possible for long sessions?
    content = ""
    try:
      with open('log.txt', 'r') as f:
        content = f.read()
    except Exception:
      log_msg("No file found, skipping to next loop","D")
      continue


    splitfile = content.splitlines()
    # return to start if seek passes the end of the file (usually b/c log file restarted)
    if seek > len(splitfile):
      log_msg("Current line number longer than lines in file, returning to start of file","D")
      seek = 0


    # process log's new output
    for line in splitfile[seek:]:
      log_msg(line,"V")
      # start of a run
      if line.startswith('RNG Start Seed:'):
        # this assumes a fixed width, but from what i see it seems safe
        seed = line[16:25]
        log_msg("Starting new run, seed: %s" % seed,"D")
        collected_items = []
        log_msg("Emptied item array","D")
      if line.startswith('Adding collectible'):
        # hacky string manip, idgaf
        space_split = line.split(" ")
        # string has the form "Adding collectible 105 (The D6)"
        item_id = space_split[2]
        item_name = " ".join(space_split[3:])[1:-1]
        log_msg("Picked up item. id: %s, name: %s" % (item_id, item_name),"D")
        collected_items.append(item_id)
        pass
    
    seek = len(splitfile)

