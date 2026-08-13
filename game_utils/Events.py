from __future__ import annotations

from enum import Enum
from typing import Any, Callable, Coroutine, Optional

try:
    from discord import Color
except (
    Exception
):  # pragma: no cover - compatibility for Windows/Python builds without audioop

    class Color:
        @staticmethod
        def brand_green() -> int:
            return 0x43B581

        @staticmethod
        def brand_red() -> int:
            return 0xF04747

        @staticmethod
        def blurple() -> int:
            return 0x5865F2


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
