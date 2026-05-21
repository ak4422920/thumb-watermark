import glob
import os
import time
from html import escape

from aiogram.types import Message
from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import OWNER_ID
import database as db
from database import (
    is_admin, add_admin, remove_admin, get_all_admins,
    ban_user, unban_user, get_all_users, get_user_count,
    get_leaderboard, get_user
)
from database import add_premium_user, remove_premium_user, check_premium_status

router = Router()

OWNER_ID = 6522435665
START_TIME = time.time()


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


def format_bytes(num_bytes: int) -> str:
    """Convert bytes into readable format."""
    size = float(num_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024 or unit == "TB":
            return f"{size:.2f} {unit}" if unit != "B" else f"{int(size)} {unit}"
        size /= 1024
    return f"{num_bytes} B"


def format_uptime(total_seconds: int) -> str:
    """Convert seconds into d/h/m/s format."""
    days, rem = divmod(total_seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)

    chunks = []
    if days:
        chunks.append(f"{days}d")
    if hours:
        chunks.append(f"{hours}h")
    if minutes:
        chunks.append(f"{minutes}m")
    if seconds or not chunks:
        chunks.append(f"{seconds}s")
    return " ".join(chunks)


def get_database():
    """Return live Mongo database object from database module."""
    return db.db if hasattr(db, "db") else None


class BroadcastState(StatesGroup):
    waiting_for_message = State()


# ==================== ADMIN CHECK ====================

async def check_admin(message: types.Message) -> bool:
    """Check if user is admin and send error if not."""
    if not await is_admin(message.from_user.id):
        await message.answer(f"⛔ {small_caps('Admin only command.')}")
        return False
    return True


@router.message(Command("addpremium"))
async def add_premium_cmd(message: Message):
    """Owner kisi bhi user ko premium bana sakta hai: /addpremium 12345678"""
    if message.from_user.id != OWNER_ID:
        return await message.answer("❌ **Aapke paas is command ka use karne ki permission nahi hai!**")

    args = message.text.split()
    if len(args) < 2:
        return await message.answer("✍️ **Sahi format use karein:**\n<code>/addpremium USER_ID</code>", parse_mode="HTML")

    try:
        target_id = int(args[1])
        await add_premium_user(target_id)
        await message.answer(
            f"🌟 **User** <code>{target_id}</code> **ko PREMIUM list mein jodd diya gaya hai! Saare features unlocked.**",
            parse_mode="HTML"
        )
    except ValueError:
        await message.answer("❌ **User ID sirf numbers mein honi chahiye!**")


@router.message(Command("rempremium"))
async def remove_premium_cmd(message: Message):
    """Owner kisi ka bhi premium status hata sakta hai: /rempremium 12345678"""
    if message.from_user.id != OWNER_ID:
        return

    args = message.text.split()
    if len(args) < 2:
        return await message.answer("✍️ **Sahi format use karein:**\n<code>/rempremium USER_ID</code>", parse_mode="HTML")

    try:
        target_id = int(args[1])
        await remove_premium_user(target_id)
        await message.answer(
            f"🗑️ **User** <code>{target_id}</code> **ka premium status successfully hata diya gaya hai!**",
            parse_mode="HTML"
        )
    except ValueError:
        await message.answer("❌ **User ID sirf numbers mein honi chahiye!**")


@router.message(Command("mypremium"))
async def check_my_premium(message: Message):
    """User khud ka status check kar sakta hai ki wo premium hai ya nahi."""
    is_prem = await check_premium_status(message.from_user.id)
    if is_prem or message.from_user.id == OWNER_ID:
        await message.answer("🌟 **Aap ek PREMIUM User hain! Saare features fully unlocked hain.**")
    else:
        await message.answer(
            "👑 **Aap abhi ek Free User hain.**\n\n"
            "Canvas Editor and Custom Font features use karne ke liye Admin se contact karke premium activate karwayein."
        )


# ==================== USERS COMMAND ====================

@router.message(Command("users"))
async def users_cmd(message: types.Message):
    """Show total user count."""
    if not await check_admin(message):
        return

    total = await get_user_count()

    await message.answer(
        f"<b>👥 {small_caps('Total Users:')}</b> <code>{total}</code>",
        parse_mode="HTML"
    )


@router.message(Command("stats"))
async def stats_cmd(message: Message):
    """Show full admin stats dashboard."""
    if not await check_admin(message):
        return

    status_msg = await message.answer("📊 **Full bot stats load kiye ja rahe hain...**")
    database = get_database()
    if database is None:
        return await status_msg.edit_text("❌ **Database abhi initialize nahi hua hai.**")

    total_users = await get_user_count()
    admin_ids = await get_all_admins()
    total_admins = len(set(admin_ids + [OWNER_ID]))
    total_premium = await database.users.count_documents({"is_premium": True})
    total_banned = await database.users.count_documents({"banned": True})
    total_free = max(total_users - total_premium, 0)
    total_with_username = await database.users.count_documents({"username": {"$nin": [None, ""]}})
    total_thumbnails = await database.users.count_documents({"thumbnail_file_id": {"$nin": [None, ""]}})
    total_custom_dump = await database.users.count_documents({"custom_dump_id": {"$exists": True, "$nin": [None, ""]}})
    total_pattern_users = await database.users.count_documents({"custom_patterns.0": {"$exists": True}})
    total_replace_users = await database.users.count_documents({"replacements.0": {"$exists": True}})

    aggregate_rows = await database.users.aggregate([
        {
            "$group": {
                "_id": None,
                "total_usage": {"$sum": {"$ifNull": ["$usage_count", 0]}},
                "today_usage": {"$sum": {"$ifNull": ["$daily_count", 0]}},
                "total_referrals": {"$sum": {"$ifNull": ["$referral_count", 0]}}
            }
        }
    ]).to_list(length=1)
    aggregate_data = aggregate_rows[0] if aggregate_rows else {}
    total_usage = aggregate_data.get("total_usage", 0)
    today_usage = aggregate_data.get("today_usage", 0)
    total_referrals = aggregate_data.get("total_referrals", 0)

    leaders = await get_leaderboard(5)
    top_lines = []
    for idx, user in enumerate(leaders, start=1):
        raw_username = user.get("username")
        raw_name = user.get("first_name") or "N/A"
        display_name = f"@{escape(str(raw_username))}" if raw_username else escape(str(raw_name))
        top_lines.append(
            f"{idx}. {display_name} - <code>{user.get('user_id')}</code> - <b>{user.get('usage_count', 0)}</b>"
        )
    top_users_text = "\n".join(top_lines) if top_lines else "No usage data yet."

    collection_names = await database.list_collection_names()
    collection_lines = []
    for col in sorted(collection_names):
        col_count = await database[col].count_documents({})
        collection_lines.append(f"• <code>{col}</code>: <b>{col_count}</b> docs")
    collections_text = "\n".join(collection_lines) if collection_lines else "• No collections found"

    patterns_to_clean = ["raw_*.jpg", "enhanced_*.jpg", "temp_*.jpg", "*.jpeg", "*.png"]
    temp_files_count = 0
    temp_files_bytes = 0
    seen_files = set()
    for pattern in patterns_to_clean:
        for file_path in glob.glob(pattern):
            if file_path in seen_files or not os.path.isfile(file_path):
                continue
            seen_files.add(file_path)
            temp_files_count += 1
            try:
                temp_files_bytes += os.path.getsize(file_path)
            except OSError:
                pass

    uptime_text = format_uptime(int(time.time() - START_TIME))

    text = (
        f"<b>📊 Full Bot Stats Dashboard</b>\n"
        f"{'━' * 28}\n\n"
        f"<b>⏱ Runtime</b>\n"
        f"• Uptime: <code>{uptime_text}</code>\n"
        f"• Database: <code>{database.name}</code>\n\n"
        f"<b>👥 Users</b>\n"
        f"• Total Users: <code>{total_users}</code>\n"
        f"• Free Users: <code>{total_free}</code>\n"
        f"• Premium Users: <code>{total_premium}</code>\n"
        f"• Banned Users: <code>{total_banned}</code>\n"
        f"• Admins: <code>{total_admins}</code>\n"
        f"• Users With Username: <code>{total_with_username}</code>\n\n"
        f"<b>🎯 Features</b>\n"
        f"• Thumbnails Set: <code>{total_thumbnails}</code>\n"
        f"• Custom Dumps Set: <code>{total_custom_dump}</code>\n"
        f"• Pattern Users: <code>{total_pattern_users}</code>\n"
        f"• Replace Users: <code>{total_replace_users}</code>\n\n"
        f"<b>📈 Usage</b>\n"
        f"• Total Usage: <code>{total_usage}</code>\n"
        f"• Today Usage Counter: <code>{today_usage}</code>\n"
        f"• Total Referrals: <code>{total_referrals}</code>\n\n"
        f"<b>🗂 Collections</b>\n"
        f"{collections_text}\n\n"
        f"<b>🧹 Cleanup Preview</b>\n"
        f"• Temp Files Found: <code>{temp_files_count}</code>\n"
        f"• Temp Size: <code>{format_bytes(temp_files_bytes)}</code>\n\n"
        f"<b>🏆 Top Users</b>\n"
        f"{top_users_text}"
    )

    await status_msg.edit_text(text, parse_mode="HTML")


# ==================== ADD/REMOVE ADMIN ====================

@router.message(Command("add_admin"))
async def add_admin_cmd(message: types.Message):
    """Add a new admin."""
    if message.from_user.id != OWNER_ID:
        await message.answer(f"⛔ {small_caps('Owner only command.')}")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer(f"❌ {small_caps('Usage: /add_admin <user_id>')}")
        return

    try:
        user_id = int(args[1])
    except ValueError:
        await message.answer(f"❌ {small_caps('Invalid user ID.')}")
        return

    await add_admin(user_id)
    await message.answer(f"✅ {small_caps('Admin added:')} <code>{user_id}</code>", parse_mode="HTML")


@router.message(Command("remove_admin"))
async def remove_admin_cmd(message: types.Message):
    """Remove an admin."""
    if message.from_user.id != OWNER_ID:
        await message.answer(f"⛔ {small_caps('Owner only command.')}")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer(f"❌ {small_caps('Usage: /remove_admin <user_id>')}")
        return

    try:
        user_id = int(args[1])
    except ValueError:
        await message.answer(f"❌ {small_caps('Invalid user ID.')}")
        return

    if user_id == OWNER_ID:
        await message.answer(f"❌ {small_caps('Cannot remove owner.')}")
        return

    removed = await remove_admin(user_id)
    if removed:
        await message.answer(f"✅ {small_caps('Admin removed:')} <code>{user_id}</code>", parse_mode="HTML")
    else:
        await message.answer(f"❌ {small_caps('User was not an admin.')}")


# ==================== BAN/UNBAN ====================

@router.message(Command("ban"))
async def ban_cmd(message: types.Message):
    """Ban a user."""
    if not await check_admin(message):
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer(f"❌ {small_caps('Usage: /ban <user_id>')}")
        return

    try:
        user_id = int(args[1])
    except ValueError:
        await message.answer(f"❌ {small_caps('Invalid user ID.')}")
        return

    if user_id == OWNER_ID:
        await message.answer(f"❌ {small_caps('Cannot ban owner.')}")
        return

    if await is_admin(user_id):
        await message.answer(f"❌ {small_caps('Cannot ban an admin.')}")
        return

    banned = await ban_user(user_id)
    if banned:
        await message.answer(f"🚫 {small_caps('User banned:')} <code>{user_id}</code>", parse_mode="HTML")
    else:
        await message.answer(f"❌ {small_caps('User not found.')}")


@router.message(Command("unban"))
async def unban_cmd(message: types.Message):
    """Unban a user."""
    if not await check_admin(message):
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer(f"❌ {small_caps('Usage: /unban <user_id>')}")
        return

    try:
        user_id = int(args[1])
    except ValueError:
        await message.answer(f"❌ {small_caps('Invalid user ID.')}")
        return

    unbanned = await unban_user(user_id)
    if unbanned:
        await message.answer(f"✅ {small_caps('User unbanned:')} <code>{user_id}</code>", parse_mode="HTML")
    else:
        await message.answer(f"❌ {small_caps('User not found or not banned.')}")


# ==================== LEADERBOARD ====================

@router.message(Command("topleaderboard"))
async def leaderboard_cmd(message: types.Message):
    """Show top users by usage."""
    if not await check_admin(message):
        return

    leaders = await get_leaderboard(10)

    if not leaders:
        await message.answer(f"📊 {small_caps('No usage data yet.')}")
        return

    text = f"<b>🏆 {small_caps('Top Leaderboard')}</b>\n\n"

    medals = ["🥇", "🥈", "🥉"]
    for i, user in enumerate(leaders):
        medal = medals[i] if i < 3 else f"{i + 1}."
        user_id = user.get("user_id")
        username = user.get("username")
        first_name = user.get("first_name") or "N/A"
        display_name = f"@{escape(str(username))}" if username else escape(str(first_name))
        usage = user.get("usage_count", 0)
        text += f"{medal} {display_name} (<code>{user_id}</code>) — <b>{usage}</b> {small_caps('videos')}\n"

    await message.answer(text, parse_mode="HTML")


# ==================== BROADCAST ====================

@router.message(Command("broadcast"))
async def broadcast_cmd(message: types.Message, state: FSMContext):
    """Start broadcast."""
    if not await check_admin(message):
        return

    await state.set_state(BroadcastState.waiting_for_message)
    await message.answer(
        f"📢 {small_caps('Send the message you want to broadcast.')}\n\n"
        f"<i>{small_caps('Send /cancel to cancel.')}</i>",
        parse_mode="HTML"
    )


@router.message(Command("cancel"))
async def cancel_broadcast(message: types.Message, state: FSMContext):
    """Cancel broadcast."""
    current_state = await state.get_state()
    if current_state:
        await state.clear()
        await message.answer(f"❌ {small_caps('Cancelled.')}")


@router.message(BroadcastState.waiting_for_message)
async def do_broadcast(message: types.Message, state: FSMContext, bot: Bot):
    """Perform the broadcast."""
    await state.clear()

    users = await get_all_users()
    success = 0
    failed = 0

    status_msg = await message.answer(f"📢 {small_caps('Broadcasting...')} 0/{len(users)}")

    for i, user in enumerate(users):
        user_id = user.get("user_id")
        try:
            await bot.copy_message(
                chat_id=user_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
            success += 1
        except Exception:
            failed += 1

        if (i + 1) % 10 == 0:
            try:
                await status_msg.edit_text(
                    f"📢 {small_caps('Broadcasting...')} {i + 1}/{len(users)}"
                )
            except Exception:
                pass

    await status_msg.edit_text(
        f"✅ {small_caps('Broadcast complete!')}\n\n"
        f"📨 {small_caps('Sent:')} {success}\n"
        f"❌ {small_caps('Failed:')} {failed}"
    )


# =========================================================================
# 1. THE /CLEANDB COMMAND (SAFE MAINTENANCE CLEANER)
# =========================================================================
@router.message(Command("cleandb"))
async def clean_db_handler(message: Message):
    user_id = message.from_user.id

    if user_id != OWNER_ID:
        return await message.answer("❌ **Access Denied!** Yeh command sirf Bot Owner use kar sakta hai.")

    status_msg = await message.answer("🔄 **Safe Maintenance Mode Started...**\nRAM aur Disk se junk saaf kiya ja raha hai...")

    deleted_files_count = 0
    freed_space_bytes = 0

    patterns_to_clean = ["raw_*.jpg", "enhanced_*.jpg", "temp_*.jpg", "*.jpeg", "*.png"]
    for pattern in patterns_to_clean:
        for file_path in glob.glob(pattern):
            if not os.path.isfile(file_path):
                continue
            try:
                file_size = os.path.getsize(file_path)
                os.remove(file_path)
                deleted_files_count += 1
                freed_space_bytes += file_size
            except Exception:
                pass

    banned_deleted_states = 0
    try:
        database = get_database()
        if database is not None:
            banned_cursor = database.users.find({"banned": True})
            async for user in banned_cursor:
                b_uid = user.get("user_id")
                await database.users.update_one(
                    {"user_id": b_uid},
                    {"$unset": {"pending_poster_url": "", "poster_results": "", "search_backup_query": ""}}
                )
                banned_deleted_states += 1
    except Exception as e:
        print(f"DB Clean Maintenance Error: {e}")

    freed_mb = round(freed_space_bytes / (1024 * 1024), 2)

    await status_msg.edit_text(
        f"✅ **MAINTENANCE CLEAN COMPLETE!**\n\n"
        f"🗑️ Junk Files Deleted: `{deleted_files_count} files`\n"
        f"💾 Storage RAM Freed: `{freed_mb} MB`\n"
        f"🚫 Banned Profiles Flushed: `{banned_deleted_states} users memory cleared`\n\n"
        f"🚀 Bot ab ekdum light aur optimize chalega!"
    )


# =========================================================================
# 2. THE MAHA COMMAND: /NUKEDB (THE NUCLEAR FACTORY RESET)
# =========================================================================
@router.message(Command("nukedb"))
async def nuke_db_handler(message: Message):
    user_id = message.from_user.id

    if user_id != OWNER_ID:
        return await message.answer("❌ **Maha Ghor Apradh!** Is command ko chhedne ki koshish dobara mat karna.")

    status_msg = await message.answer("☢️ **NUCLEAR NUKE COMMAND TRIGGERED!**\nPoore system ko wipe out kiya ja raha hai, please wait...")

    files_wiped = 0
    root_dir = "."
    try:
        for root, dirs, files in os.walk(root_dir):
            for file in files:
                if not file.endswith(".py") and not file.endswith(".txt") and file != "Dockerfile" and file != ".gitignore":
                    try:
                        os.remove(os.path.join(root, file))
                        files_wiped += 1
                    except Exception:
                        pass
    except Exception as err:
        print(f"Storage wipe error: {err}")

    collections_dropped = []
    try:
        database = get_database()
        if database is not None:
            cols = await database.list_collection_names()
            for col in cols:
                await database[col].drop()
                collections_dropped.append(col)
    except Exception as err:
        print(f"DB wipe error: {err}")

    await status_msg.edit_text(
        f"💥 **SYSTEM COMPLETED FACTORY RESET!** 💥\n\n"
        f"💀 Wiped Junk Files: `{files_wiped} assets deleted`\n"
        f"🗂️ Dropped Databases: `{', '.join(collections_dropped) if collections_dropped else 'All Collections Cleaned'}`\n\n"
        f"⚠️ **Note:** Saare premium users, cache suggestions aur user data 100% delete ho chuka hai. Bot ab ekdum brand new fresh state mein hai!"
    )
