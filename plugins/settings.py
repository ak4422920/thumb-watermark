from aiogram.filters import Command
from aiogram import Router, types, F, Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest
from database import set_custom_dump, get_custom_dump, remove_custom_dump

from config import CHANNEL_URL, DEV_URL, AUTH_CHANNEL 

from database import (
    get_thumbnail, set_thumbnail, remove_thumbnail, 
    is_banned, set_caption_style, get_caption_style
)
from database import add_custom_pattern, remove_custom_pattern, get_custom_patterns
from database import add_replacement_pair, remove_replacement_pair, get_replacements, db

from plugins.video import is_subscribed

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

# 1. State Definition
class CleanerStates(StatesGroup):
    waiting_for_word = State()

# 2. Main Cleaner Menu (Reusable for both Callback and Text Command)
async def send_cleaner_menu(target: Message | CallbackQuery, user_id: int):
    patterns = await get_custom_patterns(user_id)
    
    text = f"<b>✂️ {small_caps('Custom Caption Cleaner')}</b>\n\n"
    text += f"Aap jo bhi words ya links yahan add karenge, wo aapki video ke caption se automatic delete ho jayenge.\n\n"
    
    inline_keyboard = []
    
    if patterns:
        text += "<b>📋 Aapke Active Filters:</b>\n"
        for i, p in enumerate(patterns, 1):
            text += f"{i}. <code>{p}</code>\n"
            # Har active word ke liye ek row jismein uska naam aur samne ❌ button ho
            inline_keyboard.append([
                InlineKeyboardButton(text=f"🗑️ Delete: {p[:15]}...", callback_data=f"del_wrd_{p}")
            ])
    else:
        text += "<i>ℹ️ Abhi aapne koi custom word add nahi kiya hai.</i>"
        
    # Main functional buttons append karein
    inline_keyboard.extend([
        [InlineKeyboardButton(text="➕ Add Word/Link", callback_data="add_clean_word")],
        [InlineKeyboardButton(text="🗑️ Clear All Filters", callback_data="clear_clean_filters")],
        [InlineKeyboardButton(text="🔙 Back to Settings", callback_data="settings")]
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
    
    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    else:
        await target.answer(text, parse_mode="HTML", reply_markup=keyboard)

# 3. Handle /clean or /cleaner text command
@router.message(Command("clean", "cleaner"))
async def clean_command_handler(message: Message):
    """Direct command to open cleaner menu."""
    await send_cleaner_menu(message, message.from_user.id)

# 4. Handle Callback query for main menu
@router.callback_query(F.data == "custom_cleaner")
async def manage_cleaner_callback(callback: CallbackQuery):
    await send_cleaner_menu(callback, callback.from_user.id)
    await callback.answer()

# 5. Add Button Trigger
@router.callback_query(F.data == "add_clean_word")
async def ask_for_word(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CleanerStates.waiting_for_word)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data="custom_cleaner")]
    ])
    
    await callback.message.edit_text(
        f"✍️ <b>{small_caps('Enter Word or Link:')}</b>\n\n"
        f"Wo text bhein jo aap caption se hatana chahte hain (e.g., <code>@akmovieverse</code> ya <code>https://t.me/akmovieverse</code>):",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()

# 6. Message Catcher for Word Input
@router.message(CleanerStates.waiting_for_word, F.text)
async def process_custom_word(message: Message, state: FSMContext):
    user_id = message.from_user.id
    word_to_clean = message.text.strip()
    
    if len(word_to_clean) < 2:
        await message.answer("⚠️ Word bohot chhota hai! Kam se kam 2 characters ka hona chahiye.")
        return
        
    await add_custom_pattern(user_id, word_to_clean)
    await state.clear()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Manage Cleaner", callback_data="custom_cleaner")]
    ])
    
    await message.answer(
        f"✅ <b>{small_caps('Success!')}</b>\n\n"
        f"<code>{word_to_clean}</code> ko aapke custom cleaner mein add kar diya gaya hai.",
        parse_mode="HTML",
        reply_markup=keyboard
    )

# 7. NEW FEATURE: Single Word Delete Handler
@router.callback_query(F.data.startswith("del_wrd_"))
async def delete_single_word(callback: CallbackQuery):
    user_id = callback.from_user.id
    # Callback data se original word extract karna
    word_to_delete = callback.data.replace("del_wrd_", "")
    
    # DB se specific word remove karein
    await remove_custom_pattern(user_id, word_to_delete)
    await callback.answer(f"🗑️ Removed: {word_to_delete}", show_alert=False)
    
    # Menu ko update/refresh karein
    await send_cleaner_menu(callback, user_id)

# 8. Clear All Filters Handler
@router.callback_query(F.data == "clear_clean_filters")
async def clear_filters(callback: CallbackQuery):
    user_id = callback.from_user.id
    await db.users.update_one({"user_id": user_id}, {"$set": {"custom_patterns": []}})
    
    await callback.answer("🗑️ Saare custom filters delete ho gaye!", show_alert=True)
    await send_cleaner_menu(callback, user_id)

class ThumbnailState(StatesGroup):
    waiting_for_thumbnail = State()

def get_settings_keyboard():
    """Return the settings inline keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🖼️ Update Thumbnail", callback_data="update_thumb")],
        [InlineKeyboardButton(text="👁️ View Thumbnail", callback_data="view_thumb")],
        [InlineKeyboardButton(text="🗑️ Remove Thumbnail", callback_data="remove_thumb")],
        [InlineKeyboardButton(text="📁 Custom Dump", callback_data="manage_dump")],
        [InlineKeyboardButton(text="🎨 Canvas Editor", callback_data="manage_canvas")],
        [InlineKeyboardButton(text="📝 Caption Style", callback_data="set_font_menu")],
        [InlineKeyboardButton(text="✂️ Custom Cleaner", callback_data="custom_cleaner")],
        [InlineKeyboardButton(text="🔄 Auto Replacer", callback_data="text_replacer")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="back_to_start")],
        [InlineKeyboardButton(text="❌ Close", callback_data="close_settings")]
    ])


@router.callback_query(F.data == "settings")
async def show_settings(callback: CallbackQuery, bot: Bot):
    """Show settings menu with Force Subscribe check."""
    user_id = callback.from_user.id
    
    # 1. Banned Check
    if await is_banned(user_id):
        await callback.answer(small_caps("You are banned!"), show_alert=True)
        return

    # 2. FORCE SUBSCRIBE CHECK (Naya Logic)
    from config import AUTH_CHANNEL, CHANNEL_URL
    from plugins.video import is_subscribed # video.py se function import karna
    
    if AUTH_CHANNEL:
        subscribed = await is_subscribed(bot, user_id, AUTH_CHANNEL)
        if not subscribed:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📢 Join Channel", url=CHANNEL_URL)],
                [InlineKeyboardButton(text="🔄 Check Again", callback_data="settings")]
            ])
            # Edit text karke error message dikhayenge
            try:
                await callback.message.edit_text(
                    f"<b>❌ {small_caps('Access Denied!')}</b>\n\n"
                    f"<blockquote>{small_caps('You must join our channel to access settings and use the bot.')}</blockquote>",
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            except Exception:
                await callback.message.answer(
                    f"<b>❌ {small_caps('Access Denied!')}</b>",
                    reply_markup=keyboard
                )
            await callback.answer("Please join the channel first!", show_alert=True)
            return

    # 3. Settings Menu (Agar subscribed hai toh hi yahan tak aayega)
    thumb = await get_thumbnail(user_id)
    status = f"✅ {small_caps('Thumbnail is set')}" if thumb else f"❌ {small_caps('No thumbnail set')}"
    
    text = (
        f"<b>⚙️ {small_caps('Thumbnail Settings')}</b>\n\n"
        f"<blockquote>{status}</blockquote>\n\n"
        f"{small_caps('Choose an option below:')}"
    )
    
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    
    await bot.send_message(
        chat_id=callback.message.chat.id,
        text=text,
        parse_mode="HTML",
        reply_markup=get_settings_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_start")
async def back_to_start(callback: CallbackQuery, bot: Bot):
    """Go back to start message - fast text only."""
    
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
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📢 Join Channel", url=CHANNEL_URL),
            InlineKeyboardButton(text="👨‍💻 Developer", url=DEV_URL)
        ],
        [InlineKeyboardButton(text="⚙️ Settings", callback_data="settings"),
         InlineKeyboardButton(text="📊 My Progress", callback_data="my_stats")]
    ])
    
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    
    await bot.send_message(
        chat_id=callback.message.chat.id,
        text=welcome_text,
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()

@router.callback_query(F.data == "update_thumb")
async def update_thumbnail_prompt(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Prompt user to send a new thumbnail."""
    user_id = callback.from_user.id
    
    if await is_banned(user_id):
        await callback.answer(small_caps("You are banned!"), show_alert=True)
        return
    
    await state.set_state(ThumbnailState.waiting_for_thumbnail)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_update")]
    ])
    
    text = (
        f"<b>📸 {small_caps('Send me a photo')}</b>\n\n"
        f"<blockquote>{small_caps('This image will be used as the cover for your videos.')}</blockquote>"
    )
    
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    
    await bot.send_message(
        chat_id=callback.message.chat.id,
        text=text,
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()

@router.callback_query(F.data == "cancel_update")
async def cancel_update(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Cancel the thumbnail update."""
    await state.clear()
    await show_settings(callback, bot)

@router.message(ThumbnailState.waiting_for_thumbnail, F.photo)
async def receive_thumbnail(message: types.Message, state: FSMContext):
    """Save the received photo as thumbnail."""
    user_id = message.from_user.id
    file_id = message.photo[-1].file_id
    
    await set_thumbnail(user_id, file_id)
    await state.clear()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Back to Settings", callback_data="settings")]
    ])
    
    await message.answer(
        f"<b>✅ {small_caps('Thumbnail saved!')}</b>\n\n"
        f"<blockquote>{small_caps('Your videos will now use this cover image.')}</blockquote>",
        parse_mode="HTML",
        reply_markup=keyboard
    )

@router.callback_query(F.data == "view_thumb")
async def view_thumbnail(callback: CallbackQuery, bot: Bot):
    """Show the user's current thumbnail."""
    user_id = callback.from_user.id
    thumb = await get_thumbnail(user_id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Back to Settings", callback_data="settings")]
    ])
    
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    
    if thumb:
        await bot.send_photo(
            chat_id=callback.message.chat.id,
            photo=thumb,
            caption=f"<b>🖼️ {small_caps('Your Current Thumbnail')}</b>",
            parse_mode="HTML",
            reply_markup=keyboard
        )
    else:
        await bot.send_message(
            chat_id=callback.message.chat.id,
            text=f"<b>❌ {small_caps('No thumbnail set')}</b>\n\n"
                 f"<blockquote>{small_caps('Use Update Thumbnail to set one.')}</blockquote>",
            parse_mode="HTML",
            reply_markup=keyboard
        )
    await callback.answer()

@router.callback_query(F.data == "remove_thumb")
async def remove_thumbnail_handler(callback: CallbackQuery, bot: Bot):
    """Remove the user's thumbnail."""
    user_id = callback.from_user.id
    removed = await remove_thumbnail(user_id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Back to Settings", callback_data="settings")]
    ])
    
    if removed:
        text = (
            f"<b>🗑️ {small_caps('Thumbnail Removed')}</b>\n\n"
            f"<blockquote>{small_caps('Your videos will now be sent without a custom cover.')}</blockquote>"
        )
    else:
        text = (
            f"<b>❌ {small_caps('No thumbnail to remove')}</b>\n\n"
            f"<blockquote>{small_caps('You have not set a thumbnail yet.')}</blockquote>"
        )
    
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    
    await bot.send_message(
        chat_id=callback.message.chat.id,
        text=text,
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()


@router.message(Command("font"))
@router.callback_query(F.data == "set_font_menu")
async def font_selection_menu(event: types.Message | CallbackQuery):
    """Show font selection menu."""
    user_id = event.from_user.id
    current_style = await get_caption_style(user_id)
    
    # Buttons for different styles
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Normal", callback_data="style_Normal"),
            InlineKeyboardButton(text="Small Caps", callback_data="style_Small Caps")
        ],
        [
            InlineKeyboardButton(text="Bold", callback_data="style_Bold"),
            InlineKeyboardButton(text="Italic", callback_data="style_Italic")
        ],
        [InlineKeyboardButton(text="Monospace", callback_data="style_Monospace")],
        [InlineKeyboardButton(text="🔙 Back to Settings", callback_data="settings")]
    ])
    
    text = (
        f"<b>📝 {small_caps('Select Caption Style')}</b>\n\n"
        f"<blockquote>Current Style: <b>{current_style}</b></blockquote>\n\n"
        f"Choose how you want your video captions to look:"
    )

    if isinstance(event, types.Message):
        await event.answer(text, parse_mode="HTML", reply_markup=keyboard)
    else:
        try:
            await event.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        except TelegramBadRequest:
            pass
        await event.answer()

@router.callback_query(F.data.startswith("style_"))
async def update_style_handler(callback: CallbackQuery):
    """Save the selected font style."""
    new_style = callback.data.replace("style_", "")
    await set_caption_style(callback.from_user.id, new_style)
    
    await callback.answer(f"✅ Style set to {new_style}!", show_alert=True)
    # Refresh the menu to show updated style
    await font_selection_menu(callback) 

# ==================== CUSTOM REPLACER SYSTEM ====================

# 1. State Definition
class ReplacerStates(StatesGroup):
    waiting_for_find = State()
    waiting_for_replace = State()

# 2. Main Replacer Menu Utility Function (Dynamic Index-based Keyboard)
async def send_replacer_menu(target: Message | CallbackQuery, user_id: int):
    pairs = await get_replacements(user_id)
    
    text = f"<b>🔄 {small_caps('Auto Text Replacer')}</b>\n\n"
    text += f"Aap yahan koi bhi custom word/link dhoondh kar use apne naye text se replace kar sakte hain.\n\n"
    
    inline_keyboard = []
    
    if pairs:
        text += "<b>📋 Aapke Active Replacements:</b>\n"
        for i, pair in enumerate(pairs, 1):
            f_text = pair['find']
            r_text = pair['replace']
            text += f"{i}. <code>{f_text}</code> ➔ <code>{r_text}</code>\n"
            
            # 64-byte crash se bachne ke liye hum pure word ki jagah list ka index (i-1) bhejenge
            inline_keyboard.append([
                InlineKeyboardButton(text=f"🗑️ Delete No. {i}", callback_data=f"del_rep_{i-1}")
            ])
    else:
        text += "<i>ℹ️ Abhi aapne koi replacement filter set nahi kiya hai.</i>"
        
    inline_keyboard.extend([
        [InlineKeyboardButton(text="➕ Add New Pair", callback_data="add_rep_pair")],
        [InlineKeyboardButton(text="🔙 Back to Settings", callback_data="settings")]
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
    
    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    else:
        await target.answer(text, parse_mode="HTML", reply_markup=keyboard)

# 3. Callback trigger for menu
@router.callback_query(F.data == "text_replacer")
async def manage_replacer_callback(callback: CallbackQuery):
    await send_replacer_menu(callback, callback.from_user.id)
    await callback.answer()

@router.message(Command("replace", "replacer"))
async def replace_command_handler(message: Message):
    await send_replacer_menu(message, message.from_user.id)

# 4. Trigger Step 1: Ask for 'Find' Word
@router.callback_query(F.data == "add_rep_pair")
async def ask_for_find(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ReplacerStates.waiting_for_find)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_replacer")]
    ])
    await callback.message.edit_text(
        f"🔍 <b>{small_caps('Step 1: Enter Word to FIND')}</b>\n\n"
        f"Wo word ya link bhejiye jise aap caption se **hatana/badalna** chahte hain (e.g., <code>OldChannel</code> ya <code>@purana</code>):",
        parse_mode="HTML", reply_markup=keyboard
    )
    await callback.answer()

# 5. Catch 'Find' Word & Trigger Step 2: Ask for 'Replace' Word
@router.message(ReplacerStates.waiting_for_find, F.text)
async def catch_find_word(message: Message, state: FSMContext):
    find_text = message.text.strip()
    await state.update_data(find_text=find_text) # Temporary save in memory
    
    await state.set_state(ReplacerStates.waiting_for_replace)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_replacer")]
    ])
    await message.answer(
        f"✍️ <b>{small_caps('Step 2: Enter Word to REPLACE with')}</b>\n\n"
        f"Ab wo naya word ya link bhejiye jo aap uski **jagah lagana** chahte hain (e.g., <code>NayaChannel</code> ya <code>@apna</code>):",
        parse_mode="HTML", reply_markup=keyboard
    )

# 6. Catch 'Replace' Word & Save both to DB
@router.message(ReplacerStates.waiting_for_replace, F.text)
async def catch_replace_word(message: Message, state: FSMContext):
    user_id = message.from_user.id
    replace_text = message.text.strip()
    
    user_data = await state.get_data()
    find_text = user_data.get("find_text")
    
    # DB mein pair save karein
    await add_replacement_pair(user_id, find_text, replace_text)
    await state.clear() # State clear successfully
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Manage Replacer", callback_data="text_replacer")]
    ])
    await message.answer(
        f"✅ <b>{small_caps('Replacement Saved!')}</b>\n\n"
        f"Ab caption mein jahan bhi <code>{find_text}</code> milega, bot use automatic <code>{replace_text}</code> se badal dega.",
        parse_mode="HTML", reply_markup=keyboard
    )

# 7. Safe Index-based Single Pair Delete Callback Handler
@router.callback_query(F.data.startswith("del_rep_"))
async def delete_single_pair(callback: CallbackQuery):
    user_id = callback.from_user.id
    idx = int(callback.data.replace("del_rep_", ""))
    
    pairs = await get_replacements(user_id)
    if 0 <= idx < len(pairs):
        find_to_delete = pairs[idx]['find']
        await remove_replacement_pair(user_id, find_to_delete)
        await callback.answer(f"🗑️ Deleted: {find_to_delete}")
    else:
        await callback.answer("⚠️ Filter nahi mila!")
        
    await send_replacer_menu(callback, user_id)

# 8. Safe Cancel Handler (Clears State + Returns to Menu)
@router.callback_query(F.data == "cancel_replacer")
async def cancel_replacer(callback: CallbackQuery, state: FSMContext):
    await state.clear() # Background waiting stop karein
    await send_replacer_menu(callback, callback.from_user.id)
    await callback.answer("❌ Cancelled")  

# 1. State Definition
class DumpStates(StatesGroup):
    waiting_for_dump_id = State()

# 2. Main Dump Menu Function
async def send_dump_menu(target: Message | CallbackQuery, user_id: int, bot: Bot):
    saved_dump = await get_custom_dump(user_id)
    
    text = f"<b>📁 {small_caps('Custom Dump Channel')} (Optional)</b>\n\n"
    text += f"Is feature se bot aapki processed videos ko aapke chat ke sath-sath aapke **Dump Channel** mein bhi automatic send kar dega.\n\n"
    
    if saved_dump:
        try:
            # Channel ka naam nikalne ki koshish karte hain
            chat_info = await bot.get_chat(saved_dump)
            chat_name = chat_info.title
            text += f"📢 Connected Dump: <b>{chat_name}</b>\n🆔 ID: <code>{saved_dump}</code>\nStatus: 🟢 <b>Active</b>"
        except Exception:
            text += f"📢 Connected Dump ID: <code>{saved_dump}</code>\n⚠️ <i>Bot ko lagta hai aapne use channel se hata diya hai ya ID galat hai!</i>"
    else:
        text += "<i>ℹ️ Abhi aapne koi dump channel link nahi kiya hai. Videos sirf aapko yahan chat mein milengi.</i>"
        
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Link Dump Channel", callback_data="link_dump_chan")],
        [InlineKeyboardButton(text="❌ Remove / Turn Off", callback_data="remove_dump_chan")],
        [InlineKeyboardButton(text="🔙 Back to Settings", callback_data="settings")]
    ])
    
    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    else:
        await target.answer(text, parse_mode="HTML", reply_markup=keyboard)

# 3. Callback trigger for main dump menu
@router.callback_query(F.data == "manage_dump")
async def manage_dump_callback(callback: CallbackQuery, bot: Bot):
    await send_dump_menu(callback, callback.from_user.id, bot)
    await callback.answer()

# 4. Trigger: Ask for Dump ID
@router.callback_query(F.data == "link_dump_chan")
async def ask_for_dump(callback: CallbackQuery, state: FSMContext):
    await state.set_state(DumpStates.waiting_for_dump_id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data="manage_dump")]
    ])
    text = (
        f"✍️ <b>{small_caps('How to link your channel:')}</b>\n\n"
        f"1. Sabse pehle bot ko apne Dump Channel mein <b>Admin</b> banayein (Post Messages ki permission ke sath).\n"
        f"2. Uske baad apne channel ka <b>Username</b> (e.g., <code>@MyDumpChannel</code>) ya <b>ID</b> (e.g., <code>-100123456789</code>) yahan bhejiye:\n\n"
        f"<i>Tip: Agar private channel hai, toh kisi forward message se uski ID nikal kar bhejien (jo -100 se shuru hoti hai).</i>"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()

# 5. Catch Channel ID & Verify Admin Status
@router.message(DumpStates.waiting_for_dump_id, F.text)
async def process_dump_id(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    input_data = message.text.strip()
    
    # Agar sirf numeric/ID input hai toh use int mein badlo
    if input_data.startswith("-100") and input_data[1:].isdigit():
        target_chat = int(input_data)
    elif input_data.isdigit():
        target_chat = int(f"-100{input_data}")
    else:
        target_chat = input_data # username case like @mychannel
        
    try:
        # Verification: Bot check karega kya wo sach mein wahan admin hai aur message bhej sakta hai
        test_msg = await bot.send_message(chat_id=target_chat, text="🔄 <i>Linking with Thumbnail Changer Bot...</i>")
        await test_msg.delete() # Test message ko turant delete kar do
        
        # Agar successfully verification ho gaya, toh real chat ID database mein save karo
        chat_info = await bot.get_chat(target_chat)
        real_chat_id = chat_info.id
        
        await set_custom_dump(user_id, real_chat_id)
        await state.clear()
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚙️ Manage Dump", callback_data="manage_dump")]
        ])
        await message.answer(
            f"✅ <b>{small_caps('Success!')}</b>\n\n"
            f"Aapka channel <b>{chat_info.title}</b> successfully link ho gaya hai. Ab se processed videos yahan ke sath aapke channel par bhi automatic post hongi.",
            parse_mode="HTML", reply_markup=keyboard
        )
    except Exception as e:
        await message.answer(
            f"❌ <b>{small_caps('Verification Failed!')}</b>\n\n"
            f"Bot aapke channel par message nahi bhej pa raha hai. Kripya check karein:\n"
            f"1. Kya aapne bot ko channel mein <b>Admin</b> banaya hai?\n"
            f"2. Kya aapne sahi Username ya ID bheji hai?"
        )

# 6. Remove Dump Handler
@router.callback_query(F.data == "remove_dump_chan")
async def remove_dump_callback(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    await remove_custom_dump(user_id)
    await callback.answer("🗑️ Dump channel unlinked successfully!", show_alert=True)
    await send_dump_menu(callback, user_id, bot)      

@router.callback_query(F.data == "close_settings")
async def close_settings(callback: CallbackQuery):
    """Close the settings menu."""
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    await callback.answer(small_caps("Settings closed"))
