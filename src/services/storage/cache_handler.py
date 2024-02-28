from fastapi_cache import FastAPICache
from fastapi_cache.backends.memcached import MemcachedBackend

from beaker.cache import CacheManager
from beaker.util import parse_cache_config_options

class CacheHandler():
    def __init__(self):
        # set cache options
        self.cache_opts = {
            'cache.type': 'file',
            'cache.data_dir' : '/tmp/cache/data',
            'cache.lock_dir': '/tmp/cache/lock'
        }
        self.cacheProvider = CacheManager(**parse_cache_config_options(self.cache_opts))
        self.cache = self.cacheProvider.get_cache('data', type='dbm', expire=600)
        self.cache.get_value
    
    # Gets value. Returns null when not found
    def get(self, key: str):
        try:
            return self.cache.get_value(key)
        except:
            return None
    
    # Sets value. Returns `False` on error
    def set(self, key: str, value):
        try:
            self.cache.set_value(key, value)
        except:
            return False
    
    # Deletes value from cache. Returns `True` when deletion is successful; `False` if not
    def delete(self, key: str):
        try:
            self.cache.remove(key)
            return True
        except:
            return False