import discord
from discord.ext import commands
from discord import app_commands, ButtonStyle
from discord.ui import Button, button, View
from func.log import get_log, ExceptionLoggerAdapter
from func.dc import Bot
from .func.db import Tag_DB, Tag, Tags
from .func import lang as Langs
from typing import Literal
from .func.tools import tc_ob
from func.tagimage import create_tag_image
from discord.http import Route
import re
import aiohttp
from io import BytesIO

class Tag_Embed(View):
    def __init__(self, *, bot:Bot, pages:list, log:ExceptionLoggerAdapter, timeout: float | None = 180):
        super().__init__(timeout=timeout)
        self.pages:list[Tag] = pages
        self.current_page:int = 0
        self.bot = bot
        self.log = log

    async def create_embed(self) -> tuple[discord.Embed, discord.File]:
        a = self.pages[self.current_page]
        invite_p = re.compile(r"(?:https?:\/\/)?(?:discord\.gg|discord\.com\/invite)\/([A-Za-z0-9]+)")
        invite_code = re.search(invite_p, a.server_invite).group(1)
        res = await self.bot.http.request(Route("GET", "/invites/{invite_code}", invite_code=invite_code))
        icon:BytesIO = None
        file:discord.File = None
        try:
            async with aiohttp.ClientSession() as ses:
                async with ses.get(f"https://cdn.discordapp.com/guild-tag-badges/{res["guild_id"]}/{res["profile"]["badge_hash"]}.png") as r:
                    tag_icon = BytesIO(await r.read())
            icon = await create_tag_image(tag_icon, a.tag_name)
        except Exception as e:
            self.log.error(e)
        embed = discord.Embed(
            title=f"ページ数({self.current_page + 1} / {len(self.pages)})",
            description=f"""\
**登録ID** : {a.id}
**タグ** : {a.tag_name}
**サーバー名** : {a.server_name}
**カテゴリ** : {a.category}
**主要言語** : {a.lang}
**招待リンク** : {a.server_invite}
**登録日** : <t:{a.created_at}:f>
""",
            colour=discord.Colour.random()
        ).set_thumbnail(url=a.server_icon)
        if icon:
            file = discord.File(fp=icon, filename="badge.png")
            # print(file.uri)
            embed.set_image(url=file.uri)
        return (embed, file)
    
    async def update_message(self, interaction:discord.Interaction):
        embed, file = await self.create_embed()
        
        if self.current_page == 0:
            self.previous.disabled = True
        else:
            self.previous.disabled = False
        if self.current_page == len(self.pages) - 1 :
            self.next.disabled = True
        else:
            self.next.disabled = False
        await interaction.response.edit_message(embed=embed, view=self, attachments=[file])
    
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

    tag = tag1(name="tag", description="タグに関するコマンド。", guild_ids=[1408781348134719588])
    
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
        lang:Langs.CommandOptions = None, #type: ignore
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
                    view = Tag_Embed(pages=db.data, bot=self.bot, log=self.log)
                    embed, file = await view.create_embed()
                    view.previous.disabled = True
                    if len(db.data) == 1 :
                        view.next.disabled = True
                    await interaction.followup.send(embed=embed, view=view, file=file)
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