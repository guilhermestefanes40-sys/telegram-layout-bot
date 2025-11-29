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


# Token do bot no Railway
TOKEN = os.environ.get("BOT_TOKEN")


# ============================================================
#                      FUNÇÕES DE IMAGEM
# ============================================================

def crop_fill(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """
    Corta e dá zoom mantendo proporção para preencher toda a área.
    Igual o Instagram faz.
    """
    img_w, img_h = img.size
    target_ratio = target_w / target_h
    img_ratio = img_w / img_h

    if img_ratio > target_ratio:
        new_width = int(img_h * target_ratio)
        offset = (img_w - new_width) // 2
        img = img.crop((offset, 0, offset + new_width, img_h))
    else:
        new_height = int(img_w / target_ratio)
        offset = (img_h - new_height) // 2
        img = img.crop((0, offset, img_w, offset + new_height))

    return img.resize((target_w, target_h), Image.LANCZOS)


def montar_layout_instagram(photos: List[str], caption: str, user_id: int) -> str:
    """
    Layout final:
    - 1 foto grande em cima (620px)
    - 2 fotos menores abaixo (260px, lado a lado)
    - faixa de texto (200px)
    Preenchimento total SEM barras brancas.
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
    # FOTOS SECUNDÁRIAS (2 fotos lado a lado)
    # ------------------------------------------------------------
    thumbs = photos[1:3]
    thumb_area_top = 620
    thumb_area_height = 260

    margin_x = 12
    slot_w = (1080 - 3 * margin_x) // 2
    slot_h = thumb_area_height

    x_positions = [
        margin_x,
        margin_x * 2 + slot_w
    ]

    for idx, path in enumerate(thumbs[:2]):
        img = Image.open(path).convert("RGB")
        img = crop_fill(img, slot_w, slot_h)
        canvas.paste(img, (x_positions[idx], thumb_area_top))

    # ------------------------------------------------------------
    # FAIXA DE TEXTO FINAL (200px)
    # ------------------------------------------------------------
    faixa_h = 200
    faixa_top = 1080 - faixa_h
    draw = ImageDraw.Draw(canvas)

    draw.rectangle([(0, faixa_top), (1080, 1080)], fill=(20, 20, 20))

    try:
        font_title = ImageFont.truetype("arial.ttf", 52)
        font_body = ImageFont.truetype("arial.ttf", 36)
    except:
        font_title = ImageFont.load_default()
        font_body = ImageFont.load_default()

    lines = [l.strip() for l in caption.splitlines() if l.strip()]
    title = lines[0] if lines else "Anúncio"
    bullets = lines[1:]

    text_x = 40
    text_y = faixa_top + 18
    max_width_chars = 28

    draw.text((text_x, text_y), title, font=font_title, fill="white")
    text_y += 60

    for b in bullets:
        wrapped = textwrap.wrap(b, width=max_width_chars)
        for i, line in enumerate(wrapped):
            prefix = "• " if i == 0 else "  "
            draw.text((text_x, text_y), prefix + line, font=font_body, fill="#DCDCDC")
            text_y += 40
        text_y += 6

    os.makedirs("outputs", exist_ok=True)
    output_path = os.path.join("outputs", f"{user_id}_post_instagram.jpg")
    canvas.save(output_path, "JPEG", quality=90)

    return output_path


def montar_legenda_padrao(caption: str) -> str:
    """
    Formata legenda tipo:
    Título
    • bullet
    • bullet
    CTA final
    """
    lines = [l.strip() for l in caption.splitlines() if l.strip()]
    if not lines:
        return "Anúncio 🚛\n\n📲 Chama no direct para mais informações."

    title = lines[0]
    bullets = lines[1:]

    partes = [title]
    partes.append("")

    for b in bullets:
        partes.append(f"• {b}")

    partes.append("")
    partes.append("📲 Chama no direct ou WhatsApp para mais informações.")

    return "\n".join(partes)


# ============================================================
#                      HANDLERS DO BOT
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()
    nome = update.effective_user.first_name or "amigo"

    msg = (
        f"Fala, {nome}! 👋\n\n"
        "Vamos montar seu post com 3 fotos:\n"
        "📸 Foto 1: principal (grande)\n"
        "📸 Foto 2: detalhe\n"
        "📸 Foto 3: detalhe\n\n"
        "Depois das 3 fotos, envie o texto neste formato:\n\n"
        "Linha 1 → Título\n"
        "Linhas seguintes → Item por linha\n"
    )
    await update.message.reply_text(msg)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    photo = update.message.photo[-1]
    file = await photo.get_file()

    os.makedirs("downloads", exist_ok=True)

    photos = context.user_data.get("photos", [])
    if len(photos) >= 3:
        await update.message.reply_text(
            "Você já mandou as 3 fotos 👍\nAgora envie o TEXTO."
        )
        return

    idx = len(photos) + 1
    path = os.path.join("downloads", f"{update.effective_user.id}_{idx}.jpg")
    await file.download_to_drive(path)

    photos.append(path)
    context.user_data["photos"] = photos

    if len(photos) < 3:
        await update.message.reply_text(f"Foto {len(photos)} salva! Manda a próxima 📸")
    else:
        await update.message.reply_text("Show! Agora manda o TEXTO do anúncio.")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    photos = context.user_data.get("photos", [])

    if len(photos) < 3:
        await update.message.reply_text("Antes preciso das 3 fotos 📸")
        return

    user_id = update.effective_user.id

    # Gera a arte
    output = montar_layout_instagram(photos, text, user_id)

    # Legenda
    legenda = montar_legenda_padrao(text)

    # Envia a arte
    try:
        with open(output, "rb") as img:
            await update.message.reply_photo(
                img,
                caption="Sua arte está pronta! ✅\n\nA legenda vem abaixo 👇"
            )
    except Exception as e:
        await update.message.reply_text(f"Erro ao gerar imagem: {e}")
        return

    # Envia legenda
    await update.message.reply_text(legenda)

    # Limpa dados pro próximo post
    context.user_data.clear()


# ============================================================
#                      MAIN
# ============================================================

def main() -> None:
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN não encontrado no Railway.")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Bot iniciado. Esperando mensagens...")
    app.run_polling()


if __name__ == "__main__":
    main()
