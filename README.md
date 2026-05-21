# Video Thumbnail Bot

<p align="center">
    <b>A powerful Telegram bot to add custom thumbnails to your videos instantly.</b>
    <br>
    <a href="https://t.me/cantarellabots">
        <img src="https://img.shields.io/badge/Channel-CantarellaBots-blue?style=flat-square&logo=telegram" alt="Channel">
    </a>
    <a href="https://t.me/cantarella_wuwa">
        <img src="https://img.shields.io/badge/Developer-cantarella__wuwa-blue?style=flat-square&logo=telegram" alt="Developer">
    </a>
</p>

---

## 🔥 PREMIUM ENGINE UPGRADES (NEW)
> ⚡ **Yeh saare advanced features hal hi mein is repository mein inject kiye gaye hain jo is bot ko baaki sabse alag aur ultra-powerful banate hain:**

- 🌐 **6-Node Hybrid Parallel Mixer** - `/poster` command chalte hi bot ek sath 6 bade global servers (*Spidy OTT, TMDB, AniList, Jikan MAL, TVmaze, OMDB*) par parallel request bhejkar data fetch karta hai.
- 🔀 **Round-Robin Interleaving Balancing** - Saare sources ka data aapas mein mix hokar shuruati pages par hi user ko ek sath alag-alag sources ke best posters perfectly mix dikhte hain.
- 🖼️ **Dynamic Landscape Toggle Switch** - Built-in inline framework jo user ko 1-click mein vertical poster cover se horizontal wide landscape wallpaper par live switch karne deta hai.
- 🎨 **Natural Micro-Enhancer Pipeline (PIL)** - Low-quality thumbnails ko bina pixels faade, micro sharpness layer aur non-destructive vibrancy boost (25% Up) dekar automatic Ultra-HD crystal clear banata hai.
- 🔄 **Timestamp Cache Buster Engine** - Har file ke piche `time.time_ns()` ka unique fingerprint lagata hai, jisse Telegram ka internal cache bypass hota hai aur hamesha fresh processed HD image hi forward hoti hai.
- 🧹 **Maha Admin Advanced Cleaner** - Pure server storage aur database maintenance ke liye do solid commands: `/cleandb` (Safe junk remover) aur `/nukedb` (Full factory system reset).

---

## 🛠 Features
- 🖼️ **Custom Thumbnails** - Set your own cover for videos
- ⚡ **Fast Processing** - Instant video forwarding with multi-stream handlers
- 🔄 **Rotating Images** - Dynamic start images with smart URL input file
- 👥 **User Database** - High-speed MongoDB storage and caching grid
- 🏆 **Leaderboard** - Track top active users
- 🛡️ **Admin Controls** - Ban, Unban, Broadcast, Stats, and Database flushers
- 🐳 **Docker & Heroku Support** - Modern `.python-version` runtime compatibility

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
💻 LocalBashpip install -r requirements.txt
python main.py
⚙️ ConfigurationVariableDescriptionRequiredAPI_TOKENBot Token from @BotFather✅MONGO_URLMongoDB Connection String✅OWNER_IDYour Telegram User ID (Strict Owner Mode)✅POSTER_API_KEYSSpidy API Keys Array inside config for Round-Robin✅LOG_CHANNELLog Channel ID (e.g., -100xxxx)❌CHANNEL_URLChannel URL for Join button (Force Subscribe)❌DEV_URLDeveloper Telegram URL❌🤖 Bot CommandsCopy and paste this into BotFather:Plaintextstart - Start the bot & check progress
poster - Search movie/anime posters across 6 hybrid nodes
cleandb - (Owner) Safe RAM/Disk maintenance clean
nukedb - (Owner) Full factory reset (Wipe all data & files)
users - (Admin) View all users
topleaderboard - (Admin) Top users
broadcast - (Admin) Broadcast message
ban - (Admin) Ban a user
unban - (Admin) Unban a user
add_admin - (Owner) Add admin
remove_admin - (Owner) Remove admin
📁 Project Structurethumbnail-bot/
├── main.py            # Entry point & polling router
├── config.py          # Configuration & API array strings
├── database.py        # MongoDB schema & referral logic
├── plugins/
│   ├── start.py       # /start command & Bug-free safe text stats
│   ├── settings.py    # Thumbnail settings panel
│   ├── video.py       # Video handler & PIL Ultra-HD Enhancer Engine
│   ├── poster.py      # 6-Node Hybrid Parallel Mixer Core (New)
│   └── admin.py       # Admin commands, /cleandb and /nukedb (New)
├── Dockerfile
├── Procfile
├── .python-version    # Deprecated runtime.txt fix (New)
└── requirements.txt   # Upgraded dependencies (Pillow, Aiogram, etc.)
👨‍💻 CreditsDeveloper: @cantarella_wuwaChannel: Cantarella BotsHelper: @yatoUpgrade & Core Matrix Developer: @akmovieverse
