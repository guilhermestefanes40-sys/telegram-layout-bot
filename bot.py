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
        img = img.crop((0, offset, img_w, offset +_
