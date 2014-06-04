"""
This module contains a simple function to encode any number of
bitmap files to a .py file"""

import os
import glob

from wx.tools import img2py

output = 'bitmaps.py'

# get the list of BMP files
files = []
files.extend(glob.glob('res/*.png')) #TODO: chose your extension here
files.extend(glob.glob('res/*.xpm')) #TODO: chose your extension here
files.extend(glob.glob('res/*.ico')) #TODO: chose your extension here

open(output, 'w')

# call img2py on each file
for file in files:

    # extract the basename to be used as the image name
    name = os.path.splitext(os.path.basename(file))[0]
    name = name.replace('-', '_')

    # encode it
    if file == files[0]:
        cmd = "-u -i -n %s %s %s" % (name, file, output)
    else:
        cmd = "-a -u -i -n %s %s %s" % (name, file, output)
    img2py.main(cmd.split())

