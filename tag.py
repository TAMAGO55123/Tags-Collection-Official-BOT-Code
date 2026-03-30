import discord
from discord.ext import commands
from discord import app_commands, ButtonStyle
from discord.ui import Button, button, View
from func.log import get_log
from func.dc import Bot
from .func.db import Tag_DB, Tag, Tags
from typing import Literal
from .func.tools import tc_ob

class Tag_Embed(View):
    def __init__(self, *, pages:list, timeout: float | None = 180):
        super().__init__(timeout=timeout)
        self.pages:list[Tag] = pages
        self.current_page:int = 0
    
    async def update_message(self, interaction:discord.Interaction):
        a = self.pages[self.current_page]
        embed = discord.Embed(
            title=f"ページ数({self.current_page + 1} / {len(self.pages)})",
            description=f"""\
**登録ID** : {a.id}
**タグ** : {a.tag_name}
**サーバー名** : {a.server_name}
**カテゴリ** : {a.category}
**主要言語** : {a.lang}
**招待リンク** : {a.server_invite}
""",
            colour=discord.Colour.random()
        ).set_thumbnail(url=a.server_icon)
        if self.current_page == 0:
            self.previous.disabled = True
        else:
            self.previous.disabled = False
        if self.current_page == len(self.pages) - 1 :
            self.next.disabled = True
        else:
            self.next.disabled = False
        await interaction.response.edit_message(embed=embed, view=self)
    
    @button(label="◀︎", style=ButtonStyle.secondary)
    async def previous(self, interaction:discord.Interaction, button:Button):
        if self.current_page > 0:
            self.current_page -= 1
            await self.update_message(interaction)
        else:
            await interaction.response.defer()
    
    @button(label="▶︎", style=ButtonStyle.secondary)
    async def next(self, interaction:discord.Interaction, button:Button):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            await self.update_message(interaction)
        else:
            await interaction.response.defer()

class TagCog(commands.Cog):
    def __init__(self, bot:Bot):
        self.bot = bot
        self.log = get_log("TagCog")
        self.DB = Tag_DB()
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.log.info(f"TagCogを読み込みました!")

    @app_commands.guilds(tc_ob)
    class tag1(app_commands.Group):
        pass

    tag = tag1(name="tag", description="【β】タグに関するコマンド。", guild_ids=[1408781348134719588])
    
    @tag.command(name="list", description="タグのリストを取得します。(取得は50件ごと)")
    @app_commands.describe(
        name="タグの名前",
        category="カテゴリ",
        page="ページ数"
    )
    async def list(
        self,
        interaction:discord.Interaction,
        name:str=None,
        category:Literal["標準", "参加申請"]=None,
        lang:Literal["Japanese", "English", "Chinese"]=None,
        page:int=1
    ):
        await interaction.response.defer()
        try:
            role_id = 1408781348134719593
            has_role = any(role.id == role_id for role in interaction.user.roles)
            _kind = 0
            match category:
                case "標準":
                    _kind = 0
                case "参加申請":
                    _kind = 1
                case None:
                    _kind = None
            db:Tags = await self.DB.get_tag(tag_name=name, category=_kind, lang=lang, page=page, has_d=has_role)
            if db:
                if db.count != 0:
                    view = Tag_Embed(pages=db.data)
                    a = db.data[0]
                    is_web = False
                    webdes = ""
                    if a.description == {}:
                        is_web = False
                    else:
                        is_web = True
                        webdes = f"\n**サーバー説明**\n{a.description["description"]}"
                    embed = discord.Embed(
                        title=f"ページ数({1} / {len(db.data)})",
                        description=f"""\
                        **登録ID** : {a.id}
                        **タグ** : {a.tag_name}
                        **サーバー名** : {a.server_name}
                        **カテゴリ** : {a.category}
                        **主要言語** : {a.lang}
                        **招待リンク** : {a.server_invite}
                        **登録日** : <t:{a.created_at}:f>{webdes}
                        """,
                        colour=discord.Colour.random()
                    ).set_thumbnail(url=a.server_icon)
                    view.previous.disabled = True
                    if len(db.data) == 1 :
                        view.next.disabled = True
                    await interaction.followup.send(embed=embed, view=view)
                else:
                    await interaction.followup.send("タグがありません。")
            else:
                await interaction.followup.send("タグがありません。")
        except Exception as e:
            await interaction.followup.send(embed=discord.Embed(
                title="エラー",
                description=f"タグの読み込み中にエラーが発生しました。\n```{e}```"
            ))
            self.log.error(e)

async def setup(bot):
    await bot.add_cog(TagCog(bot))