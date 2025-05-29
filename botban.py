
import discord
from discord import app_commands
from discord.ext import commands
import os

TOKEN = os.getenv("TOKEN")
GUILD_ID = 1360356060229013605
CHANNEL_ID = 1366186686907944982
LOG_CHANNEL_ID = 1363252748820287761

REQUESTER_ROLES = [
    1365837084233039932, 1362033700946186301, 1362033883482296380,
    1362033723121602612, 1362033735910031493, 1365894628569518110,
    1362033746601316622, 1362033753538564288, 1374914013762424842,
    1362033760534663419, 1362033782357496020, 
]

VALIDATOR_ROLES = [
    1365837084233039932, 1362033700946186301,
    1362033723121602612
]

PRIORITY_ROLES = [1365837084233039932, 1362033723121602612]
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
                    f"👑 Tu as été banni du serveur Noctys pour : {self.reason}\nTu peux faire une demande de déban ici : https://discord.gg/yGuj5A7Hpa"
                )
            except:
                pass
            await self.message.guild.ban(self.target, reason=self.reason)
            log = discord.Embed(
                title="🚨 Bannissement exécuté",
                description=f"👤 {self.target} (`{self.target.id}`)\n📎 Raison : {self.reason}",
                color=discord.Color.red()
            )
            log.add_field(name="✅ Votants", value="\n".join(f"<@{uid}>" for uid in self.yes_votes), inline=False)
            await bot.get_channel(LOG_CHANNEL_ID).send(embed=log)
        else:
            embed.title = "❌ Demande refusée"
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

@bot.event
async def on_ready():
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f"✅ Connecté en tant que {bot.user}")

@bot.tree.command(name="demandeban", description="Créer une demande de ban", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(
    membre="Membre à bannir",
    raison="Raison du bannissement",
    preuve="Lien de l'image (facultatif)"
)
async def demandeban(interaction: discord.Interaction, membre: discord.Member, raison: str, preuve: str = None):
    if not any(role.id in REQUESTER_ROLES for role in interaction.user.roles):
        await interaction.response.send_message("⛔ Tu n'as pas la permission.", ephemeral=True)
        return
    mention_text = " ".join(f"<@&{rid}>" for rid in PRIORITY_ROLES)
    embed = discord.Embed(
        title="🚨 Nouvelle demande de bannissement",
        description=mention_text,
        color=discord.Color.orange()
    )
    embed.add_field(name="👤 Membre", value=f"{membre} (`{membre.id}`)", inline=False)
    embed.add_field(name="📎 Raison", value=raison, inline=False)
    embed.set_footer(text=f"Demandée par {interaction.user}", icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
    if preuve:
        embed.set_image(url=preuve)
    view = BanView(membre, raison, preuve, interaction.user.id)
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
    embed.add_field(name="/demandeban", value="Créer une demande de bannissement avec preuve et raison.", inline=False)
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
