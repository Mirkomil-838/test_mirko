import os
import logging
from telegram.ext import Application, CommandHandler
from config import BOT_TOKEN, SUBJECTS_FOLDER
from database import DatabaseManager
from admin_handlers import AdminHandlers
from user_handlers import UserHandlers
from callback_handlers import CallbackHandlers
from config import ADMIN_ID

# Log konfiguratsiyasi
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    # Papkalarni yaratish
    os.makedirs(SUBJECTS_FOLDER, exist_ok=True)
    
    # Ma'lumotlar bazasi va handlerlarni yaratish
    db = DatabaseManager()
    admin_handlers = AdminHandlers(db)
    user_handlers = UserHandlers(db)
    callback_handlers = CallbackHandlers(db, admin_handlers, user_handlers)
    
    # Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Handlerslarni qo'shish
    application.add_handler(CommandHandler("start", user_handlers.user_start))
    
    # Admin handlerlari
    for handler in admin_handlers.get_handlers():
        application.add_handler(handler)
    
    # User handlerlari
    for handler in user_handlers.get_handlers():
        application.add_handler(handler)
    
    # Callback handlerlari
    for handler in callback_handlers.get_handlers():
        application.add_handler(handler)
    
    print("Bot ishga tushdi...")
    print(f"Admin ID: {ADMIN_ID}")
    application.run_polling()

if __name__ == '__main__':
    main()