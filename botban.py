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
                        description=(
                            f"Vous avez été banni du serveur **Noctys** pour la raison suivante :\n\n{self.reason}\n\n"
                            "Pour faire une demande de débannissement, rejoignez :\n**https://discord.gg/yGuj5A7Hpa**"
                        ),
                        color=discord.Color.red()
                    )
                    dm_embed.set_footer(text="Noctys - Système Automatisé")
                    if target_member.avatar:
                        dm_embed.set_thumbnail(url=target_member.avatar.url)
                    await target_member.send(embed=dm_embed)
                except:
                    pass

                await target_member.ban(reason=self.reason)

                log_channel = bot.get_channel(LOG_CHANNEL_ID)
                if log_channel:
                    confirmateurs = []
                    for user_id in self.confirm_votes:
                        try:
                            user = await bot.fetch_user(user_id)
                            confirmateurs.append(f"• {user.mention}")
                        except:
                            confirmateurs.append(f"• ID {user_id}")
                    confirmeurs_text = "\n".join(confirmateurs) if confirmateurs else "Aucun"

                    log_embed = discord.Embed(
                        title="✅ Bannissement Validé",
                        description=(
                            f"**Membre banni :** {target_member} (`{self.target_id}`)\n"
                            f"**Raison :** {self.reason}\n\n"
                            f"**✅ Confirmé par :**\n{confirmeurs_text}"
                        ),
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

# Event & commandes ajoutées identiques...

bot.run(TOKEN)
