import os
import textwrap
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from PIL import Image, ImageDraw, ImageFont

# O token vem da variável de ambiente BOT_TOKEN no Railway
TOKEN = os.environ.get("BOT_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /start – reseta o fluxo e explica o que fazer."""
    context.user_data.clear()
    nome = update.effective_user.first_name or "amigo"
    msg = (
        f"Fala, {nome}! 👋\n\n"
        "Vou te ajudar a montar seus posts de Instagram.\n\n"
        "➡️ Passo 1: me manda a FOTO do caminhão/produto.\n"
        "➡️ Passo 2: depois me manda o TEXTO do anúncio.\n\n"
        "Eu vou te devolver uma arte 1080x1080 pronta pra postar. 😉"
    )
    await update.message.reply_text(msg)


def montar_layout_instagram(photo_path: str, caption: str, user_id: int) -> str:
    """Gera uma imagem 1080x1080 com a foto + texto."""
    # Tamanho padrão do Instagram
    size = (1080, 1080)
    bg_color = (255, 255, 255)

    # Cria fundo branco
    canvas = Image.new("RGB", size, bg_color)

    # Abre a foto original
    img = Image.open(photo_path).convert("RGB")

    # Redimensiona a foto para caber em 1080x600 mantendo proporção
    max_w, max_h = 1080, 600
    img.thumbnail((max_w, max_h))
    # Centraliza a foto horizontalmente, com margem em cima
    offset_x = (size[0] - img.width) // 2
    offset_y = 20
    canvas.paste(img, (offset_x, offset_y))

    draw = ImageDraw.Draw(canvas)

    # Tenta carregar uma fonte TTF, se não tiver usa a padrão
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except Exception:
        font = ImageFont.load_default()

    # Área de texto
    text_area_top = 650
    text_area_left = 60
    text_area_width = 960  # 1080 - 2*60

    # Quebra o texto em linhas mais curtas
    # Isso aqui é simples: ajusta o width se o texto estiver quebrando feio
    wrapped = textwrap.fill(caption, width=38)

    draw.multiline_text(
        (text_area_left, text_area_top),
        wrapped,
        font=font,
        fill=(0, 0, 0),
        spacing=10,
    )

    # Caminho do arquivo final
    os.makedirs("outputs", exist_ok=True)
    output_path = os.path.join("outputs", f"{user_id}_post_instagram.jpg")
    canvas.save(output_path, "JPEG", quality=90)

    return output_path


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Quando o usuário manda uma foto."""
    photo = update.message.photo[-1]  # melhor qualidade
    file = await photo.get_file()

    os.makedirs("downloads", exist_ok=True)
    file_path = os.path.join(
        "downloads", f"{update.effective_user.id}_latest.jpg"
    )

    await file.download_to_drive(file_path)

    # Guarda o caminho da foto
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

        # Monta a arte do Instagram
        user_id = update.effective_user.id
        output_path = montar_layout_instagram(photo_path, text, user_id)

        # Envia a arte pronta
        try:
            with open(output_path, "rb") as img_file:
                await update.message.reply_photo(
                    img_file,
                    caption="Tá aí sua arte pronta pra Instagram ✅\n\n"
                    "Se quiser fazer outro post, é só mandar outra FOTO ou usar /start.",
                )
        except Exception as e:
            await update.message.reply_text(
                f"Deu algum erro pra gerar a arte 😥\n"
                f"Tenta de novo ou me manda outra foto.\n\nDetalhe técnico: {e}"
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
