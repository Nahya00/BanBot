import discord
from discord.ext import commands
import asyncio
import os

# --- CONFIGURATION ---
TOKEN = os.getenv('TOKEN')
CHANNEL_ID = 1366186686907944982
LOG_CHANNEL_ID = 1363252748820287761

REQUESTER_ROLES = [
    1362033700946186301, 1364194597734973492, 1365837084233039932,
    1362033708487409748, 1362033723121602612, 1362033735910031493,
    1362033746601316622, 1365894628569518110, 1362033753538564288,
    1362033883482296380, 1362033760534663419, 1365044608341377127,
    1362033771595038793, 1365525197473579008, 1362033775084699711,
    1366239607238299698
]

VALIDATOR_ROLES = [
    1362033700946186301, 1364194597734973492, 1365837084233039932,
    1362033708487409748, 1362033723121602612, 1362033735910031493,
    1366239607238299698
]

PRIORITY_MENTION_ROLES = [
    1365837084233039932, 1362033723121602612
]

VOTE_THRESHOLD = 5

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.guilds = True
intents.members = True
intents.dm_messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

class BanRequestView(discord.ui.View):
    def __init__(self, target_id, reason, ctx_author_id, target_user_avatar):
        super().__init__(timeout=86400)
        self.target_id = target_id
        self.reason = reason
        self.ctx_author_id = ctx_author_id
        self.confirm_votes = set()
        self.refuse_votes = set()
        self.target_user_avatar = target_user_avatar
        self.message = None

    async def update_buttons(self):
        self.confirm_button.label = f"✅ Confirmer ({len(self.confirm_votes)}/{VOTE_THRESHOLD})"
        self.refuse_button.label = f"❌ Refuser ({len(self.refuse_votes)}/{VOTE_THRESHOLD})"
        await self.message.edit(view=self)

    async def finalize_request(self, accepted: bool):
        embed = self.message.embeds[0]
        if accepted:
            embed.title = "✅ Bannissement Validé"
            embed.color = discord.Color.green()
            try:
                target_member = await self.message.guild.fetch_member(self.target_id)

                try:
                    dm_embed = discord.Embed(
                        title="🚨 BANNISSEMENT 🚨",
                        description=f"Vous avez été banni du serveur **Noctys** pour la raison suivante :\n\n{self.reason}\n\n"
                                    "Pour faire une demande de débannissement, merci de rejoindre :\n"
                                    "**https://discord.gg/yGuj5A7Hpa**",
                        color=discord.Color.red()
                    )
                    dm_embed.set_footer(text="Noctys - Système Automatisé")
                    if target_member.avatar:
                        dm_embed.set_thumbnail(url=target_member.avatar.url)
                    await target_member.send(embed=dm_embed)
                except Exception as e:
                    print(f"Erreur lors de l'envoi du MP : {e}")

                await target_member.ban(reason=self.reason)

                log_channel = bot.get_channel(LOG_CHANNEL_ID)
                if log_channel:
                    log_embed = discord.Embed(
                        title="✅ Bannissement Validé",
                        description=f"**Membre banni :** {target_member} (`{self.target_id}`)\n**Raison :** {self.reason}",
                        color=discord.Color.green()
                    )
                    await log_channel.send(embed=log_embed)

            except Exception as e:
                print(f"Erreur lors du bannissement : {e}")
        else:
            embed.title = "❌ Demande Refusée"
            embed.color = discord.Color.red()

        await self.message.edit(embed=embed, view=None)
        self.stop()

    @discord.ui.button(label="✅ Confirmer (0/5)", style=discord.ButtonStyle.green)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not any(role.id in VALIDATOR_ROLES for role in interaction.user.roles):
            await interaction.response.send_message("❌ Tu n'as pas la permission de voter.", ephemeral=True)
            return

        if interaction.user.id in self.refuse_votes:
            self.refuse_votes.remove(interaction.user.id)
        self.confirm_votes.add(interaction.user.id)

        await self.update_buttons()

        if len(self.confirm_votes) >= VOTE_THRESHOLD:
            await self.finalize_request(accepted=True)

        await interaction.response.defer()

    @discord.ui.button(label="❌ Refuser (0/5)", style=discord.ButtonStyle.danger)
    async def refuse_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not any(role.id in VALIDATOR_ROLES for role in interaction.user.roles):
            await interaction.response.send_message("❌ Tu n'as pas la permission de voter.", ephemeral=True)
            return

        if interaction.user.id in self.confirm_votes:
            self.confirm_votes.remove(interaction.user.id)
        self.refuse_votes.add(interaction.user.id)

        await self.update_buttons()

        if len(self.refuse_votes) >= VOTE_THRESHOLD:
            await self.finalize_request(accepted=False)

        await interaction.response.defer()

    @discord.ui.button(label="🚫 Annuler", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Seuls les administrateurs peuvent annuler une demande.", ephemeral=True)
            return

        await self.finalize_request(accepted=False)
        await interaction.response.send_message("🚫 Demande annulée.", ephemeral=True)

@bot.event
async def on_ready():
    print(f"✅ Bot connecté en tant que {bot.user}")

@bot.command(name="demandeban")
async def demande_ban(ctx, user_id: int, *, reason: str):
    if ctx.guild is None:
        return

    if not any(role.id in REQUESTER_ROLES for role in ctx.author.roles):
        return

    channel = bot.get_channel(CHANNEL_ID)
    if channel is None:
        return

    try:
        user = await bot.fetch_user(user_id)
        user_display = f"**{user}** (`{user.id}`)"
        avatar_url = user.avatar.url if user.avatar else None
    except:
        user_display = f"`{user_id}`"
        avatar_url = None

    mention_text = " ".join(f"<@&{role_id}>" for role_id in PRIORITY_MENTION_ROLES)

    embed = discord.Embed(
        title="🚨 Demande de Bannissement",
        description=f"{mention_text}",
        color=discord.Color.orange()
    )
    embed.add_field(name="👤 Cible", value=user_display, inline=False)
    embed.add_field(name="📎 Raison", value=reason, inline=False)
    embed.set_footer(text=f"Demandé par {ctx.author}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
    if avatar_url:
        embed.set_image(url=avatar_url)

    view = BanRequestView(user_id, reason, ctx.author.id, avatar_url)
    ban_request_message = await channel.send(content=mention_text, embed=embed, view=view)
    view.message = ban_request_message
@bot.command(name="helpban")
async def helpban(ctx):
    embed = discord.Embed(
        title="📚 Aide - Système de Bannissement",
        description="Voici les commandes disponibles :",
        color=discord.Color.blurple()
    )
    embed.add_field(name="🚨 !demandeban <id> <raison>", value="Créer une demande de ban.", inline=False)
    embed.add_field(name="📜 !rolesautorises", value="Voir les rôles autorisés à faire ou voter.", inline=False)
    embed.add_field(name="✅ Système de vote", value="5 votes Confirmer ➔ Ban\n5 votes Refuser ➔ Annulation", inline=False)
    embed.set_footer(text="Noctys - Système Automatisé")
    await ctx.send(embed=embed)

@bot.command(name="rolesautorises")
async def rolesautorises(ctx):
    guild = ctx.guild
    if not guild:
        return

    requester_roles = []
    for role_id in REQUESTER_ROLES:
        role = guild.get_role(role_id)
        requester_roles.append(role.mention if role else f"`ID: {role_id}`")

    validator_roles = []
    for role_id in VALIDATOR_ROLES:
        role = guild.get_role(role_id)
        validator_roles.append(role.mention if role else f"`ID: {role_id}`")

    embed = discord.Embed(
        title="📜 Rôles Autorisés",
        color=discord.Color.blue()
    )
    embed.add_field(name="Peuvent faire une demande", value="\n".join(requester_roles), inline=False)
    embed.add_field(name="Peuvent voter", value="\n".join(validator_roles), inline=False)
    await ctx.send(embed=embed)
bot.run(TOKEN)
