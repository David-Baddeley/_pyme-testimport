#!/bin/bash

sudo cp pyme.xml /usr/share/mime/packages/
sudo update-mime-database /usr/share/mime

gconftool --install-schema-file=h5r.schema.xml

ln -s `pwd`/urlOpener.py ~/bin/pymeUrlOpener
ln -s `pwd`/../DSView/dh5view.py ~/bin/dh5view
ln -s `pwd`/../Analysis/LMVis/VisGUI.py ~/bin/VisGUI
ln -s `pwd`/h5-thumbnailer.py ~/bin/h5-thumbnailer
ln -s `pwd`/h5r-thumbnailer.py ~/bin/h5r-thumbnailer
ln -s `pwd`/kdf-thumbnailer.py ~/bin/kdf-thumbnailer
ln -s `pwd`/sf-thumbnailer.py ~/bin/sf-thumbnailer
