from typing import List
def montar_layout_instagram(photos: List[str], caption: str, user_id: int) -> str:
    """
    Gera uma imagem 1080x1080 com:
    - crop inteligente da foto principal
    - crop inteligente das 2 fotos menores
    - faixa inferior com texto
    """
    size = (1080, 1080)
    canvas = Image.new("RGB", size, (255, 255, 255))

    # --- FOTO PRINCIPAL (620px de altura) ---
    main_area = (1080, 620)
    main_img = Image.open(photos[0]).convert("RGB")
    main_img = crop_fill(main_img, *main_area)  # <-- agora tem zoom + corte
    canvas.paste(main_img, (0, 0))

    # --- FOTOS SECUNDÁRIAS (2 fotos lado a lado, 260px altura cada) ---
    thumb_area_top = 620
    thumb_area_height = 260
    thumbs = photos[1:3]

    thumb_margin = 12
    slot_w = (1080 - 3 * thumb_margin) // 2
    slot_h = thumb_area_height - 2 * thumb_margin

    x_positions = [thumb_margin, 2 * thumb_margin + slot_w]

    for idx, p in enumerate(thumbs[:2]):
        img = Image.open(p).convert("RGB")
        img = crop_fill(img, slot_w, slot_h)  # <-- crop inteligente
        x = x_positions[idx]
        y = thumb_area_top + thumb_margin
        canvas.paste(img, (x, y))

    # --- FAIXA DE TEXTO ---
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

    draw.text((text_x, text_y), title, font=font_title, fill="white")
    text_y += 60

    for b in bullets:
        wrapped = textwrap.wrap(b, width=28)
        for i, wline in enumerate(wrapped):
            prefix = "• " if i == 0 else "  "
            draw.text((text_x, text_y), prefix + wline, font=font_body, fill="#DCDCDC")
            text_y += 40
        text_y += 6

    os.makedirs("outputs", exist_ok=True)
    output_path = f"outputs/{user_id}_post_instagram.jpg"
    canvas.save(output_path, "JPEG", quality=90)

    return output_path
