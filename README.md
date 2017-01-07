RebirthItemTracker
==================

This uses the `log.txt` file to track item pickups in The Binding of Isaac: Rebirth, Afterbirth, Afterbirth+, and Antibirth.

This is particularly useful for streamers, so their viewers can see their items, but can be used by anyone. The game's
built-in item tracker only shows 10 items and doesn't include several oth. Additionally, it...

- tells you what an item does when you pick it up.
- marks items that were picked up during a _Curse of the Blind_.
- marks items that were rerolled using _D4_/_D100/etc.
- shows what floor items were picked up on.
- shows the floor the player is currently on.
- displays the current seed.
- allows tournament hosts to receive players' item data through a server, so they can fit nicely in a restream layout.

![](http://i.imgur.com/zG3eV8V.png)

Download it [here](https://github.com/Hyphen-ated/RebirthItemTracker/releases) (get the latest file that doesn't have "source code" in the name).

To use it, first extract that zip file and then run the exe inside. Don't put it inside the same folder as any file named log.txt.

You can right click anywhere in the window to get an options screen.

You can mouse over items you've picked up to see their stats again, and click on them to open [platinumgod.co.uk](http://platinumgod.co.uk/) in your browser for more information about that item.

It tries to read `log.txt` from inside the appropriate game folder, based on which game you select in the tracker options.
If something is unexpectedly weird about your game folder and it can't find it, you can put the tracker folder into the
folder with your log.txt and it will force it to use the specific one it finds there. (If you do this, you can't change
between different isaac games by using the tracker option, and you'd have to have multiple tracker installs to use for
Antibirth vs Afterbirth+, for example. Normally this should not have to happen.)

## Tournament/Restreaming Use

First, each competitor needs to go to the options screen, click "Let Others Watch Me", click "Get an authkey", authorize the application on twitch in the browser window that pops up, and then paste the authkey they receive into the tracker. After getting an authkey once, this step doesn't need to happen again. Don't show the authkey on stream.

If you're in "Let Others Watch Me" mode, indicated by the text "uploading to server" in the title bar, then the host can see your items with the "Watch Someone Else" button.

After closing the tracker, the tournament settings will turn themselves off automatically.

The host needs to run a separate copy of the tracker for each competitor. To compensate for twitch delay, there's a "read delay" setting which makes the tracker wait that many seconds before displaying updates from the player. Ctrl-up and ctrl-down are shortcuts to change the delay, which is also shown in the title bar.

## Known issues

* When using the _Glowing Hourglass_ right after taking any object, this object will remains in the tracker even if the character doesn't have it anymore.

* If you want to make a shortcut to the tracker, make the shortcut to the file "dist/item_tracker.exe" rather than to the existing shortcut called "Launch Item Tracker"

* When playing Antibirth, it doesn't display detailed item information, nor can it keep track of what floor you're on.
