import os.path
from config import settings

from dogpile.cache import make_region

cache = make_region().configure(
    'dogpile.cache.memory',
    expiration_time = 3600,
)

# having problems with dbm backend (compaints about unicode keys)
#cache = make_region().configure(
#    'dogpile.cache.dbm',
#    expiration_time = 3600,
#    arguments = {
#        "filename":"/tmp/sourcy-cache.dbm"
#    }
#)

