from __future__ import annotations

from enum import Enum
from typing import Any, Callable, Coroutine, Optional

from discord import Color


class EventType(Enum):
    """Event types for the Hunger Games."""

    POSITIVE = Color.brand_green()
    NEGATIVE = Color.brand_red()
    PASSIVE = Color.blurple()


class Event(object):
    """Event object for the Hunger Games."""

    def __init__(
        self,
        weight: int,
        callback: Callable[..., Coroutine[Any, Any, Event]],
    ):
        """Initializes the Event object.

        Args:
            weight (int): Event weight (to calculate the chance of the event happening).
            callback (Callable[..., Coroutine[Any, Any, Self]]): Callback of the Event.
        """

        self.weight = weight
        self.callback = callback
        self._type: Optional[EventType] = None
        self.text: Optional[str] = None

    async def execute(self, *args, **kwargs) -> Event:
        """Executes the event callback function"""
        event = await self.callback(*args, **kwargs)
        if not event._type or not event.text:
            raise ValueError(
                "Event callback does not set required parameters of Event class."
            )
        return event

    @property
    def type(self) -> EventType:
        """Event type"""
        return self._type
