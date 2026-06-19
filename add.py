import json
import discord
from discord.ext import commands
from discord import app_commands, ButtonStyle, ui, SelectOption
from discord.ui import View, button, Modal, Button
from discord.errors import HTTPException, NotFound
from func.dc import Bot
from .func.db import Tag_DB
from func.log import get_log
from .func.tools import tc_ob
from pydantic import BaseModel


class check1(View):
    def __init__(self, *, bot: commands.Bot, timeout: float | None = 180):
        super().__init__(timeout=timeout)
        self.bot = bot
    
    @button(label="OK", style=ButtonStyle.primary)
    async def ok_button(self, interaction:discord.Interaction, button: ui.Button):
        embed = discord.Embed(
            title="タグ申請",
            description="下のボタンから情報を入力してください",
            colour=discord.Colour.green()
        ).add_field(
            name="タグ名",
            value="未記入",
        ).add_field(
            name="招待リンク",
            value="未記入",
        ).add_field(
            name="アクセス範囲",
            value="未記入",
        ).add_field(
            name="主言語",
            value="未記入",
        ).add_field(
            name="サーバー名",
            value="未取得",
            inline=False
        )
        view = FormView(bot=self.bot)
        await interaction.response.edit_message(
            embed=embed,
            view=view
        )

class FormView(ui.View):
    def __init__(self, bot:commands.Bot, message:discord.Message, timeout = None):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.message = message
        self.add_item(FormBtTagName(bot=bot))
        self.add_item(FormBtInvite(bot=bot, message=message))
        self.add_item(FormBtCategory(bot=bot, message=message))
        self.add_item(FormBtLang(bot=bot, message=message))

class FormBtTagName(Button):
    def __init__(self, bot:commands.Bot, message:discord.Message):
        self.bot = bot
        self.message = message
        super().__init__(style=ButtonStyle.green, label="タグ名")
    async def callback(self, interaction:discord.Interaction):
        await interaction.response.send_modal(FormName(bot=self.bot, message=self.message))
class FormName(Modal):
    def __init__(self, bot:commands.Bot, message:discord.Message) -> None:
        super().__init__(title="タグの名前", custom_id=f"tc-add-name-md-{message.id}")
        self.bot = bot
        self.message = message
        self.name = ui.Label(
            text="タグ名を入力してください",
            component=ui.TextInput(
                style=discord.TextStyle.short,
                required=True,
                min_length=1,
                max_length=4
            )
        )
        self.add_item(self.name)
    
    async def on_submit(self, interaction: discord.Interaction) -> None:
        embed = interaction.message.embeds[0]
        for field in embed.fields:
            if field.name == "タグ名":
                field.value = self.name.component.value
        await interaction.response.edit_message(
            embed=embed
        )

class FormBtInvite(Button):
    def __init__(self, bot:commands.Bot, message:discord.Message):
        self.bot = bot
        self.message = message
        super().__init__(style=ButtonStyle.green, label="招待リンク")
    async def callback(self, interaction:discord.Interaction):
        await interaction.response.send_modal(FormInvite(bot=self.bot, message=self.message))
class FormInvite(Modal):
    def __init__(self, bot:commands.Bot, message:discord.Message) -> None:
        super().__init__(title="招待リンクを入力してください", custom_id=f"tc-add-invite-md-{message.id}")
        self.bot = bot
        self.message = message
        self.invite = ui.Label(
            text="招待リンク",
            component=ui.TextInput(
                style=discord.TextStyle.short,
                required=True
            )
        )
        self.add_item(self.invite)
    
    async def on_submit(self, interaction: discord.Interaction) -> None:
        embed = interaction.message.embeds[0]
        try:
            invite = await self.bot.fetch_invite(self.invite.component.value)
        except HTTPException:
            await interaction.response.send_message(embed=discord.Embed(
                title="エラー",
                description="招待の取得に失敗しました。\nもう一度入力してください。",
                colour=discord.Colour.red()
            ), ephemeral=True)
        except ValueError:
            await interaction.response.send_message(embed=discord.Embed(
                title="エラー",
                description="招待の形式が間違っています。\nもう一度入力してください。",
                colour=discord.Colour.red()
            ), ephemeral=True)
        except NotFound:
            await interaction.response.send_message(embed=discord.Embed(
                title="エラー",
                description="招待リンクが見つかりませんでした。\nもう一度入力してください。",
                colour=discord.Colour.red()
            ), ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(embed=discord.Embed(
                title="エラー",
                description=f"招待の取得中にエラーが発生しました。\n```{e}```",
                colour=discord.Colour.red()
            ), ephemeral=True)
        if invite.type != discord.InviteType.guild:
            await interaction.response.send_message(embed=discord.Embed(
                title="エラー",
                description="リンクがサーバー招待ではありません。\nもう一度入力してください。",
                colour=discord.Colour.red()
            ), ephemeral=True)
            return
        if "GUILD_TAGS" not in invite.guild.features:
            await interaction.response.send_message(embed=discord.Embed(
                title="エラー",
                description="指定された招待リンクのサーバーはタグがありません。",
                colour=discord.colour.red()
            ), ephemeral=True)
            return
        for field in embed.fields:
            if field.name == "招待リンク":
                field.value = self.invite.component.value
            elif field.name == "サーバー名":
                field.value = invite.guild.name
        if invite.guild.icon:
            embed.set_thumbnail(url=invite.guild.icon.url)
        await interaction.response.edit_message(
            embed=embed
        )

class FormBtCategory(Button):
    def __init__(self, bot:commands.Bot, message:discord.Message):
        self.bot = bot
        self.message = message
        super().__init__(style=ButtonStyle.green, label="アクセス範囲")
    async def callback(self, interaction:discord.Interaction):
        await interaction.response.send_message(
            content="アクセス範囲を選択してください。",
            view=FormVCategory(bot=self.bot, message=self.message)
        )
class FormVCategory(View):
    def __init__(self, bot:commands.Bot, message:discord.Message, timeout = None, selected:str = None):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.message = message
class FormSlCategory(ui.Select):
    def __init__(self, bot:commands.Bot, message:discord.Message):
        super().__init__(
            options=[
                SelectOption(label="標準", value="標準"),
                SelectOption(label="参加申請", value="参加申請")
            ],
            custom_id=f"tc-add-category-sl-{message.id}"
        )
        self.bot = bot
        self.message = message
    async def callback(self, interaction:discord.Interaction):
        embed = interaction.message.embeds[0]
        for field in embed.fields:
            if field.name == "アクセス範囲":
                field.value = self.values[0]
        await self.message.edit(
            embed=embed
        )
        await interaction.message.delete()

class FormBtLang(Button):
    def __init__(self, bot:commands.Bot, message:discord.Message):
        self.bot = bot
        self.message = message
        super().__init__(style=ButtonStyle.green, label="主言語")
    async def callback(self, interaction:discord.Interaction):
        await interaction.response.send_message(
            content="主言語を選択してください。",
            view=FormVLang(bot=self.bot, message=self.message)
        )
class FormVLang(View):
    def __init__(self, bot:commands.Bot, message:discord.Message, timeout = None, selected:str = None):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.message = message
        self.add_item(FormSlLang(bot=bot, message=message))
class FormSlLang(ui.Select):
    def __init__(self, bot:commands.Bot, message:discord.Message):
        super().__init__(
            options=[
                SelectOption(label="Japanese", value="Japanese"),
                SelectOption(label="English", value="English"),
                SelectOption(label="Chinese", value="Chinese")
            ],
            custom_id=f"tc-add-lang-sl-{message.id}"
        )
        self.bot = bot
        self.message = message
    async def callback(self, interaction:discord.Interaction):
        embed = interaction.message.embeds[0]
        for field in embed.fields:
            if field.name == "主言語":
                field.value = self.values[0]
        await self.message.edit(
            embed=embed
        )
        await interaction.message.delete()

class Field(BaseModel):
    value:str
    inline:bool

class FormBtSubmit(ui.Button):
    def __init__(self, bot:commands.Bot, message:discord.Message):
        super().__init__(style=ButtonStyle.primary, label="送信", disabled=True)
    async def callback(self, interaction:discord.Interaction):
        embed = interaction.message.embeds[0]
        fields:object[str, Field] = {}
        for field in embed.fields:
            fields[field.name] = Field(value=field.value, inline=field.inline)

# --------------------------------------------

class Form(Modal):
    def __init__(self, bot:commands.Bot) -> None:
        super().__init__(title="サーバー情報の入力")
        self.bot = bot
        self.invite = ui.Label(
            text="招待リンク",
            component=ui.TextInput(
                style=discord.TextStyle.short,
                required=True,
                placeholder="https://discord.gg/~~"
            )
        )
        self.lang = ui.Label(
            text="サーバーの主言語",
            component=ui.Select(
                required=True,
                options=[
                    SelectOption(label="日本語", value="Japanese"),
                    SelectOption(label="英語", value="English"),
                    SelectOption(label="中国語", value="Chinese")
                ],
                min_values=1,
                max_values=1
            )
        )
        self.kind = ui.Label(
            text="アクセス範囲",
            component=ui.Select(
                required=True,
                options=[
                    SelectOption(label="標準", value=0),
                    SelectOption(label="参加申請", value=1)
                ],
                min_values=1,
                max_values=1
            )
        )
        self.add_item(self.name).add_item(self.invite).add_item(self.lang).add_item(self.kind)
    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            await interaction.response.defer(ephemeral=True)
            invite = await self.bot.fetch_invite(self.invite.component.value)
            if invite.type != discord.InviteType.guild:
                raise Exception("指定されたURLはサーバー招待ではありません。")
            if "GUILD_TAGS" not in invite.guild.features:
                raise Exception("指定された招待リンクのサーバーはギルドタグを持っていないようです。")
            channel = self.bot.get_channel(1408781350399508484)
            await channel.send(
                content=f"Tag-Info{self.invite.component.value}",
                embeds=[
                    discord.Embed(
                        title="タグの申請",
                        description=f"""
タグ名: `{self.name.component.value}`
招待リンク: `{self.invite.component.value}`
主言語: `{self.lang.component.values[0]}`
アクセス範囲: `{"標準" if self.kind.component.values[0] == 0 else "参加申請"}`
                        """
                    ),
                    discord.Embed(
                        description=json.dumps({
                            "name": self.name.component.value,
                            "invite": self.invite.component.value,
                            "lang": self.lang.component.values[0],
                            "at_id": interaction.user.id,
                            "kind": self.kind.component.values[0]
                        }, ensure_ascii=False)
                    )
                ]
            )
            await interaction.followup.send("申請を行いました。", ephemeral=True)
        except NotFound as e:
            await interaction.followup.send(embed=discord.Embed(
                title="エラー",
                description=f"招待リンクが有効ではありません。\n```{e}```",
                colour=discord.Colour.red()
            ))
            self.log.error(e)
        except HTTPException as e:
            await interaction.followup.send(embed=discord.Embed(
                title="エラー",
                description=f"招待リンクの取得に失敗しました。\n```{e}```",
                colour=discord.Colour.red()
            ))
            self.log.error(e)
        except Exception as e:
            await interaction.followup.send(embed=discord.Embed(
                title="エラー",
                description=f"タグの追加中にエラーが発生しました。\n```{e}```",
                colour=discord.Colour.red()
            ))
            self.log.error(e)

class AddCog(commands.Cog):
    def __init__(self, bot:Bot):
        self.bot = bot
        self.log = get_log("AddCog")
        self.DB = Tag_DB()
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.log.info(f"AddCogを読み込みました!")
    
    @app_commands.command(name="add", description="タグの追加を申請します")
    @app_commands.guilds(tc_ob)
    async def add(self, interaction:discord.Interaction):
        await interaction.response.send_message(
            embed=discord.Embed(
                title="タグの申請",
                description="""\
タグの追加を申請します。
以下の注意事項を読んでからOKボタンを押してください。
```
・タグが有効化されていないサーバーは入力しないでください。(弾かれます)
・荒らし、Shop鯖などは入力しないでください。(審査時に弾かれます)
```
""",
                colour=discord.Colour.green()
            ),
            ephemeral=True,
            view=check1(bot=self.bot)
        )

async def setup(bot):
    await bot.add_cog(AddCog(bot))
