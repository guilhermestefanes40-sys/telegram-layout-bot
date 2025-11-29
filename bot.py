import os
import textwrap
from typing import List

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from PIL import Image, ImageDraw, ImageFont

# Token do bot (configurado como variável BOT_TOKEN no Railway)
TOKEN = os.environ.get("BOT_TOKEN")


# ============================================================
#                 FUNÇÕES DE IMAGEM / LAYOUT
# ============================================================

def crop_fill(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """
    Corta a imagem mantendo o centro e dá zoom
    para preencher exatamente target_w x target_h.
    Estilo recorte do Instagram.
    """
    img_w, img_h = img.size
    target_ratio = target_w / target_h
    img_ratio = img_w / img_h

    if img_ratio > target_ratio:
        # Imagem mais larga -> corta laterais
        new_w = int(img_h * target_ratio)
        offset = (img_w - new_w) // 2
        img = img.crop((offset, 0, offset + new_w, img_h))
    else:
        # Imagem mais alta -> corta cima/baixo
        new_h = int(img_w / target_ratio)
        offset = (img_h - new_h) // 2
        img = img.crop((0, offset, img_w, offset + new_h))

    return img.resize((target_w, target_h), Image.LANCZOS)


def montar_layout_instagram(photos: List[str], caption: str, user_id: int) -> str:
    """
    Layout final 1080x1080:
    - 1 foto grande em cima (620px)
    - 2 fotos lado a lado (320px)
    - faixa de texto fina (140px)
    """
    size = (1080, 1080)
    canvas = Image.new("RGB", size, (255, 255, 255))

    # ------------------------------------------------------------
    # FOTO PRINCIPAL (620px)
    # ------------------------------------------------------------
    main_img = Image.open(photos[0]).convert("RGB")
    main_img = crop_fill(main_img, 1080, 620)
    canvas.paste(main_img, (0, 0))

    # ------------------------------------------------------------
    # FOTOS SECUNDÁRIAS (2 fotos, 320px altura)
    # ------------------------------------------------------------
    thumbs = photos[1:3]

    thumb_area_top = 620
    faixa_h = 140
    thumb_area_height = 1080 - thumb_area_top - faixa_h  # 320px

    margin_x = 12
    slot_w = (1080 - 3 * margin_x) // 2
    slot_h = thumb_area_height  # ocupa toda a faixa

    x_positions = [
        margin_x,
        margin_x * 2 + slot_w
    ]

    for idx, path in enumerate(thumbs[:2]):
        img = Image.open(path).convert("RGB")
        img = crop_fill(img, slot_w, slot_h)
        canvas.paste(img, (x_positions[idx], thumb_area_top))

    # ------------------------------------------------------------
    # FAIXA DE TEXTO (140px)
    # ------------------------------------------------------------
    faixa_top = 1080 - faixa_h
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([(0, faixa_top), (1080, 1080)], fill=(20, 20, 20))

    try:
        font_title = ImageFont.truetype("arial.ttf", 46)
        font_body = ImageFont.truetype("arial.ttf", 30)
    except Exception:
        font_title = ImageFont.load_default()
        font_body = ImageFont.load_default()

    lines = [l.strip() for l in caption.splitlines() if l.strip()]
    title = lines[0] if lines else "Anúncio"
    bullets = lines[1:]

    text_x = 40
    text_y = faixa_top + 14
    max_width_chars = 30

    # Título
    draw.text((text_x, text_y), title, font=font_title, fill="white")
    text_y += 52

    # Bullets
    for b in bullets:
        wrapped = textwrap.wrap(b, width=max_width_chars)
        for i, line in enumerate(wrapped):
            prefix = "• " if i == 0 else "  "
            draw.text(
                (text_x, text_y),
                prefix + line,
                font=font_body,
                fill="#DCDCDC",
            )
            text_y += 34
        text_y += 4

    # Salvar arte
    os.makedirs("outputs", exist_ok=True)
    output_path = os.path.join("outputs", f"{user_id}_post_instagram.jpg")
    canvas.save(output_path, "JPEG", quality=90)

    return output_path


def montar_legenda_padrao(caption: str) -> str:
    """
    Formata a legenda:
    Título
    • bullets
    CTA final
    """
    lines = [l.strip() for l in caption.splitlines() if l.strip()]
    if not lines:
        return "Anúncio 🚛\n\n📲 Chama no direct ou WhatsApp para mais informações."

    title = lines[0]
    bullets = lines[1:]

    partes = [title, ""]
    for b in bullets:
        partes.append(f"• {b}")
    partes.append("")
    partes.append("📲 Chama no direct ou WhatsApp para mais informações.")

    return "\n".join(partes)


# ============================================================
#                 HANDLERS DO TELEGRAM
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()
    nome = update.effective_user.first_name or "amigo"

    msg = (
        f"Fala, {nome}! 👋\n\n"
        "Vou montar seu post assim:\n"
        "- 1 foto grande em cima\n"
        "- 2 fotos menores embaixo\n"
        "- faixa de texto com título + bullets\n\n"
        "📸 Me manda AGORA a PRIMEIRA FOTO (principal).\n"
        "Depois manda mais 2 fotos (detalhes). Serão 3 no total.\n"
        "Quando terminar as 3 fotos, me manda o TEXTO neste formato:\n\n"
        "Linha 1: Título (ex: Scania R-480 2019 6x4)\n"
        "Linhas seguintes: itens do anúncio (km, estado, local, preço etc.)"
    )
    await update.message.reply_text(msg)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    photo = update.message.photo[-1]
    file = await photo.get_file()

    os.makedirs("downloads", exist_ok=True)

    photos = context.user_data.get("photos", [])
    if len(photos) >= 3:
        await update.message.reply_text(
            "Você já me mandou 3 fotos 😉\n"
            "Agora me manda o TEXTO do anúncio.\n"
            "Se quiser recomeçar, é só usar /start."
        )
        return

    idx = len(photos) + 1
    file_path = os.path.join("downloads", f"{update.effective_user.id}_{idx}.jpg")
    await file.download_to_drive(file_path)

    photos.append(file_path)
    context.user_data["photos"] = photos

    if len(photos) < 3:
        await update.message.reply_text(
            f"Foto {len(photos)} salva ✅\n"
            "Me manda a PRÓXIMA foto (até fechar as 3)."
        )
    else:
        await update.message.reply_text(
            "Foto 3 salva ✅\n"
            "Agora me manda o TEXTO do anúncio naquele formato (título na primeira linha, itens nas linhas de baixo)."
        )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    photos = context.user_data.get("photos", [])

    if len(photos) < 3:
        await update.message.reply_text(
            "Pra eu montar esse layout, preciso de 3 FOTOS primeiro 📸\n"
            "Me manda as fotos e depois o TEXTO."
        )
        return

    user_id = update.effective_user.id

    # Monta a arte
    output_path = montar_layout_instagram(photos, text, user_id)

    # Monta a legenda
    legenda = montar_legenda_padrao(text)

    # Envia a arte
    try:
        with open(output_path, "rb") as img_file:
            await update.message.reply_photo(
                img_file,
                caption="Tá aí sua arte pronta pra Instagram ✅\n\n"
                        "A legenda vem na próxima mensagem. 👇",
            )
    except Exception as e:
        await update.message.reply_text(
            f"Deu erro ao gerar a arte 😥\n"
            f"Tenta de novo ou manda outra foto.\n\nDetalhe técnico: {e}"
        )
        return

    # Envia legenda
    await update.message.reply_text(legenda)

    # Limpa pra um próximo post
    context.user_data.clear()


# ============================================================
#                          MAIN
# ============================================================

def main() -> None:
    if not TOKEN:
        raise RuntimeError(
            "BOT_TOKEN não encontrado. Configure a variável de ambiente BOT_TOKEN no Railway."
        )

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Bot iniciado. Esperando mensagens...")
    app.run_polling()


if __name__ == "__main__":
    main()
