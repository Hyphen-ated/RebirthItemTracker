RebirthItemTracker
==================

This uses the `log.txt` file to track item pickups in The Binding of Isaac: Rebirth. This is particularly useful for streamers, so their viewers can see their items, but can be used by anyone. It's easier to see what items you have on the tracker than it is on the pause screen. Additionally, it...

- shows stats for picked up items.
- marks items that were picked up during a _Curse of the Blind_.
- marks items that were rerolled using _D4_.
- shows what floor items were picked up on.
- shows the floor the player is currently on.
- displays the current seed.
- allows tournament hosts to recieve players' item data through a server

![](http://i.imgur.com/zG3eV8V.png)

Download it [here](https://github.com/Hyphen-ated/RebirthItemTracker/releases) (get the latest file that doesn't have "source code" in the name).

To use it, first extract that zip file and then run the exe inside.

It tries to read `log.txt` from inside `C:\Users\ (you) \Documents\My Games\Binding of Isaac Rebirth\`.

If it's unable to find that file, you might need to put the tracker folder into that rebirth folder.

You can right click anywhere in the window to get an options screen.

You can mouse over items you've picked up to see their stats again, and click on them to open [platinumgod.co.uk](http://platinumgod.co.uk/) in your browser for more information about that item (arrow keys and enter also work).

## Tournament Use

First, each competitor needs to go to the options screen, click "Let Others Watch Me", click "Get an authkey", authorize the application on twitch in the browser window that pops up, and then paste the authkey they receive into the tracker. After getting an authkey once, this step doesn't need to happen again. Don't show the authkey on stream.

If you're in "Let Others Watch Me" mode, indicated by the text "uploading to server" in the title bar, then the host can see your items with the "Watch Someone Else" button.

After closing the tracker, the tournament settings will turn themselves off automatically.

The host needs to run a separate copy of the tracker for each competitor. To compensate for twitch delay, there's a "read delay" setting which makes the tracker wait that many seconds before displaying updates from the player. Ctrl-up and ctrl-down are shortcuts to change the delay, which is also shown in the title bar.

## Known issues

* When using the _Glowing Hourglass_ right after taking any object, this object will remains in the tracker even if the character doesn't have it anymore.

* If you want to make a shortcut to the tracker, make the shortcut to the file "dist/item_tracker.exe" rather than to the existing shortcut called "Launch Item Tracker"
