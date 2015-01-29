import copy
from google.appengine.api import datastore

class Context(object):

    def __init__(self, stack):
        self.cache = {}
        self.reverse_cache = {}
        self._stack = stack

    def apply(self, other):
        self.cache.update(other.cache)

        # We have to delete things that don't exist in the other
        for k in self.cache.keys():
            if k not in other.cache:
                del self.cache[k]

        self.reverse_cache.update(other.reverse_cache)

        # We have to delete things that don't exist in the other
        for k in self.reverse_cache.keys():
            if k not in other.reverse_cache:
                del self.reverse_cache[k]

    def cache_entity(self, identifiers, entity, situation):
        assert hasattr(identifiers, "__iter__")

        for identifier in identifiers:
            self.cache[identifier] = copy.deepcopy(entity)

        self.reverse_cache[entity.key()] = identifiers

    def remove_entity(self, entity_or_key):
        if not isinstance(entity_or_key, datastore.Key):
            entity_or_key = entity_or_key.key()

        for identifier in self.reverse_cache[entity_or_key]:
            del self.cache[identifier]

        del self.reverse_cache[entity_or_key]

    def get_entity(self, identifier):
        cache = {}

        for ctx in self._stack.stack:
            cache.update(ctx.cache)
            if ctx == self:
                break;

        return cache.get(identifier)

    def get_entity_by_key(self, key):
        cache = {}

        for ctx in self._stack.stack:
            cache.update(ctx.reverse_cache)
            if ctx == self:
                break;

        try:
            identifier = cache[key][0]  # Pick any identifier
        except KeyError:
            return None

        return self.get_entity(identifier)

class ContextStack(object):
    """
        A stack of contexts. This is used to support in-context
        caches for multi level transactions.
    """

    def __init__(self):
        self.stack = [ Context(self) ]
        self.staged = []

    def push(self):
        self.stack.append(
            Context(self) # Empty context
        )

    def pop(self, apply_staged=False, clear_staged=False, discard=False):
        """
            apply_staged: pop normally takes the top of the stack and adds it to a FIFO
            queue. By passing apply_staged it will pop to the FIFO queue then apply the
            queue to the top of the stack.

            clear_staged: pop, and then wipe out any staged contexts.

            discard: Ignores the popped entry in the stack, it's just discarded

            The staged queue will be wiped out if the pop makes the size of the stack one,
            regardless of whether you pass clear_staged or not. This is for safety!
        """
        if not discard:
            self.staged.insert(0, self.stack.pop())
        else:
            self.stack.pop()

        if apply_staged:
            while self.staged:
                self.top.apply(self.staged.pop())

        if clear_staged or len(self.stack) == 1:
            self.staged = []

    @property
    def top(self):
        return self.stack[-1]

    @property
    def size(self):
        return len(self.stack)

    @property
    def staged_count(self):
        return len(self.staged)
