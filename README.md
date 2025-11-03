<div align="center">
  <a href="https://github.com/txidstick/txid-authbot">
    <img src="https://github.com/txidstick/txid-authbot/blob/main/static/logo.png?raw=true" alt="Logo" style="width: 60%; height: 60%;">
  </a>
  
  <h2 align="center">txid's AuthBot</h2>
  <p align="center">
    Streamlined Discord OAuth2 Bot with FastAPI backend - Verify members and pull them back to your server effortlessly!
  </p>
</div>

---

<b>[Click here to join the support server](https://discord.gg/uDzAXwDsFm)</b>

### 🍕 Features

- ✅ **FastAPI Backend** - Modern, fast, and efficient web framework
- 🔐 **Advanced Permission System** - Owners and whitelist support
-  **6 Simple Commands** - Easy to use slash commands
- 🔄 Automatic token refresh system
- 🚀 Unlimited member pulling
- 📝 Dual logging (Channel + Webhook support)
- 🎨 Customizable verification embeds
- 🌍 Multi-server verification support
- ⚙️ Role hierarchy validation
- 🔒 **100%** CAPTCHA-free authentication
- 🎯 **Privacy-First** - Minimal OAuth2 scopes (identify + guilds.join only)
- 🚫 **No Data Collection** - No emails, connections, or unnecessary permissions
- ⚡ Commands work in ANY server (not limited to admin guild)

---

### 💻 Installation

**Requirements:**
- `Python 3.12` recommended (avoid Python 3.13+ due to compatibility issues)

**Steps:**
1. Download the repository *(if you haven't already)*
2. Create an application at the <b>[Discord Developer Portal](https://discord.com/developers)</b> and **enable all intents**
3. Edit the [config.json](https://github.com/txidstick/txid-authbot/blob/main/config.json) file:
   - Add your bot token, client ID, client secret, and redirect URI
   - Add owner IDs to the `owners` array
   - Optionally add webhook URL for dual logging
   - Configure verify_guilds with server_id: role_id pairs
   - **Important:** Make sure the bot's role is HIGHER than the verify role!
4. Configure the HTML page in [templates folder](https://github.com/txidstick/txid-authbot/blob/main/templates)
5. Install the requirements using `pip install -r requirements.txt`
6. Start the bot with `python bot.py` (use `python` not `py` on Windows)

**Important Notes:**
- ⚠️ Use **Python 3.12** for best compatibility
- 🔑 OAuth2 scopes are minimal: `identify` and `guilds.join` only (no email, connections, or guilds)
- 🛡️ Privacy-first approach - only essential permissions required

**Hosting Recommendation:**
For the best hosting experience, we recommend <b>[WispByte](https://wispbyte.com/)</b> - The ultimate **FREE and LIFETIME** hosting service!
- ⚡ Lightning-fast servers
- 🆓 100% Free forever - no renewals needed
- 🔧 Easy Flask/FastAPI deployment
- 🌐 Custom endpoints with port forwarding
- 🔒 Secure and reliable infrastructure

**Perfect for hosting your authbot 24/7!**

---

### 🎮 Commands

| Command | Description | Permission |
|---------|-------------|------------|
| `/verify-embed` | Create a custom verification embed in any channel | Whitelisted/Owner |
| `/pull <server_id> [amount]` | Pull verified members to your server | Whitelisted/Owner |
| `/refresh` | Refresh access tokens for all verified users | Whitelisted/Owner |
| `/auths` | Display the total stock of verified members | Whitelisted/Owner |
| `/whitelist <user>` | Add a user to the whitelist | Owner Only |
| `/blacklist <user>` | Remove a user from the whitelist | Owner Only |
| `/help` | Show all available commands | Everyone |

**Note:** Commands can be used in ANY server, not just the admin guild!

---

### ⚙️ Configuration Guide

**config.json Structure:**
```json
{
    "token": "YOUR_BOT_TOKEN",
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET",
    "redirect_uri": "http://localhost:8000",
    "scope": "identify%20guilds.join",
    
    "owners": [123456789],
    "whitelist": [],
    
    "log_channel": 987654321,
    "webhook_url": "https://discord.com/api/webhooks/...",
    
    "verify_guilds": {
        "server_id_1": role_id_1,
        "server_id_2": role_id_2
    }
}
```

**Important Notes:**
- ⚠️ **Bot's role MUST be higher than verify roles** for automatic role assignment
- 📝 You can use both log_channel and webhook_url for dual logging
- 👥 Owners have full access, whitelisted users can use all commands except whitelist/blacklist
- 🌐 Commands work globally in any server where the bot is present
- 🔐 **Minimal scopes**: Only `identify` and `guilds.join` - no email, connections, or server list

---

### 📸 Screenshots
<img src="https://github.com/txidstick/txid-authbot/blob/main/static/oauth2scr.webp?raw=true" style="width: 40%; height: 40%;" alt="An image showing a new verified user">
<img src="https://github.com/txidstick/txid-authbot/blob/main/static/pulling.webp?raw=true" style="width: 40%; height: 40%;" alt="An image showing /pull command">
<img src="https://github.com/txidstick/txid-authbot/blob/main/static/pull.webp?raw=true" style="width: 40%; height: 40%;" alt="An image showing /pull command results">
<img src="https://github.com/txidstick/txid-authbot/blob/main/static/ui.webp?raw=true" style="width: 40%; height: 40%;" alt="The UI of the program">

---

### ❗ Disclaimer

This github repo is for **EDUCATIONAL PURPOSES ONLY.** I am not responsible for your actions.

---

### 🌟 Having troubles?
If you have an error or a problem, feel free to [start a new issue!](https://github.com/txidstick/txid-authbot/issues/new)

**OR: join my [discord server](https://discord.gg/uDzAXwDsFm)**

Don't forget to leave a **star!**

---
### 📰 Changelog

```diff
v.1.0.0 ⋮ 03.11.2025
! Official stable release
+ FastAPI backend for modern web server
+ Whitelist/blacklist permission system  
+ Dual logging (channel + webhook support)
+ Global slash commands (work in any server)
+ Role hierarchy validation
+ Minimal OAuth2 scopes (identify + guilds.join only)
+ Privacy-first: No email, connections, guilds list, IP, or country tracking
+ 6 commands: /whitelist, /blacklist, /refresh, /pull, /auths, /verify-embed, /help
+ Improved role assignment with better error handling
+ Python 3.12 compatibility
+ Auto-save whitelist/blacklist to config
+ Multi-server verification support
! Optimized for privacy and security
```

---

<p align="center">
  <img src="https://img.shields.io/github/stars/txidstick/txid-authbot.svg?style=for-the-badge&labelColor=black&color=f429ff&logo=IOTA"/>
  <img src="https://img.shields.io/github/languages/top/txidstick/txid-authbot.svg?style=for-the-badge&labelColor=black&color=f429ff&logo=python"/>
</p>

---
