import re
from aiogram import Router, types, F, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ChatType

# Config aur Database se functions import
from config import (
    LOG_CHANNEL, AUTH_CHANNEL, CLEANER_PATTERNS, 
    BRAND_LINK, CHANNEL_URL, DAILY_LIMIT, 
    REFERRAL_COUNT, FORCE_LIMIT, DEV_URL
)
from database import (
    get_thumbnail, increment_usage, is_banned, 
    add_user, get_caption_style, check_and_reset_limit, 
    get_user, get_custom_patterns, get_replacements,
    check_premium_status
)

# SMART CANVAS CORE CONNECTORS IMPORT
from plugins.canvas import (
    get_canvas_status, get_canvas_watermark, 
    get_user_font, get_user_text_size, add_to_canvas_queue
)

router = Router()

OWNER_ID = 6522435665

def small_caps(text: str) -> str:
    normal = "abcdefghijklmnopqrstuvwxyz"
    small  = "ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ"
    result = ""
    for char in text:
        if char.lower() in normal:
            result += small[normal.index(char.lower())]
        else:
            result += char
    return result

async def is_subscribed(bot: Bot, user_id: int, channel_id: str | int):
    try:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return False

def clean_and_replace_engine(text: str, custom_patterns: list, replacements: list) -> str:
    if not text:
        return ""
    for p in CLEANER_PATTERNS:
        text = re.sub(p, "", text, flags=re.IGNORECASE)
    if custom_patterns:
        for cp in custom_patterns:
            if cp.strip():
                text = re.sub(re.escape(cp.strip()), "", text, flags=re.IGNORECASE)
    if replacements:
        for pair in replacements:
            if isinstance(pair, dict):
                find_word = str(pair.get("find", "")).strip()
                replace_word = str(pair.get("replace", ""))
            elif isinstance(pair, (list, tuple)) and len(pair) >= 2:
                find_word = str(pair[0]).strip()
                replace_word = str(pair[1])
            else:
                continue
            if find_word:
                text = re.sub(re.escape(find_word), replace_word, text, flags=re.IGNORECASE)
    text = re.sub(r'\n\s*\n+', '\n\n', text)
    return text.strip()

def normalize_caption_style(style: str) -> str:
    style_key = (style or "normal").strip().lower().replace(" ", "_")
    style_map = {
        "normal": "normal",
        "bold": "bold",
        "italic": "italic",
        "mono": "mono",
        "monospace": "mono",
        "small_caps": "small_caps",
    }
    return style_map.get(style_key, "normal")

def format_caption(text: str, style: str) -> str:
    style = normalize_caption_style(style)
    if not text or style == "normal":
        return text
    lines = text.split('\n')
    formatted_lines = []
    for line in lines:
        if not line.strip():
            formatted_lines.append("")
            continue
        if style == "bold":
            formatted_lines.append(f"<b>{line}</b>")
        elif style == "italic":
            formatted_lines.append(f"<i>{line}</i>")
        elif style == "mono":
            formatted_lines.append(f"<code>{line}</code>")
        elif style == "small_caps":
            formatted_lines.append(small_caps(line))
        else:
            formatted_lines.append(line)
    return '\n'.join(formatted_lines)


@router.message(F.video)
async def handle_video(message: types.Message, bot: Bot):
    user_id = message.from_user.id

    if await is_banned(user_id):
        return

    await add_user(user_id, message.from_user.username, message.from_user.full_name)

    bot_info     = await bot.get_me()
    settings_url = f"https://t.me/{bot_info.username}?start=settings"
    keyboard     = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ My Settings", url=settings_url)]
    ])

    # Force Subscribe check
    if AUTH_CHANNEL and message.chat.type == ChatType.PRIVATE:
        if not await is_subscribed(bot, user_id, AUTH_CHANNEL):
            invite_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📢 Join Channel", url=CHANNEL_URL)],
                [InlineKeyboardButton(text="🔄 Check Again", url=f"https://t.me/{bot_info.username}?start=check")]
            ])
            return await message.answer(
                f"<b>⚠️ {small_caps('Access Denied!')}</b>\n\n"
                f"<blockquote>{small_caps('Bot use karne ke liye aapko hamare channel ko join karna hoga.')}</blockquote>",
                parse_mode="HTML", reply_markup=invite_keyboard
            )

    # Premium / Limit check
    is_premium = await check_premium_status(user_id)
    if not is_premium and user_id != OWNER_ID:
        await check_and_reset_limit(user_id)
        user_data     = await get_user(user_id)
        current_count = user_data.get("daily_count", 0) if user_data else 0
        if current_count >= DAILY_LIMIT:
            referrals  = user_data.get("referral_count", 0) if user_data else 0
            needed_ref = REFERRAL_COUNT
            if referrals < needed_ref and FORCE_LIMIT:
                ref_link   = f"https://t.me/{bot_info.username}?start=refer_{user_id}"
                share_text = f"https://t.me/share/url?url={ref_link}&text=Get%20Unlimited%20Thumbnail%20Changer%20Bot%20Now!%20🚀"
                ref_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔗 Share Referral Link", url=share_text)],
                    [InlineKeyboardButton(text="👑 Buy Premium (Contact Dev)", url=DEV_URL)]
                ])
                return await message.answer(
                    f"<b>🚨 {small_caps('Daily Limit Reached!')}</b>\n\n"
                    f"Free users limit: <b>{DAILY_LIMIT} videos/day</b>.\n"
                    f"Current Referrals: <code>{referrals}/{needed_ref}</code>\n\n"
                    f"<blockquote>Invite {needed_ref} friends using link below to unlock limit or purchase premium license key!</blockquote>",
                    parse_mode="HTML", reply_markup=ref_keyboard
                )

    # Caption processing
    raw_caption      = message.caption if message.caption else ""
    user_patterns    = await get_custom_patterns(user_id)
    user_replacements = await get_replacements(user_id)
    cleaned_text     = clean_and_replace_engine(raw_caption, custom_patterns=user_patterns, replacements=user_replacements)
    user_style       = await get_caption_style(user_id)
    formatted_text   = format_caption(cleaned_text, user_style)
    final_caption    = f"{formatted_text}\n\n{BRAND_LINK}" if formatted_text else BRAND_LINK

    # Thumbnail — user ka saved thumb priority, fallback video thumb
    thumb_file_id = await get_thumbnail(user_id)

    # Smart Canvas processing
    canvas_active      = await get_canvas_status(user_id)
    canvas_source_thumb = thumb_file_id or (
        message.video.thumbnail.file_id if message.video.thumbnail else None
    )
    if canvas_active and canvas_source_thumb:
        watermark     = await get_canvas_watermark(user_id)
        selected_font = await get_user_font(user_id)
        # Canvas worker now renders, enhances, and returns a Telegram-ready HD cover file_id.
        edited_thumb  = await add_to_canvas_queue(
            bot=bot, user_id=user_id,
            thumb_file_id=canvas_source_thumb,
            movie_title=cleaned_text,
            watermark_text=watermark,
            selected_font=selected_font
        )
        if edited_thumb:
            thumb_file_id = edited_thumb

    if thumb_file_id:
        if not is_premium and user_id != OWNER_ID:
            await increment_usage(user_id)

        if message.chat.type == ChatType.CHANNEL:
            try: await message.delete()
            except Exception: pass

        await bot.send_video(
            chat_id=message.chat.id,
            video=message.video.file_id,
            caption=final_caption,
            cover=thumb_file_id,
            parse_mode="HTML",
            reply_markup=keyboard
        )

        # Dump channel
        from database import get_custom_dump
        user_dump_id = await get_custom_dump(user_id)
        if user_dump_id:
            try:
                await bot.send_video(
                    chat_id=user_dump_id,
                    video=message.video.file_id,
                    caption=final_caption,
                    cover=thumb_file_id,
                    parse_mode="HTML"
                )
            except Exception as e:
                if LOG_CHANNEL:
                    try: await bot.send_message(LOG_CHANNEL, f"⚠️ Dump Failed for <code>{user_id}</code>: {e}")
                    except Exception: pass

        # Log
        if LOG_CHANNEL:
            try:
                user_data     = await get_user(user_id)
                current_count = user_data.get("daily_count", 0) if user_data else 0
                daily_status  = "N/A" if message.chat.type == ChatType.CHANNEL else f"{current_count}/{DAILY_LIMIT if not is_premium else '∞'}"
                await bot.send_message(
                    LOG_CHANNEL,
                    f"📹 <b>ᴠɪᴅᴇᴏ ᴘʀᴏᴄᴇssᴇᴅ</b>\n🆔 <code>{user_id}</code>\n📊 Daily: {daily_status}",
                    parse_mode="HTML"
                )
            except Exception: pass
    else:
        if message.chat.type == ChatType.PRIVATE:
            await message.answer(
                f"<b>⚠️ {small_caps('No thumbnail set!')}</b>\n\n"
                f"<blockquote>{small_caps('Settings mein jaakar pehle thumbnail set karein.')}</blockquote>",
                parse_mode="HTML", reply_markup=keyboard
            )
