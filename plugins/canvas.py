import os
import asyncio
import re
from aiogram.filters import Command
from aiogram import Router, F, Bot
from aiogram.types import (Message, CallbackQuery, InlineKeyboardMarkup,
                            InlineKeyboardButton, FSInputFile)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from database import (
    set_canvas_status, get_canvas_status,
    set_canvas_watermark, get_canvas_watermark,
    set_user_font, get_user_font,
    db
)
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

# â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
# â•‘                      DB FUNCTIONS                           â•‘
# â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

async def _db():
    from database import db as active_db
    return active_db

async def set_user_text_size(user_id: int, v: str):
    d = await _db()
    await d.users.update_one({"user_id": user_id}, {"$set": {"canvas_text_size": v}}, upsert=True)

async def get_user_text_size(user_id: int) -> str:
    d = await _db()
    if d is None: return "medium"
    u = await d.users.find_one({"user_id": user_id})
    return u.get("canvas_text_size", "medium") if u else "medium"

async def set_user_title_visible(user_id: int, v: bool):
    d = await _db()
    await d.users.update_one({"user_id": user_id}, {"$set": {"canvas_title_visible": v}}, upsert=True)

async def get_user_title_visible(user_id: int) -> bool:
    d = await _db()
    if d is None: return True
    u = await d.users.find_one({"user_id": user_id})
    return u.get("canvas_title_visible", True) if u else True

async def set_user_watermark_position(user_id: int, v: str):
    d = await _db()
    await d.users.update_one({"user_id": user_id}, {"$set": {"canvas_wm_position": v}}, upsert=True)

async def get_user_watermark_position(user_id: int) -> str:
    d = await _db()
    if d is None: return "bot_center"
    u = await d.users.find_one({"user_id": user_id})
    return u.get("canvas_wm_position", "bot_center") if u else "bot_center"

async def set_user_watermark_size(user_id: int, v: str):
    d = await _db()
    await d.users.update_one({"user_id": user_id}, {"$set": {"canvas_wm_size": v}}, upsert=True)

async def get_user_watermark_size(user_id: int) -> str:
    d = await _db()
    if d is None: return "medium"
    u = await d.users.find_one({"user_id": user_id})
    return u.get("canvas_wm_size", "medium") if u else "medium"

# --- Watermark ON/OFF Toggle ---
async def set_user_wm_visible(user_id: int, v: bool):
    """Watermark ON/OFF toggle save karne ke liye."""
    d = await _db()
    await d.users.update_one({"user_id": user_id}, {"$set": {"canvas_wm_visible": v}}, upsert=True)

async def get_user_wm_visible(user_id: int) -> bool:
    """Watermark visibility check karne ke liye (Default: True = ON)."""
    d = await _db()
    if d is None: return True
    u = await d.users.find_one({"user_id": user_id})
    return u.get("canvas_wm_visible", True) if u else True

async def set_user_wm_color(user_id: int, v: str):
    d = await _db()
    await d.users.update_one({"user_id": user_id}, {"$set": {"canvas_wm_color": v}}, upsert=True)

async def get_user_wm_color(user_id: int) -> str:
    d = await _db()
    if d is None: return "yellow"
    u = await d.users.find_one({"user_id": user_id})
    return u.get("canvas_wm_color", "yellow") if u else "yellow"

async def set_user_strip_visible(user_id: int, v: bool):
    d = await _db()
    await d.users.update_one({"user_id": user_id}, {"$set": {"canvas_strip_visible": v}}, upsert=True)

async def get_user_strip_visible(user_id: int) -> bool:
    d = await _db()
    if d is None: return True
    u = await d.users.find_one({"user_id": user_id})
    return u.get("canvas_strip_visible", True) if u else True

async def set_user_strip_color(user_id: int, v: str):
    d = await _db()
    await d.users.update_one({"user_id": user_id}, {"$set": {"canvas_strip_color": v}}, upsert=True)

async def get_user_strip_color(user_id: int) -> str:
    d = await _db()
    if d is None: return "black"
    u = await d.users.find_one({"user_id": user_id})
    return u.get("canvas_strip_color", "black") if u else "black"

async def set_user_canvas_logo(user_id: int, v: str):
    d = await _db()
    await d.users.update_one({"user_id": user_id}, {"$set": {"canvas_logo_file_id": v}}, upsert=True)

async def get_user_canvas_logo(user_id: int) -> str:
    d = await _db()
    if d is None: return ""
    u = await d.users.find_one({"user_id": user_id})
    return u.get("canvas_logo_file_id", "") if u else ""

async def remove_user_canvas_logo(user_id: int):
    d = await _db()
    await d.users.update_one({"user_id": user_id}, {"$set": {"canvas_logo_file_id": ""}})

async def set_user_logo_position(user_id: int, v: str):
    d = await _db()
    await d.users.update_one({"user_id": user_id}, {"$set": {"canvas_logo_pos": v}}, upsert=True)

async def get_user_logo_position(user_id: int) -> str:
    d = await _db()
    if d is None: return "top_right"
    u = await d.users.find_one({"user_id": user_id})
    return u.get("canvas_logo_pos", "top_right") if u else "top_right"

async def set_user_logo_size(user_id: int, v: str):
    d = await _db()
    await d.users.update_one({"user_id": user_id}, {"$set": {"canvas_logo_size": v}}, upsert=True)

async def get_user_logo_size(user_id: int) -> str:
    d = await _db()
    if d is None: return "medium"
    u = await d.users.find_one({"user_id": user_id})
    return u.get("canvas_logo_size", "medium") if u else "medium"


# â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
# â•‘                   ROUTER & FSM STATES                       â•‘
# â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

router        = Router()
canvas_queue  = asyncio.Queue()
is_processing = False

class CanvasStates(StatesGroup):
    waiting_for_watermark = State()
    waiting_for_logo      = State()


# â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
# â•‘                      CONSTANTS                              â•‘
# â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

WM_SIZE_MULTIPLIERS = {
    "xs": 0.030, "small": 0.045, "medium": 0.062, "large": 0.085, "xl": 0.115,
}
WM_SIZE_MIN_PX = {
    "xs": 18, "small": 22, "medium": 28, "large": 36, "xl": 48,
}
WM_SIZE_LABELS = {
    "xs": "XS", "small": "S", "medium": "M", "large": "L", "xl": "XL",
}

WM_POSITION_LABELS = {
    "top_left": "↖ Top Left",   "top_center": "⬆ Top Center", "top_right": "↗ Top Right",
    "mid_left": "◀ Mid Left",   "mid_center": "✛ Mid Center", "mid_right": "▶ Mid Right",
    "bot_left": "↙ Bot Left",   "bot_center": "⬇ Bot Center", "bot_right": "↘ Bot Right",
}

# 12 Gradient Strip Color Schemes
# top=(R,G,B,A) fade-in from image | bot=(R,G,B,A) solid base
STRIP_COLORS = {
    "black":    {"label": "⚫ Black",     "top": (0,   0,   0,   0),   "bot": (0,   0,   0,   225)},
    "red":      {"label": "🔴 Red",       "top": (60,  0,   0,   0),   "bot": (180, 0,   0,   220)},
    "blue":     {"label": "🔵 Blue",      "top": (0,   0,   60,  0),   "bot": (0,   40,  180, 220)},
    "purple":   {"label": "🟣 Purple",    "top": (40,  0,   60,  0),   "bot": (100, 0,   180, 220)},
    "green":    {"label": "🟢 Green",     "top": (0,   50,  0,   0),   "bot": (0,   130, 0,   220)},
    "orange":   {"label": "🟠 Orange",    "top": (60,  20,  0,   0),   "bot": (200, 80,  0,   220)},
    "gold":     {"label": "🟡 Gold",      "top": (60,  40,  0,   0),   "bot": (180, 140, 0,   220)},
    "fire":     {"label": "🔥 Fire",      "top": (150, 0,   0,   100), "bot": (255, 80,  0,   220)},
    "ocean":    {"label": "🌊 Ocean",     "top": (0,   30,  80,  50),  "bot": (0,   80,  160, 220)},
    "midnight": {"label": "🌙 Midnight",  "top": (10,  0,   40,  50),  "bot": (30,  0,   120, 220)},
    "rose":     {"label": "🌹 Rose",      "top": (60,  0,   30,  0),   "bot": (180, 0,   80,  220)},
    "teal":     {"label": "💠 Teal",      "top": (0,   40,  40,  0),   "bot": (0,   120, 120, 220)},
}

# 12 Watermark Text Colors
WM_COLOR_MAP = {
    "yellow":  {"label": "🟡 Yellow", "rgb": (255, 235,  59)},
    "white":   {"label": "⚪ White",  "rgb": (255, 255, 255)},
    "red":     {"label": "🔴 Red",    "rgb": (255,  60,  60)},
    "orange":  {"label": "🟠 Orange", "rgb": (255, 140,   0)},
    "green":   {"label": "🟢 Green",  "rgb": ( 80, 220,  80)},
    "cyan":    {"label": "🔹 Cyan",   "rgb": (  0, 220, 220)},
    "pink":    {"label": "🌸 Pink",   "rgb": (255, 105, 180)},
    "gold":    {"label": "✨ Gold",   "rgb": (255, 215,   0)},
    "lime":    {"label": "💚 Lime",   "rgb": (180, 255,   0)},
    "purple":  {"label": "🟣 Purple", "rgb": (200, 100, 255)},
    "sky":     {"label": "🔵 Sky",    "rgb": ( 80, 180, 255)},
    "silver":  {"label": "⚙ Silver", "rgb": (192, 192, 192)},
}

# Logo size â€” fraction of image width
LOGO_SIZE_MAP    = {"small": 0.08, "medium": 0.13, "large": 0.20}
LOGO_SIZE_LABELS = {"small": "Small", "medium": "Medium", "large": "Large"}
LOGO_POS_LABELS  = {
    "top_left": "↖ Top Left", "top_right": "↗ Top Right",
    "bot_left": "↙ Bot Left", "bot_right": "↘ Bot Right",
}

def _bool_icon(v: bool) -> str:
    return "✅" if v else "❌"

def _back_btn(cb: str = "manage_canvas") -> list:
    return [InlineKeyboardButton(text="🔙 Back to Canvas", callback_data=cb)]


# â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
# â•‘                  PILLOW ENGINE HELPERS                      â•‘
# â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def extract_pure_movie_name(caption_text: str) -> str:
    if not caption_text:
        return "NEW MOVIE"
    clean = caption_text.split('\n')[0].strip()
    clean = re.sub(r'https?://\S+|www\.\S+|@\S+|t\.me/\S+', '', clean)
    clean = re.sub(r'\[.*?\]|\(.*?\)', '', clean)
    clean = re.sub(r'\.mkv|\.mp4|\.avi|\.webm|\.srt', '', clean, flags=re.IGNORECASE)
    for p in [
        r'720p', r'1080p', r'2160p', r'4k', r'2k', r'hdcam', r'pre-dvd', r'web-dl', r'webrip',
        r'bluray', r'hdtv', r'brrip', r'dvdrip', r'hevc', r'x264', r'h264', r'x265', r'h265',
        r'dual audio', r'hindi', r'english', r'esub', r'msub', r'org audio', r'original audio',
        r'clean audio', r'hq', r'rip', r'remastered', r'uncut', r'extended'
    ]:
        clean = re.sub(p, '', clean, flags=re.IGNORECASE)
    clean = clean.replace('.', ' ').replace('_', ' ').replace('-', ' ').replace('|', ' ')
    clean = re.sub(r'[^\x00-\x7F]+', '', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean if clean else "NEW MOVIE"


def wrap_text_to_lines(text: str, font, max_width: int):
    words, lines, cur = text.split(), [], []
    for word in words:
        test = ' '.join(cur + [word])
        if ImageDraw.Draw(Image.new('RGB', (1, 1))).textlength(test, font=font) <= max_width:
            cur.append(word)
        else:
            if cur: lines.append(' '.join(cur))
            cur = [word]
    if cur: lines.append(' '.join(cur))
    return lines[:2]


def normalize_canvas_image(img: Image.Image) -> Image.Image:
    """Normalize orientation and safely flatten alpha images."""
    img = ImageOps.exif_transpose(img)
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        base = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        return Image.alpha_composite(base, rgba).convert("RGB")
    if img.mode != "RGB":
        return img.convert("RGB")
    return img.copy()


def build_telegram_cover(source_path: str, cover_path: str) -> bool:
    """Create a fallback Telegram-safe JPEG cover from rendered canvas."""
    try:
        with Image.open(source_path) as img:
            img = normalize_canvas_image(img)
            W, H = img.size
            max_side = max(W, H, 1)
            if max_side > 1280:
                scale = 1280 / max_side
                new_size = (max(1, int(W * scale)), max(1, int(H * scale)))
                img = img.resize(new_size, Image.LANCZOS)

            quality = 96
            img.save(cover_path, "JPEG", quality=quality, subsampling=0, optimize=True)
            while os.path.getsize(cover_path) > 900_000 and quality > 80:
                quality -= 5
                img.save(cover_path, "JPEG", quality=quality, subsampling=0, optimize=True)
        return True
    except Exception as e:
        print(f"Telegram cover build error: {e}")
        return False


def enhance_canvas_output(source_path: str, enhanced_path: str) -> bool:
    """Upscale and sharpen the rendered canvas for a crisper HD cover."""
    try:
        with Image.open(source_path) as img:
            img = normalize_canvas_image(img)
            if img.size != (1280, 720):
                img = ImageOps.fit(img, (1280, 720), method=Image.LANCZOS, centering=(0.5, 0.5))

            img = ImageOps.autocontrast(img, cutoff=0.6)
            img = ImageEnhance.Contrast(img).enhance(1.12)
            img = ImageEnhance.Color(img).enhance(1.16)
            img = img.filter(ImageFilter.UnsharpMask(radius=1.8, percent=165, threshold=2))
            img.save(enhanced_path, "JPEG", quality=97, subsampling=0, optimize=True)
        return True
    except Exception as e:
        print(f"Canvas enhance error: {e}")
        return False


def draw_gradient_strip(img: Image.Image, W: int, H: int,
                         strip_height: int, color_scheme: str) -> Image.Image:
    scheme       = STRIP_COLORS.get(color_scheme, STRIP_COLORS["black"])
    top_c, bot_c = scheme["top"], scheme["bot"]
    overlay      = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ov_draw      = ImageDraw.Draw(overlay)
    for i in range(strip_height):
        t = i / max(strip_height - 1, 1)
        r = int(top_c[0] + t * (bot_c[0] - top_c[0]))
        g = int(top_c[1] + t * (bot_c[1] - top_c[1]))
        b = int(top_c[2] + t * (bot_c[2] - top_c[2]))
        a = int(top_c[3] + t * (bot_c[3] - top_c[3]))
        ov_draw.line([(0, H - strip_height + i), (W, H - strip_height + i)], fill=(r, g, b, a))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def apply_logo_overlay(img: Image.Image, logo_path: str,
                        logo_position: str, logo_size_key: str,
                        strip_height: int) -> Image.Image:
    if not logo_path or not os.path.exists(logo_path):
        return img
    try:
        W, H     = img.size
        target_w = int(W * LOGO_SIZE_MAP.get(logo_size_key, 0.13))
        margin   = int(W * 0.03)
        strip_top = H - strip_height
        with Image.open(logo_path) as logo:
            logo     = logo.convert("RGBA")
            lw, lh   = logo.size
            target_h = int(lh * (target_w / lw))
            logo     = logo.resize((target_w, target_h), Image.LANCZOS)
            if logo_position == "top_left":
                x, y = margin, margin
            elif logo_position == "top_right":
                x, y = W - target_w - margin, margin
            elif logo_position == "bot_left":
                x, y = margin, strip_top - target_h - margin
            else:
                x, y = W - target_w - margin, strip_top - target_h - margin
            x = max(0, min(x, W - target_w))
            y = max(0, min(y, H - target_h))
            base = img.convert("RGBA")
            base.paste(logo, (x, y), logo)
            return base.convert("RGB")
    except Exception as e:
        print(f"Logo overlay error: {e}")
        return img


def draw_watermark_with_bg(img: Image.Image, text: str, font,
                            position: str, strip_height: int,
                            wm_color: tuple = (255, 235, 59)) -> Image.Image:
    W, H = img.size
    t_w  = ImageDraw.Draw(Image.new('RGB', (1, 1))).textlength(text, font=font)
    try:
        bbox = font.getbbox("Ay")
        t_h  = bbox[3] - bbox[1]
    except Exception:
        t_h = int(strip_height * 0.24)

    pad_x  = int(t_h * 0.55)
    pad_y  = int(t_h * 0.30)
    margin = int(W * 0.03)
    pill_w = int(t_w) + pad_x * 2
    pill_h = t_h + pad_y * 2

    pos_map = {
        "top_left":   (margin,              margin),
        "top_center": ((W - pill_w) // 2,   margin),
        "top_right":  (W - pill_w - margin, margin),
        "mid_left":   (margin,              (H - pill_h) // 2),
        "mid_center": ((W - pill_w) // 2,   (H - pill_h) // 2),
        "mid_right":  (W - pill_w - margin, (H - pill_h) // 2),
        "bot_left":   (margin,              H - strip_height + int(strip_height * 0.60)),
        "bot_right":  (W - pill_w - margin, H - strip_height + int(strip_height * 0.60)),
        "bot_center": ((W - pill_w) // 2,   H - strip_height + int(strip_height * 0.60)),
    }
    x, y = pos_map.get(position, pos_map["bot_center"])
    x    = max(margin, min(x, W - pill_w - margin))
    y    = max(margin, min(y, H - pill_h - margin))

    base = img.convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rounded_rectangle(
        [(x, y), (x + pill_w, y + pill_h)],
        radius=pill_h // 2,
        fill=(0, 0, 0, 175)
    )

    tx, ty = x + pad_x, y + pad_y
    for ax, ay in [(-1,-1),(-1,1),(1,-1),(1,1)]:
        overlay_draw.text((tx + ax, ty + ay), text, fill=(0, 0, 0, 255), font=font)
    overlay_draw.text((tx, ty), text, fill=wm_color + (255,), font=font)

    return Image.alpha_composite(base, overlay).convert("RGB")


# â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
# â•‘                    MAIN PILLOW ENGINE                       â•‘
# â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def draw_smart_canvas(input_path: str, output_path: str, raw_title: str,
                      watermark_text: str, selected_font: str, size_setting: str,
                      watermark_position: str = "bot_center",
                      watermark_size: str     = "medium",
                      strip_color: str        = "black",
                      strip_visible: bool     = True,
                      logo_path: str          = None,
                      logo_position: str      = "top_right",
                      logo_size: str          = "medium",
                      title_visible: bool     = True,
                      wm_color: str           = "yellow",
                      wm_visible: bool        = True):    # âœ… NEW
    try:
        with Image.open(input_path) as img:
            img = normalize_canvas_image(img)
            W, H         = img.size
            strip_height = int(H * 0.24) if size_setting == "big" else int(H * 0.19)

            if strip_visible:
                img = draw_gradient_strip(img, W, H, strip_height, strip_color)
            draw = ImageDraw.Draw(img)

            font_path = (selected_font if (selected_font and os.path.exists(selected_font))
                         else "fonts/Varsity Narrow.ttf")
            if not os.path.exists(font_path):
                font_path = None

            mult = {"small": 0.40, "medium": 0.52, "big": 0.65}.get(size_setting, 0.52)
            try:
                if font_path:
                    title_font   = ImageFont.truetype(font_path, int(strip_height * mult))
                    wm_px        = max(WM_SIZE_MIN_PX.get(watermark_size, 28),
                                       int(W * WM_SIZE_MULTIPLIERS.get(watermark_size, 0.062)))
                    wm_font      = ImageFont.truetype(font_path, wm_px)
                else:
                    title_font = wm_font = ImageFont.load_default()
            except Exception:
                title_font = wm_font = ImageFont.load_default()

            movie_title       = extract_pure_movie_name(raw_title).upper().strip()
            # wm_visible=False ho to watermark bilkul mat lagao
            watermark_display = (f"JOIN: {watermark_text.upper().strip()}"
                                 if (watermark_text and wm_visible) else "")

            if title_visible:
                lines     = wrap_text_to_lines(movie_title, title_font, int(W * 0.90))
                current_y = H - strip_height + int(strip_height * 0.08)
                for line in lines:
                    t_w = draw.textlength(line, font=title_font)
                    t_x = (W - t_w) // 2
                    for ax, ay in [(-2,-2),(-2,2),(2,-2),(2,2),(-1,0),(1,0),(0,-1),(0,1)]:
                        draw.text((t_x + ax, current_y + ay), line, fill=(0, 0, 0), font=title_font)
                    draw.text((t_x, current_y), line, fill=(255, 255, 255), font=title_font)
                    current_y += int(strip_height * (mult * 0.82))

            if watermark_display:
                wm_rgb = WM_COLOR_MAP.get(wm_color, WM_COLOR_MAP["yellow"])["rgb"]
                img    = draw_watermark_with_bg(
                    img, watermark_display, wm_font,
                    watermark_position, strip_height, wm_rgb
                )
                draw   = ImageDraw.Draw(img)

            if logo_path:
                img = apply_logo_overlay(img, logo_path, logo_position, logo_size, strip_height)

            img.save(output_path, "JPEG", quality=97, subsampling=0, optimize=True)
            return True
    except Exception as e:
        print(f"Canvas Error: {e}")
        return False


# â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
# â•‘                      QUEUE WORKER                           â•‘
# â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

async def canvas_queue_worker(bot: Bot):
    global is_processing
    if is_processing:
        return
    is_processing = True
    while not canvas_queue.empty():
        task = await canvas_queue.get()
        user_id, thumb_file_id, movie_title, watermark_text, selected_font, fut = task

        size_setting       = await get_user_text_size(user_id)
        watermark_position = await get_user_watermark_position(user_id)
        watermark_size     = await get_user_watermark_size(user_id)
        wm_color           = await get_user_wm_color(user_id)
        strip_color        = await get_user_strip_color(user_id)
        strip_visible      = await get_user_strip_visible(user_id)
        logo_file_id       = await get_user_canvas_logo(user_id)
        logo_position      = await get_user_logo_position(user_id)
        logo_size_val      = await get_user_logo_size(user_id)
        title_visible      = await get_user_title_visible(user_id)
        wm_visible         = await get_user_wm_visible(user_id)      # âœ… NEW

        input_path  = f"downloads/raw_{user_id}.jpg"
        output_path = f"downloads/canvas_{user_id}.jpg"
        enhanced_path = f"downloads/canvas_hd_{user_id}.jpg"
        cover_path  = f"downloads/canvas_cover_{user_id}.jpg"
        logo_path   = f"downloads/logo_{user_id}.png" if logo_file_id else None
        os.makedirs("downloads", exist_ok=True)

        try:
            fi = await bot.get_file(thumb_file_id)
            await bot.download_file(fi.file_path, input_path)

            if logo_file_id:
                try:
                    li = await bot.get_file(logo_file_id)
                    await bot.download_file(li.file_path, logo_path)
                except Exception as e:
                    print(f"Logo download failed: {e}")
                    logo_path = None

            loop    = asyncio.get_running_loop()
            success = await loop.run_in_executor(
                None, draw_smart_canvas,
                input_path, output_path, movie_title,
                watermark_text, selected_font, size_setting,
                watermark_position, watermark_size,
                strip_color, strip_visible,
                logo_path, logo_position, logo_size_val,
                title_visible, wm_color, wm_visible
            )

            if success and os.path.exists(output_path):
                final_output_path = output_path
                if enhance_canvas_output(output_path, enhanced_path) and os.path.exists(enhanced_path):
                    final_output_path = enhanced_path

                msg = None
                try:
                    msg = await bot.send_photo(chat_id=user_id, photo=FSInputFile(final_output_path))
                except Exception as photo_err:
                    print(f"HD canvas upload failed, using fallback cover: {photo_err}")
                    if build_telegram_cover(final_output_path, cover_path) and os.path.exists(cover_path):
                        msg = await bot.send_photo(chat_id=user_id, photo=FSInputFile(cover_path))

                if msg:
                    tid = msg.photo[-1].file_id
                    await msg.delete()
                    fut.set_result(tid)
                else:
                    fut.set_result(None)
            else:
                fut.set_result(None)
        except Exception as e:
            print(f"Queue Worker: {e}")
            fut.set_result(None)
        finally:
            for p in [input_path, output_path, enhanced_path, cover_path] + ([logo_path] if logo_path else []):
                if p and os.path.exists(p):
                    try: os.remove(p)
                    except: pass
            canvas_queue.task_done()
    is_processing = False


async def add_to_canvas_queue(bot: Bot, user_id: int, thumb_file_id: str,
                               movie_title: str, watermark_text: str, selected_font: str):
    loop = asyncio.get_running_loop()
    fut  = loop.create_future()
    await canvas_queue.put((user_id, thumb_file_id, movie_title, watermark_text, selected_font, fut))
    asyncio.create_task(canvas_queue_worker(bot))
    return await fut


# â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
# â•‘              TABBED MENU BUILDERS                           â•‘
# â• â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•£
# â•‘  1. send_canvas_menu      â€” Main overview dashboard         â•‘
# â•‘  2. send_text_menu        â€” Font + Title size + toggle      â•‘
# â•‘  3. send_watermark_menu   â€” WM text/color/size/position     â•‘
# â•‘  4. send_strip_menu       â€” Strip color + on/off            â•‘
# â•‘  5. send_logo_menu        â€” Logo upload/pos/size/remove     â•‘
# â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

async def _safe_edit(target: Message | CallbackQuery, text: str, kb: InlineKeyboardMarkup):
    """Edit message safely â€” ignore 'not modified' error."""
    try:
        if isinstance(target, CallbackQuery):
            await target.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        else:
            await target.answer(text, parse_mode="HTML", reply_markup=kb)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e).lower():
            raise


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# 1. MAIN CANVAS DASHBOARD
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
async def send_canvas_menu(target: Message | CallbackQuery, user_id: int):
    status        = await get_canvas_status(user_id)
    title_visible = await get_user_title_visible(user_id)
    strip_visible = await get_user_strip_visible(user_id)
    watermark     = await get_canvas_watermark(user_id)
    size_setting  = await get_user_text_size(user_id)
    current_font  = await get_user_font(user_id)
    wm_position   = await get_user_watermark_position(user_id)
    wm_size       = await get_user_watermark_size(user_id)
    wm_color      = await get_user_wm_color(user_id)
    wm_visible    = await get_user_wm_visible(user_id)
    strip_color   = await get_user_strip_color(user_id)
    logo_file_id  = await get_user_canvas_logo(user_id)
    logo_pos      = await get_user_logo_position(user_id)
    logo_size     = await get_user_logo_size(user_id)

    font_name = (os.path.basename(current_font).replace('.ttf', '')
                 if current_font and os.path.exists(current_font)
                 else "Default")

    wm_text    = watermark if watermark else "Not Set"
    strip_lbl  = STRIP_COLORS.get(strip_color, {}).get("label", strip_color)
    wm_clr_lbl = WM_COLOR_MAP.get(wm_color, WM_COLOR_MAP["yellow"])["label"]
    logo_lbl   = (f"{LOGO_POS_LABELS.get(logo_pos, logo_pos)} • "
                  f"{LOGO_SIZE_LABELS.get(logo_size, logo_size)}" if logo_file_id else "Not Set")

    text = (
        f"<b>🎨 Smart Canvas Editor</b>\n"
        f"{'━' * 28}\n\n"
        f"{'🟢 ACTIVE' if status else '🔴 DISABLED'}   "
        f"<b>|</b>  Tap <b>Toggle</b> to switch\n\n"

        f"<b>📝 Text Settings</b>\n"
        f"  Font: <code>{font_name}</code>\n"
        f"  Size: <code>{size_setting.upper()}</code>   "
        f"Title: {_bool_icon(title_visible)}\n\n"

        f"<b>💧 Watermark</b>\n"
        f"  Text: <code>{wm_text}</code>\n"
        f"  Color: {wm_clr_lbl}   "
        f"Size: <code>{WM_SIZE_LABELS.get(wm_size, wm_size)}</code>\n"
        f"  Position: <code>{WM_POSITION_LABELS.get(wm_position, wm_position)}</code>\n\n"

        f"<b>🎨 Strip</b>\n"
        f"  {strip_lbl}   {_bool_icon(strip_visible)}\n\n"

        f"<b>🖼️ Logo</b>\n"
        f"  {logo_lbl}\n"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        # Section tabs
        [InlineKeyboardButton(text="📝 Text Settings", callback_data="canvas_tab_text"),
         InlineKeyboardButton(text="💧 Watermark", callback_data="canvas_tab_wm")],
        [InlineKeyboardButton(text="🎨 Strip", callback_data="canvas_tab_strip"),
         InlineKeyboardButton(text="🖼️ Logo", callback_data="canvas_tab_logo")],
        [InlineKeyboardButton(
            text=f"{'🟢 Canvas ON  →  Turn OFF' if status else '🔴 Canvas OFF  →  Turn ON'}",
            callback_data="toggle_canvas"
        )],
        [InlineKeyboardButton(text="🔙 Back to Settings", callback_data="settings")],
    ])
    await _safe_edit(target, text, kb)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# 2. TEXT SETTINGS TAB
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
async def send_text_menu(target: Message | CallbackQuery, user_id: int, page: int = 0):
    size_setting  = await get_user_text_size(user_id)
    title_visible = await get_user_title_visible(user_id)
    current_font  = await get_user_font(user_id)

    font_name = (os.path.basename(current_font).replace('.ttf', '')
                 if current_font and os.path.exists(current_font) else "Default")

    fonts_dir = "fonts"
    all_fonts = []
    if os.path.exists(fonts_dir):
        all_fonts = sorted([f for f in os.listdir(fonts_dir) if f.endswith('.ttf')])
    per_pg      = 6
    total_pages = max(1, (len(all_fonts) + per_pg - 1) // per_pg)
    page        = max(0, min(page, total_pages - 1))

    text = (
        f"<b>📝 Text Settings</b>\n"
        f"{'━' * 28}\n\n"
        f"🔤 Font:       <code>{font_name}</code>\n"
        f"📐 Text Size:  <code>{size_setting.upper()}</code>\n"
        f"📝 Title:      {_bool_icon(title_visible)} "
        f"{'<b>ON</b>' if title_visible else '<b>OFF</b>'}\n"
        f"📖 Font Page:  <code>{page + 1} / {total_pages}</code>\n\n"
        f"<i>Select a font style below:</i>"
    )

    # Font grid (2 per row)
    font_rows = []
    if all_fonts:
        page_fonts = all_fonts[page * per_pg : (page + 1) * per_pg]
        row = []
        for f in page_fonts:
            row.append(InlineKeyboardButton(
                text=f.replace('.ttf', ''),
                callback_data=f"setfont_{f}_{page}"
            ))
            if len(row) == 2:
                font_rows.append(row); row = []
        if row: font_rows.append(row)

    # Pagination
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️ Prev", callback_data=f"txt_page_{page-1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="Next ▶️", callback_data=f"txt_page_{page+1}"))
    if nav: font_rows.append(nav)

    controls = [
        [InlineKeyboardButton(text="📐 Small", callback_data="setsize_small"),
         InlineKeyboardButton(text="📐 Medium", callback_data="setsize_medium"),
         InlineKeyboardButton(text="📐 Big", callback_data="setsize_big")],
        [InlineKeyboardButton(
            text=f"📝 Title: {'✅ ON  →  Turn OFF' if title_visible else '❌ OFF  →  Turn ON'}",
            callback_data="toggle_title"
         )],
        [InlineKeyboardButton(text="🛡️ Reset to Default Font", callback_data="reset_font")],
        _back_btn(),
    ]

    kb = InlineKeyboardMarkup(inline_keyboard=font_rows + controls)
    await _safe_edit(target, text, kb)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# 3. WATERMARK TAB
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
async def send_watermark_menu(target: Message | CallbackQuery, user_id: int,
                               show_pos_grid: bool = False):
    watermark   = await get_canvas_watermark(user_id)
    wm_size     = await get_user_watermark_size(user_id)
    wm_position = await get_user_watermark_position(user_id)
    wm_color    = await get_user_wm_color(user_id)
    wm_visible  = await get_user_wm_visible(user_id)

    wm_clr_lbl = WM_COLOR_MAP.get(wm_color, WM_COLOR_MAP["yellow"])["label"]

    text = (
        f"<b>💧 Watermark Settings</b>\n"
        f"{'━' * 28}\n\n"
        f"📢 Text:      <code>{'JOIN: ' + watermark if watermark else 'Not Set'}</code>\n"
        f"🎨 Color:     {wm_clr_lbl}\n"
        f"📏 Size:      <code>{WM_SIZE_LABELS.get(wm_size, wm_size)}</code>\n"
        f"📍 Position:  <code>{WM_POSITION_LABELS.get(wm_position, wm_position)}</code>\n\n"
        f"<i>{'⬇️ Tap a grid cell to move watermark position:' if show_pos_grid else 'Tap 📍 Position to open placement grid.'}</i>"
    )

    # Color grid — 4 per row, always visible in WM tab
    color_rows = []
    color_keys = list(WM_COLOR_MAP.keys())
    for row_keys in [color_keys[i:i+4] for i in range(0, len(color_keys), 4)]:
        color_rows.append([
            InlineKeyboardButton(
                text=WM_COLOR_MAP[c]["label"],
                callback_data=f"setwmcolor_{c}"
            ) for c in row_keys
        ])

    # Position 3×3 grid (toggle)
    pos_rows = []
    if show_pos_grid:
        pos_rows = [
            [InlineKeyboardButton(text="↖", callback_data="setwmpos_top_left"),
             InlineKeyboardButton(text="⬆", callback_data="setwmpos_top_center"),
             InlineKeyboardButton(text="↗", callback_data="setwmpos_top_right")],
            [InlineKeyboardButton(text="◀", callback_data="setwmpos_mid_left"),
             InlineKeyboardButton(text="✛", callback_data="setwmpos_mid_center"),
             InlineKeyboardButton(text="▶", callback_data="setwmpos_mid_right")],
            [InlineKeyboardButton(text="↙", callback_data="setwmpos_bot_left"),
             InlineKeyboardButton(text="⬇", callback_data="setwmpos_bot_center"),
             InlineKeyboardButton(text="↘", callback_data="setwmpos_bot_right")],
            [InlineKeyboardButton(text="✅ Close Grid", callback_data="wm_hidepos")],
        ]

    controls = [
        # Size row
        [InlineKeyboardButton(text=f"💧 {WM_SIZE_LABELS[s].strip()}", callback_data=f"setwmsize_{s}")
         for s in ["xs", "small", "medium", "large", "xl"]],
        # Position toggle
        ([InlineKeyboardButton(text="📍 Position Grid ▲ Close", callback_data="wm_hidepos")]
         if show_pos_grid else
         [InlineKeyboardButton(text="📍 Set Position", callback_data="wm_showpos")]),
        # Set / Remove watermark text
        [InlineKeyboardButton(text="✏️ Set / Change Watermark", callback_data="ask_canvas_wm"),
         *([InlineKeyboardButton(text="🗑️ Remove", callback_data="wm_remove")]
           if watermark else [])],
        [InlineKeyboardButton(
            text=f"{'✅ Watermark ON  →  Turn OFF' if wm_visible else '❌ Watermark OFF  →  Turn ON'}",
            callback_data="toggle_wm"
        )],
        _back_btn(),
    ]

    kb = InlineKeyboardMarkup(inline_keyboard=color_rows + pos_rows + controls)
    await _safe_edit(target, text, kb)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# 4. STRIP TAB
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
async def send_strip_menu(target: Message | CallbackQuery, user_id: int):
    strip_color   = await get_user_strip_color(user_id)
    strip_visible = await get_user_strip_visible(user_id)

    strip_lbl = STRIP_COLORS.get(strip_color, {}).get("label", strip_color)

    text = (
        f"<b>🎨 Strip / Gradient Settings</b>\n"
        f"{'━' * 28}\n\n"
        f"🎨 Color:   {strip_lbl}\n"
        f"👁️ Visible: {_bool_icon(strip_visible)} "
        f"{'<b>ON</b>' if strip_visible else '<b>OFF</b>'}\n\n"
        f"<i>Choose a gradient color below:</i>"
    )

    # Color grid â€” 4 per row (3 rows = 12 colors)
    color_rows = []
    keys = list(STRIP_COLORS.keys())
    for row_keys in [keys[i:i+4] for i in range(0, len(keys), 4)]:
        color_rows.append([
            InlineKeyboardButton(
                text=STRIP_COLORS[c]["label"],
                callback_data=f"setstrip_{c}"
            ) for c in row_keys
        ])

    controls = [
        [InlineKeyboardButton(
            text=f"{'✅ Strip ON  →  Turn OFF' if strip_visible else '❌ Strip OFF  →  Turn ON'}",
            callback_data="toggle_strip"
        )],
        _back_btn(),
    ]

    kb = InlineKeyboardMarkup(inline_keyboard=color_rows + controls)
    await _safe_edit(target, text, kb)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# 5. LOGO TAB
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
async def send_logo_menu(target: Message | CallbackQuery, user_id: int):
    logo_file_id = await get_user_canvas_logo(user_id)
    logo_pos     = await get_user_logo_position(user_id)
    logo_size    = await get_user_logo_size(user_id)

    logo_status = "✅ Set" if logo_file_id else "❌ Not Set"
    pos_lbl     = LOGO_POS_LABELS.get(logo_pos, logo_pos)
    size_lbl    = LOGO_SIZE_LABELS.get(logo_size, logo_size)

    text = (
        f"<b>🖼️ Logo / Icon Overlay</b>\n"
        f"{'━' * 28}\n\n"
        f"🖼️ Logo:     {logo_status}\n"
        f"📍 Position: <code>{pos_lbl}</code>\n"
        f"📏 Size:     <code>{size_lbl}</code>\n\n"
        f"<i>{'Logo is active — it appears on every thumbnail.' if logo_file_id else 'No logo set. Upload one below.'}</i>\n\n"
        f"<b>Tip:</b> PNG with transparent background looks best!"
    )

    # Position grid (4 corners only)
    pos_row1 = [
        InlineKeyboardButton(text="↖ Top Left", callback_data="setlogopos_top_left"),
        InlineKeyboardButton(text="↗ Top Right", callback_data="setlogopos_top_right"),
    ]
    pos_row2 = [
        InlineKeyboardButton(text="↙ Bot Left", callback_data="setlogopos_bot_left"),
        InlineKeyboardButton(text="↘ Bot Right", callback_data="setlogopos_bot_right"),
    ]

    # Size row
    size_row = [
        InlineKeyboardButton(text=f"{'✅ ' if logo_size == s else ''}{'S' if s == 'small' else 'M' if s == 'medium' else 'L'}",
                             callback_data=f"setlogosize_{s}")
        for s in ["small", "medium", "large"]
    ]

    upload_row = [InlineKeyboardButton(text="📤 Upload Logo", callback_data="canvas_uploadlogo")]
    if logo_file_id:
        upload_row.append(InlineKeyboardButton(text="🗑️ Remove", callback_data="canvas_rmlogo"))

    kb = InlineKeyboardMarkup(inline_keyboard=[
        pos_row1, pos_row2,
        size_row,
        upload_row,
        _back_btn(),
    ])
    await _safe_edit(target, text, kb)


# â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
# â•‘                       CALLBACKS                             â•‘
# â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

# â”€â”€ Main Dashboard â”€â”€
@router.callback_query(F.data == "manage_canvas")
async def manage_canvas_cb(callback: CallbackQuery):
    await send_canvas_menu(callback, callback.from_user.id)
    await callback.answer()

@router.callback_query(F.data == "toggle_canvas")
async def toggle_canvas_cb(callback: CallbackQuery):
    uid = callback.from_user.id
    cur = await get_canvas_status(uid)
    await set_canvas_status(uid, not cur)
    await callback.answer(f"Canvas {'OFF' if cur else 'ON'}!", show_alert=True)
    await send_canvas_menu(callback, uid)

# â”€â”€ Tab navigation â”€â”€
@router.callback_query(F.data == "canvas_tab_text")
async def tab_text_cb(callback: CallbackQuery):
    await send_text_menu(callback, callback.from_user.id)
    await callback.answer()

@router.callback_query(F.data == "canvas_tab_wm")
async def tab_wm_cb(callback: CallbackQuery):
    await send_watermark_menu(callback, callback.from_user.id)
    await callback.answer()

@router.callback_query(F.data == "canvas_tab_strip")
async def tab_strip_cb(callback: CallbackQuery):
    await send_strip_menu(callback, callback.from_user.id)
    await callback.answer()

@router.callback_query(F.data == "canvas_tab_logo")
async def tab_logo_cb(callback: CallbackQuery):
    await send_logo_menu(callback, callback.from_user.id)
    await callback.answer()

# â”€â”€ Text Settings â”€â”€
@router.callback_query(F.data.startswith("txt_page_"))
async def txt_page_cb(callback: CallbackQuery):
    page = int(callback.data.split("_")[2])
    await send_text_menu(callback, callback.from_user.id, page=page)
    await callback.answer()

@router.callback_query(F.data.startswith("setfont_"))
async def set_font_cb(callback: CallbackQuery):
    uid   = callback.from_user.id
    parts = callback.data.split("_")
    font_file = parts[1]
    page      = int(parts[2]) if len(parts) > 2 else 0
    await set_user_font(uid, f"fonts/{font_file}")
    await callback.answer(f"🔤 {font_file.replace('.ttf','')} set!", show_alert=True)
    await send_text_menu(callback, uid, page=page)

@router.callback_query(F.data.startswith("setsize_"))
async def set_size_cb(callback: CallbackQuery):
    uid  = callback.from_user.id
    size = callback.data.split("_")[1]
    await set_user_text_size(uid, size)
    await callback.answer(f"📐 Size: {size.upper()}!", show_alert=True)
    await send_text_menu(callback, uid)

@router.callback_query(F.data == "toggle_title")
async def toggle_title_cb(callback: CallbackQuery):
    uid = callback.from_user.id
    cur = await get_user_title_visible(uid)
    await set_user_title_visible(uid, not cur)
    await callback.answer(f"📝 Title {'OFF' if cur else 'ON'}!", show_alert=True)
    await send_text_menu(callback, uid)

@router.callback_query(F.data == "reset_font")
async def reset_font_cb(callback: CallbackQuery):
    uid = callback.from_user.id
    await set_user_font(uid, "")
    await callback.answer("✅ Font reset!", show_alert=True)
    await send_text_menu(callback, uid)

# â”€â”€ Watermark â”€â”€
@router.callback_query(F.data == "wm_showpos")
async def wm_showpos_cb(callback: CallbackQuery):
    await send_watermark_menu(callback, callback.from_user.id, show_pos_grid=True)
    await callback.answer()

@router.callback_query(F.data == "wm_hidepos")
async def wm_hidepos_cb(callback: CallbackQuery):
    await send_watermark_menu(callback, callback.from_user.id, show_pos_grid=False)
    await callback.answer()

@router.callback_query(F.data.startswith("setwmpos_"))
async def set_wm_pos_cb(callback: CallbackQuery):
    uid = callback.from_user.id
    pos = callback.data.replace("setwmpos_", "")
    await set_user_watermark_position(uid, pos)
    await callback.answer(f"📍 {WM_POSITION_LABELS.get(pos, pos)}", show_alert=True)
    await send_watermark_menu(callback, uid, show_pos_grid=True)

@router.callback_query(F.data.startswith("setwmsize_"))
async def set_wm_size_cb(callback: CallbackQuery):
    uid  = callback.from_user.id
    size = callback.data.replace("setwmsize_", "")
    await set_user_watermark_size(uid, size)
    await callback.answer(f"📏 WM Size: {WM_SIZE_LABELS.get(size, size)}", show_alert=True)
    await send_watermark_menu(callback, uid)

@router.callback_query(F.data.startswith("setwmcolor_"))
async def set_wm_color_cb(callback: CallbackQuery):
    uid   = callback.from_user.id
    color = callback.data.replace("setwmcolor_", "")
    await set_user_wm_color(uid, color)
    lbl = WM_COLOR_MAP.get(color, WM_COLOR_MAP["yellow"])["label"]
    await callback.answer(f"🎨 WM Color: {lbl}!", show_alert=True)
    await send_watermark_menu(callback, uid)

@router.callback_query(F.data == "ask_canvas_wm")
async def ask_wm_cb(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CanvasStates.waiting_for_watermark)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data="canvas_tab_wm")]
    ])
    await callback.message.edit_text(
        "✍️ <b>Apna channel username ya watermark text bhejiye:</b>\n\n"
        "Example: <code>@MyMovieChannel</code>",
        parse_mode="HTML", reply_markup=kb
    )
    await callback.answer()

@router.message(CanvasStates.waiting_for_watermark, F.text)
async def process_wm(message: Message, state: FSMContext):
    await set_canvas_watermark(message.from_user.id, message.text.strip())
    await state.clear()
    await message.answer(
        "✅ <b>Watermark save ho gaya!</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💧 Watermark Settings", callback_data="canvas_tab_wm")]
        ])
    )

# â”€â”€ Watermark Toggle + Remove â”€â”€ âœ… NEW
@router.callback_query(F.data == "toggle_wm")
async def toggle_wm_cb(callback: CallbackQuery):
    uid = callback.from_user.id
    cur = await get_user_wm_visible(uid)
    await set_user_wm_visible(uid, not cur)
    await callback.answer(
        f"💧 Watermark {'OFF kar diya!' if cur else 'ON kar diya!'}",
        show_alert=True
    )
    await send_watermark_menu(callback, uid)

@router.callback_query(F.data == "wm_remove")
async def wm_remove_cb(callback: CallbackQuery):
    uid = callback.from_user.id
    await set_canvas_watermark(uid, "")           # DB se clear karo
    await set_user_wm_visible(uid, True)          # Toggle bhi reset karo
    await callback.answer("🗑️ Watermark hata diya gaya!", show_alert=True)
    await send_watermark_menu(callback, uid)

# â”€â”€ Strip â”€â”€
@router.callback_query(F.data.startswith("setstrip_"))
async def set_strip_cb(callback: CallbackQuery):
    uid   = callback.from_user.id
    color = callback.data.replace("setstrip_", "")
    await set_user_strip_color(uid, color)
    lbl = STRIP_COLORS.get(color, {}).get("label", color)
    await callback.answer(f"🎨 Strip: {lbl}!", show_alert=True)
    await send_strip_menu(callback, uid)

@router.callback_query(F.data == "toggle_strip")
async def toggle_strip_cb(callback: CallbackQuery):
    uid = callback.from_user.id
    cur = await get_user_strip_visible(uid)
    await set_user_strip_visible(uid, not cur)
    await callback.answer(f"🎨 Strip {'OFF' if cur else 'ON'}!", show_alert=True)
    await send_strip_menu(callback, uid)

# â”€â”€ Logo â”€â”€
@router.callback_query(F.data.startswith("setlogopos_"))
async def set_logo_pos_cb(callback: CallbackQuery):
    uid = callback.from_user.id
    pos = callback.data.replace("setlogopos_", "")
    await set_user_logo_position(uid, pos)
    await callback.answer(f"🖼️ {LOGO_POS_LABELS.get(pos, pos)}", show_alert=True)
    await send_logo_menu(callback, uid)

@router.callback_query(F.data.startswith("setlogosize_"))
async def set_logo_size_cb(callback: CallbackQuery):
    uid  = callback.from_user.id
    size = callback.data.replace("setlogosize_", "")
    await set_user_logo_size(uid, size)
    await callback.answer(f"📏 Logo: {LOGO_SIZE_LABELS.get(size, size)}", show_alert=True)
    await send_logo_menu(callback, uid)

@router.callback_query(F.data == "canvas_rmlogo")
async def remove_logo_cb(callback: CallbackQuery):
    await remove_user_canvas_logo(callback.from_user.id)
    await callback.answer("🗑️ Logo removed!", show_alert=True)
    await send_logo_menu(callback, callback.from_user.id)

@router.callback_query(F.data == "canvas_uploadlogo")
async def upload_logo_cb(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CanvasStates.waiting_for_logo)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data="canvas_tab_logo")]
    ])
    await callback.message.edit_text(
        "🖼️ <b>Apna Logo / Icon bhejiye:</b>\n\n"
        "• <b>PNG</b> with transparent bg → best result\n"
        "• Square / round shape → clean look\n"
        "• <b>Photo ke roop mein bhejiye</b> (document nahi)\n\n"
        "<i>Ek baar set hone ke baad har thumbnail pe auto lagega.</i>",
        parse_mode="HTML", reply_markup=kb
    )
    await callback.answer()

@router.message(CanvasStates.waiting_for_logo, F.photo)
async def process_logo(message: Message, state: FSMContext):
    await set_user_canvas_logo(message.from_user.id, message.photo[-1].file_id)
    await state.clear()
    await message.answer(
        "✅ <b>Logo save ho gaya!</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🖼️ Logo Settings", callback_data="canvas_tab_logo")]
        ])
    )

@router.message(CanvasStates.waiting_for_logo)
async def process_logo_wrong(message: Message):
    await message.answer(
        "⚠️ <b>Sirf Photo bhejiye!</b>\n"
        "Document/file nahi chalega — image as <b>photo</b> send karein.",
        parse_mode="HTML"
    )

# â”€â”€ Command entry â”€â”€
@router.message(Command("canvas"))
async def canvas_cmd(message: Message):
    await send_canvas_menu(message, message.from_user.id)