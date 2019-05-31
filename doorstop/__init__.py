"""Package for doorstop."""

from doorstop.common import DoorstopError, DoorstopWarning, DoorstopInfo
from doorstop.core import Item, Document, Tree
from doorstop.core import build
from doorstop.core import importer, exporter, builder, editor, publisher

__project__ = 'Doorstop'
__version__ = '1.6b1'

CLI = 'doorstop'
GUI = 'doorstop-gui'
SERVER = 'doorstop-server'
VERSION = "{0} v{1}".format(__project__, __version__)
DESCRIPTION = "Requirements management using version control."
