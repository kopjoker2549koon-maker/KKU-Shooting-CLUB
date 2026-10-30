from PIL import Image, ImageDraw
import os

def create_default_gray_avatar(output_paths):
    size = 2048
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx, cy = size // 2, size // 2
    r = size // 2 - 40

    # Neutral soft gray circle background (RGB: 228, 230, 235)
    bg_color = (228, 230, 235, 255)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=bg_color)

    # Neutral medium gray head and shoulders (RGB: 120, 125, 135)
    fg_color = (120, 125, 135, 255)

    # Head: radius = 320, centered at cx, cy - 200
    head_r = 320
    head_cy = cy - 200
    draw.ellipse([cx - head_r, head_cy - head_r, cx + head_r, head_cy + head_r], fill=fg_color)

    # Torso/Shoulders: smooth ellipse positioned at cy + 500
    torso_img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    torso_draw = ImageDraw.Draw(torso_img)
    torso_w = 690
    torso_h = 580
    torso_cy = cy + 500
    torso_draw.ellipse([cx - torso_w, torso_cy - torso_h, cx + torso_w, torso_cy + torso_h], fill=fg_color)

    # Clip torso to the outer circle
    clip_mask = Image.new('L', (size, size), 0)
    clip_draw = ImageDraw.Draw(clip_mask)
    clip_draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    
    torso_alpha = Image.composite(torso_img.split()[3], Image.new('L', (size, size), 0), clip_mask)
    torso_img.putalpha(torso_alpha)

    img.alpha_composite(torso_img)

    # Downsample to 512x512 with LANCZOS
    final_512 = img.resize((512, 512), Image.Resampling.LANCZOS)

    for p in output_paths:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        final_512.save(p, 'PNG', optimize=True)
        print(f'Successfully saved default avatar to: {p}')

create_default_gray_avatar(['static/default_avatar.png', 'static/profiles/default_avatar.png'])
