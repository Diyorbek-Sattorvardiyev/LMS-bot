from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
   
    chat_id = update.message.chat_id
    await update.message.reply_text(f"Sizning chat ID'ingiz: {chat_id}")

def main():
    
    app = ApplicationBuilder().token("7635414762:AAFT3MwKoWr6EfCoRBe9oTofJ1NKIiIzjSA").build()

    # /chat_id komandasini qo'shamiz
    app.add_handler(CommandHandler("chat_id", get_chat_id))

   
    app.run_polling()

if __name__ == "__main__":
    main()


# lmsbot-18a44-firebase-adminsdk-mpn8z-9ed43638d1