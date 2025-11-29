# ==========================
# IMPORTS NECESSÁRIOS
# ==========================
from PIL import Image, ImageDraw, ImageFont
import textwrap
import os
from typing import List


# ==========================
# FUNÇÃO DE CROP INTELIGENTE
# ==========================
def crop_fill(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Corta e dá zoom mantendo o centro, no formato target_w x target_h."""
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


# ==========================
# FUNÇÃO DO LAYOUT DO INSTAGRAM
# ==========================
def montar_layout_instagram(photos: List[str], caption: str, user_id: int) -> str:
    """
    Layout:
    - 1 foto grande em cima (620px)
    - 2 fotos lado a lado maiores (320px)
    - faixa de texto mais fina (140px)
    A foto ocupa o máximo possível da tela.
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
    # FOTOS SECUNDÁRIAS (320px)
    # ------------------------------------------------------------
    thumbs = photos[1:3]

    thumb_area_top = 620
    faixa_h = 140
    thumb_area_height = 1080 - thumb_area_top - faixa_h  # altura exata das 2 fotos

    margin_x = 12
    slot_w = (1080 - 3 * margin_x) // 2
    slot_h = thumb_area_height  # 320px

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
    except:
        font_title = ImageFont.load_default()
        font_body = ImageFont.load_default()

    # título + bullets
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
            draw.text((text_x, text_y), prefix + line, font=font_body, fill="#DCDCDC")
            text_y += 34
        text_y += 4

    # Salvar o arquivo
    os.makedirs("outputs", exist_ok=True)
    output_path = os.path.join("outputs", f"{user_id}_post_instagram.jpg")
    canvas.save(output_path, "JPEG", quality=90)

    return output_path
