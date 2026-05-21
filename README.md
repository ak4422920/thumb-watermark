# Video Thumbnail Bot

<p align="center">
    <b>A powerful Telegram bot to add custom thumbnails to your videos instantly.</b>
    <br>
</p>

---

## 🛠 Features
- 🖼️ **Custom Thumbnails** - Set your own cover for videos
- ⚡ **Fast Processing** - Instant video forwarding
- 🔄 **Rotating Images** - Dynamic start images
- 👥 **User Database** - MongoDB storage
- 🏆 **Leaderboard** - Track top users
- 🛡️ **Admin Controls** - Ban, Broadcast, Stats
- 🐳 **Docker & Heroku Support**

## 🚀 Deployment

### 💜 Heroku
<p>
<a href="https://heroku.com/deploy?template=https://github.com/cantarella-wuwa/thumbnail-bot">
  <img src="https://www.herokucdn.com/deploy/button.svg" alt="Deploy">
</a>
</p>

1. Fork this repo.
2. Create a new app on Heroku.
3. Connect GitHub repo.
4. Add Config Vars.
5. Deploy `web` dyno.

### ☁️ Render (Free Tier)
1. Fork this repo.
2. Create a new **Web Service** on Render.
3. Connect GitHub repo.
4. Add Environment Variables.
5. Deploy! (Runs on free tier).

### 🟢 Koyeb (Free Tier)
1. Fork this repo.
2. Create a new **App** on Koyeb.
3. Select Docker deployment.
4. Add Environment Variables.
5. Deploy!

### 🐳 Docker
```bash
docker build -t cantarellabots-thumbnail-bot .
docker run --env-file .env cantarellabots-thumbnail-bot
```

### 💻 Local
```bash
pip install -r requirements.txt
python main.py
```

## ⚙️ Configuration

| Variable | Description | Required |
|----------|-------------|----------|
| `API_TOKEN` | Bot Token from @BotFather | ✅ |
| `MONGO_URL` | MongoDB Connection String | ✅ |
| `OWNER_ID` | Your Telegram User ID | ✅ |
| `LOG_CHANNEL` | Log Channel ID (e.g., -100xxxx) | ❌ |
| `CHANNEL_URL` | Channel URL for Join button | ❌ |
| `DEV_URL` | Developer Telegram URL | ❌ |

## 🤖 Bot Commands
Copy and paste this into BotFather:
```text
start - Start the bot
users - (Admin) View all users
topleaderboard - (Admin) Top users
broadcast - (Admin) Broadcast message
ban - (Admin) Ban a user
unban - (Admin) Unban a user
add_admin - (Owner) Add admin
remove_admin - (Owner) Remove admin
```

## 📁 Project Structure
```
thumbnail-bot/
├── main.py           # Entry point
├── config.py         # Configuration
├── database.py       # MongoDB functions
├── plugins/
│   ├── start.py      # /start command
│   ├── settings.py   # Thumbnail settings
│   ├── video.py      # Video handler
│   └── admin.py      # Admin commands
├── Dockerfile
├── Procfile
└── requirements.txt
```

## 👨‍💻 Credits
- **Developer**: [@cantarella_wuwa](https://t.me/cantarella_wuwa)
- **Channel**: [Cantarella Bots](https://t.me/cantarellabots)
- **Helper**: [@yato](https://github.com/ProYato)
- **Upgrade**: [@akmovieverse](https://t.me/akmovieverse)
<p align="center">
  <b>⭐ Star this repo if you like it!</b>
</p>
