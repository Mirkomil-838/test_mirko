import os
import random
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler
from database import DatabaseManager
from file_parser import FileParser

logger = logging.getLogger(__name__)

class UserHandlers:
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.file_parser = FileParser()
        self.questions_cache = {}
    
    async def user_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Foydalanuvchi uchun start handler"""
        try:
            user_id = update.message.from_user.id
            user_name = update.message.from_user.first_name
            
            keyboard = [
                [InlineKeyboardButton("🎯 Test ishlash", callback_data="user_start_test")]
            ]
            text = f"Assalomu alaykum, {user_name}! Test botiga xush kelibsiz! 🎓\n\nQuyidagi tugmalardan foydalanishingiz mumkin:"
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(text, reply_markup=reply_markup)
            
            logger.info(f"User {user_id} started the bot")
            
        except Exception as e:
            logger.error(f"Start command error: {e}")
            await update.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")
    
    async def show_subjects(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mavjud fanlarni ko'rsatish"""
        try:
            query = update.callback_query
            await query.answer()
            
            subjects = self.db.get_subjects()
            
            if not subjects:
                keyboard = [[InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    "❌ Hozircha hech qanday fan mavjud emas.\n\nAdmin tomonidan fan qo'shilishini kuting.",
                    reply_markup=reply_markup
                )
                return
            
            keyboard = []
            for subject_id, subject_name in subjects:
                keyboard.append([InlineKeyboardButton(subject_name, callback_data=f"subject_{subject_id}")])
            
            keyboard.append([InlineKeyboardButton("🔙 Bosh menyu", callback_data="main_menu")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "📚 Mavjud fanlar:\n\nQuyidagi fanlardan birini tanlang:",
                reply_markup=reply_markup
            )
            
            logger.info(f"User {query.from_user.id} viewed subjects list")
            
        except Exception as e:
            logger.error(f"Show subjects error: {e}")
            await update.callback_query.edit_message_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")
    
    async def handle_subject_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Fanni tanlash"""
        try:
            query = update.callback_query
            await query.answer()
            
            user_id = query.from_user.id
            subject_id = int(query.data.split('_')[1])
            
            context.user_data['selected_subject_id'] = subject_id
            
            # Test sonini so'rash
            keyboard = [
                [InlineKeyboardButton("10 ta", callback_data=f"count_10_{subject_id}")],
                [InlineKeyboardButton("20 ta", callback_data=f"count_20_{subject_id}")],
                [InlineKeyboardButton("30 ta", callback_data=f"count_30_{subject_id}")],
                [InlineKeyboardButton("40 ta", callback_data=f"count_40_{subject_id}")],
                [InlineKeyboardButton("60 ta", callback_data=f"count_60_{subject_id}")],
                [InlineKeyboardButton("Hammasi", callback_data=f"count_all_{subject_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            subject_name = self.db.get_subject_file(subject_id)[0]
            await query.edit_message_text(
                f"📖 Tanlangan fan: {subject_name}\n\n"
                f"🔢 Nechta test ishlamoqchisiz?\n\n"
                f"ℹ️ Eslatma: Agar faylda kamroq savol bo'lsa, mavjud savollar soni ko'rsatiladi.",
                reply_markup=reply_markup
            )
            
            logger.info(f"User {user_id} selected subject {subject_id}")
            
        except Exception as e:
            logger.error(f"Subject selection error: {e}")
            await update.callback_query.edit_message_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")
    
    async def handle_question_count(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Testlar sonini tanlash"""
        try:
            query = update.callback_query
            await query.answer()
            
            user_id = query.from_user.id
            data_parts = query.data.split('_')
            count_type = data_parts[1]
            subject_id = int(data_parts[2])
            
            subject_name, file_path = self.db.get_subject_file(subject_id)
            
            # Fayl mavjudligini tekshirish
            if not os.path.exists(file_path):
                await query.edit_message_text(
                    f"❌ Fayl topilmadi: {file_path}\n\n"
                    f"Iltimos, admin bilan bog'laning."
                )
                return
            
            # Savollarni yuklash
            if subject_id in self.questions_cache:
                all_questions = self.questions_cache[subject_id]
            else:
                # Birinchi oddiy usul
                all_questions = self.file_parser.parse_file(file_path)
                
                # Agar savol topilmasa, tahlil qilish
                if not all_questions:
                    logger.warning(f"Faylda savol topilmadi. Tahlil qilinmoqda: {file_path}")
                    
                    # Kengaytirilgan usul
                    all_questions = self.file_parser.parse_docx_advanced(file_path)
                
                # Savollarni tekshirish
                all_questions = self.file_parser.validate_questions(all_questions)
                self.questions_cache[subject_id] = all_questions
            
            if not all_questions:
                await query.edit_message_text(
                    "❌ Faylda savollar topilmadi!\n\n"
                    "Iltimos, admin bilan bog'laning."
                )
                return
            
            # Testlar sonini belgilash
            if count_type == 'all':
                questions_count = len(all_questions)
                selected_questions = all_questions
            else:
                questions_count = int(count_type)
                selected_questions = random.sample(all_questions, min(questions_count, len(all_questions)))
            
            # Variantlarni tekshirish va to'g'rilash
            validated_questions = []
            for q in selected_questions:
                if len(q['options']) >= 2:  # Kamida 2 ta variant bo'lishi kerak
                    # Variantlarni tozalash
                    cleaned_options = []
                    for opt in q['options']:
                        if opt and opt.strip():  # Bo'sh bo'lmagan variantlarni qo'shish
                            cleaned_options.append(opt.strip())
                    
                    if len(cleaned_options) >= 2:
                        q['options'] = cleaned_options
                        validated_questions.append(q)
            
            if not validated_questions:
                await query.edit_message_text("❌ Faylda to'g'ri formatdagi savollar topilmadi!")
                return
            
            # Sessionni boshlash
            session_data = {
                'questions': validated_questions,
                'current_question': 0,
                'answers': [],
                'score': 0,
                'total_questions': len(validated_questions)
            }
            
            self.db.save_user_session(user_id, subject_id, 
                                    session_data['questions'],
                                    session_data['current_question'],
                                    session_data['answers'],
                                    session_data['score'],
                                    session_data['total_questions'])
            
            await query.edit_message_text(
                f"🎯 Test boshlandi!\n\n"
                f"📖 Fan: {subject_name}\n"
                f"🔢 Savollar: {len(validated_questions)} ta\n\n"
                f"📝 Ko'rsatma:\n"
                f"• Har bir savolga javob bering\n"
                f"• Darhol natija ko'rsatiladi\n"
                f"• Keyingi savolga o'ting\n\n"
                f"🎓 Omad!"
            )
            
            # Birinchi savolni yuborish
            await self.send_question(context, user_id, subject_id)
            
            logger.info(f"User {user_id} started test with {len(validated_questions)} questions")
            
        except Exception as e:
            logger.error(f"Question count selection error: {e}")
            await update.callback_query.edit_message_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")
    
    async def send_question(self, context: ContextTypes.DEFAULT_TYPE, user_id: int, subject_id: int):
        """Savolni yuborish"""
        try:
            session = self.db.get_user_session(user_id, subject_id)
            if not session:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ Test sessiyasi topilmadi. Iltimos, qaytadan boshlang."
                )
                return
            
            current_q = session['current_question']
            questions = session['questions']
            
            if current_q >= len(questions):
                await self.show_results(context, user_id, subject_id)
                return
            
            question = questions[current_q]
            
            # Variantlarni aralashtirish (lekin to'g'ri javobni saqlab qolish)
            options = question['options'].copy()
            
            # Variantlarni aralashtirish
            shuffled_indices = list(range(len(options)))
            random.shuffle(shuffled_indices)
            
            shuffled_options = [options[i] for i in shuffled_indices]
            new_correct_index = shuffled_indices.index(question['correct_answer'])
            
            # Klaviatura yaratish
            keyboard = []
            for i, option in enumerate(shuffled_options):
                # Uzun variantlarni qisqartirish
                display_option = option
                if len(option) > 50:
                    display_option = option[:50] + "..."
                
                keyboard.append([InlineKeyboardButton(
                    f"{chr(65+i)}) {display_option}", 
                    callback_data=f"ans_{subject_id}_{current_q}_{i}_{new_correct_index}"
                )])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Progress
            progress = f"({current_q + 1}/{len(questions)})"
            
            # Savol matnini tayyorlash
            question_text = question['question']
            if len(question_text) > 1000:
                # Uzun savollarni bo'laklab yuborish
                await context.bot.send_message(
                    chat_id=user_id,
                    text=question_text[:1000]
                )
                question_text = question_text[1000:2000] + "..." if len(question_text) > 2000 else question_text[1000:]
            
            await context.bot.send_message(
                chat_id=user_id,
                text=f"❓ Savol {progress}\n\n{question_text}",
                reply_markup=reply_markup
            )
            
            logger.info(f"Sent question {current_q + 1} to user {user_id}")
            
        except Exception as e:
            logger.error(f"Send question error: {e}")
            await context.bot.send_message(
                chat_id=user_id,
                text="❌ Savol yuborishda xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring."
            )
    
    async def handle_answer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Javobni qayta ishlash - real vaqtda natijani ko'rsatish"""
        try:
            query = update.callback_query
            user_id = query.from_user.id
            data_parts = query.data.split('_')
            
            logger.info(f"Answer callback received: {query.data}")
            
            if len(data_parts) < 5:
                await query.answer("Xato: Noto'g'ri format!", show_alert=True)
                return
            
            subject_id = int(data_parts[1])
            question_index = int(data_parts[2])
            selected_option = int(data_parts[3])
            correct_index = int(data_parts[4])
            
            session = self.db.get_user_session(user_id, subject_id)
            if not session:
                await query.edit_message_text("❌ Test sessiyasi topilmadi. Iltimos, qaytadan boshlang.")
                return
            
            # Javobni tekshirish
            is_correct = (selected_option == correct_index)
            
            # Javob ma'lumotlarini saqlash
            question_data = session['questions'][question_index]
            session['answers'].append({
                'question': question_data['question'],
                'selected': selected_option,
                'correct': correct_index,
                'is_correct': is_correct,
                'options': question_data['options']
            })
            
            if is_correct:
                session['score'] += 1
            
            # REAL VAQTDA NATIJANI KO'RSATISH
            current_question = session['current_question']
            total_questions = session['total_questions']
            
            # Variantlarni olish
            options = question_data['options'].copy()
            shuffled_indices = list(range(len(options)))
            random.shuffle(shuffled_indices)
            shuffled_options = [options[i] for i in shuffled_indices]
            
            # Natija xabarini tayyorlash
            if is_correct:
                result_icon = "✅"
                result_text = "**To'g'ri!** 🎉"
            else:
                result_icon = "❌"
                correct_answer_letter = chr(65 + correct_index)  # A, B, C, D
                correct_answer_text = shuffled_options[correct_index]
                result_text = f"**Noto'g'ri!** 😕\n\n**To'g'ri javob:** {correct_answer_letter}) {correct_answer_text}"
            
            # Progress
            progress = f"({current_question + 1}/{total_questions})"
            
            # Yangilangan savol matni
            question_display = f"{result_icon} Savol {progress}\n\n{question_data['question']}\n\n{result_text}"
            
            # Keyingi savol tugmasi
            keyboard = [[InlineKeyboardButton("➡️ Keyingi savol", callback_data=f"next_{subject_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Xabarni yangilash
            await query.edit_message_text(
                text=question_display,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            # Sessionni saqlash
            self.db.save_user_session(user_id, subject_id,
                                    session['questions'],
                                    session['current_question'],
                                    session['answers'],
                                    session['score'],
                                    session['total_questions'])
            
            logger.info(f"User {user_id} answered question {current_question + 1}, correct: {is_correct}")
            
        except Exception as e:
            logger.error(f"Handle answer error: {e}")
            await update.callback_query.answer("Xatolik yuz berdi!", show_alert=True)
    
    async def handle_next_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Keyingi savolga o'tish"""
        try:
            query = update.callback_query
            user_id = query.from_user.id
            
            logger.info(f"Next question callback: {query.data}")
            
            data_parts = query.data.split('_')
            if len(data_parts) < 2:
                await query.answer("Xato: Noto'g'ri format!", show_alert=True)
                return
            
            subject_id = int(data_parts[1])
            
            await query.answer()
            
            # Sessionni olish
            session = self.db.get_user_session(user_id, subject_id)
            if not session:
                await query.edit_message_text("❌ Test sessiyasi topilmadi. Iltimos, qaytadan boshlang.")
                return
            
            # Keyingi savolga o'tish
            session['current_question'] += 1
            
            # Yangilangan sessionni saqlash
            self.db.save_user_session(user_id, subject_id,
                                    session['questions'],
                                    session['current_question'],
                                    session['answers'],
                                    session['score'],
                                    session['total_questions'])
            
            # Keyingi savolni yuborish
            await self.send_question(context, user_id, subject_id)
            
            logger.info(f"User {user_id} moved to question {session['current_question']}")
            
        except Exception as e:
            logger.error(f"Next question error: {e}")
            await update.callback_query.answer("Xatolik yuz berdi!", show_alert=True)
    
    async def show_results(self, context: ContextTypes.DEFAULT_TYPE, user_id: int, subject_id: int):
        """Natijalarni ko'rsatish"""
        try:
            session = self.db.get_user_session(user_id, subject_id)
            if not session:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ Natijalarni ko'rsatishda xatolik yuz berdi."
                )
                return
            
            total = session['total_questions']
            score = session['score']
            percentage = round((score / total) * 100, 1) if total > 0 else 0
            
            subject_name = self.db.get_subject_file(subject_id)[0]
            user = await context.bot.get_chat(user_id)
            user_name = user.first_name
            
            # Natijani bazaga saqlash
            self.db.save_result(user_id, user_name, subject_id, score, total, percentage)
            
            # Natija xabarini tayyorlash
            result_text = f"🏆 TEST YAKUNLANDI!\n\n"
            result_text += f"📖 Fan: {subject_name}\n"
            result_text += f"👤 Ishtirokchi: {user_name}\n"
            result_text += f"📊 Umumiy savollar: {total} ta\n"
            result_text += f"✅ To'g'ri javoblar: {score} ta\n"
            result_text += f"❌ Noto'g'ri javoblar: {total - score} ta\n"
            result_text += f"📈 Foiz: {percentage}%\n\n"
            
            # Baholash
            if percentage >= 90:
                result_text += "🎉 A'lo! Juda zo'r natija! 🎉\nSiz bu fandan yaxshi tayyorgarlikka egasiz!"
            elif percentage >= 75:
                result_text += "👍 Yaxshi! Yaxshi natija! 👏\nYana bir oz mashq qilsangiz, a'lo bo'lasiz!"
            elif percentage >= 60:
                result_text += "👌 Qoniqarli! 💪\nYana mashq qiling va bilimingizni mustahkamlang!"
            elif percentage >= 40:
                result_text += "📚 O'rtacha! ✨\nQaytadan o'rganing va yaxshiroq tayyorlaning!"
            else:
                result_text += "🔰 Boshlang'ich! 📖\nAsosiy tushunchalarni qaytadan o'rganing va mashq qiling!"
            
            result_text += f"\n\n🔄 Yangi test ishlash uchun quyidagi tugmalardan foydalaning:"
            
            keyboard = [
                [InlineKeyboardButton("📚 Boshqa test ishlash", callback_data="user_start_test")],
                [InlineKeyboardButton("🔄 Shu fanda qayta", callback_data=f"subject_{subject_id}")],
                [InlineKeyboardButton("🏠 Bosh menyu", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                chat_id=user_id,
                text=result_text,
                reply_markup=reply_markup
            )
            
            # Sessionni tozalash
            self.db.delete_user_session(user_id, subject_id)
            
            logger.info(f"User {user_id} completed test with score {score}/{total} ({percentage}%)")
            
        except Exception as e:
            logger.error(f"Show results error: {e}")
            await context.bot.send_message(
                chat_id=user_id,
                text="❌ Natijalarni ko'rsatishda xatolik yuz berdi."
            )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Yordam buyrug'i"""
        try:
            help_text = """
🤖 **Test Boti Yordam**

🎯 **Botdan foydalanish:**
1. /start - botni ishga tushirish
2. "Test ishlash" tugmasini bosing
3. Kerakli fanni tanlang
4. Testlar sonini tanlang (10, 20, 30, 40, 60 yoki hammasi)
5. Savollarga javob bering
6. Darhol natijani ko'ring
7. Keyingi savolga o'ting

📝 **Eslatmalar:**
• Har bir savolga javob bergach, natija darhol ko'rsatiladi
• To'g'ri javob: ✅ + "To'g'ri!"
• Noto'g'ri javob: ❌ + to'g'ri javob ko'rsatiladi
• Keyingi savolga o'tish uchun "Keyingi savol" tugmasini bosing

🆘 **Muammolar bo'lsa:**
Agar test ishlashda muammo bo'lsa, /start buyrug'i orqali qaytadan boshlang.
            """
            
            await update.message.reply_text(help_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Help command error: {e}")
            await update.message.reply_text("❌ Yordam xabarini yuborishda xatolik yuz berdi.")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Foydalanuvchi statistikasi"""
        try:
            user_id = update.message.from_user.id
            user_name = update.message.from_user.first_name
            
            stats_text = f"""
📊 **Statistika**

👤 Foydalanuvchi: {user_name}
🆔 ID: {user_id}

📈 Testlar: Tez orada qo'shiladi
🏆 Reyting: Tez orada qo'shiladi

ℹ️ Statistika funksiyalari tez orada qo'shiladi.
            """
            
            await update.message.reply_text(stats_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Stats command error: {e}")
            await update.message.reply_text("❌ Statistika ko'rsatishda xatolik yuz berdi.")
    
    async def cancel_test(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Testni bekor qilish"""
        try:
            user_id = update.message.from_user.id
            
            # Foydalanuvchining barcha aktiv sessionlarini topish
            subjects = self.db.get_subjects()
            cancelled_sessions = 0
            
            for subject_id, subject_name in subjects:
                session = self.db.get_user_session(user_id, subject_id)
                if session:
                    self.db.delete_user_session(user_id, subject_id)
                    cancelled_sessions += 1
            
            if cancelled_sessions > 0:
                await update.message.reply_text(
                    f"✅ {cancelled_sessions} ta aktiv test sessiyasi bekor qilindi.\n\n"
                    f"Endi yangi test ishlashni boshlashingiz mumkin."
                )
            else:
                await update.message.reply_text(
                    "ℹ️ Sizda hozircha aktiv test sessiyalari mavjud emas."
                )
                
        except Exception as e:
            logger.error(f"Cancel test error: {e}")
            await update.message.reply_text("❌ Testni bekor qilishda xatolik yuz berdi.")
    
    async def list_subjects(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Fanlar ro'yxatini ko'rsatish"""
        try:
            subjects = self.db.get_subjects()
            
            if not subjects:
                await update.message.reply_text(
                    "❌ Hozircha hech qanday fan mavjud emas.\n\n"
                    "Admin tomonidan fan qo'shilishini kuting."
                )
                return
            
            subjects_list = "📚 **Mavjud fanlar:**\n\n"
            for i, (subject_id, subject_name) in enumerate(subjects, 1):
                subjects_list += f"{i}. {subject_name}\n"
            
            subjects_list += "\nℹ️ Test ishlash uchun /start buyrug'idan foydalaning."
            
            await update.message.reply_text(subjects_list, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"List subjects error: {e}")
            await update.message.reply_text("❌ Fanlar ro'yxatini ko'rsatishda xatolik yuz berdi.")
    
    def get_handlers(self):
        """Handlerlarni qaytarish"""
        return [
            CommandHandler("start", self.user_start),
            CommandHandler("help", self.help_command),
            CommandHandler("stats", self.stats_command),
            CommandHandler("cancel", self.cancel_test),
            CommandHandler("subjects", self.list_subjects),
        ]
