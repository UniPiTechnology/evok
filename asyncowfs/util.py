# utility code

import attr
import outcome

import anyio
from concurrent.futures import CancelledError


@attr.s
class ValueEvent:
    """A waitable value useful for inter-task synchronization,
    inspired by :class:`threading.Event`.

    An event object manages an internal value, which is initially
    unset, and tasks can wait for it to become True.

    """

    event = attr.ib(factory=anyio.Event, init=False)
    value = attr.ib(default=None, init=False)

    def set(self, value):
        """Set the internal flag value to True, and wake any waiting tasks."""
        self.value = outcome.Value(value)
        self.event.set()
        #return anyio.DeprecatedAwaitable(self.set)

    def is_set(self):
        return self.value is not None

    def set_error(self, exc):
        """Set the internal flag value to True, and wake any waiting tasks."""
        self.value = outcome.Error(exc)
        self.event.set()
        #return anyio.DeprecatedAwaitable(self.set_error)

    def cancel(self):
        self.set_error(CancelledError())
        #return anyio.DeprecatedAwaitable(self.cancel)

    async def get(self):
        """Block until the internal flag value becomes True.

        If it's already True, then this method is still a checkpoint, but
        otherwise returns immediately.

        """
        await self.event.wait()
        return self.value.unwrap()
