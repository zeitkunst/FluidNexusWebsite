ALLDIRS = ['/var/www/fluidnexus.net/FluidNexusWebsite/lib/python2.6/site-packages']

import os
import sys 
import site 

# Remember original sys.path.
prev_sys_path = list(sys.path) 

# Add each new site-packages directory.
for directory in ALLDIRS:
    site.addsitedir(directory)

# Reorder sys.path so new directories at the front.
new_sys_path = [] 
for item in list(sys.path): 
    if item not in prev_sys_path: 
        new_sys_path.append(item) 
        sys.path.remove(item) 
sys.path[:0] = new_sys_path 

os.environ['PYTHON_EGG_CACHE'] = '/var/www/fluidnexus.net/FluidNexusWebsite/.python-eggs'

from pyramid.paster import get_app
application = get_app(
  '/var/www/fluidnexus.net/FluidNexusWebsite/FluidNexus/production.ini', 'main')

