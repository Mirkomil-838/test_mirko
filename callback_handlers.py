import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from database import DatabaseManager
from admin_handlers import AdminHandlers
from user_handlers import UserHandlers

logger = logging.getLogger(__name__)

class CallbackHandlers:
    def __init__(self, db: DatabaseManager, admin_handlers: AdminHandlers, user_handlers: UserHandlers):
        self.db = db
        self.admin_handlers = admin_handlers
        self.user_handlers = user_handlers
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        data = query.data
        
        logger.info(f"Callback received: {data}")
        
        try:
            if data == "main_menu":
                await self.start_callback(query, context)
            elif data == "admin_add_subject":
                await query.edit_message_text(
                    "📁 Yangi fan qo'shish uchun:\n"
                    "1. Fan nomini kiriting: /addsubject [Fan nomi]\n"
                    "2. So'ngra Word yoki PDF fayl yuboring"
                )
            elif data == "admin_management":
                await self.admin_handlers.admin_management(update, context)
            elif data == "add_admin":
                await query.edit_message_text(
                    "➕ Yangi admin qo'shish uchun:\n"
                    "Quyidagi formatda buyruq yuboring:\n"
                    "/addadmin [ID] [Username]\n\n"
                    "Masalan: /addadmin 123456789 YangiAdmin"
                )
            elif data == "remove_admin":
                await query.edit_message_text(
                    "➖ Admin o'chirish uchun:\n"
                    "Quyidagi formatda buyruq yuboring:\n"
                    "/removeadmin [ID]\n\n"
                    "Masalan: /removeadmin 123456789"
                )
            elif data == "admin_view_results":
                await query.edit_message_text("📊 Natijalar ko'rsatiladi...")
            elif data == "user_start_test":
                await self.user_handlers.show_subjects(update, context)
            elif data.startswith("subject_"):
                await self.user_handlers.handle_subject_selection(update, context)
            elif data.startswith("count_"):
                await self.user_handlers.handle_question_count(update, context)
            elif data.startswith("ans_"):
                await self.user_handlers.handle_answer(update, context)
            elif data.startswith("next_"):
                await self.user_handlers.handle_next_question(update, context)
            else:
                await query.answer("Noma'lum buyruq!", show_alert=True)
                logger.warning(f"Noma'lum callback data: {data}")
        
        except Exception as e:
            logger.error(f"Callback处理错误: {e}")
            await query.answer("Xatolik yuz berdi!", show_alert=True)
    
    async def start_callback(self, query, context):
        user_id = query.from_user.id
        user_name = query.from_user.first_name
        
        if self.admin_handlers.is_admin(user_id):
            keyboard = [
                [InlineKeyboardButton("📁 Fan qo'shish", callback_data="admin_add_subject")],
                [InlineKeyboardButton("👥 Adminlar", callback_data="admin_management")],
                [InlineKeyboardButton("📊 Natijalar", callback_data="admin_view_results")],
                [InlineKeyboardButton("🎯 Test ishlash", callback_data="user_start_test")]
            ]
            text = f"Assalomu alaykum, Admin {user_name}! 🎓"
        else:
            keyboard = [
                [InlineKeyboardButton("🎯 Test ishlash", callback_data="user_start_test")]
            ]
            text = f"Assalomu alaykum, {user_name}! Test botiga xush kelibsiz! 🎓"
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    def get_handlers(self):
        return [CallbackQueryHandler(self.handle_callback)]
