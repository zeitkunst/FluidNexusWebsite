#!/bin/bash

echo "Creating manual"
rst2html.py --stylesheet-path=css/desktop_manual.css manual.rst manual/index.html

echo "Copying to desktop version"
cp -R manual /home/nknouf/Documents/Research/Projects/FluidNexus/code/FluidNexus/share/FluidNexus/

echo "Copying to Android version"
cp -R manual/* /home/nknouf/Documents/Research/Projects/FluidNexus/code/FluidNexusAndroid/assets/

echo "Creating manual for website"
rst2html.py --template=manual_website.template manual.rst tmpManual.pt
sed 's/src="images/src="${images_static_url}/g' <tmpManual.pt > manual.pt
cp manual.pt ../templates/
rm -f manual.pt
rm -f tmpManual.pt
