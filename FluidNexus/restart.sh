#!/bin/bash
source /var/www/fluidnexus.net/FluidNexusWebsite/bin/activate && python setup.py install && killall supervisord && supervisord -c supervisord.ini
