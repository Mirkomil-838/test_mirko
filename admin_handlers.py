import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from config import ADMIN_ID, SUBJECTS_FOLDER
from database import DatabaseManager
from file_parser import FileParser

logger = logging.getLogger(__name__)

class AdminHandlers:
    def __init__(self, db: DatabaseManager):
        self.db = db
        # Dastlabki adminni qo'shish
        if not self.db.is_admin(ADMIN_ID):
            self.db.add_admin(ADMIN_ID, "AsosiyAdmin")
    
    def is_admin(self, user_id):
        return self.db.is_admin(user_id)
    
    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        
        if not self.is_admin(user_id):
            await update.message.reply_text("❌ Siz admin emassiz!")
            return
        
        keyboard = [
            [InlineKeyboardButton("📁 Fan qo'shish", callback_data="admin_add_subject")],
            [InlineKeyboardButton("👥 Adminlar", callback_data="admin_management")],
            [InlineKeyboardButton("📊 Natijalar", callback_data="admin_view_results")],
            [InlineKeyboardButton("🎯 Test ishlash", callback_data="user_start_test")]
        ]
        text = f"Assalomu alaykum, Admin! 🎓"
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup)
    
    async def admin_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        user_id = query.from_user.id
        
        if not self.is_admin(user_id):
            await query.answer("❌ Siz admin emassiz!", show_alert=True)
            return
        
        admins = self.db.get_admins()
        
        admin_list = "👥 Adminlar ro'yxati:\n\n"
        for admin_id, username in admins:
            admin_list += "• ID: {}, Username: {}\n".format(admin_id, username or "Noma'lum")
        
        keyboard = [
            [InlineKeyboardButton("➕ Admin qo'shish", callback_data="add_admin")],
            [InlineKeyboardButton("➖ Admin o'chirish", callback_data="remove_admin")],
            [InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(admin_list, reply_markup=reply_markup)
    
    async def add_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        
        if not self.is_admin(user_id):
            await update.message.reply_text("❌ Siz admin emassiz!")
            return
        
        if context.args:
            try:
                new_admin_id = int(context.args[0])
                new_admin_username = ' '.join(context.args[1:]) if len(context.args) > 1 else "Yangi admin"
                
                if self.db.add_admin(new_admin_id, new_admin_username):
                    await update.message.reply_text(f"✅ Admin muvaffaqiyatli qo'shildi!\nID: {new_admin_id}")
                else:
                    await update.message.reply_text("❌ Admin qo'shishda xatolik!")
            except ValueError:
                await update.message.reply_text("❌ Iltimos, to'g'ri ID kiriting (raqam)!")
        else:
            await update.message.reply_text(
                "❌ Iltimos, admin ID'sini kiriting:\n"
                "Masalan: /addadmin 123456789 FoydalanuvchiNomi"
            )
    
    async def remove_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        
        if not self.is_admin(user_id):
            await update.message.reply_text("❌ Siz admin emassiz!")
            return
        
        if context.args:
            try:
                admin_id_to_remove = int(context.args[0])
                
                if admin_id_to_remove == user_id:
                    await update.message.reply_text("❌ O'zingizni adminlikdan o'chira olmaysiz!")
                    return
                
                if self.db.remove_admin(admin_id_to_remove):
                    await update.message.reply_text(f"✅ Admin muvaffaqiyatli o'chirildi!\nID: {admin_id_to_remove}")
                else:
                    await update.message.reply_text("❌ Admin o'chirishda xatolik!")
            except ValueError:
                await update.message.reply_text("❌ Iltimos, to'g'ri ID kiriting (raqam)!")
        else:
            await update.message.reply_text(
                "❌ Iltimos, o'chiriladigan admin ID'sini kiriting:\n"
                "Masalan: /removeadmin 123456789"
            )
    
    async def add_subject_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        
        if not self.is_admin(user_id):
            await update.message.reply_text("❌ Siz admin emassiz!")
            return
        
        if context.args:
            subject_name = ' '.join(context.args)
            context.user_data['waiting_for_subject_name'] = True
            context.user_data['subject_name'] = subject_name
            await update.message.reply_text(
                f"📝 Fan nomi: {subject_name}\n"
                f"📎 Endi ushbu fan uchun Word yoki PDF fayl yuboring."
            )
        else:
            await update.message.reply_text(
                "❌ Iltimos, fan nomini kiriting:\n"
                "Masalan: /addsubject Matematika"
            )
    
    async def handle_admin_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        
        if not self.is_admin(user_id):
            await update.message.reply_text("❌ Siz admin emassiz!")
            return
        
        if not context.user_data.get('waiting_for_subject_name'):
            await update.message.reply_text("❌ Iltimos, avval fan nomini yuboring /addsubject buyrug'i orqali")
            return
        
        document = update.message.document
        file_name = document.file_name.lower()
        
        if not (file_name.endswith('.docx') or file_name.endswith('.pdf')):
            await update.message.reply_text("❌ Iltimos, faqat Word (.docx) yoki PDF fayl yuboring.")
            return
        
        # Faylni yuklash
        file = await context.bot.get_file(document.file_id)
        file_path = f"{SUBJECTS_FOLDER}/{context.user_data['subject_name']}_{file_name}"
        os.makedirs(SUBJECTS_FOLDER, exist_ok=True)
        await file.download_to_drive(file_path)
        
        # Fan ma'lumotlarini saqlash
        subject_name = context.user_data['subject_name']
        if self.db.add_subject(subject_name, file_path):
            await update.message.reply_text(f"✅ '{subject_name}' fani muvaffaqiyatli qo'shildi!")
        else:
            await update.message.reply_text("❌ Fan qo'shishda xatolik yuz berdi!")
        
        # User datani tozalash
        context.user_data.pop('waiting_for_subject_name', None)
        context.user_data.pop('subject_name', None)
    
    def get_handlers(self):
        return [
            CommandHandler("addsubject", self.add_subject_command),
            CommandHandler("addadmin", self.add_admin_command),
            CommandHandler("removeadmin", self.remove_admin_command),
            MessageHandler(filters.Document.ALL, self.handle_admin_document)
        ]