import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# O token vem da variável de ambiente BOT_TOKEN no Railway
TOKEN = os.environ.get("BOT_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /start – reseta o fluxo e explica o que fazer."""
    context.user_data.clear()
    nome = update.effective_user.first_name or "amigo"
    msg = (
        f"Fala, {nome}! 👋\n\n"
        "Vou te ajudar a montar seus posts.\n\n"
        "➡️ Passo 1: me manda a FOTO do caminhão/produto.\n"
        "➡️ Passo 2: depois me manda o TEXTO do anúncio.\n\n"
        "Quando estiver pronto, eu vou confirmar que recebi tudo certinho. "
        "Na próxima fase vou começar a te devolver a arte pronta pro Instagram. 😉"
    )
    await update.message.reply_text(msg)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Quando o usuário manda uma foto."""
    photo = update.message.photo[-1]  # pega a foto em melhor qualidade
    file = await photo.get_file()

    # Pasta para guardar as imagens temporárias
    os.makedirs("downloads", exist_ok=True)
    file_path = os.path.join(
        "downloads", f"{update.effective_user.id}_latest.jpg"
    )

    await file.download_to_drive(file_path)

    # Guarda o caminho da foto para esse usuário
    context.user_data["photo_path"] = file_path
    context.user_data.pop("caption", None)
    context.user_data.pop("caption_done", None)

    await update.message.reply_text(
        "Boa! 📸 Já salvei sua foto.\n\n"
        "Agora me manda o TEXTO que você quer colocar nesse post."
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Quando o usuário manda texto. Se já tiver foto, tratamos como legenda."""
    text = update.message.text.strip()
    photo_path = context.user_data.get("photo_path")

    # Se já tem foto salva e ainda não recebemos legenda, usamos esse texto
    if photo_path and not context.user_data.get("caption_done"):
        context.user_data["caption"] = text
        context.user_data["caption_done"] = True

        await update.message.reply_text(
            "Show! ✅\n\n"
            "Já tenho:\n"
            f"• Foto salva em: {photo_path}\n"
            f"• Texto do post:\n{text}\n\n"
            "Por enquanto eu só estou guardando a foto + texto.\n"
            "Na próxima fase vou começar a te devolver a arte pronta pro Instagram. 😉\n\n"
            "Se quiser começar outro post, é só mandar outra FOTO ou usar /start."
        )
    else:
        # Caso o usuário mande texto sem ter mandado foto antes
        await update.message.reply_text(
            "Pra eu montar seu post, primeiro me manda uma FOTO 📸\n"
            "Depois você me manda o TEXTO do anúncio. 😉"
        )


def main() -> None:
    if not TOKEN:
        raise RuntimeError(
            "BOT_TOKEN não encontrado. Configure a variável de ambiente BOT_TOKEN no Railway."
        )

    app = ApplicationBuilder().token(TOKEN).build()

    # Comando /start
    app.add_handler(CommandHandler("start", start))

    # Quando mandar FOTO
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Quando mandar TEXTO normal (que não seja comando)
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
    )

    print("Bot iniciado. Esperando mensagens...")
    app.run_polling()


if __name__ == "__main__":
    main()
