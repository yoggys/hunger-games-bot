from __future__ import annotations

from tortoise import fields
from tortoise.models import Model


class BaseModel(Model):
    """Base model for all models."""

    class Meta:
        abstract = True

    id = fields.IntField(pk=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)


class GameModel(BaseModel):
    """Represents a Hunger Games game."""

    guild_id = fields.BigIntField()
    channel_id = fields.BigIntField()
    owner_id = fields.BigIntField()

    is_invite_only = fields.BooleanField(default=False)
    is_started = fields.BooleanField(default=False)
    is_ended = fields.BooleanField(default=False)

    day_length = fields.IntField(default=60)
    max_players = fields.IntField(default=24)
    current_day = fields.IntField(default=1)
    current_day_choices = fields.JSONField(default=[])
    invited_users = fields.JSONField(default=[])

    players: fields.ReverseRelation[PlayerModel]
    winner: fields.BackwardOneToOneRelation[PlayerModel]

    def __str__(self) -> str:
        return f"#{self.id}"


class PlayerModel(BaseModel):
    """Represents a player in a Hunger Games game."""

    game: fields.ForeignKeyRelation[GameModel] = fields.ForeignKeyField(
        "models.GameModel", related_name="players"
    )
    user_id = fields.BigIntField()
    current_day = fields.IntField(default=0)  # only for bot reloads

    is_bot = fields.BooleanField(default=False)
    winner_of = fields.OneToOneRelation(
        "models.GameModel", related_name="winner", null=True
    )

    is_alive = fields.BooleanField(default=True)
    is_injured = fields.BooleanField(default=False)
    is_protected = fields.BooleanField(default=False)
    is_armored = fields.BooleanField(default=False)
    inventory = fields.JSONField(default=[])

    allied_with: fields.ReverseRelation[PlayerModel]
    killed_by: fields.ReverseRelation[PlayerModel]
    death_by = fields.CharField(max_length=256, null=True)

    allied_players = fields.ManyToManyField(
        "models.PlayerModel", related_name="allied_with"
    )
    killed_players = fields.ManyToManyField(
        "models.PlayerModel", related_name="killed_by"
    )

    def has_item(self, item: str) -> bool:
        item_name = str(item).strip().lower()
        raw_items = self.inventory or []
        return any(str(existing).strip().lower() == item_name for existing in raw_items)

    def add_item(self, item: str) -> bool:
        item_name = str(item).strip().lower()
        if not item_name:
            return False

        inventory = list(self.inventory or [])
        normalized = [str(existing).strip().lower() for existing in inventory]
        if item_name in normalized:
            return False

        inventory.append(item_name)
        self.inventory = inventory
        return True

    def remove_item(self, item: str) -> bool:
        item_name = str(item).strip().lower()
        if not item_name:
            return False

        inventory = list(self.inventory or [])
        remaining = [
            existing
            for existing in inventory
            if str(existing).strip().lower() != item_name
        ]
        if len(remaining) == len(inventory):
            return False

        self.inventory = remaining
        return True

    def sync_gear_from_inventory(self) -> None:
        self.is_armored = self.has_item("armor") or self.has_item("shield")
        self.is_protected = (
            self.has_item("medkit")
            or self.has_item("medicine")
            or self.has_item("potion")
        )

    def __str__(self) -> str:
        return f"` Bot #{self.user_id} `" if self.is_bot else f"<@{self.user_id}>"
