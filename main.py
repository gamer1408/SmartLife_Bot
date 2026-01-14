import asyncio
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from config import BOT_TOKEN
import processor
import google_service
from database import init_db, save_idea, get_all_ideas
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
USER_ID = "6150118850"
sent_reminders = set()

# 1. Bot ishga tushganda bazani tayyorlash
init_db()

# 2. START buyrug'i (Eng tepada bo'lishi shart)
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Assalomu alaykum! Men aqlli yordamchiman.\n\n"
                         "✍️ Vazifa qo'shish: `vazifa: Nom, YYYY-MM-DD, HH:MM`\n"
                         "💡 G'oya qo'shish: Shunchaki matn yozing\n"
                         "📂 G'oyalarni ko'rish: /ideas")

@dp.message(Command("list"))
async def cmd_list(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="Bugun", callback_data="list_today"))
    builder.row(types.InlineKeyboardButton(text="Ertaga", callback_data="list_tomorrow"))
    builder.row(types.InlineKeyboardButton(text="Indinga", callback_data="list_after"))
    
    await message.answer("🗓 Qaysi kun rejalari kerak?", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("list_"))
async def process_list_callback(callback: types.CallbackQuery):
    today = datetime.now()
    if callback.data == "list_today":
        target, label = today, "Bugun"
    elif callback.data == "list_tomorrow":
        target, label = today + timedelta(days=1), "Ertaga"
    else:
        target, label = today + timedelta(days=2), "Indinga"
        
    date_str = target.strftime("%Y-%m-%d")
    events = google_service.get_events_for_date(date_str)
    
    builder = InlineKeyboardBuilder()
    
    if not events:
        builder.row(types.InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_list"))
        await callback.message.edit_text(f"📅 {label} ({date_str}) uchun reja yo'q.", reply_markup=builder.as_markup())
        return

    # Vazifalarni saralash va matn tayyorlash
    timed_events = []
    all_day_events = []
    
    for event in events:
        summary = event.get('summary', 'Vazifa')
        event_id = event['id']
        start = event['start'].get('dateTime', event['start'].get('date'))
        
        # Ro'yxat uchun matn yig'ish
        if 'T' in start:
            time_part = start.split('T')[1][:5]
            timed_events.append(f"🕒 {time_part} — {summary}")
        else:
            all_day_events.append(f"📋 {summary}")
        
        # Har bir vazifa uchun O'CHIRISH tugmasini qo'shish
        builder.row(types.InlineKeyboardButton(
            text=f"❌ {summary[:20]}...", 
            callback_data=f"del_{event_id}")
        )

    # Yakuniy xabarni shakllantirish
    res = f"📅 **{label} ({date_str}) rejalari:**\n\n"
    if timed_events:
        res += "⌛ **Vaqtli vazifalar:**\n" + "\n".join(timed_events) + "\n\n"
    if all_day_events:
        res += "📌 **Kunlik missiyalar:**\n" + "\n".join(all_day_events)

    builder.row(types.InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_list"))
    
    # MUHIM: Faqat bir marta edit_text qilamiz va tugmalarni (reply_markup) ham qo'shamiz
    await callback.message.edit_text(res, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await callback.answer()

# 3. Orqaga qaytish tugmasi
@dp.callback_query(F.data == "back_to_list")
async def back_to_list_menu(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="Bugun", callback_data="list_today"))
    builder.row(types.InlineKeyboardButton(text="Ertaga", callback_data="list_tomorrow"))
    builder.row(types.InlineKeyboardButton(text="Indinga", callback_data="list_after"))
    await callback.message.edit_text("🗓 Qaysi kun rejalari kerak?", reply_markup=builder.as_markup())
    await callback.answer()

async def check_calendar_reminders():
    global sent_reminders
    events = google_service.get_upcoming_events()
    
    now = datetime.now()
    
    for event in events:
        event_id = event['id']
        summary = event.get('summary')
        start_str = event['start'].get('dateTime', event['start'].get('date'))
        
        # Google vaqtini Python vaqtiga o'tkazish
        # Misol: 2026-01-10T22:30:00+05:00 -> datetime obyekti
        start_dt = datetime.fromisoformat(start_str.replace('Z', '+00:00')).replace(tzinfo=None)
        
        # Agar vazifaga 2 daqiqadan kam vaqt qolgan bo'lsa VA hali xabar yuborilmagan bo'lsa
        diff = (start_dt - now).total_seconds() / 60
        
        if 0 <= diff <= 5: # 5 daqiqa qolganda eslatish
            if event_id not in sent_reminders:
                await bot.send_message(USER_ID, f"⏰ **ESLATMA:**\n\n📌 {summary}\n🕒 Yaqin qoldi!")
                sent_reminders.add(event_id)
                
    # Eskirgan ID larni tozalash (xotira to'lib ketmasligi uchun)
    if len(sent_reminders) > 100:
        sent_reminders.clear()

@dp.callback_query(F.data.startswith("del_"))
async def delete_event_handler(callback: types.CallbackQuery):
    # Callback data format: del_eventid_daytype (masalan: del_123_today)
    parts = callback.data.split("_")
    event_id = parts[1]
    
    # 1. Google Calendar'dan o'chirish
    try:
        google_service.delete_event(event_id)
        await callback.answer("✅ Vazifa o'chirildi", show_alert=False)
        
        # 2. Ro'yxatni yangilash uchun foydalanuvchini asosiy menyuga qaytaramiz
        # Bu eng xavfsiz yo'l, chunki ro'yxat keshdan emas, qaytadan olinadi
        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text="Bugun", callback_data="list_today"))
        builder.row(types.InlineKeyboardButton(text="Ertaga", callback_data="list_tomorrow"))
        builder.row(types.InlineKeyboardButton(text="Indinga", callback_data="list_after"))
        
        await callback.message.edit_text(
            "🗑 Vazifa o'chirildi! Yangi ro'yxatni ko'rish uchun kunni tanlang:", 
            reply_markup=builder.as_markup()
        )
        
    except Exception as e:
        print(f"Delete Error: {e}")
        await callback.answer("❌ O'chirishda xatolik yuz berdi", show_alert=True)

# 3. IDEAS buyrug'i (Matndan tepada bo'lishi shart)
@dp.message(Command("ideas"))
async def show_ideas(message: types.Message):
    ideas = get_all_ideas()
    if not ideas:
        await message.answer("Hozircha g'oyalar yo'q.")
        return
    
    response = "📝 **Sizning g'oyalaringiz:**\n\n"
    for i, (content, cat) in enumerate(ideas, 1):
        # Buyruqlarni bazadan chiqarib tashlash (agar adashib tushgan bo'lsa)
        if content.startswith('/'): continue
        response += f"{i}. {content} (_{cat}_)\n"
    await message.answer(response, parse_mode="Markdown")
    
@dp.message(Command("ideas"))
async def list_ideas(message: types.Message):
    from database import get_ideas
    ideas = get_ideas()
    
    if not ideas:
        await message.answer("💡 Hozircha g'oyalar bazasi bo'sh.")
        return

    builder = InlineKeyboardBuilder()
    res = "💡 **Sizning barcha g'oyalaringiz:**\n\n"
    
    for idea in ideas:
        # Bazadan kelgan tartib: 0:id, 1:content, 2:category, 3:date
        idea_id = idea[0]
        content = idea[1]
        category = idea[2]
        
        # Ro'yxat matni (G'oyani to'liq ko'rsatamiz)
        res += f"📌 **{category}**: {content}\n\n"
        
        # Har bir g'oya uchun o'chirish tugmasi
        builder.row(types.InlineKeyboardButton(
            text=f"🗑 O'chirish: {content[:15]}...", 
            callback_data=f"delidea_{idea_id}")
        )
    
    # DIQQAT: reply_markup tugmalarni Telegramga yuboradi
    await message.answer(res, reply_markup=builder.as_markup(), parse_mode="Markdown")


@dp.callback_query(F.data.startswith("delidea_"))
async def process_delete_idea(callback: types.CallbackQuery):
    idea_id = callback.data.split("_")[1]
    
    try:
        from database import delete_idea
        delete_idea(idea_id) # Bazadan o'chiradi
        
        await callback.answer("✅ G'oya o'chirildi")
        
        # Xabarni yangilab qo'yamiz
        await callback.message.edit_text(
            "🗑 G'oya o'chirildi! Yangilangan ro'yxatni ko'rish uchun qaytadan /ideas yozing."
        )
    except Exception as e:
        print(f"O'chirishda xato: {e}")
        await callback.answer("❌ O'chirishda xatolik yuz berdi")

# 4. Ovozli xabarlar
@dp.message(F.voice)
async def handle_voice(message: types.Message):
    # 1. Status xabari
    status_msg = await message.answer("🎤 Ovoz eshitilmoqda...")
    
    file_id = message.voice.file_id
    file = await bot.get_file(file_id)
    file_path = f"{file_id}.ogg"
    
    try:
        # 2. Faylni yuklab olish
        await bot.download_file(file.file_path, file_path)
        
        # 3. Ovozni matnga o'girish (TEXT o'zgaruvchisi shu yerda yaratiladi)
        await status_msg.edit_text("✍️ Matnga o'girilmoqda...")
        text = processor.transcribe_voice(file_path) # <--- MUHIM
        
        # 4. AI orqali tahlil qilish
        await status_msg.edit_text("🧠 Tahlil qilinmoqda...")
        result = processor.process_text_with_ai(text)
        
        # 5. Vaqtni aniqlashtirish tekshiruvi
        if result['type'] == 'task' and result['time'] == "NEED_CLARIFICATION":
            await status_msg.edit_text(
                f"🧐 Vazifani tushundim: **{result['content']}**\n\n"
                "Lekin soat nechaligini bilolmadim. Iltimos, vaqtini ayta olasizmi?"
            )
            return

        # 6. Vazifa yoki G'oya sifatida saqlash
        if result['type'] == 'task':
            google_service.add_event(result['content'], result['date'], result['time'])
            await status_msg.edit_text(f"✅ Vazifa qo'shildi:\n📌 {result['content']}\n🕒 {result['date']} | {result['time']}")
        else:
            from database import save_idea
            save_idea(result['content'], result['category'])
            await status_msg.edit_text(f"💡 G'oya saqlandi:\n📌 {result['content']}")

    except Exception as e:
        print(f"Ovozli xabar xatosi: {e}")
        await status_msg.edit_text("❌ Kechirasiz, ovozni qayta ishlashda xatolik yuz berdi.")
    
    finally:
        # Faylni o'chirish
        if os.path.exists(file_path):
            os.remove(file_path)    # 1. Yuklanayotganini bildirish
    status_msg = await message.answer("🎤 Ovozli xabar eshitilmoqda...")
    result = processor.process_text_with_ai(text)
    # 2. Ovozli faylni yuklab olish
    file_id = message.voice.file_id
    file = await bot.get_file(file_id)
    file_path = f"{file_id}.ogg"
    await bot.download_file(file.file_path, file_path)

    if result['type'] == 'task':
            if result['time'] == "NEED_CLARIFICATION":
                await status_msg.edit_text(
                    f"🧐 Vazifani tushundim: **{result['content']}**\n\n"
                    "Lekin soat nechaligini anglay olmadim. Iltimos, vaqtini aniqroq ayta olasizmi? "
                    "(Masalan: 'soat 10 da' yoki 'kechki 7 da')"
                )
                return # Calendar-ga qo'shmasdan to'xtatamiz
            
            # Agar hammasi aniq bo'lsa qo'shish
            google_service.add_event(result['content'], result['date'], result['time'])
            await status_msg.edit_text(
                f"✅ Vazifa qo'shildi:\n📌 {result['content']}\n"
                f"📅 {result['date']} | ⏰ {result['time']}"
            )
    
    try:
        # 3. Groq orqali ovozni matnga o'girish (Whisper)
        await status_msg.edit_text("✍️ Matnga o'girilmoqda...")
        text = processor.transcribe_voice(file_path)
        
        # 4. Groq orqali matnni tahlil qilish (Llama)
        await status_msg.edit_text("🧠 Tahlil qilinmoqda...")
        result = processor.process_text_with_ai(text)
        
        # 5. Natijaga qarab ish tutish
        if result['type'] == 'task':
            google_service.add_event(result['content'], result['date'], result['time'])
            await status_msg.edit_text(
                f"✅ Ovozli vazifa qo'shildi:\n📌 {result['content']}\n"
                f"📅 {result['date']} | ⏰ {result['time']}"
            )
        else:
            from database import save_idea
            save_idea(result['content'], result['category'])
            await status_msg.edit_text(f"💡 G'oya saqlandi:\n📌 {result['content']}")
            
    except Exception as e:
        await status_msg.edit_text(f"❌ Kechirasiz, tushunolmadim: {e}")
    finally:
        # Vaqtinchalik faylni o'chirish
        if os.path.exists(file_path):
            os.remove(file_path)    # Ovozli xabar mantiqi shu yerda qoladi...
    # Hozircha OpenAI puli yo'qligi uchun xato berishi mumkin
    await message.answer("Ovozli xizmat ertaga (to'lovdan so'ng) ishga tushadi.")

# 5. MATNLI xabarlar (Eng pastda bo'lishi shart!)
@dp.message(F.text & ~F.command)
async def handle_text(message: types.Message):
    user_input = message.text 
    
    try:
        result = processor.process_text_with_ai(user_input)
        
        if result.get('type') == 'task':
            content = result.get('content')
            date_val = result.get('date')
            time_val = result.get('time')
            desc = result.get('description', "")

            # Endi 4 ta argument yuboramiz, google_service uni qabul qiladi
            google_service.add_event(content, date_val, time_val, desc)
            
            # Xabarni chiroyli chiqarish
            time_msg = f"⏰ {time_val}" if time_val and time_val != "null" else "📅 Kun bo'yi (Missiya)"
            desc_msg = f"\n📝 Tavsif: {desc}" if desc else ""
            
            await message.answer(
                f"✅ Vazifa qo'shildi:\n📌 {content}\n"
                f"🕒 {date_val} | {time_msg}{desc_msg}"
            )
        else:
            from database import save_idea
            save_idea(result['content'], result.get('category', 'General'))
            await message.answer(f"💡 G'oya saqlandi:\n📌 {result['content']}")

    except Exception as e:
        print(f"Xato: {e}")
        await message.answer("❌ Xabarni tahlil qilishda xatolik yuz berdi.")



async def main():
    scheduler = AsyncIOScheduler()
    # Har 1 daqiqada tekshirish
    scheduler.add_job(check_calendar_reminders, 'interval', minutes=1)
    scheduler.start()
    
    print("Bot va Eslatmalar ishga tushdi...")
    await dp.start_polling(bot)
    try:
        print("Bot ishga tushdi...")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())