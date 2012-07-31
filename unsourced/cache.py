import os.path
from config import settings

from dogpile.cache import make_region

# using dogpile.cache as a frontend to memcached.
# handles the dogpile problem nicely.


#cache = make_region().configure(
#    'dogpile.cache.memory',
#    expiration_time = 3600,
#)

# memcached backend
cache = make_region().configure(
    'dogpile.cache.memcached',
    expiration_time = 3600,
    arguments = {
        'url':"127.0.0.1:11211",
    }
)

