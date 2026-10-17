import discord
from discord import app_commands
from discord.ext import commands
import datetime
import io
import os
from flask import Flask
from threading import Thread

# ==================== SERVIDOR WEB PARA O RENDER (UPTIME) ====================

app = Flask('')

@app.route('/')
def home():
    return "Bot Vision PvP está Online 24/7!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Inicia o servidor em segundo plano antes do bot
keep_alive()

# ==================== CONFIGURAÇÃO DO BOT ====================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.moderation = True
intents.guilds = True
intents.voice_states = True

client = commands.Bot(command_prefix="!", intents=intents)

# ==================== CONFIGURAÇÕES GLOBAIS ====================

CARGO_MEMBRO_ID = 1560996054545993791

# Canais de Logs e Sugestões
CANAL_LOGS_GERAL_ID = 1559685968489877515
CANAL_LOGS_TICKETS_ID = 1559685943143956526
CANAL_TRANSCRIPTS_ID = 1559685972449566760
CANAL_SUGESTOES_ID = 1559686098903371846

# IDs das Categorias dos Tickets
CATEGORIAS_TICKETS = {
    "shop": 1559685733604655135,    # Store / Loja
    "other": 1559685735521456169,   # Outros Assuntos
    "bug": 1559685736402395286,     # Report Bug
    "player": 1559685737446776964,  # Report Player
    "ban": 1559685738445148240      # Ban Appeal / Unbans
}

# Links de Imagens / GIFs
LINK_LOGO_GIF = "https://media.discordapp.net/attachments/1560996055443578911/1561061738798121092/Vision_PVP_gif2.gif?ex=6ad4fb89&is=6ad3aa09&hm=fc97c40e6f3c8d2b6f7deb2a73cd523b5cf85e3eab79559973576c4396403264&="

# Função auxiliar para enviar logs
async def send_log(guild, channel_id, embed, file=None):
    channel = guild.get_channel(channel_id)
    if channel:
        try:
            if file:
                await channel.send(embed=embed, file=file)
            else:
                await channel.send(embed=embed)
        except Exception as e:
            print(f"Erro ao enviar log para {channel_id}: {e}")

# ==================== MODAL DE SUGESTÕES ====================

class SuggestionModal(discord.ui.Modal, title="Vision PvP - Sugestão"):
    sugestao_input = discord.ui.TextInput(
        label="Escreve a tua sugestão:",
        placeholder="Descreve a tua ideia aqui...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user
        texto_sugestao = self.sugestao_input.value

        canal_sugestoes = guild.get_channel(CANAL_SUGESTOES_ID)
        
        if canal_sugestoes:
            embed = discord.Embed(
                description=f"**{member.name}**\n\n{texto_sugestao}",
                color=discord.Color.from_rgb(47, 49, 54)
            )
            embed.set_author(name=member.name, icon_url=member.display_avatar.url)
            embed.set_footer(
                text="Vision PvP",
                icon_url=guild.icon.url if guild.icon else None
            )

            msg = await canal_sugestoes.send(embed=embed)
            await msg.add_reaction("👍")
            await msg.add_reaction("👎")

            try:
                await msg.create_thread(
                    name="SUGGESTION 💡",
                    auto_archive_duration=1440
                )
            except Exception as e:
                print(f"Erro ao criar thread de sugestão: {e}")

            await interaction.response.send_message("A tua sugestão foi enviada com sucesso!", ephemeral=True)
        else:
            await interaction.response.send_message("Erro: O canal de sugestões não foi encontrado.", ephemeral=True)

class SuggestionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Fazer sugestão / Make a suggestion", style=discord.ButtonStyle.secondary, emoji="💡", custom_id="make_suggestion_btn")
    async def suggestion_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SuggestionModal())

# ==================== MODAIS DE TICKETS ====================

class TicketModal(discord.ui.Modal):
    def __init__(self, title, fields, category_key):
        super().__init__(title=f"Vision PvP - {title}")
        self.category_key = category_key
        self.inputs = []
        for label, placeholder in fields:
            input_field = discord.ui.TextInput(
                label=label,
                placeholder=placeholder,
                style=discord.TextStyle.short if "Horas" in label or "ID" in label or "BanID" in label else discord.TextStyle.paragraph,
                required=True
            )
            self.inputs.append(input_field)
            self.add_item(input_field)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user
        category_name = self.title.replace('Vision PvP - ', '')
        
        category_id = CATEGORIAS_TICKETS.get(self.category_key)
        category_obj = guild.get_channel(category_id) if category_id else None

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        channel = await guild.create_text_channel(
            name=f"ticket-{member.name}",
            category=category_obj,
            overwrites=overwrites
        )

        embed = discord.Embed(
            title=f"Ticket: {category_name}",
            description=(
                "🇵🇹 **Para agilizar o processo de resposta deves:**\n"
                "▪ Explicar claramente a informação que pretendes obter;\n"
                "▪ Questionar sobre um assunto que não tenha uma categoria atribuída.\n\n"
                "🇬🇧 **To speed up the response process, you should:**\n"
                "▪ Clearly explain the information you want to obtain;\n"
                "▪ Ask about a topic that does not have a designated category."
            ),
            color=discord.Color.dark_red()
        )
        if LINK_LOGO_GIF.startswith("http"):
            embed.set_thumbnail(url=LINK_LOGO_GIF)
        embed.set_footer(text="Vision PvP • Sistema de Tickets")

        for item in self.inputs:
            field_name = getattr(item, "_label", item.label)
            embed.add_field(name=field_name, value=f"```\n{item.value}\n```", inline=False)

        view = CloseTicketView(ticket_owner=member, ticket_category=category_name)
        await channel.send(
            content=f"Opened by: {member.mention}\nWait patiently for a response from our Staff Team.\nDo not mention any member of the Team.",
            embed=embed,
            view=view
        )

        await interaction.response.send_message(f"O teu ticket foi criado em {channel.mention}!", ephemeral=True)

        log_embed = discord.Embed(
            title="🎟️ Novo Ticket Aberto",
            color=discord.Color.green(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        log_embed.set_thumbnail(url=member.display_avatar.url)
        log_embed.add_field(name="Utilizador", value=f"{member.mention}\n(`{member.id}`)", inline=True)
        log_embed.add_field(name="Categoria", value=f"`{category_name}`", inline=True)
        log_embed.add_field(name="Canal", value=f"{channel.mention}", inline=False)
        log_embed.set_footer(text="Vision PvP • Logs de Tickets")
        await send_log(guild, CANAL_LOGS_TICKETS_ID, log_embed)

class CloseTicketView(discord.ui.View):
    def __init__(self, ticket_owner=None, ticket_category="Geral"):
        super().__init__(timeout=None)
        self.ticket_owner = ticket_owner
        self.ticket_category = ticket_category

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close_ticket_btn")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("A fechar o ticket e a gerar o transcript...")
        
        channel = interaction.channel
        guild = interaction.guild
        closed_by = interaction.user
        owner = self.ticket_owner or closed_by

        messages = []
        async for msg in channel.history(limit=1000, oldest_first=True):
            time_str = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
            content = msg.content if msg.content else "[Embed / Anexo]"
            messages.append(f"[{time_str}] {msg.author.name} ({msg.author.id}): {content}")

        transcript_text = f"=== VISION PVP - TRANSCRIPT DO TICKET ===\n"
        transcript_text += f"Canal: #{channel.name}\n"
        transcript_text += f"Categoria: {self.ticket_category}\n"
        transcript_text += f"Aberto por: {owner.name} ({owner.id})\n"
        transcript_text += f"Fechado por: {closed_by.name} ({closed_by.id})\n"
        transcript_text += f"Data de Fecho: {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
        transcript_text += "=========================================\n\n"
        transcript_text += "\n".join(messages)

        buffer = io.BytesIO(transcript_text.encode("utf-8"))
        file = discord.File(fp=buffer, filename=f"transcript-{channel.name}.txt")

        transcript_embed = discord.Embed(
            title="📄 Transcript Gerado",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        transcript_embed.add_field(name="Canal", value=f"`#{channel.name}`", inline=True)
        transcript_embed.add_field(name="Categoria", value=f"`{self.ticket_category}`", inline=True)
        transcript_embed.add_field(name="Aberto por", value=f"{owner.mention}\n(`{owner.id}`)", inline=True)
        transcript_embed.add_field(name="Fechado por", value=f"{closed_by.mention}\n(`{closed_by.id}`)", inline=True)
        transcript_embed.set_footer(text="Vision PvP • Sistema de Transcripts")
        await send_log(guild, CANAL_TRANSCRIPTS_ID, transcript_embed, file=file)

        close_log_embed = discord.Embed(
            title="🔒 Ticket Fechado",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        close_log_embed.add_field(name="Canal", value=f"`#{channel.name}`", inline=True)
        close_log_embed.add_field(name="Categoria", value=f"`{self.ticket_category}`", inline=True)
        close_log_embed.add_field(name="Fechado por", value=f"{closed_by.mention} (`{closed_by.id}`)", inline=False)
        close_log_embed.set_footer(text="Vision PvP • Logs de Tickets")
        await send_log(guild, CANAL_LOGS_TICKETS_ID, close_log_embed)

        await discord.utils.sleep_until(discord.utils.utcnow() + datetime.timedelta(seconds=3))
        await channel.delete()

class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Loja / Shop", description="Information about the store.", emoji="🛒", value="shop"),
            discord.SelectOption(label="Outros Assuntos / Other subjects", description="Other matters.", emoji="🌍", value="other"),
            discord.SelectOption(label="Report Bug", description="Bug reports.", emoji="🔧", value="bug"),
            discord.SelectOption(label="Report Player", description="Player reports.", emoji="👤", value="player"),
            discord.SelectOption(label="Ban Appeal", description="Ban appeals.", emoji="⛔", value="ban")
        ]
        super().__init__(
            placeholder="Select one of the options...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="ticket_select_menu"
        )

    async def callback(self, interaction: discord.Interaction):
        selection = self.values[0]
        if selection == "shop":
            modal = TicketModal("Loja / Shop", [("Motivo/Reason:", "Aqui/Here")], category_key="shop")
        elif selection == "other":
            modal = TicketModal("Outros Assuntos", [("Motivo/Reason:", "Aqui/Here")], category_key="other")
        elif selection == "bug":
            modal = TicketModal("Report Bug", [("Descrever o bug/Describe the bug:", "Aqui/Here")], category_key="bug")
        elif selection == "player":
            modal = TicketModal("Report Player", [("Motivo/Reason:", "Aqui/Here"), ("ID do player / ID of the player", "1"), ("Horas do acontecido / Hours of what happened", "23:59")], category_key="player")
        elif selection == "ban":
            modal = TicketModal("Ban Appeal", [("Motivo/Reason:", "Aqui/Here"), ("BanID", "BanID: SSMM-6XX9 or 666a1s69")], category_key="ban")

        await interaction.response.send_modal(modal)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

# ==================== EVENTOS E LOGS ====================

@client.event
async def on_ready():
    client.add_view(TicketView())
    client.add_view(CloseTicketView())
    client.add_view(SuggestionView())
    
    try:
        synced = await client.tree.sync()
        print(f"Sincronizados {len(synced)} comandos slash com sucesso.")
    except Exception as e:
        print(f"Erro ao sincronizar comandos slash: {e}")

    print(f'Bot Vision PvP Online como: {client.user}')

@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    raise error

@client.event
async def on_member_join(member):
    role = member.guild.get_role(CARGO_MEMBRO_ID)
    if role:
        try:
            await member.add_roles(role)
        except Exception as e:
            print(f"Erro ao atribuir cargo: {e}")

    embed = discord.Embed(title="📥 Novo Membro no Servidor", color=discord.Color.green(), timestamp=datetime.datetime.now(datetime.timezone.utc))
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Utilizador", value=f"{member.mention}\n(`{member.name}`)", inline=True)
    embed.add_field(name="ID", value=f"`{member.id}`", inline=True)
    embed.add_field(name="Conta Criada", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=False)
    embed.set_footer(text=f"Vision PvP • Total de membros: {member.guild.member_count}")
    await send_log(member.guild, CANAL_LOGS_GERAL_ID, embed)

@client.event
async def on_member_remove(member):
    embed = discord.Embed(title="📤 Membro Saiu do Servidor", color=discord.Color.red(), timestamp=datetime.datetime.now(datetime.timezone.utc))
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Utilizador", value=f"{member.mention}\n(`{member.name}`)", inline=True)
    embed.add_field(name="ID", value=f"`{member.id}`", inline=True)
    embed.set_footer(text=f"Vision PvP • Total de membros: {member.guild.member_count}")
    await send_log(member.guild, CANAL_LOGS_GERAL_ID, embed)

@client.event
async def on_message_delete(message):
    if message.author.bot or not message.guild:
        return
    embed = discord.Embed(title="🗑️ Mensagem Apagada", color=discord.Color.orange(), timestamp=datetime.datetime.now(datetime.timezone.utc))
    embed.add_field(name="Autor", value=f"{message.author.mention} (`{message.author.id}`)", inline=False)
    embed.add_field(name="Canal", value=f"{message.channel.mention}", inline=False)
    content = message.content if message.content else "[Conteúdo vazio / Imagem / Anexo]"
    if len(content) > 1024:
        content = content[:1021] + "..."
    embed.add_field(name="Conteúdo", value=f"```\n{content}\n```", inline=False)
    embed.set_footer(text="Vision PvP • Sistema de Logs")
    await send_log(message.guild, CANAL_LOGS_GERAL_ID, embed)

@client.event
async def on_message_edit(before, after):
    if before.author.bot or not before.guild or before.content == after.content:
        return
    embed = discord.Embed(title="✏️ Mensagem Editada", color=discord.Color.blue(), timestamp=datetime.datetime.now(datetime.timezone.utc))
    embed.add_field(name="Autor", value=f"{before.author.mention} (`{before.author.id}`)", inline=False)
    embed.add_field(name="Canal", value=f"{before.channel.mention}", inline=False)
    
    b_content = before.content if before.content else "[Vazio]"
    a_content = after.content if after.content else "[Vazio]"
    if len(b_content) > 500: b_content = b_content[:497] + "..."
    if len(a_content) > 500: a_content = a_content[:497] + "..."

    embed.add_field(name="Antes", value=f"```\n{b_content}\n```", inline=False)
    embed.add_field(name="Depois", value=f"```\n{a_content}\n```", inline=False)
    embed.set_footer(text="Vision PvP • Sistema de Logs")
    await send_log(before.guild, CANAL_LOGS_GERAL_ID, embed)

@client.event
async def on_member_update(before, after):
    if before.nick != after.nick:
        embed = discord.Embed(title="👤 Alcunha Alterada", color=discord.Color.gold(), timestamp=datetime.datetime.now(datetime.timezone.utc))
        embed.set_thumbnail(url=after.display_avatar.url)
        embed.add_field(name="Utilizador", value=f"{after.mention} (`{after.id}`)", inline=False)
        embed.add_field(name="Antiga Alcunha", value=f"`{before.nick or before.name}`", inline=True)
        embed.add_field(name="Nova Alcunha", value=f"`{after.nick or after.name}`", inline=True)
        embed.set_footer(text="Vision PvP • Logs de Membros")
        await send_log(after.guild, CANAL_LOGS_GERAL_ID, embed)

    elif len(before.roles) != len(after.roles):
        added = [r for r in after.roles if r not in before.roles]
        removed = [r for r in before.roles if r not in after.roles]
        
        embed = discord.Embed(title="🛡️ Cargos Atualizados", color=discord.Color.purple(), timestamp=datetime.datetime.now(datetime.timezone.utc))
        embed.set_thumbnail(url=after.display_avatar.url)
        embed.add_field(name="Utilizador", value=f"{after.mention} (`{after.id}`)", inline=False)
        if added:
            embed.add_field(name="Cargos Adicionados", value=", ".join([r.mention for r in added]), inline=False)
        if removed:
            embed.add_field(name="Cargos Removidos", value=", ".join([r.mention for r in removed]), inline=False)
        embed.set_footer(text="Vision PvP • Logs de Cargos")
        await send_log(after.guild, CANAL_LOGS_GERAL_ID, embed)

@client.event
async def on_guild_channel_create(channel):
    embed = discord.Embed(title="📁 Canal Criado", description=f"O canal **{channel.name}** (`{channel.id}`) foi criado.", color=discord.Color.green(), timestamp=datetime.datetime.now(datetime.timezone.utc))
    embed.set_footer(text="Vision PvP")
    await send_log(channel.guild, CANAL_LOGS_GERAL_ID, embed)

@client.event
async def on_guild_channel_delete(channel):
    embed = discord.Embed(title="📁 Canal Apagado", description=f"O canal **{channel.name}** (`{channel.id}`) foi apagado.", color=discord.Color.red(), timestamp=datetime.datetime.now(datetime.timezone.utc))
    embed.set_footer(text="Vision PvP")
    await send_log(channel.guild, CANAL_LOGS_GERAL_ID, embed)

@client.event
async def on_member_ban(guild, user):
    embed = discord.Embed(title="🔨 Utilizador Banido", description=f"{user.mention} (`{user.name}` - `{user.id}`)", color=discord.Color.dark_red(), timestamp=datetime.datetime.now(datetime.timezone.utc))
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.set_footer(text="Vision PvP • Moderação")
    await send_log(guild, CANAL_LOGS_GERAL_ID, embed)

@client.event
async def on_member_unban(guild, user):
    embed = discord.Embed(title="🔓 Utilizador Desbanido", description=f"{user.mention} (`{user.name}` - `{user.id}`)", color=discord.Color.teal(), timestamp=datetime.datetime.now(datetime.timezone.utc))
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.set_footer(text="Vision PvP • Moderação")
    await send_log(guild, CANAL_LOGS_GERAL_ID, embed)

# ==================== COMANDOS DO BOT ====================

@client.tree.command(name="sugestao", description="Envia uma sugestão para o servidor Vision PvP.")
async def sugestao_slash(interaction: discord.Interaction):
    await interaction.response.send_modal(SuggestionModal())

@client.command()
@commands.has_permissions(administrator=True)
async def sugestao(ctx):
    try:
        await ctx.message.delete()
    except Exception:
        pass

    embed = discord.Embed(
        title="Vision PvP - Suggestions",
        description=(
            "🇵🇹 Clica no botão abaixo para escrever e enviar a tua sugestão.\n"
            "🇬🇧 Click the button below to write and submit your suggestion."
        ),
        color=discord.Color.dark_red()
    )
    embed.set_footer(text="Vision PvP")

    await ctx.send(embed=embed, view=SuggestionView())

@client.command()
@commands.has_permissions(administrator=True)
async def ticket(ctx):
    try:
        await ctx.message.delete()
    except Exception:
        pass
    
    embed = discord.Embed(
        title="Vision PvP - Tickets",
        description="Select the category of your ticket below:",
        color=discord.Color.dark_red()
    )
    if LINK_LOGO_GIF.startswith("http"):
        embed.set_image(url=LINK_LOGO_GIF)
    
    embed.set_footer(text="Vision PvP")

    await ctx.send(embed=embed, view=TicketView())

# Substitui 'O_TEU_TOKEN_AQUI' pelo teu token real do Discord (ou usa variável de ambiente no Render)
# Passa o token diretamente como string entre aspas
client.run('MTU2MTA1NTc4MTEzMzA5OTA3OQ.G94LP-.pywS2qRV8QtFb4SUtB-bqEzI3Zh9BOUCEq4R6E')