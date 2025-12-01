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

# Caminho do arquivo de logo (PNG com fundo transparente).
# Se quiser logo, coloque um arquivo "logo_renatruck.png" na raiz do repo.
LOGO_PATH = "logo_renatruck.png"


# ============================================================
#                 FUNÇÕES DE IMAGEM / LAYOUT
# ============================================================

def crop_fill(img, target_w, target_h):
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


def extrair_modelo_e_preco(caption):
    """
    Extrai:
    - modelo = PRIMEIRA LINHA inteira
    - preço  = PRIMEIRA linha que contém 'R$'
    Não depende de vírgula, pode ter texto extra, ✅, etc.
    """
    lines = [l.strip() for l in caption.splitlines() if l.strip()]

    modelo = ""
    preco = ""

    if lines:
        modelo = lines[0]  # título completo (primeira linha)

    for l in lines:
        if "R$" in l:
            idx = l.find("R$")
            preco = l[idx:].replace("✅", "").strip()
            break

    if not modelo:
        modelo = "Caminhão"
    if not preco:
        preco = "Sob consulta"

    return modelo, preco


def montar_layout_instagram(photo_path, caption, user_id):
    """
    Layout final 1080x1080 estilo Renatruck:
    - Foto ocupa a parte de cima
    - Barra preta embaixo com:
      - Preço grande (esquerda)
      - Modelo grande abaixo do preço
      - Centro com frase + telefone
      - Direita com logo (se existir o arquivo)
    """
    size = (1080, 1080)
    canvas = Image.new("RGB", size, (255, 255, 255))

    # Alturas
    bar_height = 260  # altura da barra preta
    photo_height = size[1] - bar_height  # resto para a foto

    # ------------------------------------------------------------
    # FOTO PRINCIPAL (topo) - com crop inteligente
    # ------------------------------------------------------------
    img = Image.open(photo_path).convert("RGB")
    img = crop_fill(img, size[0], photo_height)
    canvas.paste(img, (0, 0))

    # ------------------------------------------------------------
    # BARRA PRETA INFERIOR
    # ------------------------------------------------------------
    bar_top = photo_height
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([(0, bar_top), (size[0], size[1])], fill=(10, 10, 10))

    # ------------------------------------------------------------
    # TEXTOS: modelo e preço extraídos da legenda
    # ------------------------------------------------------------
    modelo, preco = extrair_modelo_e_preco(caption)

    try:
        font_price = ImageFont.truetype("arial.ttf", 70)
        font_model = ImageFont.truetype("arial.ttf", 40)
        font_small = ImageFont.truetype("arial.ttf", 30)
    except Exception:
        font_price = ImageFont.load_default()
        font_model = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Áreas da barra (esquerda / centro / direita)
    total_w = size[0]
    left_w = int(total_w * 0.55)
    center_w = int(total_w * 0.28)
    right_w = total_w - left_w - center_w

    left_x0, left_x1 = 0, left_w
    center_x0, center_x1 = left_x1, left_x1 + center_w
    right_x0, right_x1 = center_x1, total_w

    # ------------------- BLOCO ESQUERDO (PREÇO + MODELO) -------------------
    padding_left = 30
    y_price = bar_top + 30

    draw.text((padding_left, y_price), preco, font=font_price, fill="white")

    # modelo abaixo do preço (quebrando se ficar muito longo)
    y_model = y_price + 80
    max_chars_model = 26
    wrapped_model = textwrap.wrap(modelo, width=max_chars_model)
    for line in wrapped_model:
        draw.text((padding_left, y_model), line, font=font_model, fill="white")
        y_model += 42

    # ------------------- BLOCO CENTRAL (TAGLINE + TEL) -------------------
    centro_texto = "A maior vitrine de pesados do Brasil! 🇧🇷"
    telefone = "(84) 98160-3052"

    center_mid_y = bar_top + bar_height // 2

    # Tagline
    w_tagline, h_tagline = draw.textsize(centro_texto, font=font_small)
    tagline_x = center_x0 + (center_w - w_tagline) // 2
    tagline_y = center_mid_y - h_tagline
    draw.text((tagline_x, tagline_y), centro_texto, font=font_small, fill="#F5F5F5")

    # Telefone
    w_tel, h_tel = draw.textsize(telefone, font=font_small)
    tel_x = center_x0 + (center_w - w_tel) // 2
    tel_y = center_mid_y + 4
    draw.text((tel_x, tel_y), telefone, font=font_small, fill="#F5F5F5")

    # ------------------- BLOCO DIREITO (LOGO) -------------------
    try:
        if os.path.exists(LOGO_PATH):
            logo = Image.open(LOGO_PATH).convert("RGBA")
            max_logo_w = right_w - 40
            max_logo_h = bar_height - 40
            logo.thumbnail((max_logo_w, max_logo_h), Image.LANCZOS)

            logo_x = right_x0 + (right_w - logo.width) // 2
            logo_y = bar_top + (bar_height - logo.height) // 2

            canvas.paste(logo, (logo_x, logo_y), logo)
    except Exception:
        # Se der erro na logo, ignora e segue
        pass

    # Salvar arte
    os.makedirs("outputs", exist_ok=True)
    output_path = os.path.join("outputs", f"{user_id}_post_instagram.jpg")
    canvas.save(output_path, "JPEG", quality=90)

    return output_path


def montar_legenda_padrao(caption):
    """
    Formata a legenda:
    Título (primeira linha)
    • bullets (demais linhas, inclusive preço)
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
        "Layout Renatruck (1 foto):\n"
        "- Foto grande em cima\n"
        "- Barra preta embaixo com PREÇO, MODELO, frase e logo\n\n"
        "Como usar:\n"
        "1️⃣ Me manda UMA FOTO do caminhão 📸\n"
        "2️⃣ Depois me manda o TEXTO do anúncio.\n\n"
        "Exemplo de texto (pode variar):\n\n"
        "MB 710 ano 2007, vai com carroceria de madeira (que está ajeitando), "
        "com 389 mil km, carro todo revisado, pronto para trabalhar.\n"
        "R$ 185.000,00 ✅\n\n"
        "→ Eu uso a PRIMEIRA linha inteira como título grande.\n"
        "→ E uso a PRIMEIRA linha que tiver 'R$' como preço grande.\n\n"
        "Pode me mandar a FOTO agora 📸"
    )
    await update.message.reply_text(msg)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    photo = update.message.photo[-1]
    file = await photo.get_file()

    os.makedirs("downloads", exist_ok=True)

    file_path = os.path.join("downloads", f"{update.effective_user.id}_1.jpg")
    await file.download_to_drive(file_path)

    context.user_data["photo_path"] = file_path

    await update.message.reply_text(
        "Foto salva ✅\n\n"
        "Agora me manda o TEXTO do anúncio.\n\n"
        "Lembra: eu pego a PRIMEIRA linha como título e a PRIMEIRA linha com 'R$' como preço 😉"
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

    # Tenta gerar a arte e a legenda. Se der erro, avisa no próprio WhatsApp.
    try:
        output_path = montar_layout_instagram(photo_path, text, user_id)
        legenda = montar_legenda_padrao(text)
    except Exception as e:
        await update.message.reply_text(
            "Deu um erro interno ao montar a arte 😥\n\n"
            f"Detalhe técnico (me manda isso aqui):\n{e}"
        )
        return

    # Envia a arte
    try:
        with open(output_path, "rb") as img_file:
            await update.message.reply_photo(
                img_file,
                caption=(
                    "Tá aí sua arte pronta pra Instagram ✅\n\n"
                    "Na próxima mensagem eu te mando a legenda pra você copiar e colar. 👇"
                ),
            )
    except Exception as e:
        await update.message.reply_text(
            "Consegui gerar o arquivo, mas deu erro na hora de enviar a imagem 😥\n\n"
            f"Detalhe técnico (me manda isso aqui):\n{e}"
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
