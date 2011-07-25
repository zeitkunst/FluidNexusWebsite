#!/usr/bin/env python
from migrate.versioning.shell import main
main(url='sqlite:///FluidNexus.db', debug='False', repository='data/repository')
