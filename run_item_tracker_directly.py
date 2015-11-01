# to make this source tree a little cleaner, all the actual python code for the program itself goes in src/
# data files and build scripts etc do not go in that directory. so if you want to run the code while working on it,
# use this little script so the running program can see the data files in the places it expects
import sys
sys.path.append("./src/")
import item_tracker
item_tracker.main()