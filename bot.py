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

# Token do bot (configurado no Railway como BOT_TOKEN)
TOKEN = os.environ.get("BOT_TOKEN")

# Arquivos que você precisa ter na raiz do repositório:
LOGO_PATH = "logo_renatruck.png"
FONT_BOLD = "renatruck_bold.ttf"
FONT_REGULAR = "renatruck_regular.ttf"


# ===================================================================
#                   FUNÇÃO COMPATÍVEL PARA MEDIR TEXTO
# ===================================================================
def medir_texto(draw, texto, fonte):
    """
    Substitui textsize() por textbbox(), compatível com Railway.
    Retorna largura e altura do texto.
    """
    box = draw.textbbox((0, 0), texto, font=fonte)
    w = box[2] - box[0]
    h = box[3] - box[1]
    return w, h


# ===================================================================
#               RECORTE INTELIGENTE (MESMO DO INSTA)
# ===================================================================
def crop_fill(img, target_w, target_h):
    img_w, img_h = img.size
    target_ratio = target_w / target_h
    img_ratio = img_w / img_h

    if img_ratio > target_ratio:
        new_w = int(img_h * target_ratio)
        offset = (img_w - new_w) // 2
        img = img.crop((offset, 0, offset + new_w, img_h))
    else:
        new_h = int(img_w / target_ratio)
        offset = (img_h - new_h) // 2
        img = img.crop((0, offset, img_w, offset + new_h))

    return img.resize((target_w, target_h), Image.LANCZOS)


# ===================================================================
#              EXTRAI MODELO E PREÇO DO TEXTO ENVIADO
# ===================================================================
def extrair_modelo_e_preco(caption):
    lines = [l.strip() for l in caption.splitlines() if l.strip()]

    modelo = lines[0] if lines else "Caminhão"
    preco = ""

    for l in lines:
        if "R$" in l:
            preco = l[l.find("R$"):].replace("✅", "").strip()
            break

    if not preco:
        preco = "Sob consulta"

    return modelo, preco


# ===================================================================
#                   GERA A ARTE DO POST 1080x1080
# ===================================================================
def montar_layout_instagram(photo_path, caption, user_id):
    size = (1080, 1080)
    canvas = Image.new("RGB", size, (255, 255, 255))

    # barra um pouco menor pra foto ganhar mais espaço
    bar_height = 230
    photo_height = size[1] - bar_height

    # FOTO ================================
    img = Image.open(photo_path).convert("RGB")
    img = crop_fill(img, size[0], photo_height)
    canvas.paste(img, (0, 0))

    # BARRA PRETA ==========================
    bar_top = photo_height
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([(0, bar_top), (1080, 1080)], fill=(10, 10, 10))

    modelo, preco = extrair_modelo_e_preco(caption)

    # Tenta carregar fontes da Renatruck, senão cai na default
    try:
        font_price = ImageFont.truetype(FONT_BOLD, 90)
        font_model = ImageFont.truetype(FONT_BOLD, 50)
        font_small = ImageFont.truetype(FONT_REGULAR, 30)
    except Exception:
        font_price = ImageFont.load_default()
        font_model = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Divisões da barra
    total_w = 1080
    left_w = int(total_w * 0.55)
    center_w = int(total_w * 0.28)
    right_w = total_w - left_w - center_w

    left_x0 = 0
    center_x0 = left_w
    right_x0 = left_w + center_w

    # ================= BLOCO ESQUERDO (PREÇO + MODELO) =================
    padding_left = 30
    y_price = bar_top + 20

    # Preço grande
    draw.text((padding_left, y_price), preco, font=font_price, fill="white")

    # Modelo embaixo do preço, quebrando em mais de uma linha se for grande
    y_model = y_price + 90
    wrapped_model = textwrap.wrap(modelo, width=26)
    for line in wrapped_model:
        draw.text((padding_left, y_model), line, font=font_model, fill="white")
        y_model += 48

    # ================= BLOCO CENTRAL (TAGLINE + TEL) ==================
    centro_texto = "A maior vitrine de pesados do Brasil! 🇧🇷"
    telefone = "(84) 98160-3052"

    w_tag, h_tag = medir_texto(draw, centro_texto, font_small)
    w_tel, h_tel = medir_texto(draw, telefone, font_small)

    center_mid_y = bar_top + bar_height // 2

    # Frase
    draw.text(
        (center_x0 + (center_w - w_tag) // 2, center_mid_y - h_tag),
        centro_texto,
        font=font_small,
        fill="#F5F5F5",
    )

    # Telefone
    draw.text(
        (center_x0 + (center_w - w_tel) // 2, center_mid_y + 5),
        telefone,
        font=font_small,
        fill="#F5F5F5",
    )

    # ================= BLOCO DIREITO (LOGO) ============================
    try:
        if os.path.exists(LOGO_PATH):
            logo = Image.open(LOGO_PATH).convert("RGBA")
            logo.thumbnail((right_w - 40, bar_height - 40), Image.LANCZOS)

            logo_x = right_x0 + (right_w - logo.width) // 2
            logo_y = bar_top + (bar_height - logo.height) // 2

            canvas.paste(logo, (logo_x, logo_y), logo)
    except Exception:
        pass

    # Salvar arquivo final
    os.makedirs("outputs", exist_ok=True)
    output_path = f"outputs/{user_id}_post_instagram.jpg"
    canvas.save(output_path, "JPEG", quality=90)

    return output_path


# ===================================================================
#                  LEGENDA AUTOMÁTICA
# ===================================================================
def montar_legenda_padrao(caption):
    lines = [l.strip() for l in caption.splitlines() if l.strip()]
    if not lines:
        return "Anúncio 🚛\n\n📲 Chama no WhatsApp para mais informações."

    title = lines[0]
    bullets = lines[1:]

    partes = [title, ""]
    for b in bullets:
        partes.append(f"• {b}")
    partes.append("")
    partes.append("📲 Chama no direct ou WhatsApp para mais informações.")

    return "\n".join(partes)


# ===================================================================
#                  HANDLERS DO BOT
# ===================================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Fala! 👋\n\n"
        "Me envie primeiro **UMA FOTO** 📸\n"
        "Depois me envie o **texto do anúncio**.\n\n"
        "Exemplo:\n"
        "Mercedes 710 ano 2007, revisada...\n"
        "R$ 185.000,00 ✅"
    )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await photo.get_file()

    os.makedirs("downloads", exist_ok=True)
    path = f"downloads/{update.effective_user.id}_1.jpg"
    await file.download_to_drive(path)

    context.user_data["photo"] = path
    await update.message.reply_text("Foto salva! ✅ Agora me mande o texto.")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "photo" not in context.user_data:
        await update.message.reply_text("Antes preciso da FOTO 📸")
        return

    caption = update.message.text
    photo_path = context.user_data["photo"]
    user_id = update.effective_user.id

    try:
        output_path = montar_layout_instagram(photo_path, caption, user_id)
        legenda = montar_legenda_padrao(caption)
    except Exception as e:
        await update.message.reply_text(
            "Erro ao montar a arte 😥\n\n"
            f"Detalhe técnico:\n{e}"
        )
        return

    # Envia a imagem
    with open(output_path, "rb") as img:
        await update.message.reply_photo(
            img,
            caption="Sua arte está pronta! ✅\n\nAbaixo envio a legenda:",
        )

    await update.message.reply_text(legenda)
    context.user_data.clear()


# ===================================================================
#                            MAIN
# ===================================================================
def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN não configurado no Railway.")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Bot rodando…")
    app.run_polling()


if __name__ == "__main__":
    main()
