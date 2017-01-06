#Run this in a dir with copies of new item images to add the glow effect to them in-place
for toto in `ls *.png`; do
    convert $toto \( +clone -channel A -blur 0x2.5 -level 0,80% +channel +level-colors white \) -compose DstOver -composite $toto
done
