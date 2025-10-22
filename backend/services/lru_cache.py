from collections import OrderedDict


# LRU Cache for queries
class LRUCache:
    def __init__(self, capacity: int = 30):
        self.cache = OrderedDict()
        self.capacity = capacity

    def get(self, key):
        key = key.lower().strip()
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        return None

    def set(self, key, value):
        key = key.lower().strip()
        self.cache[key] = value
        self.cache.move_to_end(key)
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)