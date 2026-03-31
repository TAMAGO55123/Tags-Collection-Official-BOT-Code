import discord
from discord.ext import commands
from discord import app_commands
from func.dc import Bot
from .func.db import Tag_DB
from func.log import get_log

class WelcomeCog(commands.Cog):
    def __init__(self, bot:Bot):
        self.bot = bot
        self.log = get_log("WelcomeCog")
        self.DB = Tag_DB()
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.log.info(f"WelcomeCogを読み込みました!")
    
    @commands.Cog.listener()
    async def on_member_join(self, member:discord.Member):
        if member.guild.id == 1408781348134719588:
            join_channel = member.guild.get_channel(1408781348616933487)
            verify_channel = member.guild.get_channel(1408781348616933488)
            
            await join_channel.send(content=f"""# Welcome to Server!
    Joined <@{member.id}> ({member.name})
    Now members: {member.guild.member_count - 1} -> {member.guild.member_count}""")
            msg = await verify_channel.send(content=f"<@{member.id}>")
            await msg.delete()
    
    @commands.Cog.listener()
    async def on_member_remove(self, member:discord.Member):
        if member.guild.id == 1408781348134719588:
            join_channel = member.guild.get_channel(1408781348616933487)
        
            await join_channel.send(content=f"""User Left...
    Left <@{member.id}> ({member.name})
    Now members: {member.guild.member_count + 1} -> {member.guild.member_count}
    """)

async def setup(bot):
    # await bot.add_cog(WelcomeCog(bot))
    pass