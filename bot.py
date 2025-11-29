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

# Token do bot vem da variável de ambiente no Railway
TOKEN = os.environ.get("BOT_TOKEN")


# ---------- Funções de layout / arte ----------

def montar_layout_instagram(photos: List[str], caption: str, user_id: int) -> str:
    """
    Gera uma imagem 1080x1080 com:
    - 1 foto grande em cima (principal)
    - 2 fotos menores embaixo (lado a lado)
    - faixa inferior escura com título + bullets
    """
    size = (1080, 1080)
    canvas = Image.new("RGB", size, (255, 255, 255))

    # --- FOTO PRINCIPAL (topo) ---
    main_img = Image.open(photos[0]).convert("RGB")
    main_max_w, main_max_h = 1080, 550  # ocupa boa parte de cima
    main_img.thumbnail((main_max_w, main_max_h))
    main_x = (size[0] - main_img.width) // 2
    main_y = 0
    canvas.paste(main_img, (main_x, main_y))

    # --- FOTOS SECUNDÁRIAS (embaixo, lado a lado) ---
    thumbs = photos[1:3]  # exatamente 2 (porque vamos exigir 3 no fluxo)
    thumb_margin = 10
    thumb_area_top = 560
    thumb_area_height = 250

    if len(thumbs) > 0:
        thumb_width = (size[0] - (3 * thumb_margin)) // 2
        thumb_height = thumb_area_height - 2 * thumb_margin

        x_positions = [thumb_margin, thumb_margin * 2 + thumb_width]
        for idx, path in enumerate(thumbs):
            if idx > 1:
                break
            try:
                img = Image.open(path).convert("RGB")
                img.thumbnail((thumb_width, thumb_height))
                x = x_positions[idx] + (thumb_width - img.width) // 2
                y = thumb_area_top + thumb_margin + (thumb_height - img.height) // 2
                canvas.paste(img, (x, y))
            except Exception:
                continue

    # --- FAIXA INFERIOR DE TEXTO ---
    faixa_altura = 180
    faixa_top = size[1] - faixa_altura
    draw = ImageDraw.Draw(canvas)
    # faixa escura neutra
    draw.rectangle([(0, faixa_top), (size[0], size[1])], fill=(20, 20, 20))

    # Tenta carregar fonte "bonitinha", senão usa default
    try:
        font_title = ImageFont.truetype("arial.ttf", 52)
        font_body = ImageFont.truetype("arial.ttf", 36)
    except Exception:
        font_title = ImageFont.load_default()
        font_body = ImageFont.load_default()

    # Quebrar legenda: primeira linha = título, resto = bullets
    lines = [l.strip() for l in caption.splitlines() if l.strip()]
    title = lines[0] if lines else "Anúncio"
    bullets = lines[1:] if len(lines) > 1 else []

    # Área de texto na faixa
    text_x = 40
    text_y = faixa_top + 20
    max_width_chars = 28  # ajusta se quiser mais ou menos quebrado

    # Título (em branco)
    draw.text((text_x, text_y), title, font=font_title, fill=(255, 255, 255))
    text_y += 60

    # Bullets (em cinza claro)
    for b in bullets:
        wrapped = textwrap.wrap(b, width=max_width_chars)
        for i, wline in enumerate(wrapped):
            prefix = "• " if i == 0 else "  "
            draw.text(
                (text_x, text_y),
                prefix + wline,
                font=font_body,
                fill=(230, 230, 230),
            )
            text_y += 40
        text_y += 6

    # Caminho de saída
    os.makedirs("outputs", exist_ok=True)
    output_path = os.path.join("outputs", f"{user_id}_post_instagram.jpg")
    canvas.save(output_path, "JPEG", quality=90)
    return output_path


def montar_legenda_padrao(caption: str) -> str:
    """
    Usa o texto que você mandou e formata num padrão:
    - primeira linha = título
    - demais linhas viram bullets
    - CTA no final
    """
    lines = [l.strip() for l in caption.splitlines() if l.strip()]
    if not lines:
        return "Anúncio 🚛\n\n📲 Chama no direct ou WhatsApp para mais informações."

    title = lines[0]
    bullets = lines[1:]

    partes = [f"{title}"]
    if bullets:
        partes.append("")
        for b in bullets:
            partes.append(f"• {b}")
    partes.append("")
    partes.append("📲 Chama no direct ou WhatsApp para mais informações.")

    return "\n".join(partes)


# ---------- Handlers do bot ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reseta o fluxo e explica o que fazer."""
    context.user_data.clear()
    nome = update.effective_user.first_name or "amigo"
    msg = (
        f"Fala, {nome}! 👋\n\n"
        "Vou montar seu post no seguinte layout:\n"
        "- 1 foto grande em cima\n"
        "- 2 fotos menores embaixo\n"
        "- faixa inferior com título + bullets\n\n"
        "📸 Me manda AGORA a PRIMEIRA FOTO (principal).\n"
        "Depois manda mais 2 fotos (detalhes). Serão 3 no total.\n"
        "Quando terminar as 3 fotos, me manda o TEXTO nesse formato:\n\n"
        "Linha 1: Título (ex: Scania R-480 2019 6x4)\n"
        "Linhas seguintes: itens do anúncio (km, estado, local, preço etc.)"
    )
    await update.message.reply_text(msg)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Recebe até 3 fotos. Depois disso, só aceita texto."""
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
    """Quando o usuário manda o texto após as 3 fotos."""
    text = update.message.text.strip()
    photos = context.user_data.get("photos", [])

    # Se não tem 3 fotos ainda
    if len(photos) < 3:
        await update.message.reply_text(
            "Pra eu montar esse layout, preciso de 3 FOTOS primeiro 📸\n"
            "Me manda as fotos e depois o TEXTO."
        )
        return

    user_id = update.effective_user.id

    # Monta a arte com 3 fotos
    output_path = montar_layout_instagram(photos, text, user_id)

    # Monta a legenda padrão
    legenda = montar_legenda_padrao(text)

    # Envia a arte pronta
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

    # Envia a legenda em texto separado
    await update.message.reply_text(legenda)

    # Limpa os dados pra um próximo post
    context.user_data.clear()


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
