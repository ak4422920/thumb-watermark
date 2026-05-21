import os
import aiohttp
import urllib.parse
import time
import re
import asyncio
from difflib import SequenceMatcher

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram import types
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from database import db
from config import POSTER_API_KEYS

router = Router()

user_cooldowns = {}

class PosterStates(StatesGroup):
    waiting_for_movie_name = State()

def get_db_instance():
    if hasattr(db, "db"):
        return db.db
    return db

def normalize_search_text(text: str) -> str:
    text = (text or "").lower()
    text = urllib.parse.unquote_plus(text)
    text = re.sub(r'https?://\S+|www\.\S+|t\.me/\S+|@\S+', ' ', text)
    text = re.sub(r'\[[^\]]*\]|\([^\)]*\)', ' ', text)
    text = re.sub(r'\b(?:19|20)\d{2}\b', ' ', text)
    text = re.sub(r'\b(?:s\d{1,2}e\d{1,2}|season\s*\d+|episode\s*\d+|ep\s*\d+)\b', ' ', text, flags=re.IGNORECASE)
    text = re.sub(
        r'\b(?:720p|1080p|2160p|4k|hdrip|webrip|web-dl|bluray|brrip|dvdrip|hdtv|x264|x265|h264|h265|hevc|dual audio|multi audio|uncut|extended|proper|remastered)\b',
        ' ',
        text,
        flags=re.IGNORECASE
    )
    text = text.replace(".", " ").replace("_", " ").replace("-", " ").replace(":", " ")
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_query_year(text: str) -> str | None:
    match = re.search(r'\b(19|20)\d{2}\b', text or "")
    return match.group(0) if match else None


def build_query_variants(title: str) -> list[str]:
    raw = (title or "").strip()
    normalized = normalize_search_text(raw)
    variants = []
    for candidate in [
        normalized,
        re.sub(r'\b(?:season\s*\d+|episode\s*\d+|ep\s*\d+|s\d{1,2}e\d{1,2})\b', ' ', normalized, flags=re.IGNORECASE),
        normalized.split(" aka ")[0].strip(),
        normalized.split(" vs ")[0].strip(),
    ]:
        candidate = re.sub(r'\s+', ' ', candidate).strip()
        if candidate and candidate not in variants:
            variants.append(candidate)
    return variants or [raw]


def get_fuzzy_ratio(s1: str, s2: str) -> float:
    s1 = normalize_search_text(s1)
    s2 = normalize_search_text(s2)
    return SequenceMatcher(None, s1, s2).ratio() * 100


def get_source_priority(source: str) -> int:
    order = {
        "SPIDY OTT": 35,
        "TMDB GLOBAL": 32,
        "ANILIST": 26,
        "MYANIMELIST": 24,
        "TVMAZE NETWORK": 22,
        "OMDB BACKUP": 20,
        "WEB ENGINE": 8,
    }
    return order.get(source or "", 10)


def score_poster_result(user_query: str, item: dict) -> float:
    query_norm = normalize_search_text(user_query)
    title_norm = normalize_search_text(item.get("title", ""))
    title_score = get_fuzzy_ratio(query_norm, title_norm)
    query_year = extract_query_year(user_query)
    item_year = str(item.get("year", "") or "")
    year_bonus = 12 if query_year and query_year == item_year else 0
    prefix_bonus = 8 if len(query_norm) >= 4 and title_norm.startswith(query_norm[:12]) else 0
    source_bonus = get_source_priority(item.get("source", ""))
    type_text = str(item.get("type", "")).upper()
    type_bonus = 4 if any(key in query_norm for key in ["anime", "season", "series", "tv"]) and "SERIES" in type_text else 0
    return title_score + year_bonus + prefix_bonus + source_bonus + type_bonus


def dedupe_and_rank_results(user_query: str, results: list[dict]) -> list[dict]:
    best_map = {}
    for item in results:
        poster = str(item.get("poster") or "").strip()
        title = str(item.get("title") or "").strip()
        if not poster or not title:
            continue
        key = (normalize_search_text(title), str(item.get("year") or ""), poster)
        item_copy = dict(item)
        item_copy["match_score"] = round(score_poster_result(user_query, item_copy), 2)
        old_item = best_map.get(key)
        if old_item is None or item_copy["match_score"] > old_item["match_score"]:
            best_map[key] = item_copy

    ranked = sorted(
        best_map.values(),
        key=lambda x: (
            x.get("match_score", 0),
            get_source_priority(x.get("source", "")),
            len(str(x.get("title", "")))
        ),
        reverse=True
    )
    strong = [item for item in ranked if item.get("match_score", 0) >= 55]
    return strong[:18] if strong else ranked[:12]

async def find_local_suggestions(user_query: str) -> list:
    suggestions = []
    database = get_db_instance()
    if database is None:
        return suggestions
    try:
        normalized_query = normalize_search_text(user_query)
        lead_token = normalized_query.split()[0] if normalized_query.split() else normalized_query[:3]
        cursor = database.cached_posters.find(
            {"title": {"$regex": lead_token, "$options": "i"}},
            {"title": 1}
        ).limit(50)
        async for doc in cursor:
            cached_title = doc.get("title", "")
            if cached_title:
                score = get_fuzzy_ratio(normalized_query, cached_title)
                if score >= 65:
                    suggestions.append(cached_title)
    except Exception as e:
        print(f"Local Suggestion Error: {e}")
    return list(set(suggestions))[:5]

async def get_next_api_key() -> str:
    database = get_db_instance()
    if database is None:
        return POSTER_API_KEYS[0]
    try:
        setting = await database.api_settings.find_one({"type": "round_robin"})
        if not setting:
            await database.api_settings.insert_one({"type": "round_robin", "current_index": 0})
            current_index = 0
        else:
            current_index = setting.get("current_index", 0)
        next_index = (current_index + 1) % len(POSTER_API_KEYS)
        await database.api_settings.update_one(
            {"type": "round_robin"}, {"$set": {"current_index": next_index}}
        )
        return POSTER_API_KEYS[current_index]
    except Exception as e:
        print(f"API Key Rotation Error: {e}")
        return POSTER_API_KEYS[0]


# ╔══════════════════════════════════════════════════════════════╗
# ║         6-NODE HYBRID ENGINE — CRITICAL BUG FIXED           ║
# ╠══════════════════════════════════════════════════════════════╣
# ║  BUG: Ek shared TCPConnector sabhi nodes ko pass hota tha.  ║
# ║  Pehla ClientSession close hote hi connector band ho jaata  ║
# ║  tha — baaki 5 nodes silently fail. Result: sirf 1 node.    ║
# ║                                                             ║
# ║  FIX: Har node ka apna independent connector — properly     ║
# ║  close bhi hota hai finally block mein.                     ║
# ╚══════════════════════════════════════════════════════════════╝

async def fetch_spidy_node(cleaned_title: str, encoded_title: str, token: str, headers: dict) -> list:
    results   = []
    api_urls  = [
        f"https://poster-api.ispidy.com/v1/fetch?api_key={token}&title={encoded_title}",
        f"https://poster-api.ispidy.com/v1/fetch?api_key={token}&query={encoded_title}"
    ]
    connector = aiohttp.TCPConnector(ssl=False)
    try:
        async with aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=6)) as session:
            for url in api_urls:
                try:
                    async with session.get(url, headers=headers) as response:
                        if response.status != 200: continue
                        raw_data = await response.json()
                        if not raw_data: continue
                        res_list = raw_data.get("results", []) or ([raw_data] if "title" in raw_data else [])
                        for item in res_list:
                            p_url = item.get("poster") or item.get("landscape")
                            l_url = item.get("landscape") or item.get("poster")
                            if not (p_url and str(p_url).startswith("http")): continue
                            if "media-amazon" in p_url or "m.media-amazon" in p_url:
                                p_url = p_url.replace("SX300", "SX1000").replace("._V1_", "._V1_UX1200_")
                                l_url = l_url.replace("SX300", "SX1000").replace("._V1_", "._V1_UX1200_")
                            raw_type   = str(item.get("type", "MOVIE")).upper()
                            type_badge = "📺 SERIES" if ("TV" in raw_type or "SERIES" in raw_type) else "🎬 MOVIE"
                            results.append({"title": str(item.get("title", cleaned_title)), "poster": str(p_url),
                                            "landscape": str(l_url), "year": str(item.get("year", "N/A")),
                                            "type": type_badge, "season": item.get("season"), "source": "SPIDY OTT"})
                except Exception: continue
    except Exception as e:
        print(f"Spidy Node Error: {e}")
    finally:
        await connector.close()
    return results


async def fetch_tmdb_node(cleaned_title: str) -> list:
    results   = []
    url       = (f"https://api.themoviedb.org/3/search/multi?api_key=f09113847b51fe0d26d5ac841a914644"
                 f"&query={urllib.parse.quote(cleaned_title)}&include_adult=false")
    connector = aiohttp.TCPConnector(ssl=False)
    try:
        async with aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=6)) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    for item in data.get("results", [])[:10]:
                        p_path = item.get("poster_path")
                        b_path = item.get("backdrop_path") or p_path
                        if not p_path: continue
                        p_url  = f"https://image.tmdb.org/t/p/original{p_path}"
                        l_url  = f"https://image.tmdb.org/t/p/original{b_path}"
                        name   = item.get("title") or item.get("name") or cleaned_title
                        r_date = item.get("release_date") or item.get("first_air_date") or "N/A"
                        year   = r_date.split("-")[0] if "-" in r_date else r_date
                        m_type = "📺 SERIES" if item.get("media_type") == "tv" else "🎬 MOVIE"
                        results.append({"title": str(name), "poster": p_url, "landscape": l_url,
                                        "year": str(year), "type": m_type, "season": None, "source": "TMDB GLOBAL"})
    except Exception as e:
        print(f"TMDB Node Error: {e}")
    finally:
        await connector.close()
    return results


async def fetch_anilist_node(cleaned_title: str) -> list:
    results   = []
    query     = '''query ($search: String) { Page (perPage: 8) { media (search: $search, type: ANIME) {
                   title { romaji english } coverImage { extraLarge large } bannerImage startDate { year } format } } }'''
    connector = aiohttp.TCPConnector(ssl=False)
    try:
        async with aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=5)) as session:
            async with session.post('https://graphql.anilist.co',
                                    json={'query': query, 'variables': {'search': cleaned_title}}) as response:
                if response.status == 200:
                    data       = await response.json()
                    media_list = data.get('data', {}).get('Page', {}).get('media', [])
                    for item in media_list:
                        p_url = item.get('coverImage', {}).get('extraLarge') or item.get('coverImage', {}).get('large')
                        l_url = item.get('bannerImage') or p_url
                        if not p_url: continue
                        title_name = (item.get('title', {}).get('english')
                                      or item.get('title', {}).get('romaji') or cleaned_title)
                        results.append({"title": str(title_name), "poster": str(p_url), "landscape": str(l_url),
                                        "year": str(item.get('startDate', {}).get('year', 'N/A')),
                                        "type": f"🏮 ANIME ({item.get('format', 'TV')})", "season": None, "source": "ANILIST"})
    except Exception as e:
        print(f"AniList Node Error: {e}")
    finally:
        await connector.close()
    return results


async def fetch_jikan_mal_node(cleaned_title: str) -> list:
    results   = []
    url       = f"https://api.jikan.moe/v4/anime?q={urllib.parse.quote(cleaned_title)}&limit=8"
    connector = aiohttp.TCPConnector(ssl=False)
    try:
        async with aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=5)) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    for item in data.get("data", []):
                        images = item.get("images", {}).get("jpg", {})
                        p_url  = images.get("large_image_url") or images.get("image_url")
                        if not p_url: continue
                        results.append({"title": str(item.get("title_english") or item.get("title")),
                                        "poster": str(p_url), "landscape": str(p_url),
                                        "year": str(item.get("year") or "N/A"),
                                        "type": "🏮 ANIME (MAL)", "season": None, "source": "MYANIMELIST"})
    except Exception as e:
        print(f"Jikan Node Error: {e}")
    finally:
        await connector.close()
    return results


async def fetch_tvmaze_node(cleaned_title: str) -> list:
    results   = []
    url       = f"https://api.tvmaze.com/search/shows?q={urllib.parse.quote(cleaned_title)}"
    connector = aiohttp.TCPConnector(ssl=False)
    try:
        async with aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=5)) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    for show_box in data:
                        item    = show_box.get("show", {})
                        img_obj = item.get("image") or {}
                        p_url   = img_obj.get("original") or img_obj.get("medium")
                        if not p_url: continue
                        r_date = item.get("premiered") or "N/A"
                        year   = r_date.split("-")[0] if "-" in r_date else r_date
                        results.append({"title": str(item.get("name")), "poster": str(p_url), "landscape": str(p_url),
                                        "year": str(year), "type": "📺 SERIES (TVMAZE)", "season": None, "source": "TVMAZE NETWORK"})
    except Exception as e:
        print(f"TVMaze Node Error: {e}")
    finally:
        await connector.close()
    return results


async def fetch_omdb_node(encoded_title: str) -> list:
    results   = []
    url       = f"https://www.omdbapi.com/?s={encoded_title}&apikey=2356c9a"
    connector = aiohttp.TCPConnector(ssl=False)
    try:
        async with aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=5)) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("Response") == "True":
                        for item in data.get("Search", [])[:10]:
                            p_url = item.get("Poster")
                            if not (p_url and p_url.startswith("http") and p_url != "N/A"): continue
                            p_url      = p_url.replace("SX300", "SX1000")
                            raw_type   = str(item.get("Type")).upper()
                            type_badge = "📺 SERIES" if ("SERIES" in raw_type or "EPISODE" in raw_type) else "🎬 MOVIE"
                            results.append({"title": str(item.get("Title")), "poster": str(p_url), "landscape": str(p_url),
                                            "year": str(item.get("Year")), "type": type_badge, "season": None, "source": "OMDB BACKUP"})
    except Exception as e:
        print(f"OMDB Node Error: {e}")
    finally:
        await connector.close()
    return results


async def fetch_scraper_fallback(cleaned_title: str) -> list:
    results   = []
    url       = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(cleaned_title + ' poster cinema hd')}"
    headers   = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
    connector = aiohttp.TCPConnector(ssl=False)
    try:
        async with aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=6)) as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    html  = await response.text()
                    links = re.findall(r'//external-content.duckduckgo.com/iu/\?u=([^&"\' >]+)', html)
                    count = 0
                    for img_url in links:
                        actual_url = urllib.parse.unquote(img_url)
                        if actual_url.startswith("http") and any(ext in actual_url.lower() for ext in [".jpg", ".jpeg", ".png"]):
                            results.append({"title": cleaned_title.upper(), "poster": actual_url, "landscape": actual_url,
                                            "year": "N/A", "type": "🔍 WEB METADATA", "season": None, "source": "WEB ENGINE"})
                            count += 1
                            if count >= 10: break
    except Exception as e:
        print(f"Scraper Fallback Error: {e}")
    finally:
        await connector.close()
    return results


async def fetch_all_hybrid_posters(title: str) -> list:
    if not title: return []

    token         = await get_next_api_key()
    query_variants = build_query_variants(title)
    cleaned_title = query_variants[0]
    encoded_title = urllib.parse.quote(cleaned_title)
    headers       = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Accept": "application/json"}

    tasks = [
        fetch_spidy_node(cleaned_title, encoded_title, token, headers),
        fetch_tmdb_node(cleaned_title),
        fetch_anilist_node(cleaned_title),
        fetch_jikan_mal_node(cleaned_title),
        fetch_tvmaze_node(cleaned_title),
        fetch_omdb_node(encoded_title),
    ]

    # return_exceptions=True — ek node crash bhi kare to baaki ke results milte hain
    node_outputs = await asyncio.gather(*tasks, return_exceptions=True)

    clean_outputs = []
    for i, output in enumerate(node_outputs):
        if isinstance(output, Exception):
            print(f"Node {i+1} exception: {output}")
            clean_outputs.append([])
        else:
            clean_outputs.append(output or [])

    # True Round-Robin Interleaving
    combined_list = []
    max_length    = max((len(n) for n in clean_outputs), default=0)
    for i in range(max_length):
        for node_res in clean_outputs:
            if i < len(node_res):
                item = node_res[i]
                existing_urls = {r["poster"] for r in combined_list}
                if item["poster"] not in existing_urls:
                    combined_list.append(item)

    ranked_results = dedupe_and_rank_results(title, combined_list)

    if len(ranked_results) < 4 and len(query_variants) > 1:
        relaxed_title = query_variants[1]
        relaxed_encoded = urllib.parse.quote(relaxed_title)
        relaxed_outputs = await asyncio.gather(
            fetch_spidy_node(relaxed_title, relaxed_encoded, token, headers),
            fetch_tmdb_node(relaxed_title),
            fetch_anilist_node(relaxed_title),
            fetch_jikan_mal_node(relaxed_title),
            fetch_tvmaze_node(relaxed_title),
            fetch_omdb_node(relaxed_encoded),
            return_exceptions=True
        )
        extra_items = []
        for output in relaxed_outputs:
            if isinstance(output, Exception):
                continue
            extra_items.extend(output or [])
        ranked_results = dedupe_and_rank_results(title, combined_list + extra_items)

    if not ranked_results:
        ranked_results = dedupe_and_rank_results(title, await fetch_scraper_fallback(cleaned_title))

    return ranked_results


# ╔══════════════════════════════════════════════════════════════╗
# ║                    KEYBOARD & HANDLERS                      ║
# ╚══════════════════════════════════════════════════════════════╝

def get_poster_keyboard(current_index: int, total_items: int, mode: str = "poster") -> InlineKeyboardMarkup:
    nav_row = []
    if current_index > 0:
        nav_row.append(InlineKeyboardButton(text="◀️ Prev", callback_data=f"poster_page_{current_index - 1}"))
    # ✅ FIX: ignore_click → poster_count_info (handler registered below)
    nav_row.append(InlineKeyboardButton(text=f"📊 {current_index + 1}/{total_items}", callback_data="poster_count_info"))
    if current_index < total_items - 1:
        nav_row.append(InlineKeyboardButton(text="Next ▶️", callback_data=f"poster_page_{current_index + 1}"))

    toggle_text     = "🖼️ Switch to Landscape" if mode == "poster" else "📱 Switch to Vertical"
    toggle_callback = "poster_mode_landscape"   if mode == "poster" else "poster_mode_poster"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=toggle_text, callback_data=toggle_callback)],
        nav_row,
        [InlineKeyboardButton(text="❌ Close", callback_data="cancel_poster_flow")],
    ])


@router.message(Command("poster"))
async def poster_cmd_handler(message: Message, state: FSMContext):
    now       = time.time()
    last_used = user_cooldowns.get(message.from_user.id, 0)
    if now - last_used < 5:
        return await message.answer("⏳ Please wait 5 seconds before another search.")
    user_cooldowns[message.from_user.id] = now
    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        await process_poster_search(message, args[1].strip(), state)
    else:
        await state.set_state(PosterStates.waiting_for_movie_name)
        cancel_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_poster_flow")]])
        await message.answer("✍️ <b>Movie, Series ya Anime ka naam likhiye:</b>", parse_mode="HTML", reply_markup=cancel_kb)

@router.message(PosterStates.waiting_for_movie_name, F.text)
async def poster_fsm_text_handler(message: Message, state: FSMContext):
    await process_poster_search(message, message.text.strip(), state)


async def process_poster_search(message: Message, query: str, state: FSMContext):
    status_msg = await message.answer("🔍 <b>Multiple poster engines se best result nikaale ja rahe hain...</b>", parse_mode="HTML")
    await state.clear()

    results = await fetch_all_hybrid_posters(query)

    if not results:
        local_suggestions = await find_local_suggestions(query)
        if local_suggestions:
            buttons = [[InlineKeyboardButton(text=f"📌 {item.upper()}", callback_data=f"search_fuzzy_{item}")] for item in local_suggestions]
            buttons.append([InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_poster_flow")])
            return await status_msg.edit_text("❌ <b>Poster nahi mila!</b>\n\n🤔 <b>Kya aap ye dhundh rahe the?</b>",
                                              parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        return await status_msg.edit_text("❌ <b>Kisi bhi source se poster nahi mila!</b>\n\nSpelling check karke dobara try karein.", parse_mode="HTML")

    await state.update_data(poster_results=results, current_page=0, view_mode="poster", search_backup_query=query)

    first_item   = results[0]
    caption_text = (
        f"🎬 <b>{first_item['title'].upper()}</b>\n"
        f"📅 {first_item['year']}  {first_item['type']}\n"
        f"🗂️ <i>{first_item['source']}</i>  •  📊 <i>{len(results)} results</i>"
    )
    if first_item.get("match_score"):
        caption_text += f"\n🎯 Match: <b>{int(first_item['match_score'])}%</b>"
    if first_item.get("season"):
        caption_text += f"\n📺 <b>{str(first_item['season']).upper()}</b>"

    try:
        await status_msg.delete()
        await message.answer_photo(photo=first_item["poster"], caption=caption_text,
                                   parse_mode="HTML", reply_markup=get_poster_keyboard(0, len(results), "poster"))
    except Exception as e:
        print(f"Photo send error: {e}")
        await message.answer(f"❌ Image load nahi hui.\n🔗 Link: <code>{first_item['poster']}</code>", parse_mode="HTML")


@router.callback_query(F.data.startswith("poster_page_") | F.data.startswith("poster_mode_"))
async def poster_carousel_callbacks(callback: CallbackQuery, state: FSMContext):
    user_data    = await state.get_data()
    results      = user_data.get("poster_results", [])
    current_page = user_data.get("current_page", 0)
    mode         = user_data.get("view_mode", "poster")
    backup_q     = user_data.get("search_backup_query", "Movie")

    if not results:
        retry_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Search Again", callback_data=f"search_fuzzy_{backup_q}")],
            [InlineKeyboardButton(text="❌ Dismiss",      callback_data="cancel_poster_flow")]
        ])
        return await callback.message.edit_caption(caption="<b>⚠️ Session Expired!</b>\n\nRefresh karein.",
                                                   reply_markup=retry_kb, parse_mode="HTML")

    if callback.data.startswith("poster_page_"):
        current_page = int(callback.data.split("poster_page_")[1])
    elif callback.data.startswith("poster_mode_"):
        mode = callback.data.split("poster_mode_")[1]

    current_page = max(0, min(current_page, len(results) - 1))
    await state.update_data(current_page=current_page, view_mode=mode)

    item             = results[current_page]
    active_photo_url = item["landscape"] if mode == "landscape" else item["poster"]
    caption_text     = (
        f"🎬 <b>{item['title'].upper()}</b>\n"
        f"📅 {item['year']}  {item['type']}\n"
        f"🗂️ <i>{item['source']}</i>  •  📊 <i>{len(results)} results</i>"
    )
    if item.get("match_score"):
        caption_text += f"\n🎯 Match: <b>{int(item['match_score'])}%</b>"
    if item.get("season"):
        caption_text += f"\n📺 <b>{str(item['season']).upper()}</b>"

    try:
        await callback.message.edit_media(
            media=types.InputMediaPhoto(media=active_photo_url, caption=caption_text, parse_mode="HTML"),
            reply_markup=get_poster_keyboard(current_page, len(results), mode)
        )
        database = get_db_instance()
        if database is not None:
            try:
                await database.cached_posters.update_one(
                    {"title": item["title"].lower()},
                    {"$set": {"title": item["title"], "poster": item["poster"], "year": item["year"], "type": "HYBRID_CACHE"}},
                    upsert=True
                )
            except Exception: pass
    except Exception as e:
        print(f"Carousel Error: {e}")
        await callback.answer("❌ Error loading poster!", show_alert=True)
        return
    await callback.answer()


# ✅ FIX: ignore_click → poster_count_info — Telegram spinner forever issue fixed
@router.callback_query(F.data == "poster_count_info")
async def poster_count_info_cb(callback: CallbackQuery):
    await callback.answer("📊 Total results counter", show_alert=False)


@router.callback_query(F.data.startswith("search_fuzzy_"))
async def search_fuzzy_callback(callback: CallbackQuery, state: FSMContext):
    chosen_movie = callback.data.split("search_fuzzy_")[1]
    try: await callback.message.edit_text(f"🔄 Re-searching: <b>{chosen_movie.upper()}</b>...", parse_mode="HTML")
    except Exception:
        try: await callback.message.edit_caption(caption=f"🔄 Re-searching: {chosen_movie.upper()}...")
        except Exception: pass
    await process_poster_search(callback.message, chosen_movie, state)
    await callback.answer()


@router.callback_query(F.data == "cancel_poster_flow")
async def cancel_poster_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try: await callback.message.delete()
    except Exception:
        try: await callback.message.edit_text("❌ Search closed.")
        except Exception: pass
    await callback.answer("Closed!")
