#Run this in 'collectibles' to resize and blur them
for toto in `ls *.png`; do
    mogrify -scale 200% $toto
    convert $toto \( +clone -channel A -blur 0x2.5 -level 0,80% +channel +level-colors white \) -compose DstOver -composite $toto
done
