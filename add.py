import json
import discord
from discord.ext import commands
from discord import app_commands, ButtonStyle, ui, SelectOption
from discord.ui import View, button, Modal
from discord.utils import MISSING
from discord.errors import HTTPException, NotFound
from func.dc import Bot
from .func.db import Tag_DB
from func.log import get_log
from .func.tools import tc_ob

class check1(View):
    def __init__(self, *, bot: commands.Bot, timeout: float | None = 180):
        super().__init__(timeout=timeout)
        self.bot = bot
    
    @button(label="OK", style=ButtonStyle.primary)
    async def ok_button(self, interaction:discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(Form(self.bot))
    
class Form(Modal):
    def __init__(self, bot:commands.Bot) -> None:
        super().__init__(title="サーバー情報の入力")
        self.bot = bot
        self.name = ui.Label(
            text="タグ名",
            component=ui.TextInput(
                style=discord.TextStyle.short,
                required=True,
                min_length=1,
                max_length=4
            )
        )
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
        self.add_item(self.name).add_item(self.invite).add_item(self.lang)
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
                        """
                    ),
                    discord.Embed(
                        description=json.dumps({
                            "name": self.name.component.value,
                            "invite": self.invite.component.value,
                            "lang": self.lang.component.values[0],
                            "at_id": interaction.user.id
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