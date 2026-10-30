from PIL import Image, ImageDraw
import os

os.makedirs('scratch', exist_ok=True)

def generate_avatar(bg_color, fg_color, filename):
    # Render at 4x resolution (2048x2048) for super smooth anti-aliased curves
    size = 2048
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx, cy = size // 2, size // 2
    r = size // 2 - 32

    # Draw background circle if bg_color is provided
    if bg_color:
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=bg_color)

    # Head: circle centered at cx, cy - 180, radius ~320
    head_r = 310
    head_cy = cy - 220
    draw.ellipse([cx - head_r, head_cy - head_r, cx + head_r, head_cy + head_r], fill=fg_color)

    # Shoulders/Torso: smooth rounded shape or arc
    # Semicircle / rounded curve from cy + 220 down to bottom of circle
    # Using an ellipse clipped to the circular boundary
    torso_w = 680
    torso_h = 560
    torso_cy = cy + 480
    
    # Create mask for torso
    torso_img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    torso_draw = ImageDraw.Draw(torso_img)
    torso_draw.ellipse([cx - torso_w, torso_cy - torso_h, cx + torso_w, torso_cy + torso_h], fill=fg_color)

    # If background circle exists, clip torso to circle
    if bg_color:
        clip_mask = Image.new('L', (size, size), 0)
        clip_draw = ImageDraw.Draw(clip_mask)
        clip_draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
        torso_img.putalpha(Image.composite(torso_img.split()[3], Image.new('L', (size, size), 0), clip_mask))

    img.alpha_composite(torso_img)

    # Downsample to 512x512 with LANCZOS
    final_img = img.resize((512, 512), Image.Resampling.LANCZOS)
    final_img.save(filename, 'PNG', optimize=True)
    print(f'Saved avatar: {filename}')

# Option 1: Classic neutral slate dark (slate-700 bg #334155, slate-400 fg #94a3b8)
generate_avatar((51, 65, 85, 255), (148, 163, 184, 255), 'scratch/avatar_slate_dark.png')

# Option 2: Classic neutral light gray (gray-200 bg #e2e8f0, gray-500 fg #64748b)
generate_avatar((226, 232, 240, 255), (100, 116, 139, 255), 'scratch/avatar_classic_gray.png')

# Option 3: Modern neutral medium (gray-300 bg #cbd5e1, gray-600 fg #475569)
generate_avatar((203, 213, 225, 255), (71, 85, 105, 255), 'scratch/avatar_neutral_mid.png')

# Option 4: Transparent background with neutral silver/gray head and body (#94a3b8)
generate_avatar(None, (148, 163, 184, 255), 'scratch/avatar_transparent_gray.png')
