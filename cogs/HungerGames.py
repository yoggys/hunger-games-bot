import asyncio
from typing import Any, Optional

import discord
from discord.ext import commands
from tortoise.functions import Sum
from tortoise.queryset import Count, Q

from game_utils.GamesManager import GamesManager
from utils.client import HungerGamesBot
from utils.models import GameModel, PlayerModel
from utils.Paginator import Paginator
from utils.Views import JoinGameView


class HungerGames(commands.Cog):
    def __init__(self, client):
        self.client: HungerGamesBot = client
        self.GamesManager: GamesManager = GamesManager(client=self.client)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.GamesManager.run_games()

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        custom_id = interaction.custom_id
        if not custom_id:
            return

        if custom_id.startswith("start_game_"):
            game_id = int(custom_id.split("start_game_")[1])

            game = await GameModel.get_or_none(
                id=game_id, guild_id=interaction.guild.id
            )
            if not game:
                return await interaction.response.send_message(
                    "❌ Game not found.", ephemeral=True
                )

            if game.owner_id != interaction.user.id:
                return await interaction.response.send_message(
                    "❌ You are not the owner of this game.", ephemeral=True
                )

            if game.is_started:
                return await interaction.response.send_message(
                    "❌ This game has already started.", ephemeral=True
                )

            await game.fetch_related("players")
            if len(game.players) < 2:
                return await interaction.response.send_message(
                    "❌ This game does not have enough players.", ephemeral=True
                )

            try:
                await interaction.message.edit(view=None)
            except (discord.NotFound, discord.Forbidden):
                game.is_ended = True
                return await game.save()

            game.is_started = True
            await game.save()

            await interaction.response.send_message(
                f"✅ The game **{game}** has started.", ephemeral=True
            )
            asyncio.ensure_future(self.GamesManager.run_game(game=game))

        elif custom_id.startswith("join_game_"):
            game_id = int(custom_id.split("join_game_")[1])

            game = await GameModel.get_or_none(
                id=game_id, guild_id=interaction.guild.id
            )
            if not game:
                return await interaction.response.send_message(
                    "❌ Game not found.", ephemeral=True
                )

            if game.is_started:
                return await interaction.response.send_message(
                    "❌ This game has already started.", ephemeral=True
                )

            if (
                game.is_invite_only
                and interaction.user.id not in game.invited_users
                and game.owner_id != interaction.user.id
            ):
                return await interaction.response.send_message(
                    "❌ You are not invited to this game.", ephemeral=True
                )

            await game.fetch_related("players")
            if interaction.user.id in [player.user_id for player in game.players]:
                return await interaction.response.send_message(
                    "❌ You are already in this game.", ephemeral=True
                )

            if len(game.players) >= game.max_players:
                return await interaction.response.send_message(
                    "❌ This game is full.", ephemeral=True
                )

            await PlayerModel.create(game=game, user_id=interaction.user.id)
            current_players = len(game.players) + 1

            await interaction.response.send_message(
                f"✅ {interaction.user.mention} has joined the game **{game}** ({current_players}/{game.max_players}).",
                ephemeral=True,
            )

    @commands.slash_command(description="Create a Hunger Games game.")
    @discord.default_permissions(moderate_members=True)
    async def hgcreate(
        self,
        ctx: discord.ApplicationContext,
        private: discord.Option(bool, "Should the game be private?") = False,
        day_length: discord.Option(int, "Length of each day in minutes.") = 60,
        max_players: discord.Option(int, "Maximum number of players.") = 24,
        channel: discord.Option(
            discord.TextChannel, "Channel to create the game in."
        ) = None,
    ) -> Any:
        if max_players < 2 or (
            max_players > 24 and not await ctx.bot.is_owner(ctx.author)
        ):
            return await ctx.respond(
                "❌ Maximum players must be between 2 and 24.", ephemeral=True
            )

        channel = channel or ctx.channel
        game = await GameModel.create(
            guild_id=ctx.guild.id,
            channel_id=channel.id,
            owner_id=ctx.author.id,
            max_players=max_players,
            is_invite_only=private,
            day_length=day_length,
        )

        description = (
            "This game is private, so only the owner can invite players."
            if private
            else None
        )

        embed = discord.Embed(
            description=description,
            color=discord.Color.gold(),
        )

        embed.set_author(
            name=f"Hunger Games",
            icon_url=ctx.bot.user.display_avatar.url,
        )

        embed.add_field(name="Game ID", value=f"` {game.id} `")
        embed.add_field(name="Max players", value=f"` {game.max_players} `")
        embed.add_field(
            name="Private",
            value="` {} `".format("✅" if game.is_invite_only else "❌"),
        )
        embed.add_field(name="Channel", value=channel.mention)
        embed.add_field(name="Host", value=ctx.author.mention)

        message = await channel.send(embed=embed, view=JoinGameView(game.id))
        game.message_id = message.id
        await game.save()

        await ctx.respond(
            f"✅ Hunger Games created: {message.jump_url}", ephemeral=True
        )

    @commands.slash_command(description="Check players in a Hunger Games game.")
    async def hgplayers(
        self,
        ctx: discord.ApplicationContext,
        game_id: discord.Option(int, "Game ID to check."),
    ) -> Any:
        game = await GameModel.get_or_none(id=game_id, guild_id=ctx.guild.id)
        if not game:
            return await ctx.respond("❌ Game not found.", ephemeral=True)

        await game.fetch_related("players")

        description = ""
        for index, player in enumerate(game.players):
            if player.is_bot:
                description += f"{index + 1}. ` Bot #{player.user_id} `\n"
            else:
                description += f"{index + 1}. <@{player.user_id}>\n"

        embed = discord.Embed(
            description=description or "> No players yet.",
            color=discord.Color.gold(),
        )
        embed.set_author(
            name=f"Hunger Games #{game.id}",
            icon_url=ctx.bot.user.display_avatar.url,
        )

        await ctx.respond(embed=embed, ephemeral=True)

    @commands.slash_command(description="Invite someone to a Hunger Games game.")
    async def hginvite(
        self,
        ctx: discord.ApplicationContext,
        game_id: discord.Option(int, "Game ID to invite to."),
        member: discord.Option(discord.Member, "Member to invite."),
    ) -> Any:
        game = await GameModel.get_or_none(id=game_id, guild_id=ctx.guild.id)
        if not game:
            return await ctx.respond("❌ Game not found.", ephemeral=True)

        if not game.is_invite_only:
            return await ctx.respond("❌ This game is not private.", ephemeral=True)

        if game.owner_id != ctx.author.id:
            return await ctx.respond(
                "❌ You are not the owner of this game.", ephemeral=True
            )

        if game.is_started:
            return await ctx.respond(
                "❌ This game has already started.", ephemeral=True
            )

        if member.bot:
            return await ctx.respond(
                "❌ You cannot invite bots to a game.", ephemeral=True
            )

        if member.id in game.invited_users:
            return await ctx.respond(
                "❌ This player has already been invited.", ephemeral=True
            )

        await game.fetch_related("players")
        if member.id in [player.user_id for player in game.players]:
            return await ctx.respond(
                "❌ This player is already in the game.", ephemeral=True
            )

        if len(game.players) >= game.max_players:
            return await ctx.respond("❌ This game is full.", ephemeral=True)

        game.invited_users.append(member.id)
        await game.save()

        await ctx.respond(
            f"✅ {member.mention} has been invited to the game **{game}**."
        )

    @commands.slash_command(description="Join a Hunger Games game.")
    async def hgjoin(
        self,
        ctx: discord.ApplicationContext,
        game_id: discord.Option(int, "Game ID to join."),
    ) -> Any:
        game = await GameModel.get_or_none(id=game_id, guild_id=ctx.guild.id)
        if not game:
            return await ctx.respond("❌ Game not found.", ephemeral=True)

        if game.is_started:
            return await ctx.respond(
                "❌ This game has already started.", ephemeral=True
            )

        if (
            game.is_invite_only
            and ctx.author.id not in game.invited_users
            and game.owner_id != ctx.author.id
        ):
            return await ctx.respond(
                "❌ You are not invited to this game.", ephemeral=True
            )

        await game.fetch_related("players")
        if ctx.author.id in [player.user_id for player in game.players]:
            return await ctx.respond("❌ You are already in this game.", ephemeral=True)

        current_players = len(game.players)
        if current_players >= game.max_players:
            return await ctx.respond("❌ This game is full.", ephemeral=True)

        await PlayerModel.create(game=game, user_id=ctx.author.id)
        await ctx.respond(
            f"✅ {ctx.author.mention} have joined the game **{game}** ({current_players + 1}/{game.max_players})."
        )

    @commands.slash_command(description="Create a Hunger Games game.")
    @discord.default_permissions(moderate_members=True)
    async def hgstart(
        self,
        ctx: discord.ApplicationContext,
        game_id: discord.Option(int, "Game ID to invite to."),
    ) -> Any:
        game = await GameModel.get_or_none(id=game_id, guild_id=ctx.guild.id)
        if not game:
            return await ctx.respond("❌ Game not found.", ephemeral=True)

        if game.owner_id != ctx.author.id:
            return await ctx.respond(
                "❌ You are not the owner of this game.", ephemeral=True
            )

        if game.is_started:
            return await ctx.respond(
                "❌ This game has already started.", ephemeral=True
            )

        await game.fetch_related("players")
        if len(game.players) < 2:
            return await ctx.respond(
                "❌ This game does not have enough players.", ephemeral=True
            )

        channel = ctx.guild.get_channel(game.channel_id)
        message = (
            channel.get_partial_message(game.message_id)
            if channel and game.message_id
            else None
        )

        try:
            await message.edit(view=None)
        except (discord.NotFound, discord.Forbidden):
            game.is_ended = True
            return await game.save()

        game.is_started = True
        await game.save()

        await ctx.respond(f"✅ The game **{game}** has started.", ephemeral=True)
        asyncio.ensure_future(self.GamesManager.run_game(game=game))

    def format_player(self, player: PlayerModel, winner: Optional[PlayerModel]) -> str:
        if not player.is_alive:
            return f"~~{player}~~ 💀\n>  Died by {player.death_by}. "

        item_labels = {
            "armor": "🛡️ Armor",
            "shield": "🛡️ Shield",
            "medkit": "💉 Medkit",
            "medicine": "💊 Medicine",
            "potion": "🧪 Potion",
            "food": "🍖 Food",
            "charm": "✨ Charm",
            "herbs": "🌿 Herbs",
            "knife": "🗡️ Knife",
            "map": "🗺️ Map",
            "legendary_sword": "⚔️ Legendary Sword",
            "crown": "👑 Crown",
            "divine_favor": "☆ Divine Favor",
            "hope": "💫 Hope",
            "rope": "🪢 Rope",
            "stamina": "⚡ Stamina",
            "ancient_relic": "🏺 Ancient Relic",
            "rivalry_marker": "⚔️ Rivalry",
            "warning_gift": "⚠️ Warning",
            "spirit_gift": "👻 Spirit Gift",
            "temporal_edge": "⏳ Temporal Edge",
            "oracle_blessing": "🔮 Oracle Blessing",
            "knowledge_shard": "📜 Knowledge",
            "fresh_water": "💧 Fresh Water",
            "seeds": "🌱 Seeds",
            "blessing": "✨ Blessing",
            "volcanic_treasure": "🌋 Molten Treasure",
        }

        badges = []
        inventory = sorted(
            {str(item).strip().lower() for item in (player.inventory or [])}
        )

        if player.is_injured:
            badges.append("`[ 🤕 Injured ]`")

        item_badges = []
        for item in inventory:
            label = item_labels.get(item)
            if label:
                item_badges.append(f"`[ {label} ]`")

        if item_badges:
            badges.extend(item_badges)
        else:
            badges.append("`[ ⚔️ Bare ]`")

        return "{} {}{}".format(
            player,
            "👑" if player == winner else "❤️",
            ("\n> " + " ".join(badges)) if badges else "",
        )

    def format_entry(
        self, index: int, player: PlayerModel, winner: Optional[PlayerModel]
    ) -> str:
        return f"{index + 1}. {self.format_player(player, winner)}"

    @commands.slash_command(description="Get more info about Hunger Game game.")
    async def hginfo(
        self,
        ctx: discord.ApplicationContext,
        game_id: discord.Option(int, "Game ID to get more info."),
    ) -> Any:
        game = await GameModel.get_or_none(id=game_id, guild_id=ctx.guild.id)
        if not game:
            return await ctx.respond("❌ Game not found.", ephemeral=True)

        players = await PlayerModel.filter(game=game).order_by(
            "-is_alive", "-current_day", "is_injured"
        )

        if not game.is_started:
            return await ctx.respond(
                f"❌ This game has not started yet ({len(players)}/{game.max_players}).",
                ephemeral=True,
            )

        if len(players) == 0:
            return await ctx.respond("❌ This game has no players.", ephemeral=True)

        alive_count = len([player for player in players if player.is_alive])
        dead_count = len(players) - alive_count

        game_embed = discord.Embed(color=discord.Color.gold())
        game_embed.set_author(
            name=f"Hunger Games #{game_id}",
            icon_url=ctx.bot.user.display_avatar.url,
        )

        game_embed.add_field(name="Day", value=f"` {game.current_day} `", inline=True)
        game_embed.add_field(name="Alive", value=f"` {alive_count} `", inline=True)
        game_embed.add_field(name="Dead", value=f"` {dead_count} `", inline=True)
        game_embed.set_thumbnail(
            url=ctx.bot.user.display_avatar.url,
        )

        if game.is_ended:
            game_embed.add_field(
                name="Winner",
                value=str(await game.winner.get()),
            )

        max_day = max([player.current_day for player in players])
        embeds = [game_embed]
        current_day = None
        description = ""

        winner = await game.winner.get_or_none()
        for i in range(0, len(players), 10):
            for player in players[i : i + 10]:
                player_day = max_day if player.is_alive else player.current_day
                if player_day != current_day:
                    current_day = player_day
                    description += f"\n## Day {current_day}\n"

                description += (
                    f"{self.format_entry(players.index(player), player, winner)}\n"
                )
            embed = discord.Embed(description=description, color=discord.Color.gold())
            embeds.append(embed)

        if len(embeds) == 1:
            await ctx.respond(embeds=embeds[0], ephemeral=True)
        else:
            pages = Paginator(pages=embeds)
            await pages.respond(ctx.interaction, ephemeral=True)

    @commands.slash_command(description="Check player history of Hunger Games.")
    async def hgplayer(
        self,
        ctx: discord.ApplicationContext,
        member: discord.Option(
            discord.Member,
            "Member to check history.",
        ) = None,
        state: discord.Option(
            str, "State to check history.", choices=["global", "server"]
        ) = "server",
    ) -> Any:
        member = member or ctx.author

        if state == "global":
            games = await PlayerModel.filter(user_id=member.id).count()
            won_games = await PlayerModel.filter(
                Q(user_id=member.id) & ~Q(winner_of=None)
            ).count()
            player_kills = await PlayerModel.filter(user_id=member.id).annotate(
                kills=Count("killed_players")
            )
            player_kills = sum([p.kills for p in player_kills if p.kills])
        else:
            games = await PlayerModel.filter(
                Q(user_id=member.id, game__guild_id=ctx.guild.id)
            ).count()
            won_games = await PlayerModel.filter(
                Q(user_id=member.id, game__guild_id=ctx.guild.id) & ~Q(winner_of=None)
            ).count()
            player_kills = await PlayerModel.filter(
                Q(user_id=member.id, game__guild_id=ctx.guild.id)
            ).annotate(kills=Count("killed_players"))
        player_kills = sum([p.kills for p in player_kills if p.kills])
        if games == 0:
            return await ctx.respond(
                f"{member.mention} did not participate in any Hunger Games.",
                ephemeral=True,
            )

        embed = discord.Embed(color=discord.Color.gold())
        embed.set_author(
            name=f"Hunger Games - player {state} history",
            icon_url=ctx.bot.user.display_avatar.url,
        )

        embed.add_field(name="Games", value=f"` {games} `")
        embed.add_field(name="Won", value=f"` {won_games} `")
        embed.add_field(name="Kills", value=f"` {player_kills} `")

        await ctx.respond(embed=embed, ephemeral=True)

    @commands.slash_command(description="Check server history of Hunger Games.")
    async def hgserver(
        self,
        ctx: discord.ApplicationContext,
    ) -> Any:
        embeds = []
        games = await GameModel.filter(guild_id=ctx.guild.id).count()
        games_finished = await GameModel.filter(
            guild_id=ctx.guild.id, is_ended=True
        ).count()
        games_kills = await GameModel.filter(guild_id=ctx.guild.id).annotate(
            killed_players=Count("players__killed_by")
        )
        games_kills = sum([g.killed_players for g in games_kills if g.killed_players])

        embed = discord.Embed(color=discord.Color.gold())
        embed.set_author(
            name="Hunger Games - server history",
            icon_url=ctx.bot.user.display_avatar.url,
        )

        embed.add_field(name="Games", value=f"` {games} `")
        embed.add_field(name="Finished", value=f"` {games_finished} `")
        embed.add_field(name="Total kills", value=f"` {games_kills} `")
        embeds.append(embed)

        recent_winners = (
            await PlayerModel.filter(
                Q(game__guild_id=ctx.guild.id, is_bot=False) & ~Q(winner_of=None)
            )
            .order_by("-updated_at")
            .limit(3)
        )

        if len(recent_winners) > 0:
            recent_winners = "\n".join(
                [
                    "{} - ` Hunger Games {} `".format(winner, await winner.game.get())
                    for winner in recent_winners
                ]
            )
            recent_winners = discord.Embed(
                title="Recent Winners",
                description=recent_winners,
                color=discord.Color.gold(),
            )
            embeds.append(recent_winners)

        await ctx.respond(embeds=embeds, ephemeral=True)

    @commands.slash_command(description="Create and start a Hunger Games game.")
    @commands.is_owner()
    async def hgdebug(
        self,
        ctx: discord.ApplicationContext,
        players: discord.Option(int, "Number of players to create.") = 2,
        instant: discord.Option(bool, "Instantly end days of the game.") = False,
    ) -> Any:
        game = await GameModel.create(
            guild_id=ctx.guild.id,
            channel_id=ctx.channel.id,
            owner_id=ctx.author.id,
            day_length=0 if instant else 1,
            is_invite_only=True,
            is_started=True,
        )

        for index in range(players):
            await PlayerModel.create(game=game, user_id=index, is_bot=True)

        await ctx.respond(f"✅ Done - **{game}** with **{players}** players.")
        await self.GamesManager.run_game(game=game)

        await PlayerModel.filter(game=game).delete()
        await game.delete()

    @commands.slash_command(description="Fill game with bots.")
    @commands.is_owner()
    async def hgbots(
        self,
        ctx: discord.ApplicationContext,
        game_id: discord.Option(int, "Game ID."),
        count: discord.Option(int, "Number of bots to create.") = 1,
    ) -> Any:
        game = await GameModel.get_or_none(id=game_id, guild_id=ctx.guild.id)
        if not game:
            return await ctx.respond("❌ Game not found.", ephemeral=True)

        if game.is_started:
            await ctx.respond("❌ Game has already started.", ephemeral=True)

        await ctx.defer(ephemeral=True)

        if (
            model := await PlayerModel.filter(game=game, is_bot=True)
            .order_by("-id")
            .first()
        ):
            max_id = model.id
        else:
            max_id = 0

        for index in range(1, count + 1):
            await PlayerModel.create(game=game, user_id=max_id + index, is_bot=True)

        await ctx.respond(
            f"✅ Added **{count-max_id}** bots to **{game}**.", ephemeral=True
        )


def setup(client):
    client.add_cog(HungerGames(client))
