from tkinter import NO
from turtle import title
import discord
from discord.ext import commands
from discord import app_commands, ButtonStyle, HTTPException
from discord.errors import NotFound
from discord.app_commands import Choice
from discord.ui import View, button, Button
from func.dc import Bot
from func.log import get_log
from typing import Literal
import json
import datetime
import math
from os import getenv
from dotenv import load_dotenv
load_dotenv()
from .func.db import Tag_DB, Tags, Tag
from .func.tools import tc_ob
import re

@app_commands.guilds(tc_ob)
class tagdb1(app_commands.Group):
    pass

class ManageTagCog(commands.Cog):
    def __init__(self, bot:Bot):
        self.bot = bot
        self.log = get_log("ManageTagCog")
        self.DB = Tag_DB()
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.log.info(f"ManageTagCogを読み込みました!")

    

    tagdb = tagdb1(name="tagdb", description="【β】タグに関するコマンド。", guild_ids=[1408781348134719588])

    @tagdb.command(name="add", description="【β】タグを追加します。")
    @app_commands.describe(
        name="タグの名前",
        invite_url="サーバーの招待リンク(あればバニティURLとか)",
        lang="タグサーバーの主言語(選んでね)"
    )
    async def add(
        self,
        interaction:discord.Interaction, 
        name:str, 
        invite_url:str, 
        lang:Literal["Japanese", "English", "Chinese"]
    ):
        try:
            _kind = 0
            embeds:list[discord.Embed] = []
            await interaction.response.defer()
            invite = await self.bot.fetch_invite(invite_url)
            if "MEMBER_VERIFICATION_GATE_ENABLED" in invite.guild.features:
                _kind = 1
            else:
                _kind = 0
            kind = "参加申請" if _kind == 1 else "標準"
            if invite.type != discord.InviteType.guild:
                raise Exception("指定されたURLはサーバー招待ではありません。")
            if "GUILD_TAGS" not in invite.guild.features:
                raise Exception("指定された招待リンクのサーバーはギルドタグを持っていないようです。")
            if invite.expires_at != None:
                sec_exp = 60*60*24
                now = datetime.datetime.now()
                exp = invite.expires_at - now
                invite_sec_exp = exp.total_seconds()
                if invite_sec_exp < sec_exp:
                    raise Exception("招待リンクが1日未満で切れるため追加できません")
                embeds.append(discord.Embed(
                    title="警告",
                    description=f"**招待リンクの有効期限が無制限ではありません。**\n**有効期限** : <t:{invite.expires_at.timestamp()}:f>",
                    colour=discord.Colour.orange()
                ))
            
            
            server_icon = invite.guild.icon.url if invite.guild.icon else ""
            
            ok, res = await self.DB.add_tag(
                guild_id=invite.guild.id,
                guild_name=invite.guild.name,
                invite_url=invite.url,
                guild_icon=server_icon,
                tag_name=name,
                category=_kind,
                lang=lang
            )
            if res == "登録済み":
                raise Exception("登録済みです。")
            if ok != True:
                raise Exception(f"データベースエラー:{res}")
            embeds.insert(0, discord.Embed(
                title="タグ追加",
                description=f"""\
                **データベースに情報を追加しました。**
                ----------------------
                **タグ** : {name}
                **サーバー名** : {invite.guild.name}
                **カテゴリ** : {kind}
                **主要言語** : {lang}
                **招待リンク** : {invite.url}""",
                colour=discord.Colour.green()
            ).set_thumbnail(url=server_icon))
            await interaction.followup.send(embeds=embeds)
            notice_ch = interaction.guild.get_channel(1409368112993927379)
            nt_mes = await notice_ch.send(embed=discord.Embed(
                title="タグが追加されました！",
                description=f"""\
                **タグ** : {name}
                **サーバー名** : {invite.guild.name}
                **カテゴリ** : {kind}
                **主要言語** : {lang}
                **招待リンク** : {invite.url}""",
                colour=discord.Colour.green()
            ).set_thumbnail(url=server_icon))
            await nt_mes.publish()
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
    
    @tagdb.command(name="delete", description="タグを削除します")
    @app_commands.describe(
        id="管理ID"
    )
    async def delete(self, interaction:discord.Interaction, id:int):
        await interaction.response.defer()
        try:
            ok, res = await self.DB.delete_tag(id)
            if ok != True:
                raise Exception(f"データベースエラー : {res}")
            await interaction.followup.send(embed=discord.Embed(
                title="タグ削除",
                description="タグを削除しました。",
                colour=discord.Colour.red()
            ))
        except Exception as e:
            await interaction.followup.send(embed=discord.Embed(
                title="エラー",
                description=f"タグの削除中にエラーが発生しました。\n```{e}```"
            ))
            self.log.error(e)
    
    @tagdb.command(name="name", description="タグの名前を変更します。")
    @app_commands.describe(
        id="管理ID",
        name="新しいタグの名前"
    )
    async def name(self, interaction:discord.Interaction, id:int, name:str):
        await interaction.response.defer()
        try:
            db:Tags = await self.DB.get_tag(id=id)
            if db.count == 0:
                raise Exception("タグを取得できませんでした。")
            
            invite:discord.Invite = await self.bot.fetch_invite(db.data[0].server_invite)
            if "MEMBER_VERIFICATION_GATE_ENABLED" in invite.guild.features:
                _kind = 1
            else:
                _kind = 0
            server_name = invite.guild.name
            server_icon = invite.guild.icon.url if invite.guild.icon else ""
            ok, res = await self.DB.edit_tag(
                tag_id=id,
                tag_name=name,
                server_name=server_name,
                server_icon=server_icon,
            )
            if ok != True:
                raise Exception(f"データベースエラー : {res}")
            await interaction.followup.send(embed=discord.Embed(
                title="タグ名変更",
                description="タグの名前を変更し、サーバー名とアイコンも更新しました。",
                colour=discord.Colour.green()
            ))
        except NotFound as e:
            await interaction.followup.send(embed=discord.Embed(
                title="エラー",
                description=f"保存した招待リンクが有効ではないため、タグを削除します。\n```{e}```",
                colour=discord.Colour.orange()
            ))
            self.log.error(e)
            try:
                db:Tags = await self.DB.get_tag(id=id)
                if db.count == 0:
                    raise Exception("タグを取得できませんでした。")
                ok, res = await self.DB.delete_tag(db.data[0].id)
                if ok != True:
                    raise Exception(f"データベースエラー : {res}")
                await interaction.followup.send(embed=discord.Embed(
                    title="タグ削除",
                    description="タグを削除しました。",
                    colour=discord.Colour.red()
                ))
            except Exception as e:
                await interaction.followup.send(embed=discord.Embed(
                    title="エラー",
                    description=f"タグの削除中にエラーが発生しました。\n```{e}```",
                    colour=discord.Colour.red()
                ))
                self.log.error(e)
        except Exception as e:
            await interaction.followup.send(embed=discord.Embed(
                title="エラー",
                description=f"名前変更中にエラーが発生しました。\n```{e}```",
                colour=discord.Colour.red()
            ))
            self.log.error(e)
    
    @tagdb.command(name="invite", description="タグの招待を変更します。")
    @app_commands.describe(
        id="管理ID",
        invite_url="新しい招待リンク"
    )
    async def invite(self, interaction:discord.Interaction, id:int, invite_url:str):
        await interaction.response.defer()
        try:
            db:Tags = await self.DB.get_tag(id=id)
            if db.count == 0:
                raise Exception("タグを取得できませんでした。")
            
            invite:discord.Invite = await self.bot.fetch_invite(invite_url)
            server_name = invite.guild.name
            server_icon = invite.guild.icon.url if invite.guild.icon else ""
            ok, res = await self.DB.edit_tag(
                tag_id=id,
                server_name=server_name,
                server_icon=server_icon,
                server_invite=invite_url
            )
            if ok != True:
                raise Exception(f"データベースエラー : {res}")
            await interaction.followup.send(embed=discord.Embed(
                title="タグ名変更",
                description="タグの招待を変更し、サーバー名とアイコンも更新しました。",
                colour=discord.Colour.green()
            ))
        except NotFound as e:
            await interaction.followup.send(embed=discord.Embed(
                title="エラー",
                description=f"保存した招待リンクが有効ではないため、タグを削除します。\n```{e}```",
                colour=discord.Colour.orange()
            ))
            self.log.error(e)
            try:
                db:Tags = await self.DB.get_tag(id=id)
                if db.count == 0:
                    raise Exception("タグを取得できませんでした。")
                ok, res = await self.DB.delete_tag(db.data[0].id)
                if ok != True:
                    raise Exception(f"データベースエラー : {res}")
                await interaction.followup.send(embed=discord.Embed(
                    title="タグ削除",
                    description="タグを削除しました。",
                    colour=discord.Colour.red()
                ))
            except Exception as e:
                await interaction.followup.send(embed=discord.Embed(
                    title="エラー",
                    description=f"タグの削除中にエラーが発生しました。\n```{e}```",
                    colour=discord.Colour.red()
                ))
                self.log.error(e)
        except Exception as e:
            await interaction.followup.send(embed=discord.Embed(
                title="エラー",
                description=f"招待変更中にエラーが発生しました。\n```{e}```",
                colour=discord.Colour.red()
            ))
            self.log.error(e)
    @tagdb.command(name="update_icon", description="アイコンをアップデートします")
    @app_commands.describe(
        id="管理用ID"
    )
    async def update_icon(self, interaction:discord.Interaction, id:int):
        await interaction.response.defer()
        try:
            db:Tags = await self.DB.get_tag(id=id)
            if db.count == 0:
                raise Exception("タグを取得できませんでした。")
            
            invite:discord.Invite = await self.bot.fetch_invite(db.data[0].server_invite)
            server_icon = invite.guild.icon.url if invite.guild.icon else ""
            ok, res = await self.DB.edit_tag(
                tag_id = id,
                server_icon=server_icon
            )
            await interaction.followup.send(embed=discord.Embed(
                title="アイコンアップデート",
                description="アイコンを更新しました。",
                colour=discord.Colour.green()
            ).set_thumbnail(url=server_icon))
        except NotFound as e:
            await interaction.followup.send(embed=discord.Embed(
                title="エラー",
                description=f"保存した招待リンクが有効ではないため、タグを削除します。\n```{e}```",
                colour=discord.Colour.orange()
            ))
            self.log.error(e)
            try:
                db:Tags = await self.DB.get_tag(id=id)
                if db.count == 0:
                    raise Exception("タグを取得できませんでした。")
                ok, res = await self.DB.delete_tag(db.data[0].id)
                if ok != True:
                    raise Exception(f"データベースエラー : {res}")
                await interaction.followup.send(embed=discord.Embed(
                    title="タグ削除",
                    description="タグを削除しました。",
                    colour=discord.Colour.red()
                ))
            except Exception as e:
                await interaction.followup.send(embed=discord.Embed(
                    title="エラー",
                    description=f"タグの削除中にエラーが発生しました。\n```{e}```",
                    colour=discord.Colour.red()
                ))
                self.log.error(e)
        except Exception as e:
            await interaction.followup.send(embed=discord.Embed(
                title="エラー",
                description=f"アイコンのアップデート中にエラーが発生しました。\n```{e}```",
                colour=discord.Colour.red()
            ))
            self.log.error(e)
    
    @app_commands.command(name="update_tag_count")
    @app_commands.guilds(tc_ob)
    @app_commands.default_permissions(administrator=True)
    async def update_tag_count(self, interaction:discord.Interaction):
        try:
            cch_id = 1408781348616933484
            db:Tags = await self.DB.get_tag()
            count_ch = interaction.guild.get_channel(cch_id)
            await count_ch.edit(
                name=f"タグの数: {db.count}"
            )
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="タグの数を変更",
                    description=f"<#{cch_id}>"
                )
            )
        except Exception as e:
            await interaction.followup.send(embed=discord.Embed(
                title="エラー",
                description=f"カウントの編集中にエラーが発生しました。\n```{e}```",
                colour=discord.Colour.red()
            ))
            self.log.error(e)
    
    @commands.command(name="ok")
    async def ok_command(self, ctx:commands.Context):
        try:
            if ctx.guild.id == 1408781348134719588:
                if 1408781348151234672 in [i.id for i in ctx.author.roles]:
                    ref = ctx.message.reference
                    if ref:
                        if isinstance(ref.resolved, discord.Message):
                            replied = ref.resolved
                        else:
                            try:
                                replied = await ctx.message.channel.fetch_message(ref.message_id)
                            except:
                                replied = None
                    if replied:
                        if "Tag-Info" in replied.content:
                            data = json.loads(replied.embeds[1].description)
                            invite = await self.bot.fetch_invite(data["invite"])
                            server_icon = invite.guild.icon.url if invite.guild.icon else ""
                            embeds:list[discord.Embed] = []
                            if invite.expires_at != None:
                                sec_exp = 60*60*24
                                now = datetime.datetime.now()
                                exp = invite.expires_at - now
                                invite_sec_exp = exp.total_seconds()
                                if invite_sec_exp < sec_exp:
                                    raise Exception("招待リンクが1日未満で切れるため追加できません")
                                embeds.append(discord.Embed(
                                    title="警告",
                                    description=f"**招待リンクの有効期限が無制限ではありません。**\n**有効期限** : <t:{invite.expires_at.timestamp()}:f>",
                                    colour=discord.Colour.orange()
                                ))
                            if "MEMBER_VERIFICATION_GATE_ENABLED" in invite.guild.features:
                                _kind = 1
                            else:
                                _kind = 0
                            ok, res = await self.DB.add_tag(
                                guild_id=invite.guild.id,
                                guild_name=invite.guild.name,
                                invite_url=data["invite"],
                                guild_icon=server_icon,
                                tag_name=data["name"],
                                category=_kind,
                                lang=data["lang"]
                            )
                            if res == "登録済み":
                                raise Exception("登録済みです。")
                            if ok != True:
                                raise Exception(f"データベースエラー:{res}")
                            embeds.insert(0, discord.Embed(
                                title="タグ追加",
                                description=f"""\
                                **データベースに情報を追加しました。**
                                ----------------------
                                **タグ** : {data["name"]}
                                **サーバー名** : {invite.guild.name}
                                **カテゴリ** : {_kind}
                                **主要言語** : {data["lang"]}
                                **招待リンク** : {invite.url}""",
                                colour=discord.Colour.green()
                            ).set_thumbnail(url=server_icon))
                            await ctx.reply(embeds=embeds)
                            notice_ch = ctx.guild.get_channel(1409368112993927379)
                            nt_mes = await notice_ch.send(embed=discord.Embed(
                                title="タグが追加されました！",
                                description=f"""\
                                **タグ** : {data["name"]}
                                **サーバー名** : {invite.guild.name}
                                **カテゴリ** : {_kind}
                                **主要言語** : {data["lang"]}
                                **招待リンク** : {invite.url}""",
                                colour=discord.Colour.green()
                            ).set_thumbnail(url=server_icon))
                            await nt_mes.publish()
        except NotFound as e:
            await ctx.send(embed=discord.Embed(
                title="エラー",
                description=f"招待リンクが有効ではありません。\n```{e}```",
                colour=discord.Colour.red()
            ))
            self.log.error(e)
        except HTTPException as e:
            await ctx.send(embed=discord.Embed(
                title="エラー",
                description=f"招待リンクの取得に失敗しました。\n```{e}```",
                colour=discord.Colour.red()
            ))
            self.log.error(e)
        except Exception as e:
            await ctx.send(embed=discord.Embed(
                title="エラー",
                description=f"タグの追加中にエラーが発生しました。\n```{e}```",
                colour=discord.Colour.red()
            ))
            self.log.error(e)



async def setup(bot):
    await bot.add_cog(ManageTagCog(bot))