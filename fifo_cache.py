from queue import SimpleQueue


class FifoCache:
    def __init__(self, max_length: int):
        self.dictionary = dict()
        self.queue = SimpleQueue()

        assert max_length > 0
        self._max_length = max_length
        self.size = 0

    def values(self):
        return self.dictionary.values()

    def __getitem__(self, item):
        return self.dictionary[item]

    def __setitem__(self, key, value):
        if key in self.dictionary:
            self.dictionary[key] = value
            return
        if self.size >= self._max_length:
            del self.dictionary[self.queue.get()]
            self.queue.put(key)
            self.dictionary[key] = value
        else:
            self.queue.put(key)
            self.dictionary[key] = value
            self.size += 1

    def __contains__(self, item):
        return item in self.dictionary

    def __len__(self):
        return self.size
