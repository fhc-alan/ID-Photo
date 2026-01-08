import streamlit as st
from rembg import remove
from PIL import Image, ImageFilter, ImageOps, ImageEnhance
import io
import traceback

st.set_page_config(page_title="AI 專業證件相排版版", page_icon="👤")

st.title("📸 專業證件相自動轉換器")
st.markdown("現在已加入 **4R 排版功能**，方便直接去印相店列印！")

# --- 側邊欄：功能選單 ---
st.sidebar.header("🖨️ 列印排版設定")
layout_choice = st.sidebar.radio(
    "選擇排版模式",
    ["單張相片", "一圖四格 (2x2) - 4R相紙", "一圖八格 (4x2) - 4R相紙"]
)

st.sidebar.divider()
st.sidebar.header("✨ 邊緣與色彩")
feather_val = st.sidebar.slider("邊緣羽化 (Feathering)", 0.0, 5.0, 1.0, 0.5)
brightness_val = st.sidebar.slider("亮度 (Brightness)", 0.5, 1.5, 1.0, 0.05)
contrast_val = st.sidebar.slider("對比度 (Contrast)", 0.5, 1.5, 1.0, 0.05)

st.sidebar.divider()
st.sidebar.header("📏 尺寸與位置")
person_scale = st.sidebar.slider("人像縮放 (Zoom)", 0.5, 2.0, 1.0, 0.05)
vertical_move = st.sidebar.slider("上下移動", -300, 300, 0, 10)

st.sidebar.divider()
st.sidebar.header("🎨 背景顏色")
bg_choice = st.sidebar.selectbox("選擇背景顏色", ["白色", "藍色", "粉紅色"])
color_dict = {"白色": (255, 255, 255), "藍色": (0, 191, 255), "粉紅色": (255, 192, 203)}

# --- 輔助函數：建立 4R 排版 ---
def create_print_layout(single_img, mode):
    # 標準 4R (4"x6") 比例，約為 1200x1800 像素 (300 DPI)
    canvas_w, canvas_h = 1800, 1200 # 橫向 4R
    canvas = Image.new("RGB", (canvas_w, canvas_h), (255, 255, 255))
    
    img_w, img_h = single_img.size # 600x800
    
    if mode == "一圖四格 (2x2) - 4R相紙":
        # 2x2 排列，每張稍作縮放以留白
        display_img = single_img.resize((500, 667), Image.Resampling.LANCZOS)
        w, h = display_img.size
        # 計算座標
        positions = [(400, 200), (900, 200), (400, 700), (900, 700)]
        for pos in positions:
            canvas.paste(display_img, pos)
            
    elif mode == "一圖八格 (4x2) - 4R相紙":
        # 4x2 排列
        display_img = single_img.resize((400, 533), Image.Resampling.LANCZOS)
        w, h = display_img.size
        # 兩排四列
        for row in range(2):
            for col in range(4):
                x = 50 + col * (w + 40)
                y = 50 + row * (h + 50)
                canvas.paste(display_img, (x, y))
                
    return canvas

# --- 主程式 ---
uploaded_file = st.file_uploader("上傳相片", type=["jpg", "png", "jpeg"])

if uploaded_file:
    try:
        with st.spinner('正在進行高級處理...'):
            raw_img = Image.open(uploaded_file)
            input_image = ImageOps.exif_transpose(raw_img)
            
            MAX_SIZE = 1200
            if max(input_image.size) > MAX_SIZE:
                input_image.thumbnail((MAX_SIZE, MAX_SIZE), Image.Resampling.LANCZOS)
            
            img_byte_arr = io.BytesIO()
            input_image.save(img_byte_arr, format='PNG')
            output_bytes = remove(img_byte_arr.getvalue(), alpha_matting=True)
            
            foreground = Image.open(io.BytesIO(output_bytes)).convert("RGBA")

            # 色彩強化
            if brightness_val != 1.0:
                foreground = ImageEnhance.Brightness(foreground).enhance(brightness_val)
            if contrast_val != 1.0:
                foreground = ImageEnhance.Contrast(foreground).enhance(contrast_val)

            # 羽化
            if feather_val > 0:
                r, g, b, a = foreground.split()
                a = a.filter(ImageFilter.GaussianBlur(radius=feather_val))
                foreground.putalpha(a)

            # 裁邊
            bbox = foreground.getbbox()
            if bbox:
                foreground = foreground.crop(bbox)

            # 建立單張 3:4 證件相 (600x800)
            target_w, target_h = 600, 800
            bg_rgb = color_dict[bg_choice]
            single_photo = Image.new("RGB", (target_w, target_h), bg_rgb).convert("RGBA")

            fg_w, fg_h = foreground.size
            base_scale = (target_h * 0.75) / fg_h
            final_scale = base_scale * person_scale
            new_w, new_h = int(fg_w * final_scale), int(fg_h * final_scale)
            foreground_res = foreground.resize((new_w, new_h), Image.Resampling.LANCZOS)

            paste_x = (target_w - new_w) // 2
            paste_y = (target_h - new_h) + vertical_move
            
            temp_layer = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
            temp_layer.paste(foreground_res, (paste_x, paste_y), foreground_res)
            single_photo = Image.alpha_composite(single_photo, temp_layer).convert("RGB")

            # --- 根據選擇輸出最終結果 ---
            if layout_choice == "單張相片":
                final_output = single_photo
                st.image(final_output, caption="預覽 (單張模式)", width=300)
            else:
                final_output = create_print_layout(single_photo, layout_choice)
                st.image(final_output, caption=f"預覽 ({layout_choice})", use_container_width=True)

            # 下載按鈕
            buf = io.BytesIO()
            final_output.save(buf, format="JPEG", quality=98)
            st.download_button(
                label=f"💾 下載 {layout_choice} 檔案",
                data=buf.getvalue(),
                file_name=f"id_photo_{layout_choice}.jpg",
                mime="image/jpeg"
            )

    except Exception as e:
        st.error("處理失敗")
        st.expander("詳細日誌").code(traceback.format_exc())