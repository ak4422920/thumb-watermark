
import os
import random

API_TOKEN = os.environ.get("API_TOKEN", "8865551346:AAEXPNMq4jPNvtF-x9YkV78GfoGUGh6_Eqk")

MONGO_URL = os.environ.get("MONGO_URL", "mongodb+srv://ak:ak@cluster0.97safhj.mongodb.net/?appName=Cluster0")
DB_NAME = "thumbnail_bot"

OWNER_ID = int(os.environ.get("OWNER_ID", "6522435665"))

START_PICS = [
    "https://i.ibb.co/0jjgxKM4/changli-wuthering-waves-4k-wallpaper-uhdpaper-com-437-2-b.jpg",
    # Add more direct image URLs here
]

CHANNEL_URL = os.environ.get("CHANNEL_URL", "https://t.me/akmovieverse")
AUTH_CHANNEL = os.environ.get("AUTH_CHANNEL", "@akmovieverse")
DEV_URL = os.environ.get("DEV_URL", "https://t.me/ak_ownerbot")
LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", "-1003865436133"))  # e.g., -100xxxxxxxxxxxx


DAILY_LIMIT = 50            # Rozana ki free limit
REFERRAL_COUNT = 3         # Premium ke liye kitne bande chahiye
FORCE_LIMIT = True         # Agar limit hatani ho toh isse False kar dena


def get_random_pic() -> str:
    """Get a random image from START_PICS."""
    if START_PICS:
        return random.choice(START_PICS)
    return None

# config.py mein add karein
POSTER_API_KEYS = [
    "spidy_zws7xa8aczb", 
    "spidy_l4bnk5ow5", 
    "spidy_v74cbzipa4b", 
    "spidy_wfm4fam8gd", 
    "spidy_ldn5qsgh7or", 
    "spidy_fp5z85is6sd", 
    "spidy_gxxbtvro53m", 
    "spidy_7rm5i09kmvs"
]

# Smart Cleaner patterns (Regex patterns for links and usernames)
CLEANER_PATTERNS = [
    r"https?://\S+",           # Links (http/https)
    r"t\.me/\S+",               # Telegram links
    r"@\w+",                    # Usernames (@name)
    r"www\.\S+"                 # Websites
]

# Available Font Styles
CAPTION_STYLES = ["Normal", "Small Caps", "Bold", "Italic", "Monospace"]

# Aapka Global Brand Link (Har processed video ke niche jayega)
BRAND_LINK = "@AkMovieVerse"


