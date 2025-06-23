
import discord
from discord import app_commands
from discord.ext import commands
import os

TOKEN = os.getenv("TOKEN")
GUILD_ID = 1361778893681463436
CHANNEL_ID = 1379270661360451737
LOG_CHANNEL_ID = 1379271417392009216

REQUESTER_ROLES = [
    1379268686141063289, 1379268700145717374, 1379268712250474516,
    1379268737206714408, 1379268752335569036, 1379268744991215769,
    1379268795536769137, 1379268792122605619, 1379268763605532763,
    1379268759239528499, 1379268748824940575, 1379268777765638243,
    1379268770727596093
]

VALIDATOR_ROLES = [
    1379268686141063289, 1379268700145717374
]

PRIORITY_ROLES = [1379268686141063289, 1379268700145717374]
VOTE_THRESHOLD = 5

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

class BanView(discord.ui.View):
    def __init__(self, target, reason, image_url, requester_id):
        super().__init__(timeout=86400)
        self.target = target
        self.reason = reason
        self.image_url = image_url
        self.requester_id = requester_id
        self.yes_votes = set()
        self.no_votes = set()
        self.message = None

    async def update_view(self):
        self.yes_button.label = f"✅ Oui ({len(self.yes_votes)}/5)"
        self.no_button.label = f"❌ Non ({len(self.no_votes)}/5)"
        await self.message.edit(view=self)

    async def finalize(self, approved, interaction):
        embed = self.message.embeds[0]
        if approved:
            embed.title = "✅ Bannissement approuvé"
            embed.color = discord.Color.green()
            try:
                await self.target.send(
                    f"👑 Tu as été banni du serveur Noctys pour : {self.reason}
Tu peux faire une demande de déban ici : https://discord.gg/yGuj5A7Hpa"
                )
            except:
                pass
            await self.message.guild.ban(self.target, reason=self.reason)
            log = discord.Embed(
                title="🚨 Bannissement exécuté",
                description=f"👤 {self.target} (`{self.target.id}`)
📎 Raison : {self.reason}",
                color=discord.Color.red()
            )
            log.add_field(name="✅ Votants", value="\n".join(f"<@{uid}>" for uid in self.yes_votes), inline=False)
            await bot.get_channel(LOG_CHANNEL_ID).send(embed=log)
        else:
            embed.title = "❌ Demande annulée"
            embed.color = discord.Color.red()
        await self.message.edit(embed=embed, view=None)
        self.stop()

    @discord.ui.button(label="✅ Oui (0/5)", style=discord.ButtonStyle.success)
    async def yes_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not any(role.id in VALIDATOR_ROLES for role in interaction.user.roles):
            await interaction.response.send_message("⛔ Tu ne peux pas voter.", ephemeral=True)
            return
        self.no_votes.discard(interaction.user.id)
        self.yes_votes.add(interaction.user.id)
        await self.update_view()
        if len(self.yes_votes) >= VOTE_THRESHOLD:
            await self.finalize(True, interaction)
        await interaction.response.defer()

    @discord.ui.button(label="❌ Non (0/5)", style=discord.ButtonStyle.danger)
    async def no_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not any(role.id in VALIDATOR_ROLES for role in interaction.user.roles):
            await interaction.response.send_message("⛔ Tu ne peux pas voter.", ephemeral=True)
            return
        self.yes_votes.discard(interaction.user.id)
        self.no_votes.add(interaction.user.id)
        await self.update_view()
        if len(self.no_votes) >= VOTE_THRESHOLD:
            await self.finalize(False, interaction)
        await interaction.response.defer()

    @discord.ui.button(label="🛑 Annuler", style=discord.ButtonStyle.secondary, row=1)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.requester_id and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("⛔ Tu ne peux pas annuler cette demande.", ephemeral=True)
            return
        await self.finalize(False, interaction)
        await interaction.response.send_message("🚫 Demande annulée.", ephemeral=True)

@bot.event
async def on_ready():
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f"✅ Connecté en tant que {bot.user}")

@bot.tree.command(name="demandeban", description="Créer une demande de ban", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(
    membre="Membre à bannir",
    raison="Raison du bannissement",
    preuve="Lien ou explication",
    image="Image en pièce jointe (facultatif)"
)
async def demandeban(interaction: discord.Interaction, membre: discord.Member, raison: str, preuve: str = None, image: discord.Attachment = None):
    if not any(role.id in REQUESTER_ROLES for role in interaction.user.roles):
        await interaction.response.send_message("⛔ Tu n'as pas la permission.", ephemeral=True)
        return

    mention_text = " ".join(f"<@&{rid}>" for rid in PRIORITY_ROLES)
    embed = discord.Embed(
        title="🚨 Nouvelle demande de bannissement",
        description=mention_text,
        color=discord.Color.orange()
    )
    embed.set_author(
        name=f"{membre} ({membre.id})",
        icon_url=membre.display_avatar.url if membre.display_avatar else None
    )
    embed.add_field(name="📎 Raison", value=raison, inline=False)
    if preuve:
        embed.add_field(name="🧾 Preuve", value=preuve, inline=False)
    embed.set_footer(
        text=f"Demandée par {interaction.user}",
        icon_url=interaction.user.avatar.url if interaction.user.avatar else None
    )
    embed.set_thumbnail(url=membre.display_avatar.url if membre.display_avatar else None)
    if image and hasattr(image, "content_type") and image.content_type and image.content_type.startswith("image/"):
        embed.set_image(url=image.url)

    view = BanView(membre, raison, image.url if image else None, interaction.user.id)
    sent = await bot.get_channel(CHANNEL_ID).send(content=mention_text, embed=embed, view=view)
    view.message = sent
    await interaction.response.send_message("✅ Demande envoyée avec succès.", ephemeral=True)

@bot.tree.command(name="helpban", description="Affiche l'aide des commandes disponibles", guild=discord.Object(id=GUILD_ID))
async def helpban(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📚 Aide - Système de bannissement",
        description="Voici les commandes et leur fonctionnement :",
        color=discord.Color.blurple()
    )
    embed.add_field(name="/demandeban", value="Créer une demande de bannissement avec preuve et image.", inline=False)
    embed.add_field(name="✅ Votes requis", value="5 votes positifs ou négatifs valident ou annulent automatiquement.", inline=False)
    embed.add_field(name="📬 MP automatique", value="Un message privé est envoyé à la personne bannie avec la raison et un lien de recours.", inline=False)
    embed.set_footer(text="Noctys - Tribunal Automatisé")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="rolesautorises", description="Liste des rôles autorisés à voter ou créer une demande", guild=discord.Object(id=GUILD_ID))
async def rolesautorises(interaction: discord.Interaction):
    guild = interaction.guild
    req_roles = [guild.get_role(r) for r in REQUESTER_ROLES]
    val_roles = [guild.get_role(r) for r in VALIDATOR_ROLES]
    embed = discord.Embed(title="📋 Rôles autorisés", color=discord.Color.blue())
    embed.add_field(
        name="Peuvent faire une demande",
        value="\n".join(role.mention for role in req_roles if role is not None) or "Aucun",
        inline=False
    )
    embed.add_field(
        name="Peuvent voter",
        value="\n".join(role.mention for role in val_roles if role is not None) or "Aucun",
        inline=False
    )
    embed.set_footer(text="Mis à jour automatiquement")
    await interaction.response.send_message(embed=embed, ephemeral=True)

bot.run(TOKEN)

