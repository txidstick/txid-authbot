import traceback
import requests
import logging
import discord
import asyncio
import aiohttp
import json
import os
from threading import Thread

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pystyle import Write, Colors
import uvicorn

with open('config.json', 'r') as f:
    config = json.load(f)

__title__ = "txid's authbot"
__author__ = "txidstick"
__version__ = "1.0.0"

token = config['token']
redirect_uri = config['redirect_uri']
client_secret = config['client_secret']
client_id = config['client_id']
scope = config['scope']
owners = config['owners']
whitelist = config.get('whitelist', [])
admin_guild = config.get('admin_guild', 0)
log_channel = config['log_channel']
webhook_url = config.get('webhook_url', '')

quart_logging = config['server_logging']

server_host = config['server_host']
server_port = config['server_port']

if not quart_logging:
    logging.getLogger('hypercorn.access').disabled = True

DISCORD_API = "https://discord.com/api/"

LOGIN_URL = f"{DISCORD_API}oauth2/authorize/?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope={scope}"
LOGIN_REDIRECT = f"https://discord.com/oauth2/authorize/?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope={scope}"
TOKEN_URL = f"{DISCORD_API}oauth2/token"


def is_authorized(user_id):
    """Check if user is owner or whitelisted"""
    return user_id in owners or user_id in whitelist


def is_owner(user_id):
    """Check if user is owner"""
    return user_id in owners


async def send_webhook(embed_data):
    """Send log to webhook if configured"""
    if not webhook_url:
        return
    
    try:
        async with aiohttp.ClientSession() as session:
            webhook_payload = {
                "embeds": [embed_data]
            }
            await session.post(webhook_url, json=webhook_payload)
    except Exception as e:
        print(f"Failed to send webhook: {e}")


async def get_token(code, redirect_uri, session):
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "scope": scope
    }

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    access_token = await session.post(url=TOKEN_URL, data=payload, headers=headers)
    return await access_token.json()


async def get_userdata(access_token, session):
    url = f"{DISCORD_API}/users/@me"
    guilds_url = f"{DISCORD_API}/users/@me/guilds"

    headers = {"Authorization": f"Bearer {access_token}"}

    userdata_response = await session.get(url=url, headers=headers)
    if userdata_response.status != 200:
        return None

    userdata = await userdata_response.json()

    guild_data_response = await session.get(url=guilds_url, headers=headers)
    if guild_data_response.status == 200:
        guild_data = await guild_data_response.json()
    else:
        guild_data = []
        
    return userdata, guild_data


async def refresh_token(refresh_token, session):
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    r = await session.post(TOKEN_URL, data=data, headers=headers)
    json_resp = await r.json()

    return json_resp


async def update_data_file(user_id, refresh_token, access_token):
    try:
        with open('data.json', 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        data = {"users": {}}

    # Check if user already exists by user_id
    for rt, user_data in data["users"].items():
        if user_data.get("id") == user_id:
            # User already verified, don't add duplicate
            return "already authed"
    
    # New user - add to data.json
    if refresh_token not in data["users"]:
        data["users"][refresh_token] = {"id": user_id, "at": access_token}

        with open('data.json', 'w') as file:
            json.dump(data, file)
        return "new user"
    else:
        return "already authed"


async def pull(ctx, server_id, amount=None):
    session = aiohttp.ClientSession()
    success = 0
    fail = 0
    already_in_server = 0
    total = 0

    with open('data.json', 'r') as f:
        data1 = json.load(f)

    keys = list(data1["users"].keys())

    if amount is not None and amount > 0:
        keys = keys[:amount]

    for refresh_token2 in keys:
        user_data = data1["users"][refresh_token2]
        user_id = user_data["id"]

        refresh_json = await refresh_token(refresh_token2, session)

        at = refresh_json.get("access_token")
        rt = refresh_json.get("refresh_token")

        if at is None and rt is None:
            continue

        data1["users"][rt] = {"id": user_id, "at": at}
        del data1["users"][refresh_token2]

        with open('data.json', 'w') as f:
            json.dump(data1, f)

        url = f'https://discord.com/api/guilds/{server_id}/members/{user_id}'
        data = {
            'access_token': at
        }
        headers = {
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json"
        }
        try:
            r = await session.put(url, json=data, headers=headers)
            if r.status in (200, 201):
                success += 1
            elif r.status == 204:
                already_in_server += 1
            else:
                fail += 1
        except Exception as e:
            fail += 1
            continue
        finally:
            total += 1
            await asyncio.sleep(1)

    if fail > success:
        color = discord.Color.red()
    else:
        color = discord.Color.green()

    embed = discord.Embed(title="Pull results", color=color)

    embed.description = f"**Pull to `{bot.get_guild(int(server_id)).name}`**\n\n"
    embed.description += f":ballot_box_with_check: **Already in server: `{already_in_server}`**\n"
    embed.description += f":white_check_mark: **Success: `{success}`**\n"
    embed.description += f":x: **Fail: `{fail}`**\n\n"
    embed.description += f":information: **Total users pulled: `{total}`**"

    embed.set_footer(text="txid's authbot")

    await ctx.respond(
        content=f"{ctx.author.mention} Pulling ended!",
        embed=embed,
        ephemeral=True
    )

    await session.close()
    return {"status": "success"}


app = FastAPI()
templates = Jinja2Templates(directory="templates")
bot = discord.Bot(intents=discord.Intents.all())


@app.get('/')
async def index(request: Request, code: str = None, state: str = None):
    if not code:
        return RedirectResponse(url=LOGIN_REDIRECT)
    
    return RedirectResponse(url=f"{redirect_uri}/{state}?code={code}")


@app.get('/{endpoint}')
async def login(request: Request, endpoint: str, code: str = None):
    session = aiohttp.ClientSession()
    state = endpoint

    if not code:
        await session.close()
        return templates.TemplateResponse("index.html", {"request": request})
    
    access_token = await get_token(code, redirect_uri, session)

    try:
        refresh_token = access_token['refresh_token']
    except KeyError:
        if 'error' in access_token:
            if 'invalid' in access_token['error']:
                Write.Print(f"Some bot credentials are invalid. Discord says: {access_token['error'].replace('_', ' ')}", Colors.light_red)
                await session.close()
                return
            
            Write.Print(f"Error when authorizing a user: {access_token['error'].replace('_', ' ')}", Colors.yellow)
        else:
            Write.Print(f"Got an invalid JSON when authorizing a user: {access_token}", Colors.yellow)

        await session.close()
        return
    except Exception as e:
        Write.Print(f"Unknown exception when authorizing a user: {e} (Access token JSON: {access_token}). Printing traceback:\n\n", Colors.light_red)
        traceback.print_exc()

        await session.close()
        return

    user_json, user_guilds = await get_userdata(access_token['access_token'], session)

    await session.close()

    updater = await update_data_file(user_json['id'], refresh_token, access_token['access_token'])
    
    user_id = user_json['id']
    username = user_json['username']
    avatar_hash = user_json['avatar']
    global_name = user_json['global_name']
    mfa = user_json['mfa_enabled']
    locale = user_json['locale']

    if avatar_hash is not None:
        avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.webp?size=1024"
    else:
        avatar_url = "https://discord.com/assets/02b73275048e30fd09ac.png"

    embed = discord.Embed(title=":star: New authed user!", description=None)
    embed.set_thumbnail(url=avatar_url)

    embed.add_field(name=":bust_in_silhouette: User", value=f"{username if global_name is None else global_name} ({username})", inline=False)
    embed.add_field(name=':id: Info', value=f"ID: **`{user_id}`**\nLocale: **{locale}**\nMFA: **{mfa}**", inline=False)

    if len(user_guilds) > 0:
        owned_guilds = [guild for guild in user_guilds if guild['owner']]

        owned_guilds_field_val = "```"

        for guild in owned_guilds:
            owned_guilds_field_val += f"- {guild['name']}\n"

        owned_guilds_field_val += "```"
        embed.add_field(name=":technologist: Servers I own", value=f"{owned_guilds_field_val}", inline=False)

    if state is not None:
        try:
            embed.add_field(name=f":information: State", value=f"**{state}** ({bot.get_guild(int(state)).name if bot.get_guild(int(state)) is not None else 'Unknown guild'})")
        except ValueError:
            pass

    if updater == "new user":
        Write.Print(f"New user!\nID: {user_json['id']}\nAccess Token: {access_token['access_token']}\nRefresh Token: {refresh_token}\n", Colors.blue_to_cyan, interval=0)
        
        for guild_id in config['verify_guilds']:
            if str(guild_id).startswith('_'):  # Skip comment lines
                continue
                
            if str(guild_id) == str(state):
                verified_role_id = config['verify_guilds'].get(str(state))

                guild = bot.get_guild(int(guild_id))
                if not guild:
                    embed.description = ":x: Guild not found."
                    continue
                    
                role = guild.get_role(int(verified_role_id))

                if role:
                    # Check if bot's role is higher than verify role
                    bot_member = guild.get_member(bot.user.id)
                    if bot_member.top_role <= role:
                        embed.description = ":warning: Bot's role must be HIGHER than the verify role!"
                        Write.Print(f"[ ! ] Warning: Bot role is not high enough in {guild.name} to assign {role.name}", Colors.yellow)
                        continue
                    
                    member = guild.get_member(int(user_id))
                    if member:
                        # Check if user already has the role
                        if role in member.roles:
                            embed.description = ":white_check_mark: Member is already verified."
                        else:
                            # Create an async task in the bot's event loop to add the role
                            async def add_role_task():
                                try:
                                    await member.add_roles(role, reason="OAuth2 Verification")
                                    Write.Print(f"[ + ] Successfully added role {role.name} to {member}", Colors.green)
                                except discord.Forbidden:
                                    Write.Print(f"[ ! ] Missing permissions to add role {role.name}", Colors.light_red)
                                except discord.HTTPException as e:
                                    Write.Print(f"[ ! ] HTTP Error adding role: {str(e)}", Colors.light_red)
                                except Exception as e:
                                    Write.Print(f"[ ! ] Error adding role: {str(e)}", Colors.light_red)
                            
                            # Schedule the task in bot's event loop
                            bot.loop.create_task(add_role_task())
                            embed.description = ":white_check_mark: Member was successfully verified."
                    else:
                        embed.description = ":x: Member not found."
                else:
                    embed.description = ":x: Role not found."
                
        # Send to channel
        if log_channel:
            try:
                await bot.get_channel(int(log_channel)).send(embed=embed)
            except:
                pass
        
        # Send to webhook
        if webhook_url:
            await send_webhook(embed.to_dict())
            
    return templates.TemplateResponse("index.html", {"request": request})


@bot.event
async def on_ready():
    with open('data.json', 'r') as f:
        data = json.load(f)
        total_users = len(data['users'])
    banner = """
\t████████╗██╗  ██╗██╗██████╗      █████╗ ██╗   ██╗████████╗██╗  ██╗██████╗  ██████╗ ████████╗
\t╚══██╔══╝╚██╗██╔╝██║██╔══██╗    ██╔══██╗██║   ██║╚══██╔══╝██║  ██║██╔══██╗██╔═══██╗╚══██╔══╝
\t   ██║    ╚███╔╝ ██║██║  ██║    ███████║██║   ██║   ██║   ███████║██████╔╝██║   ██║   ██║   
\t   ██║    ██╔██╗ ██║██║  ██║    ██╔══██║██║   ██║   ██║   ██╔══██║██╔══██╗██║   ██║   ██║   
\t   ██║   ██╔╝ ██╗██║██████╔╝    ██║  ██║╚██████╔╝   ██║   ██║  ██║██████╔╝╚██████╔╝   ██║   
\t   ╚═╝   ╚═╝  ╚═╝╚═╝╚═════╝     ╚═╝  ╚═╝ ╚═════╝    ╚═╝   ╚═╝  ╚═╝╚═════╝  ╚═════╝    ╚═╝   
"""
    Write.Print(banner + '\n', Colors.purple_to_blue, interval=0)

    print(f"\t\t\t\t\ttxid's authbot v{__version__}\n")

    print(f"\t\t\t\t\tLogged as {bot.user}")
    print(f"\t\t\t\t\tTotal Users: {total_users}")
    print(f"\t\t\t\t\tScopes: {scope.replace('%20', ', ')}")
    print(f"\t\t\t\t\tGuilds: {len(bot.guilds)}\n")

    Write.Print(f"\t\t\t\thttps://github.com/txidstick/txid-authbot/\n\n", Colors.blue_to_purple, interval=0)
    
    if redirect_uri.endswith('/'):
        Write.Print(f"[ ! ] Warning: your redirect URI should not end with \"/\" symbol. Please remove it and restart the script.", Colors.yellow)
    
    # Check role hierarchy
    for guild_id, role_id in config['verify_guilds'].items():
        if str(guild_id).startswith('_'):
            continue
        try:
            guild = bot.get_guild(int(guild_id))
            if guild:
                role = guild.get_role(int(role_id))
                bot_member = guild.get_member(bot.user.id)
                if role and bot_member:
                    if bot_member.top_role <= role:
                        Write.Print(f"[ ! ] Warning: In {guild.name}, bot's role must be HIGHER than {role.name}!", Colors.yellow)
        except:
            pass


@bot.slash_command(name="whitelist", description="Add user to whitelist (Owner only)")
async def whitelist_command(ctx: discord.ApplicationContext, 
                           user: discord.Option(discord.User, description="User to whitelist")): # type: ignore
    if not is_owner(ctx.author.id):
        return await ctx.respond("❌ Only owners can use this command.", ephemeral=True)
    
    if user.id in whitelist:
        return await ctx.respond(f"⚠️ {user.mention} is already whitelisted.", ephemeral=True)
    
    whitelist.append(user.id)
    config['whitelist'] = whitelist
    
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=4)
    
    embed = discord.Embed(title="✅ User Whitelisted", color=discord.Color.green())
    embed.description = f"{user.mention} (`{user.id}`) can now use bot commands."
    embed.set_footer(text="txid's authbot")
    
    await ctx.respond(embed=embed, ephemeral=True)


@bot.slash_command(name="blacklist", description="Remove user from whitelist (Owner only)")
async def blacklist_command(ctx: discord.ApplicationContext, 
                           user: discord.Option(discord.User, description="User to blacklist")): # type: ignore
    if not is_owner(ctx.author.id):
        return await ctx.respond("❌ Only owners can use this command.", ephemeral=True)
    
    if user.id not in whitelist:
        return await ctx.respond(f"⚠️ {user.mention} is not whitelisted.", ephemeral=True)
    
    whitelist.remove(user.id)
    config['whitelist'] = whitelist
    
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=4)
    
    embed = discord.Embed(title="🚫 User Blacklisted", color=discord.Color.red())
    embed.description = f"{user.mention} (`{user.id}`) can no longer use bot commands."
    embed.set_footer(text="txid's authbot")
    
    await ctx.respond(embed=embed, ephemeral=True)


@bot.slash_command(name="refresh", description="Refresh access tokens for all users")
async def refresh_command(ctx: discord.ApplicationContext):
    if not is_authorized(ctx.author.id):
        return await ctx.respond("❌ You don't have permission to use this command.", ephemeral=True)
    
    await ctx.respond("Starting token refresh...", ephemeral=True)
    
    session = aiohttp.ClientSession()
    refreshed = 0
    failed = 0
    
    with open('data.json', 'r') as f:
        data = json.load(f)
    
    keys = list(data["users"].keys())
    
    for refresh_token_key in keys:
        user_data = data["users"][refresh_token_key]
        user_id = user_data["id"]
        
        refresh_json = await refresh_token(refresh_token_key, session)
        
        at = refresh_json.get("access_token")
        rt = refresh_json.get("refresh_token")
        
        if at is None or rt is None:
            failed += 1
            continue
            
        data["users"][rt] = {"id": user_id, "at": at}
        if rt != refresh_token_key:
            del data["users"][refresh_token_key]
        
        refreshed += 1
        await asyncio.sleep(0.5)
    
    with open('data.json', 'w') as f:
        json.dump(data, f)
    
    await session.close()
    await ctx.edit(content=f"✅ Refreshed: **{refreshed}**\n❌ Failed: **{failed}**")


@bot.slash_command(name="pull", description="Pull members to your server")
async def pull_command(ctx: discord.ApplicationContext, 
                       server_id: discord.Option(str, description="Server ID to pull members to"), # type: ignore
                       amount: discord.Option(int, description="Amount of members to pull (optional)", required=False)=None): # type: ignore
    if not is_authorized(ctx.author.id):
        return await ctx.respond("❌ You don't have permission to use this command.", ephemeral=True)

    guild = bot.get_guild(int(server_id))
    if guild is None:
        await ctx.respond("Guild not found! Make sure the bot is in it!", ephemeral=True)
        return
        
    t = f"Pulling started! Server: `{guild.name}`"
    if amount is not None:
        t += f"\nPulling **{amount}** members"

    await ctx.respond(t, ephemeral=True)
    await pull(ctx, server_id, amount)


@bot.slash_command(name="auths", description="Show stock of verified members")
async def auths_command(ctx: discord.ApplicationContext):
    if not is_authorized(ctx.author.id):
        return await ctx.respond("❌ You don't have permission to use this command.", ephemeral=True)
    
    with open('data.json', 'r') as f:
        data = json.load(f)
        count = len(data["users"])

    embed = discord.Embed(title="📊 Member Stock", color=discord.Color.green())
    embed.description = f"**Total Verified Members: `{count}`**"
    embed.set_footer(text="txid's authbot")
    
    await ctx.respond(embed=embed, ephemeral=True)


@bot.slash_command(name="verify-embed", description="Create a custom verification embed")
async def verify_embed(ctx: discord.ApplicationContext,
                        channel_id: discord.Option(str, description="Channel ID to send the embed to"), # type: ignore
                        title: discord.Option(str, description="Embed title", required=False)="Verify", # type: ignore
                        description: discord.Option(str, description="Embed description", required=False)="Please verify by clicking the button below:", # type: ignore
                        image: discord.Option(str, description="Embed image URL", required=False)=None, # type: ignore
                        thumbnail: discord.Option(str, description="Thumbnail image URL", required=False)=None, # type: ignore
                        button_text: discord.Option(str, description="Verify button text", required=False)="Verify", # type: ignore
                        button_emoji: discord.Option(str, description="Verify button emoji ID", required=False)=None): # type: ignore
    if not is_authorized(ctx.author.id):
        return await ctx.respond("❌ You don't have permission to use this command.", ephemeral=True)
    
    embed = discord.Embed(title=title, description=description.replace("\\n", "\n"), color=discord.Color.embed_background())
    if image is not None:
        embed.set_image(url=image)
    if thumbnail is not None:
        embed.set_thumbnail(url=thumbnail)


    channel = bot.get_channel(int(channel_id))
    if channel is None:
        return await ctx.respond("Channel not found!", ephemeral=True)
    
    login_url_with_state = LOGIN_URL + f"&state={channel.guild.id}"

    view = discord.ui.View()
    try:
        view.add_item(discord.ui.Button(label=button_text, url=login_url_with_state, emoji=bot.get_emoji(int(button_emoji)) if button_emoji is not None else None))
    except Exception as e:
        return await ctx.respond(f'An error occurred while adding button to the view: `{e}`', ephemeral=True)

    await channel.send(embed=embed, view=view)
    await ctx.respond(":white_check_mark:", ephemeral=True)


@bot.slash_command(name="help", description="Show all available commands")
async def help_command(ctx: discord.ApplicationContext):
    is_auth = is_authorized(ctx.author.id)
    is_own = is_owner(ctx.author.id)
    
    embed = discord.Embed(
        title="📚 txid's AuthBot - Commands",
        description="OAuth2 verification bot with member pulling capabilities",
        color=discord.Color.blue()
    )
    
    if is_auth:
        embed.add_field(
            name="🔄 /refresh",
            value="Refresh all user access tokens",
            inline=False
        )
        embed.add_field(
            name="👥 /pull <server_id> [amount]",
            value="Pull verified members to your server",
            inline=False
        )
        embed.add_field(
            name="📊 /auths",
            value="Show total verified member count",
            inline=False
        )
        embed.add_field(
            name="✅ /verify-embed <channel_id>",
            value="Create a custom verification embed",
            inline=False
        )
    
    if is_own:
        embed.add_field(
            name="➕ /whitelist <user>",
            value="Add user to whitelist (Owner only)",
            inline=False
        )
        embed.add_field(
            name="➖ /blacklist <user>",
            value="Remove user from whitelist (Owner only)",
            inline=False
        )
    
    embed.add_field(
        name="❓ /help",
        value="Show this help message",
        inline=False
    )
    
    embed.set_footer(text=f"txid's authbot v{__version__} | Made by {__author__}")
    
    if not is_auth and not is_own:
        embed.description = "❌ You don't have permission to use bot commands.\nContact an owner to get whitelisted."
    
    await ctx.respond(embed=embed, ephemeral=True)


def run_bot():
    try:
        bot.run(token)
    except Exception as e:
        print(f"Unhandled error running bot: {e}")


def run_api():
    uvicorn.run(app, host=server_host, port=int(server_port))


if __name__ == "__main__":
    bot_thread = Thread(target=run_bot)
    bot_thread.start()
    run_api()
