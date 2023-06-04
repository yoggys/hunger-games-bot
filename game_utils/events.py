from __future__ import annotations

from enum import Enum
from typing import Any, Coroutine

from discord import Color


class EventType(Enum):
    """Event types for the Hunger Games."""

    POSITIVE = Color.brand_green()
    NEGATIVE = Color.brand_red()
    PASSIVE = Color.blurple()


class Event(object):
    """Event object for the Hunger Games."""

    _type: EventType = None
    text: str = None

    def __init__(
        self,
        weight: int,
        callback: Coroutine[Any, Any, Event],
    ):
        """Initializes the Event object.

        Args:
            text (str): Event text.
            weight (int): Event weight (to calculate the chance of the event happening).
        """

        self.weight = weight
        self.callback = callback

    async def execute(self, *args, **kwargs) -> Coroutine[Any, Any, Event]:
        """Executes the event callback function"""
        event = await self.callback(*args, **kwargs)
        if not event._type or not event.text:
            raise ValueError(
                "Event callback does not set required parameters of Event class."
            )
        return event
