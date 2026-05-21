from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, List, Dict, Any
from datetime import datetime
from config import MONGO_URL, DB_NAME, OWNER_ID

client: AsyncIOMotorClient = None
db = None

async def init_db():
    """Initialize MongoDB connection and setup indexes."""
    global client, db
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Create indexes for faster lookups
    await db.users.create_index("user_id", unique=True)
    await db.admins.create_index("user_id", unique=True)
    
    # Add owner as admin by default
    await add_admin(OWNER_ID)
    print("✅ MongoDB connected & Database Fully Initialized")

async def close_db():
    """Close MongoDB connection."""
    global client
    if client:
        client.close()

# ==================== USER & PROFILE FUNCTIONS ====================

async def add_user(user_id: int, username: str = None, first_name: str = None):
    """Add or update a user with Referral and Limit fields."""
    await db.users.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "username": username,
                "first_name": first_name
            },
            "$setOnInsert": {
                "user_id": user_id,
                "caption_style": "Normal",
                "custom_patterns": [],
                "thumbnail_file_id": None,
                "usage_count": 0,
                "banned": False,
                "is_premium": False,
                "daily_count": 0,
                "last_reset": datetime.now().date().isoformat(),
                "referral_count": 0,
                "referred_by": None,
                "replacements": []
            }
        },
        upsert=True
    )

async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """Get user data."""
    return await db.users.find_one({"user_id": user_id})

async def get_all_users() -> List[Dict[str, Any]]:
    """Get all users for broadcast or stats."""
    return await db.users.find().to_list(length=None)

async def get_user_count() -> int:
    """Get total user count."""
    return await db.users.count_documents({})

# ==================== LIMIT & PREMIUM LOGIC ====================

async def check_and_reset_limit(user_id: int):
    """Check if date changed to reset daily count. Returns (count, is_premium)."""
    user = await get_user(user_id)
    if not user:
        return 0, False
    
    today = datetime.now().date().isoformat()
    last_reset = user.get("last_reset")
    is_premium = user.get("is_premium", False)

    if last_reset != today:
        # Naya din hai, count 0 kardo
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"daily_count": 0, "last_reset": today}}
        )
        return 0, is_premium
    
    return user.get("daily_count", 0), is_premium

async def update_premium(user_id: int, status: bool) -> bool:
    """Manually add or remove premium status."""
    result = await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"is_premium": status}}
    )
    return result.modified_count > 0

# ==================== REFERRAL LOGIC ====================

async def add_referral(referrer_id: int, new_user_id: int) -> bool:
    """Links a new user to a referrer and increments count."""
    new_user = await get_user(new_user_id)
    
    # Check if user was already referred or exists before referral
    if new_user and new_user.get("referred_by") is None and new_user_id != referrer_id:
        # Update Referrer
        await db.users.update_one({"user_id": referrer_id}, {"$inc": {"referral_count": 1}})
        # Update New User
        await db.users.update_one({"user_id": new_user_id}, {"$set": {"referred_by": referrer_id}})
        return True
    return False

# ==================== THUMBNAIL & SETTINGS ====================

async def set_thumbnail(user_id: int, file_id: str):
    """Set user's thumbnail."""
    await db.users.update_one({"user_id": user_id}, {"$set": {"thumbnail_file_id": file_id}})

async def get_thumbnail(user_id: int) -> Optional[str]:
    """Get user's thumbnail file_id."""
    user = await get_user(user_id)
    return user.get("thumbnail_file_id") if user else None

async def remove_thumbnail(user_id: int) -> bool:
    """Remove user's thumbnail."""
    result = await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"thumbnail_file_id": None}}
    )
    return result.modified_count > 0

async def set_caption_style(user_id: int, style: str):
    """Save user's caption style."""
    await db.users.update_one({"user_id": user_id}, {"$set": {"caption_style": style}})

async def get_caption_style(user_id: int) -> str:
    """Get user's saved caption style."""
    user = await get_user(user_id)
    return user.get("caption_style", "Normal") if user else "Normal"

# ==================== USAGE & LEADERBOARD ====================

async def increment_usage(user_id: int):
    """Increments total usage and daily usage."""
    await db.users.update_one(
        {"user_id": user_id},
        {"$inc": {"usage_count": 1, "daily_count": 1}}
    )

async def get_leaderboard(limit: int = 10) -> List[Dict[str, Any]]:
    """Get top users by usage count."""
    return await db.users.find(
        {"usage_count": {"$gt": 0}}
    ).sort("usage_count", -1).limit(limit).to_list(length=limit)

async def add_premium_user(user_id: int):
    """User ko premium list mein add karne ke liye."""
    await db.users.update_one({"user_id": user_id}, {"$set": {"is_premium": True}}, upsert=True)

async def remove_premium_user(user_id: int):
    """User ko premium list se remove karne ke liye."""
    await db.users.update_one({"user_id": user_id}, {"$set": {"is_premium": False}})

async def check_premium_status(user_id: int) -> bool:
    """Check karne ke liye ki kya user premium hai (Default: False)."""
    user = await db.users.find_one({"user_id": user_id})
    return user.get("is_premium", False) if user else False

# ==================== ADMIN & BAN FUNCTIONS ====================

async def is_admin(user_id: int) -> bool:
    """Check if user is admin."""
    if user_id == OWNER_ID: return True
    admin = await db.admins.find_one({"user_id": user_id})
    return admin is not None

async def add_admin(user_id: int):
    """Add a new admin."""
    await db.admins.update_one({"user_id": user_id}, {"$set": {"user_id": user_id}}, upsert=True)

async def remove_admin(user_id: int) -> bool:
    """Remove an admin."""
    if user_id == OWNER_ID: return False
    result = await db.admins.delete_one({"user_id": user_id})
    return result.deleted_count > 0

async def get_all_admins() -> List[int]:
    """Get all admin IDs."""
    admins_list = await db.admins.find().to_list(length=None)
    return [a["user_id"] for a in admins_list]

async def is_banned(user_id: int) -> bool:
    """Check if user is banned."""
    user = await get_user(user_id)
    return user.get("banned", False) if user else False

async def ban_user(user_id: int) -> bool:
    """Ban a user."""
    result = await db.users.update_one({"user_id": user_id}, {"$set": {"banned": True}})
    return result.modified_count > 0

async def unban_user(user_id: int) -> bool:
    """Unban a user."""
    result = await db.users.update_one({"user_id": user_id}, {"$set": {"banned": False}})
    return result.modified_count > 0

async def add_custom_pattern(user_id: int, pattern: str):
    """User ka apna word/link list mein add karna."""
    await db.users.update_one(
        {"user_id": user_id},
        {"$addToSet": {"custom_patterns": pattern}}
    )

async def remove_custom_pattern(user_id: int, pattern: str):
    """User ka pattern list se hatana."""
    await db.users.update_one(
        {"user_id": user_id},
        {"$pull": {"custom_patterns": pattern}}
    )

async def get_custom_patterns(user_id: int) -> list:
    """User ke saare custom patterns nikalna."""
    user = await get_user(user_id)
    return user.get("custom_patterns", []) if user else []

async def add_replacement_pair(user_id: int, find_text: str, replace_text: str):
    """Find aur Replace ka pair database mein insert karna."""
    pair = {"find": find_text, "replace": replace_text}
    # Agar pehle se same 'find' word ho toh use hata do taaki duplicate na ho
    await db.users.update_one(
        {"user_id": user_id},
        {"$pull": {"replacements": {"find": find_text}}}
    )
    # Naya pair push karo
    await db.users.update_one(
        {"user_id": user_id},
        {"$push": {"replacements": pair}}
    )

async def remove_replacement_pair(user_id: int, find_text: str):
    """Specific key/find word ke pair ko delete karna."""
    await db.users.update_one(
        {"user_id": user_id},
        {"$pull": {"replacements": {"find": find_text}}}
    )

async def get_replacements(user_id: int) -> list:
    """User ke saare saved find/replace pairs nikalna."""
    user = await db.users.find_one({"user_id": user_id})
    return user.get("replacements", []) if user else []

async def set_custom_dump(user_id: int, chat_id: int):
    """User ka custom dump channel ID save karne ke liye."""
    await db.users.update_one({"user_id": user_id}, {"$set": {"custom_dump_id": chat_id}})

async def get_custom_dump(user_id: int) -> Optional[int]:
    """User ka saved dump channel ID nikalne ke liye."""
    user = await db.users.find_one({"user_id": user_id})
    return user.get("custom_dump_id") if user else None

async def remove_custom_dump(user_id: int):
    """Custom dump channel ko hataane/disable karne ke liye."""
    await db.users.update_one({"user_id": user_id}, {"$set": {"custom_dump_id": None}})

async def set_canvas_status(user_id: int, status: bool):
    """Smart Canvas Editor ko ON/OFF karne ke liye."""
    await db.users.update_one({"user_id": user_id}, {"$set": {"canvas_status": status}})

async def get_canvas_status(user_id: int) -> bool:
    """Smart Canvas Status check karne ke liye (Default: False)."""
    user = await db.users.find_one({"user_id": user_id})
    return user.get("canvas_status", False) if user else False

async def set_canvas_watermark(user_id: int, watermark: str):
    """User ka custom channel watermark save karne ke liye."""
    await db.users.update_one({"user_id": user_id}, {"$set": {"canvas_watermark": watermark}})

async def get_canvas_watermark(user_id: int) -> str:
    """User ka saved watermark nikalne ke liye (Default: empty string)."""
    user = await db.users.find_one({"user_id": user_id})
    return user.get("canvas_watermark", "") if user else ""

async def set_user_font(user_id: int, font_path: str):
    """User ka select kiya hua font path database mein save karne ke liye."""
    await db.users.update_one({"user_id": user_id}, {"$set": {"canvas_font": font_path}})

async def get_user_font(user_id: int) -> str:
    """User ka saved font path nikalne ke liye (Default: 'fonts/hermes.ttf')."""
    user = await db.users.find_one({"user_id": user_id})
    # Note: Agar folder mein hermes.ttf ki jagah koi aur naam hai, toh wo naam yahan default rakhna
    return user.get("canvas_font", "fonts/hermes.ttf") if user else "fonts/hermes.ttf"    