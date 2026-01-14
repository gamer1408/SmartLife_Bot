import asyncio
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from config import BOT_TOKEN
import processor
import google_service
from database import init_db, save_idea, get_ideas, delete_idea
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
    welcome_text = (
        "🌟 **Aqlli hayot yordamchisiga xush kelibsiz!**\n\n"
        "Men sizga vaqtingizni unumli boshqarish va g'oyalaringizni tartibga solishda yordam beraman.\n\n"
        "🚀 **Imkoniyatlarim:**\n"
        "1️⃣ **Vazifalar:** Shunchaki 'Ertaga 10:00da uchrashuv' deb yozing yoki ovozli xabar yuboring. Men uni Google Calendar-ga qo'shaman.\n"
        "2️⃣ **Missiyalar:** Vaqtini aytmasangiz, men uni 'Kunlik missiya' sifatida belgilayman.\n"
        "3️⃣ **G'oyalar:** Shunchaki fikrlaringizni yozing, men ularni bazaga saqlayman.\n\n"
        "🛠 **Asosiy buyruqlar:**\n"
        "📅 /list — Kelgusi 15 kunlik rejalarni ko'rish\n"
        "💡 /ideas — Barcha saqlangan g'oyalar ro'yxati\n\n"
        "Sizga qanday yordam bera olaman?"
    )
    await message.answer(welcome_text, parse_mode="Markdown")


async def cmd_list(message: types.Message):
    builder = InlineKeyboardBuilder()
    now = datetime.now()
    
    # Bugundan boshlab kelgusi 15 kun uchun tugmalar
    for i in range(15):
        day = now + timedelta(days=i)
        date_str = day.strftime("%Y-%m-%d")
        
        # Tugma yorlig'ini chiroyli qilish
        if i == 0: label = "Bugun"
        elif i == 1: label = "Ertaga"
        else: label = day.strftime("%d-%b") # Masalan: 15-Jan
        
        builder.button(text=f"📅 {label}", callback_data=f"list_{date_str}")
    
    builder.adjust(3) # Tugmalarni 3 qatordan terish
    await message.answer("🗓 Qaysi kun rejalarini ko'rmoqchisiz?", reply_markup=builder.as_markup())


# 1. Vazifalar va Missiyalarni ajratilgan bitta hisobotda ko'rsatish
@dp.callback_query(F.data.startswith("list_"))
async def process_list_callback(callback: types.CallbackQuery):
    date_str = callback.data.split("_")[1]
    events = google_service.get_events_for_date(date_str)
    
    builder = InlineKeyboardBuilder()
    
    if not events:
        builder.row(types.InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_list"))
        await callback.message.edit_text(f"📅 {date_str} kuni uchun reja yo'q.", reply_markup=builder.as_markup())
        return

    timed_tasks = []    
    daily_missions = [] 
    
    for event in events:
        summary = event.get('summary', 'Vazifa')
        event_id = event['id']
        start_node = event.get('start', {})
        
        # O'chirish tugmasi
        builder.row(types.InlineKeyboardButton(
            text=f"❌ {summary[:20]}...", 
            callback_data=f"del_{event_id}_{date_str}")
        )
        
        # dateTime bo'lsa - VAQTLI, faqat date bo'lsa - KUNLIK MISSIA
        if 'dateTime' in start_node:
            time_part = start_node['dateTime'].split('T')[1][:5] 
            timed_tasks.append(f"🕒 {time_part} — {summary}")
        else:
            daily_missions.append(f"📌 {summary}")

    # Yagona hisobot (Report)
    res = f"📅 **{date_str} hisoboti:**\n\n"
    res += "⌛ **VAQTLI VAZIFALAR:**\n" + ("\n".join(timed_tasks) if timed_tasks else "(Bo'sh)") + "\n\n"
    res += "📋 **KUNLIK MISSIYALAR:**\n" + ("\n".join(daily_missions) if daily_missions else "(Bo'sh)")

    builder.row(types.InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_list"))
    await callback.message.edit_text(res, reply_markup=builder.as_markup(), parse_mode="Markdown")

# 2. Vazifa o'chirilgandan so'ng darhol o'sha kunni refresh qilish
@dp.callback_query(F.data.startswith("del_"))
async def delete_event_handler(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    event_id = parts[1]
    current_date = parts[2] # Sanani saqlab qolamiz
    
    try:
        google_service.delete_event(event_id)
        await callback.answer("✅ Vazifa muvaffaqiyatli o'chirildi")
        
        # Eski menyuga qaytmasdan, o'sha kunning ro'yxatini qayta yuklaymiz
        callback.data = f"list_{current_date}"
        await process_list_callback(callback)
        
    except Exception as e:
        print(f"O'chirish xatosi: {e}")
        await callback.answer("❌ O'chirishda xato yuz berdi", show_alert=True)

@dp.callback_query(F.data == "back_to_list")
async def back_to_list_menu(callback: types.CallbackQuery):
    # cmd_list funksiyasidagi mantiqni edit_text orqali qaytaramiz
    builder = InlineKeyboardBuilder()
    now = datetime.now()
    for i in range(15):
        day = now + timedelta(days=i)
        date_str = day.strftime("%Y-%m-%d")
        label = "Bugun" if i == 0 else "Ertaga" if i == 1 else day.strftime("%d-%b")
        builder.button(text=f"📅 {label}", callback_data=f"list_{date_str}")
    
    builder.adjust(3)
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
    # 1. Yuklanayotganini bildirish uchun status xabari
    status_msg = await message.answer("🎤 Ovozli xabar qabul qilindi...")
    
    file_id = message.voice.file_id
    file = await bot.get_file(file_id)
    file_path = f"{file_id}.ogg"
    
    try:
        # 2. Ovozli faylni yuklab olish
        await bot.download_file(file.file_path, file_path)
        
        # 3. Groq Whisper orqali ovozni matnga o'girish
        await status_msg.edit_text("✍️ Matnga o'girilmoqda...")
        text = processor.transcribe_voice(file_path)
        
        if not text:
            await status_msg.edit_text("❌ Ovozdan matn ajratib bo'lmadi.")
            return

        # 4. AI orqali matnni tahlil qilish
        await status_msg.edit_text("🧠 Tahlil qilinmoqda...")
        result = processor.process_text_with_ai(text)
        
        # 5. Natijaga qarab ish tutish (Vazifa yoki G'oya)
        if result.get('type') == 'task':
            content = result.get('content')
            date_val = result.get('date')
            time_val = result.get('time')
            description = result.get('description', "")

            # Vaqtni aniqlashtirish kerakmi?
            if time_val == "NEED_CLARIFICATION":
                await status_msg.edit_text(
                    f"🧐 Vazifani tushundim: **{content}**\n\n"
                    "Lekin soat nechaligini anglay olmadim. Iltimos, vaqtini yozib yuboring."
                )
                return

            # Google Calendar-ga qo'shish
            google_service.add_event(content, date_val, time_val, description)
            
            time_display = f"⏰ {time_val}" if time_val and time_val != "null" else "📅 Kun bo'yi"
            await status_msg.edit_text(
                f"✅ Ovozli vazifa qo'shildi:\n📌 {content}\n"
                f"🕒 {date_val} | {time_display}"
            )
        
        else:
            # G'oya sifatida saqlash
            from database import save_idea
            save_idea(result['content'], result.get('category', 'General'))
            await status_msg.edit_text(f"💡 G'oya saqlandi:\n📌 {result['content']}")
            
    except Exception as e:
        print(f"Ovozli xabar xatosi: {e}")
        await status_msg.edit_text(f"❌ Xatolik yuz berdi: {e}")
        
    finally:
        # Vaqtinchalik faylni o'chirish
        if os.path.exists(file_path):
            os.remove(file_path)
# 5. MATNLI xabarlar (Eng pastda bo'lishi shart!)
@dp.message(F.text & ~F.command)
async def handle_text(message: types.Message):
    user_input = message.text 
    
    try:
        # AI tahlili
        result = processor.process_text_with_ai(user_input)
        
        # 1. Vazifa (task) bo'lsa
        if result.get('type') == 'task':
            content = result.get('content')
            date_val = result.get('date')
            time_val = result.get('time')
            desc = result.get('description', "")

            # Google Calendar-ga yuborish
            google_service.add_event(content, date_val, time_val, desc)
            
            time_msg = f"⏰ {time_val}" if time_val and time_val != "null" else "📅 Kun bo'yi"
            await message.answer(
                f"✅ Vazifa qo'shildi:\n📌 {content}\n🕒 {date_val} | {time_msg}"
            )
            
        # 2. G'oya (idea) bo'lsa
        elif result.get('type') == 'idea':
            from database import save_idea
            # G'oya matnini to'liq saqlash
            save_idea(result['content'], result.get('category', 'General'))
            await message.answer(f"💡 G'oya saqlandi:\n📌 {result['content']}")

    except Exception as e:
        print(f"Xato: {e}")
        await message.answer("❌ Xatolik yuz berdi. Qayta urinib ko'ring.")


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