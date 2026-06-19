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
from typing import Union
import datetime
from .func import lang as Langs

class check1(View):
    def __init__(self, *, bot: commands.Bot, timeout: float | None = 180):
        super().__init__(timeout=timeout)
        self.bot = bot
    
    @button(label="OK", style=ButtonStyle.primary)
    async def ok_button(self, interaction:discord.Interaction, button: ui.Button):
        view = FormView(bot=self.bot, message=interaction.message)
        await interaction.response.edit_message(
            embed=view.format_message(),
            view=view
        )

class AddData(BaseModel):
    tag_name: str = None
    invite_url: str = None
    category: str = None
    lang: str = None
    invite: discord.Invite = None

    model_config = {
        "arbitrary_types_allowed": True
    }

class FormView(ui.View):
    def __init__(self, bot:commands.Bot, message:discord.Message, timeout = None):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.message = message
        self.data = AddData()
        self.submit = FormBtSubmit(parent_view=self)
        self.add_item(FormBtTagName(parent_view=self))
        self.add_item(FormBtInvite(parent_view=self))
        self.add_item(FormBtCategory(parent_view=self))
        self.add_item(FormBtLang(parent_view=self))
        self.add_item(self.submit)
    
    def format_message(self) -> discord.Embed:
        embed = discord.Embed(
            title="タグ申請",
            description="下のボタンから情報を入力してください",
            colour=discord.Colour.green()
        ).add_field(
            name="タグ名",
            value=self.data.tag_name if self.data.tag_name else "未記入",
        ).add_field(
            name="招待リンク",
            value=self.data.invite_url if self.data.invite_url else "未記入",
        ).add_field(
            name="アクセス範囲",
            value=("標準" if self.data.category == "0" else "参加申請") if self.data.category else "未記入",
        ).add_field(
            name="主言語",
            value=self.data.lang if self.data.lang else "未記入",
        ).add_field(
            name="サーバー名",
            value=self.data.invite.guild.name if self.data.invite else "未取得",
            inline=False
        )
        if self.data.invite:
            if self.data.invite.guild.icon:
                embed.set_thumbnail(url=self.data.invite.guild.icon.url)
        if self.data.tag_name and self.data.invite_url and self.data.category and self.data.lang:
            self.submit.disabled = False
        return embed

class FormBtTagName(Button):
    def __init__(self, parent_view: FormView):
        super().__init__(style=ButtonStyle.green, label="タグ名")
        self.parent_view = parent_view
    async def callback(self, interaction:discord.Interaction):
        await interaction.response.send_modal(FormName(parent_view=self.parent_view))
class FormName(Modal):
    def __init__(self, parent_view: FormView) -> None:
        super().__init__(title="タグの名前", custom_id=f"tc-add-name-md-{parent_view.message.id}")
        self.parent_view = parent_view
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
        self.parent_view.data.tag_name = self.name.component.value
        await interaction.response.edit_message(
            embed=self.parent_view.format_message(),
            view=self.parent_view
        )

class FormBtInvite(Button):
    def __init__(self, parent_view: FormView):
        self.parent_view = parent_view
        super().__init__(style=ButtonStyle.green, label="招待リンク")
    async def callback(self, interaction:discord.Interaction):
        await interaction.response.send_modal(FormInvite(parent_view=self.parent_view))
class FormInvite(Modal):
    def __init__(self, parent_view: FormView) -> None:
        super().__init__(title="招待リンクを入力してください", custom_id=f"tc-add-invite-md-{parent_view.message.id}")
        self.parent_view = parent_view
        self.invite = ui.Label(
            text="招待リンク",
            component=ui.TextInput(
                style=discord.TextStyle.short,
                required=True
            ),
        )
        self.add_item(self.invite)
    
    async def on_submit(self, interaction: discord.Interaction) -> None:
        invite: discord.Invite = None
        try:
            invite = await self.parent_view.bot.fetch_invite(self.invite.component.value)
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
        
        if invite:
            if invite.expires_at != None:
                sec_exp = 60*60*24
                now = datetime.datetime.now(datetime.timezone.utc)
                exp = invite.expires_at - now
                invite_sec_exp = exp.total_seconds()
                if invite_sec_exp < sec_exp:
                    await interaction.response.send_message(embed=discord.Embed(
                        title="エラー",
                        description=f"招待リンクが1日未満で切れるため追加できません",
                        colour=discord.Colour.red()
                    ), ephemeral=True)
                await interaction.response.send_message(embed=discord.Embed(
                    title="警告",
                    description=f"**招待リンクの有効期限が無制限ではありません。**\n**有効期限** : <t:{invite.expires_at.timestamp()}:f>",
                    colour=discord.Colour.orange()
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
                    colour=discord.Colour.red()
                ), ephemeral=True)
                return
            self.parent_view.data.invite_url = self.invite.component.value
            self.parent_view.data.invite = invite
            await interaction.response.edit_message(
                embed=self.parent_view.format_message(),
                view=self.parent_view
            )
        else:
            await interaction.response.send_message(embed=discord.Embed(
                title="エラー",
                description=f"招待の取得中にエラーが発生しました。\n```{e}```",
                colour=discord.Colour.red()
            ), ephemeral=True)

class FormBtCategory(Button):
    def __init__(self, parent_view: FormView):
        self.parent_view = parent_view
        super().__init__(style=ButtonStyle.green, label="アクセス範囲")
    async def callback(self, interaction:discord.Interaction):
        await interaction.response.send_modal(FormCategory(parent_view=self.parent_view))
class FormCategory(Modal):
    def __init__(self, parent_view: FormView) -> None:
        super().__init__(title="アクセス範囲", custom_id=f"tc-add-category-md-{parent_view.message.id}")
        self.parent_view = parent_view
        self.category = ui.Label(
            text="アクセス範囲を選択してください",
            component=ui.Select(
                options=[
                    discord.SelectOption(label="標準", value=0),
                    discord.SelectOption(label="参加申請", value=1)
                ],
                min_values=1,
                max_values=1,
                required=True
            )
        )
        self.add_item(self.category)
    
    async def on_submit(self, interaction: discord.Interaction) -> None:
        self.parent_view.data.category = self.category.component.values[0]
        await interaction.response.edit_message(
            embed=self.parent_view.format_message(),
            view=self.parent_view
        )

class FormBtLang(Button):
    def __init__(self, parent_view: FormView):
        self.parent_view = parent_view
        super().__init__(style=ButtonStyle.green, label="主言語")
    async def callback(self, interaction:discord.Interaction):
        await interaction.response.send_modal(FormLang(parent_view=self.parent_view))
class FormLang(Modal):
    def __init__(self, parent_view: FormView) -> None:
        super().__init__(title="主言語", custom_id=f"tc-add-category-md-{parent_view.message.id}")
        self.parent_view = parent_view
        self.lang = ui.Label(
            text="主言語を選択してください",
            component=ui.Select(
                options=Langs.ModalSelectOptions,
                min_values=1,
                max_values=1,
                required=True
            )
        )
        self.add_item(self.lang)
    
    async def on_submit(self, interaction: discord.Interaction) -> None:
        self.parent_view.data.lang = self.lang.component.values[0]
        await interaction.response.edit_message(
            embed=self.parent_view.format_message(),
            view=self.parent_view
        )

class SubmitView(ui.View):
    def __init__(self, timeout:int = None):
        super().__init__(timeout=timeout)
    
    @ui.button(label="タグ通知を受け取る", style=ButtonStyle.green, emoji="📣")
    async def tag_notice(self, interaction:discord.Interaction, button: Button):
        notice_role = interaction.guild.get_role(1408781348134719595)
        if notice_role in interaction.user.roles:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="エラー",
                    description="すでに有効になっているようです。\n停止したい場合は<#1408781348994551904>から",
                    colour=discord.Colour.yellow()
                ),
                ephemeral=True
            )
        else:
            await interaction.user.add_roles([notice_role])
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="付与",
                    description="タグ通知を有効にしました!",
                    colour=discord.Colour.green()
                ),
                ephemeral=True
            )
    
    @ui.button(label="閉じる", style=ButtonStyle.secondary, emoji="✖")
    async def close(self, interaction:discord.Interaction, button: Button):
        await interaction.response.defer()
        await interaction.delete_original_response()

class FormBtSubmit(ui.Button):
    def __init__(self, parent_view: FormView):
        super().__init__(style=ButtonStyle.primary, label="送信", disabled=True)
        self.parent_view = parent_view
    async def callback(self, interaction:discord.Interaction):
        ret = {
            "name": self.parent_view.data.tag_name,
            "invite": self.parent_view.data.invite.url,
            "lang": self.parent_view.data.lang,
            "at_id": interaction.user.id,
            "kind": int(self.parent_view.data.category)
        }
        channel = interaction.guild.get_channel(1408781350399508484)
        await channel.send(
        content=f"Tag-Info\n{self.parent_view.data.invite.url}\n<@&1516579047726125216>",
            embeds=[
                discord.Embed(
                    title="タグの申請",
                    description=f"""\
タグ名: `{self.parent_view.data.tag_name}`
招待リンク: `{self.parent_view.data.invite.url}`
主言語: `{self.parent_view.data.lang}`
アクセス範囲: `{"標準" if self.parent_view.data.category == "0" else "参加申請"}`
申請者: <@{interaction.user.id}>
""",
                    colour=discord.Colour.green()
                ),
                discord.Embed(
                    description=json.dumps(ret, ensure_ascii=False)
                )
            ]
        )
        #await channel.send(content=)
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="申請が完了しました!",
                description=f"タグ `{self.parent_view.data.tag_name}`の申請を受け付けました。\n下のボタンよりタグ通知を設定すると追加されたときにお知らせします!(任意)",
                colour=discord.Colour.green()
            ),
            view=SubmitView()
        )

# --------------------------------------------

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
・招待リンクは作成時にリンク有効期間を無制限に変更するか、無制限な宣伝用リンクなどを使用してください。
```
""",
                colour=discord.Colour.green()
            ),
            ephemeral=True,
            view=check1(bot=self.bot)
        )

async def setup(bot):
    await bot.add_cog(AddCog(bot))