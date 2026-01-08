import streamlit as st
from rembg import remove
from PIL import Image, ImageFilter, ImageOps, ImageEnhance, ImageDraw # 新增 ImageDraw
import io
import traceback

st.set_page_config(page_title="AI 專業證件相 (排版修正版)", page_icon="👤")

# --- 側邊欄與原本邏輯保持一致 ---
st.sidebar.header("🖨️ 列印排版設定")
layout_choice = st.sidebar.radio(
    "選擇排版模式",
    ["單張相片", "一圖四格 (2x2) - 4R相紙", "一圖八格 (4x2) - 4R相紙"]
)

st.sidebar.divider()
st.sidebar.header("✨ 影像微調")
feather_val = st.sidebar.slider("邊緣羽化", 0.0, 5.0, 1.0, 0.5)
brightness_val = st.sidebar.slider("亮度", 0.5, 1.5, 1.0, 0.05)
contrast_val = st.sidebar.slider("對比度", 0.5, 1.5, 1.0, 0.05)
person_scale = st.sidebar.slider("人像縮放", 0.5, 2.0, 1.0, 0.05)
vertical_move = st.sidebar.slider("上下移動", -300, 300, 0, 10)

st.sidebar.divider()
st.sidebar.header("🎨 背景顏色")
bg_choice = st.sidebar.selectbox("選擇背景顏色", ["白色", "藍色", "粉紅色"])
color_dict = {"白色": (255, 255, 255), "藍色": (0, 191, 255), "粉紅色": (255, 192, 203)}

# --- 核心：全新的排版與裁切線函數 ---
def create_print_layout(single_img, mode):
    # 採用橫向 4R 畫布 (4x6 吋, 300 DPI) = 1800 x 1200 像素
    canvas_w, canvas_h = 1800, 1200
    canvas = Image.new("RGB", (canvas_w, canvas_h), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    
    # 取得單張圖比例
    sw, sh = single_img.size
    aspect = sw / sh

    if mode == "一圖四格 (2x2) - 4R相紙":
        # 2x2 模式下，每張相片寬度設定為約 500 像素
        target_w = 500
        target_h = int(target_w / aspect)
        img_resized = single_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        
        # 計算邊距以達到完全置中
        cols, rows = 2, 2
        gap_x, gap_y = 150, 100
        total_grid_w = cols * target_w + (cols - 1) * gap_x
        total_grid_h = rows * target_h + (rows - 1) * gap_y
        
        offset_x = (canvas_w - total_grid_w) // 2
        offset_y = (canvas_h - total_grid_h) // 2
        
        for r in range(rows):
            for c in range(cols):
                x = offset_x + c * (target_w + gap_x)
                y = offset_y + r * (target_h + gap_y)
                canvas.paste(img_resized, (x, y))
                # 畫上淡淡的裁切參考線
                draw.rectangle([x-1, y-1, x+target_w+1, y+target_h+1], outline=(220, 220, 220), width=2)

    elif mode == "一圖八格 (4x2) - 4R相紙":
        # 4x2 模式（每行4張，共2行）
        target_w = 350
        target_h = int(target_w / aspect)
        img_resized = single_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        
        cols, rows = 4, 2
        gap_x, gap_y = 60, 80
        total_grid_w = cols * target_w + (cols - 1) * gap_x
        total_grid_h = rows * target_h + (rows - 1) * gap_y
        
        offset_x = (canvas_w - total_grid_w) // 2
        offset_y = (canvas_h - total_grid_h) // 2
        
        for r in range(rows):
            for c in range(cols):
                x = offset_x + c * (target_w + gap_x)
                y = offset_y + r * (target_h + gap_y)
                canvas.paste(img_resized, (x, y))
                draw.rectangle([x-1, y-1, x+target_w+1, y+target_h+1], outline=(220, 220, 220), width=1)
                
    return canvas

# --- 主程式邏輯 (省略重複部分，確保 single_photo 生成後呼叫 layout) ---
uploaded_file = st.file_uploader("上傳相片", type=["jpg", "png", "jpeg"])

if uploaded_file:
    try:
        with st.spinner('處理中...'):
            raw_img = Image.open(uploaded_file)
            input_image = ImageOps.exif_transpose(raw_img)
            
            # (中間去背、色彩、羽化邏輯與之前相同...)
            # ... [此處省略部分重複代碼] ...
            # 建立單張 600x800
            target_w, target_h = 600, 800
            bg_rgb = color_dict[bg_choice]
            single_photo_rgba = Image.new("RGBA", (target_w, target_h), bg_rgb + (255,))
            
            # (計算人像縮放與位移...)
            img_byte_arr = io.BytesIO()
            input_image.save(img_byte_arr, format='PNG')
            output_bytes = remove(img_byte_arr.getvalue(), alpha_matting=True)
            foreground = Image.open(io.BytesIO(output_bytes)).convert("RGBA")
            
            # 色彩強化與羽化
            if brightness_val != 1.0: foreground = ImageEnhance.Brightness(foreground).enhance(brightness_val)
            if contrast_val != 1.0: foreground = ImageEnhance.Contrast(foreground).enhance(contrast_val)
            if feather_val > 0:
                r, g, b, a = foreground.split()
                a = a.filter(ImageFilter.GaussianBlur(radius=feather_val))
                foreground.putalpha(a)
                
            bbox = foreground.getbbox()
            if bbox: foreground = foreground.crop(bbox)
            
            fg_w, fg_h = foreground.size
            base_scale = (target_h * 0.75) / fg_h
            final_scale = base_scale * person_scale
            new_w, new_h = int(fg_w * final_scale), int(fg_h * final_scale)
            foreground_res = foreground.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            paste_x = (target_w - new_w) // 2
            paste_y = (target_h - new_h) + vertical_move
            
            temp_layer = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
            temp_layer.paste(foreground_res, (paste_x, paste_y), foreground_res)
            single_photo = Image.alpha_composite(single_photo_rgba, temp_layer).convert("RGB")

            # 根據選擇顯示
            if layout_choice == "單張相片":
                st.image(single_photo, width=300)
                final_output = single_photo
            else:
                final_output = create_print_layout(single_photo, layout_choice)
                st.image(final_output, use_container_width=True)

            # 下載
            buf = io.BytesIO()
            final_output.save(buf, format="JPEG", quality=98)
            st.download_button(label=f"💾 下載 {layout_choice}", data=buf.getvalue(), file_name="id_photo.jpg")

    except Exception as e:
        st.error("處理失敗")
        st.expander("詳細日誌").code(traceback.format_exc())