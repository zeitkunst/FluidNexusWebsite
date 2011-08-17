import os
import sys

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.txt')).read()
CHANGES = open(os.path.join(here, 'CHANGES.txt')).read()

requires = [
    'pyramid',
    'SQLAlchemy',
    'transaction',
    'repoze.tm2>=1.0b1', # default_commit_veto
    'zope.sqlalchemy',
    'WebError',
    'docutils',
    'pyramid_formalchemy',
    'fa.jquery',
    'textile',
    'Babel',
    'lingua',
    'py-bcrypt',
    'beaker',
    'pyramid-beaker',
    'pycryptopp',
    'pyramid-openid',
    'oauth2',
    'sqlalchemy-migrate',
    'cherrypy',
    'pyrss2gen',
    'PIL',
    'supervisor',
    'python-memcached',
    ]

if sys.version_info[:3] < (2,5,0):
    requires.append('pysqlite')

setup(name='FluidNexus',
      version='0.2.0',
      description='FluidNexus',
      long_description=README + '\n\n' +  CHANGES,
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Pylons",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        ],
      author='',
      author_email='',
      url='',
      keywords='web wsgi bfg pylons pyramid',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      test_suite='fluidnexus',
      install_requires = requires,
      message_extractors = {'.': [
        ('**.py', 'lingua_python', None),
          ('**.pt', 'lingua_xml', None),
      ]},
      entry_points = """\
      [paste.app_factory]
      main = fluidnexus:main
      """,
      paster_plugins=['pyramid'],
      )

