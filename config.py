from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from datetime import datetime, timedelta
import asyncio
import pytz

API_ID = 123456  # Ganti
API_HASH = "abc123"  # Ganti
BOT_TOKEN = "123456:ABCDEF"  # Ganti

app = Client("absen_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

absensi_data = {}  # Format: {chat_id: {"users": set(), "pesan_id": int, "timezone": "Asia/Jakarta"}}


# ✨ Admin-only check
async def is_admin(client, chat_id, user_id):
    member = await client.get_chat_member(chat_id, user_id)
    return member.status in ["administrator", "creator"]


# ⏰ Background task: reset tiap jam 00:00
async def reset_absen_tiap_hari():
    while True:
        now = datetime.now()
        target = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        tunggu = (target - now).total_seconds()
        await asyncio.sleep(tunggu)

        for chat_id in absensi_data:
            absensi_data[chat_id]["users"].clear()


@app.on_message(filters.command("mulai", prefixes="/") & filters.group)
async def mulai_absen(client, message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    group_name = message.chat.title

    if not await is_admin(client, chat_id, user_id):
        await message.reply("Perintah ini hanya bisa digunakan oleh admin.")
        return

    # Ambil zona waktu dari argumen
    try:
        zone_arg = message.text.split(" ")[1].lower()
        zones = {
            "wib": "Asia/Jakarta",
            "wita": "Asia/Makassar",
            "wit": "Asia/Jayapura"
        }
        if zone_arg not in zones:
            raise Exception()
        timezone_str = zones[zone_arg]
    except:
        await message.reply("Contoh penggunaan: `/mulai wib` atau `/mulai wita` atau `/mulai wit`", parse_mode="markdown")
        return

    waktu = datetime.now(pytz.timezone(timezone_str))
    tanggal = waktu.strftime("%A, tanggal %d %B %Y")

    absensi_data[chat_id] = {
        "users": set(),
        "pesan_id": None,
        "timezone": timezone_str
    }

    teks = (
        f"*{group_name}*\n"
        f"Daftar hadir hari *{tanggal}*.\n\n"
        f"Waktu dalam timezone {zone_arg.upper()}.\n"
        "Yang telah hadir, silakan klik tombol HADIR di bawah ini."
    )

    tombol = InlineKeyboardMarkup(
        [[InlineKeyboardButton("✅ Hadir", callback_data=f"hadir_{chat_id}")]]
    )

    sent = await message.reply_text(teks, reply_markup=tombol, parse_mode="markdown")
    absensi_data[chat_id]["pesan_id"] = sent.message_id


@app.on_callback_query(filters.regex(r"^hadir_(\-\d+)$"))
async def absen_callback(client, callback: CallbackQuery):
    chat_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    nama = callback.from_user.first_name

    if chat_id not in absensi_data:
        await callback.answer("Sesi absen belum dimulai.", show_alert=True)
        return

    users = absensi_data[chat_id]["users"]
    if user_id in users:
        await callback.answer("Kamu sudah absen hari ini 😄", show_alert=True)
        return

    users.add(user_id)

    daftar_nama = ""
    for i, uid in enumerate(users, start=1):
        try:
            user = await client.get_users(uid)
            daftar_nama += f"{i}. [{user.first_name}](tg://user?id={user.id})\n"
        except:
            daftar_nama += f"{i}. User ID {uid}\n"

    zone_name = absensi_data[chat_id]["timezone"]
    waktu = datetime.now(pytz.timezone(zone_name))
    tanggal = waktu.strftime("%A, %d %B %Y")
    zone_label = zone_name.split("/")[-1].upper().replace("JAYAPURA", "WIT").replace("MAKASSAR", "WITA").replace("JAKARTA", "WIB")

    teks_baru = (
        f"*{callback.message.chat.title}*\n"
        f"Daftar hadir hari *{tanggal}*.\n\n"
        f"{daftar_nama}\n"
        f"Waktu dalam timezone {zone_label}.\n"
        "Yang telah hadir, silakan klik tombol HADIR di bawah ini."
    )

    await callback.message.edit_text(teks_baru, reply_markup=callback.message.reply_markup, parse_mode="markdown")
    await callback.answer("✅ Kamu sudah tercatat hadir!")


# Jalankan reset otomatis
@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply("Bot absensi siap digunakan!")


# Mulai bot + task background
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(reset_absen_tiap_hari())
    app.run()
