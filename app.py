import streamlit as st
from rembg import remove
from PIL import Image, ImageFilter, ImageOps, ImageEnhance, ImageDraw
import io
import gc # 新增記憶體清理工具
import traceback

st.set_page_config(page_title="AI 專業證件相 (輕量穩定版)", page_icon="👤")

st.title("📸 專業證件相自動轉換器")
st.info("已開啟大圖保護模式：自動優化記憶體以防止崩潰。")

# --- 側邊欄 ---
st.sidebar.header("🖨️ 排版模式")
layout_choice = st.sidebar.radio("選擇模式", ["單張相片", "一圖四格 (2x2)", "一圖八格 (4x2)"])

st.sidebar.divider()
st.sidebar.header("✨ 精細調整")
feather_val = st.sidebar.slider("邊緣羽化", 0.0, 3.0, 1.0, 0.5)
brightness_val = st.sidebar.slider("亮度", 0.7, 1.3, 1.0, 0.05)
contrast_val = st.sidebar.slider("對比度", 0.7, 1.3, 1.0, 0.05)

st.sidebar.divider()
st.sidebar.header("📏 尺寸與位置")
person_scale = st.sidebar.slider("人像縮放", 0.5, 2.0, 1.0, 0.05)
vertical_move = st.sidebar.slider("上下移動", -200, 200, 0, 10)

bg_choice = st.sidebar.selectbox("背景顏色", ["白色", "藍色", "粉紅色"])
color_dict = {"白色": (255, 255, 255), "藍色": (0, 191, 255), "粉紅色": (255, 192, 203)}

# --- 核心函數：排版 ---
def create_print_layout(single_img, mode):
    canvas_w, canvas_h = 1800, 1200 # 4R 橫向
    canvas = Image.new("RGB", (canvas_w, canvas_h), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    sw, sh = single_img.size
    aspect = sw / sh

    if "四格" in mode:
        tw = 500
        th = int(tw / aspect)
        img = single_img.resize((tw, th), Image.Resampling.LANCZOS)
        gap_x, gap_y = 150, 100
        for r in range(2):
            for c in range(2):
                x = (canvas_w - (2*tw + gap_x))//2 + c*(tw+gap_x)
                y = (canvas_h - (2*th + gap_y))//2 + r*(th+gap_y)
                canvas.paste(img, (x, y))
                draw.rectangle([x, y, x+tw, y+th], outline=(230, 230, 230))
    elif "八格" in mode:
        tw = 350
        th = int(tw / aspect)
        img = single_img.resize((tw, th), Image.Resampling.LANCZOS)
        gap_x, gap_y = 60, 80
        for r in range(2):
            for c in range(4):
                x = (canvas_w - (4*tw + 3*gap_x))//2 + c*(tw+gap_x)
                y = (canvas_h - (2*th + gap_y))//2 + r*(th+gap_y)
                canvas.paste(img, (x, y))
                draw.rectangle([x, y, x+tw, y+th], outline=(230, 230, 230))
    return canvas

# --- 主程式 ---
uploaded_file = st.file_uploader("上傳相片", type=["jpg", "png", "jpeg"])

if uploaded_file:
    try:
        with st.spinner('AI 處理中...'):
            # 1. 讀取並【立刻強制壓縮】
            raw_img = Image.open(uploaded_file)
            raw_img = ImageOps.exif_transpose(raw_img)
            
            # 將解析度限制在 1000px 以內 (記憶體保護關鍵)
            if max(raw_img.size) > 1000:
                raw_img.thumbnail((1000, 1000), Image.Resampling.LANCZOS)
            
            # 2. 轉為 JPEG 格式處理 (比 PNG 更省記憶體)
            temp_buffer = io.BytesIO()
            raw_img.convert("RGB").save(temp_buffer, format="JPEG", quality=85)
            
            # 3. 執行 AI 去背 (關閉 alpha_matting 以防止崩潰)
            output_bytes = remove(temp_buffer.getvalue())
            foreground = Image.open(io.BytesIO(output_bytes)).convert("RGBA")
            
            # 釋放原始圖片記憶體
            del raw_img
            gc.collect()

            # 4. 色彩與羽化
            if brightness_val != 1.0:
                foreground = ImageEnhance.Brightness(foreground).enhance(brightness_val)
            if contrast_val != 1.0:
                foreground = ImageEnhance.Contrast(foreground).enhance(contrast_val)
            if feather_val > 0:
                r, g, b, a = foreground.split()
                a = a.filter(ImageFilter.GaussianBlur(radius=feather_val))
                foreground.putalpha(a)

            # 5. 裁切與排版
            bbox = foreground.getbbox()
            if bbox: foreground = foreground.crop(bbox)

            target_w, target_h = 600, 800
            bg_color = color_dict[bg_choice]
            single_photo = Image.new("RGBA", (target_w, target_h), bg_color + (255,))
            
            fg_w, fg_h = foreground.size
            final_scale = ((target_h * 0.75) / fg_h) * person_scale
            nw, nh = int(fg_w * final_scale), int(fg_h * final_scale)
            foreground_res = foreground.resize((nw, nh), Image.Resampling.LANCZOS)
            
            px = (target_w - nw) // 2
            py = (target_h - nh) + vertical_move
            
            tmp = Image.new("RGBA", (target_w, target_h), (0,0,0,0))
            tmp.paste(foreground_res, (px, py), foreground_res)
            single_result = Image.alpha_composite(single_photo, tmp).convert("RGB")

            # 6. 輸出
            if layout_choice == "單張相片":
                final_output = single_result
                st.image(final_output, width=300)
            else:
                final_output = create_print_layout(single_result, layout_choice)
                st.image(final_output, use_container_width=True)

            buf = io.BytesIO()
            final_output.save(buf, format="JPEG", quality=95)
            st.download_button("💾 下載相片", buf.getvalue(), "photo.jpg", "image/jpeg")

    except Exception as e:
        st.error("伺服器記憶體溢出，請嘗試先將手機照片截圖再上傳，或換一張較小的照片。")
        st.expander("錯誤代碼").code(traceback.format_exc())