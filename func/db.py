import aiohttp
from os import getenv
from dotenv import load_dotenv
load_dotenv()
from typing import Tuple, Union
from pydantic import BaseModel
from discord.ext.commands import Bot
import json

API_URL = getenv("API_URL")
API_KEY = getenv("API_KEY")

class Tag(BaseModel):
    id: int
    server_name: str
    server_icon: str
    server_invite: str
    server_id: str
    tag_name: str
    category: str
    lang: str
    bumped: int
    created_at: int
    description: dict

class Tags(BaseModel):
    page: int
    limit: int
    count: int
    data: list[Tag]

class Tag_DB:
    async def add_tag(self,guild_id:int, guild_name:str, invite_url:str, guild_icon:str, tag_name: str, category: int, lang: str) -> Tuple[bool, Union[dict, str]]:
        """
        Cloudflare Workers の /tags API にタグを登録する関数
        """

        payload = {
            "server_id": str(guild_id),
            "server_name": guild_name,
            "server_invite": invite_url,
            "server_icon": guild_icon,
            "tag_name": tag_name,
            "category": category,
            "lang": lang
        }

        header = {
            "x-api-key": API_KEY,
            "Content-Type": "application/json"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, json=payload, headers=header) as resp:
                if resp.status == 200:
                    return True, await resp.json()
                elif resp.status == 208:
                    return True, "登録済み"
                else:
                    return False, await resp.text()

    async def get_tag(self, id:int = None, tag_name: str = None, category:int = None, lang:str = None, server_id:int = None, page:int = 1, limit = 30, has_d:bool = False) -> Tags:
        params = {
            "offset": page,
            "limit": limit
        }

        if id:
            params["id"] = id
        if tag_name:
            params["tag_name"] = tag_name
        if category:
            params["category"] = category
        if lang:
            params["lang"] = lang
        if server_id:
            params["server_id"] = server_id
        params["skip"] = str(not has_d).lower()
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                else:
                    return
        tags:list = []
        for i in data["data"]:
            kind = ""
            match i["category"]:
                case 0:
                    kind = "標準"
                case 1:
                    kind = "参加申請"
                case 2:
                    kind = "危険"
            desc: dict = {}
            if i["description"] != '':
                desc = json.loads(i["description"])
            tags.append(Tag(
                id=i["id"],
                server_name=i["server_name"],
                server_icon=i["server_icon"],
                server_invite=i["server_invite"],
                server_id=i["server_id"],
                tag_name=i["tag_name"],
                category=kind,
                lang=i["lang"],
                bumped=i["bumped"],
                created_at=i["created_at"],
                description=desc
            ))
        result = Tags(page=data["page"], limit=data["limit"], count=data["count"], data=tags)
        return result
    
    async def delete_tag(self, tag_id: int) -> Tuple[bool, str]:
        headers = {
            "x-api-key": API_KEY
        }
        url = f"{API_URL}/{tag_id}"

        async with aiohttp.ClientSession() as session:
            async with session.delete(url, headers=headers) as resp:
                text = await resp.text()
                if resp.status == 200:
                    return True, text
                else:
                    return False, text
    async def edit_tag(self, tag_id: int, tag_name:str = None, server_name:str = None, server_icon:str = None, server_invite:str = None) -> Tuple[bool, str]:
        headers = {
            "x-api-key": API_KEY
        }
        url = f"{API_URL}/{tag_id}"
        params = {}
        if tag_name:
            params["tag_name"] = tag_name
        if server_name:
            params["server_name"] = server_name
        if server_icon:
            params["server_icon"] = server_icon
        if server_invite:
            params["server_invite"] = server_invite
        async with aiohttp.ClientSession() as session:
            async with session.patch(url=url, headers=headers, json=params) as resp:
                text = await resp.text()
                if resp.status == 200:
                    return True, text
                else:
                    return False, text
    async def update_icon(self, id:int):
        url = f"{API_URL}/update_icon"
        params = {"id": str(id)}

        async with aiohttp.ClientSession() as session:
            async with session.patch(url, headers={"x-api-key": API_KEY}, params=params) as resp:
                return resp.status, await resp.text()
