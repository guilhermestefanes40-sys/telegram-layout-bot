import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# O token NÃO vai ficar aqui no código.
# Ele vai vir da variável de ambiente BOT_TOKEN lá no Railway.
TOKEN = os.environ.get("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    nome = update.effective_user.first_name or "amigo"
    await update.message.reply_text(
        f"Fala, {nome}! Seu bot da Renatruck tá online ✅"
    )

async def main():
    if not TOKEN:
        raise RuntimeError(
            "BOT_TOKEN não encontrado. Configure a variável de ambiente BOT_TOKEN no Railway."
        )

    app = ApplicationBuilder().token(TOKEN).build()

    # Comando /start
    app.add_handler(CommandHandler("start", start))

    print("Bot iniciado. Esperando mensagens...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
