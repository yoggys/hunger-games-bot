from typing import Any, Coroutine

from discord.errors import NotFound
from discord.ext import pages
from discord.interactions import Interaction
from discord.ui import Item


class Paginator(pages.Paginator):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    async def on_error(
        self, error: Exception, item: Item, interaction: Interaction
    ) -> Coroutine[Any, Any, None]:
        """This method is called when an error is raised within the paginator."""

        if isinstance(error, NotFound):
            return

        await interaction.respond(
            "Unexpected error occurred, please try again...", ephemeral=True
        )
