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


def montar_layout_instagram(photo_path: str, caption: str, user_id: int) -> str:
    """
    Layout final 1080x1080:
    - 1 foto grande ocupando a parte de cima (ex: 760px)
    - faixa de texto embaixo com título + bullets
    """
    size = (1080, 1080)
    canvas = Image.new("RGB", size, (255, 255, 255))

    # ------------------------------------------------------------
    # FOTO PRINCIPAL (topo) - com crop inteligente
    # ------------------------------------------------------------
    foto_altura = 760  # mais espaço pra foto
    foto_largura = 1080

    img = Image.open(photo_path).convert("RGB")
    img = crop_fill(img, foto_largura, foto_altura)
    canvas.paste(img, (0, 0))

    # ------------------------------------------------------------
    # FAIXA DE TEXTO (parte de baixo)
    # ------------------------------------------------------------
    faixa_top = foto_altura          # começa logo após a foto
    faixa_altura = size[1] - faixa_top  # resto da imagem

    draw = ImageDraw.Draw(canvas)
    draw.rectangle([(0, faixa_top), (1080, 1080)], fill=(20, 20, 20))

    # fontes
    try:
        font_title = ImageFont.truetype("arial.ttf", 50)
        font_body = ImageFont.truetype("arial.ttf", 32)
    except Exception:
        font_title = ImageFont.load_default()
        font_body = ImageFont.load_default()

    lines = [l.strip() for l in caption.splitlines() if l.strip()]
    title = lines[0] if lines else "Anúncio"
    bullets = lines[1:]

    text_x = 40
    text_y = faixa_top + 20
    max_width_chars = 32

    # título
    draw.text((text_x, text_y), title, font=font_title, fill="white")
    text_y += 60

    # bullets
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
            text_y += 38
        text_y += 6

    # salvar arte
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
        "Novo fluxo:\n"
        "- Você me manda APENAS 1 FOTO (principal)\n"
        "- Depois manda o TEXTO do anúncio\n\n"
        "Formato do texto:\n"
        "Linha 1: Título (ex: Scania R-480 2019 6x4)\n"
        "Linhas seguintes: itens do anúncio (km, estado, local, preço etc.)\n\n"
        "Pode mandar a FOTO agora 📸"
    )
    await update.message.reply_text(msg)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    photo = update.message.photo[-1]
    file = await photo.get_file()

    os.makedirs("downloads", exist_ok=True)

    # Se já tem uma foto guardada, substitui ou pede pra /start
    if "photo_path" in context.user_data:
        # Vamos sobrescrever a anterior com a nova (caso a pessoa queira trocar)
        idx = 1
    else:
        idx = 1

    file_path = os.path.join("downloads", f"{update.effective_user.id}_{idx}.jpg")
    await file.download_to_drive(file_path)

    context.user_data["photo_path"] = file_path

    await update.message.reply_text(
        "Foto salva ✅\nAgora me manda o TEXTO do anúncio naquele formato (título na primeira linha, itens nas linhas abaixo)."
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    photo_path = context.user_data.get("photo_path")

    if not photo_path:
        await update.message.reply_text(
            "Antes preciso da FOTO 📸\nMe manda a foto primeiro, depois o texto."
        )
        return

    user_id = update.effective_user.id

    # Monta a arte
    output_path = montar_layout_instagram(photo_path, text, user_id)

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
