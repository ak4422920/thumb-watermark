from aiogram import Router, types, Bot, F
from aiogram.filters import Command, CommandObject
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, URLInputFile, CallbackQuery
from config import CHANNEL_URL, DEV_URL, get_random_pic, LOG_CHANNEL, REFERRAL_COUNT
from database import add_user, is_banned, get_user, add_referral, update_premium

router = Router()

def small_caps(text: str) -> str:
    """Convert text to small caps unicode."""
    normal = "abcdefghijklmnopqrstuvwxyz"
    small = "ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ"
    result = ""
    for char in text:
        if char.lower() in normal:
            idx = normal.index(char.lower())
            result += small[idx]
        else:
            result += char
    return result

@router.message(Command("start"))
async def start_cmd(message: types.Message, bot: Bot, command: CommandObject):
    """Handle /start command with Referral tracking."""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    # 1. Banned Check
    if await is_banned(user_id):
        await message.answer(small_caps("You are banned from using this bot."))
        return

    # 2. Check if it's a new user for Referral Logic
    existing_user = await get_user(user_id)
    is_new_user = existing_user is None
    
    # 3. Handle Referral Link (e.g., /start refer_12345)
    args = command.args
    if is_new_user and args and (args.startswith("refer_") or args.startswith("ref_")):
        try:
            referrer_id = int(args.split("_")[1])
            if referrer_id != user_id: # Khud ko refer nahi kar sakta
                success = await add_referral(referrer_id, user_id)
                if success:
                    # Referrer ko notify karein
                    referrer_data = await get_user(referrer_id)
                    current_refs = referrer_data.get("referral_count", 0)
                    
                    try:
                        ref_text = f"👤 <b>{small_caps('New Referral!')}</b>\n\n{first_name} has joined using your link.\n"
                        ref_text += f"📊 Total Referrals: <b>{current_refs}/{REFERRAL_COUNT}</b>"
                        
                        # Agar target reach ho gaya
                        if current_refs >= REFERRAL_COUNT:
                            await update_premium(referrer_id, True)
                            ref_text += f"\n\n🎉 <b>{small_caps('Congratulations!')}</b>\nYou are now a <b>PREMIUM</b> user with unlimited access!"
                        
                        await bot.send_message(referrer_id, ref_text, parse_mode="HTML")
                    except Exception:
                        pass
        except (ValueError, IndexError):
            pass

    # 4. Add/Update User in DB
    await add_user(user_id, username, first_name)

    # 5. Log New User
    if is_new_user and LOG_CHANNEL:
        try:
            await bot.send_message(
                chat_id=LOG_CHANNEL,
                text=f"👤 <b>ɴᴇᴡ ᴜsᴇʀ</b>\n\n"
                     f"🆔 <code>{user_id}</code>\n"
                     f"👤 {first_name}\n"
                     f"🔗 @{username or 'N/A'}",
                parse_mode="HTML"
            )
        except Exception:
            pass

    # 6. Welcome Text
    welcome_text = (
        f"<b>{small_caps('Welcome to Thumbnail Bot!')}</b>\n\n"
        f"<blockquote>{small_caps('Send me a video and I will add your custom thumbnail to it.')}</blockquote>\n\n"
        f"<b>{small_caps('How to use:')}</b>\n"
        f"<blockquote>"
        f"1️ {small_caps('Set your thumbnail in Settings')}\n"
        f"2️ {small_caps('Send any video')}\n"
        f"3️ {small_caps('Get video with your thumbnail!')}"
        f"</blockquote>"
    )

    # 7. Buttons
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📢 Join Channel", url=CHANNEL_URL),
            InlineKeyboardButton(text="👨‍💻 Developer", url=DEV_URL)
        ],
        [   InlineKeyboardButton(text="⚙️ Settings", callback_data="settings"),
            InlineKeyboardButton(text="📊 My Progress", callback_data="my_stats")
        ]
    ])

    # 8. Send Image or Fallback
    pic_url = get_random_pic()
    if pic_url:
        try:
            await bot.send_photo(
                chat_id=message.chat.id,
                photo=URLInputFile(pic_url),
                caption=welcome_text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
            return
        except Exception:
            pass

    await message.answer(welcome_text, parse_mode="HTML", reply_markup=keyboard)


@router.callback_query(F.data == "my_stats")
async def show_stats(callback: CallbackQuery):
    """Show user referral stats via button safely without Caption/Text crashes."""
    user_data = await get_user(callback.from_user.id)
    if not user_data:
        try:
            await callback.answer("⚠️ Data not found!", show_alert=True)
        except Exception:
            pass
        return

    is_premium = user_data.get("is_premium", False)
    refs = user_data.get("referral_count", 0)
    limit = "Unlimited" if is_premium else "15 per day"
    
    status_text = (
        f"👤 <b>{small_caps('Your Statistics')}</b>\n\n"
        f"👑 Premium: <b>{'✅ Yes' if is_premium else '❌ No'}</b>\n"
        f"📊 Referrals: <b>{refs}/{REFERRAL_COUNT}</b>\n"
        f"🚀 Daily Limit: <b>{limit}</b>\n\n"
        f"🔗 Referral Link: <code>https://t.me/{(await callback.bot.get_me()).username}?start=refer_{callback.from_user.id}</code>"
    )
    
    # 🔥 BULLETPROOF FIX: Auto-Detect and Route to edit_caption or edit_text
    try:
        # Agar start message photo ke saath bheja gaya tha
        await callback.message.edit_caption(
            caption=status_text, 
            parse_mode="HTML", 
            reply_markup=callback.message.reply_markup
        )
    except Exception:
        try:
            # Fallback: Agar normal plain text message hai (no caption exist)
            await callback.message.edit_text(
                text=status_text, 
                parse_mode="HTML", 
                reply_markup=callback.message.reply_markup
            )
        except Exception:
            pass

    # Safe callback query answer handler to protect from timeout alerts
    try:
        await callback.answer()
    except Exception:
        pass
