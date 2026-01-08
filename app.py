import streamlit as st
from rembg import remove
from PIL import Image, ImageFilter, ImageOps, ImageEnhance  # 新增 ImageEnhance
import io
import traceback

st.set_page_config(page_title="AI 專業證件相 (進階調色版)", page_icon="👤")

st.title("📸 專業證件相自動轉換器")
st.markdown("現在你可以手動調校照片的光暗與對比度，確保面部清晰。")

# --- 側邊欄：功能選單 ---
st.sidebar.header("💡 影像亮度調校")
brightness_val = st.sidebar.slider("亮度 (Brightness)", 0.5, 1.5, 1.0, 0.05)
contrast_val = st.sidebar.slider("對比度 (Contrast)", 0.5, 1.5, 1.0, 0.05)

st.sidebar.divider()
st.sidebar.header("📏 尺寸與位置微調")
person_scale = st.sidebar.slider("人像縮放 (Zoom)", 0.5, 2.0, 1.0, 0.05)
vertical_move = st.sidebar.slider("上下移動", -300, 300, 0, 10)

st.sidebar.divider()
st.sidebar.header("🎨 背景設定")
bg_choice = st.sidebar.selectbox("選擇背景顏色", ["白色", "藍色", "粉紅色"])
color_dict = {"白色": (255, 255, 255), "藍色": (0, 191, 255), "粉紅色": (255, 192, 203)}

# --- 主程式 ---
uploaded_file = st.file_uploader("上傳相片", type=["jpg", "png", "jpeg"])

if uploaded_file:
    try:
        with st.spinner('正在處理影像...'):
            # 1. 讀取並校正旋轉
            raw_img = Image.open(uploaded_file)
            input_image = ImageOps.exif_transpose(raw_img)
            
            # 2. 預壓縮節省記憶體 [cite: 7]
            MAX_SIZE = 1200
            if max(input_image.size) > MAX_SIZE:
                input_image.thumbnail((MAX_SIZE, MAX_SIZE), Image.Resampling.LANCZOS)
            
            # 3. AI 去背 [cite: 6]
            img_byte_arr = io.BytesIO()
            input_image.save(img_byte_arr, format='PNG')
            output_bytes = remove(img_byte_arr.getvalue(), alpha_matting=True)
            
            foreground = Image.open(io.BytesIO(output_bytes)).convert("RGBA")

            # 4. 【新增：影像強化處理】
            # 調校亮度
            if brightness_val != 1.0:
                enhancer = ImageEnhance.Brightness(foreground)
                foreground = enhancer.enhance(brightness_val)
            
            # 調校對比度
            if contrast_val != 1.0:
                enhancer = ImageEnhance.Contrast(foreground)
                foreground = enhancer.enhance(contrast_val)

            # 5. 自動裁掉透明邊緣並進行縮放
            bbox = foreground.getbbox()
            if bbox:
                foreground = foreground.crop(bbox)

            target_w, target_h = 600, 800
            bg_rgb = color_dict[bg_choice]
            final_bg = Image.new("RGB", (target_w, target_h), bg_rgb).convert("RGBA")

            fg_w, fg_h = foreground.size
            base_scale = (target_h * 0.75) / fg_h
            final_scale = base_scale * person_scale
            
            new_w, new_h = int(fg_w * final_scale), int(fg_h * final_scale)
            foreground_res = foreground.resize((new_w, new_h), Image.Resampling.LANCZOS)

            # 6. 計算位置並合成
            paste_x = (target_w - new_w) // 2
            paste_y = (target_h - new_h) + vertical_move
            
            temp_layer = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
            temp_layer.paste(foreground_res, (paste_x, paste_y), foreground_res)
            final_bg = Image.alpha_composite(final_bg, temp_layer)

            # 7. 輸出
            result_img = final_bg.convert("RGB")
            st.image(result_img, caption="調整預覽", width=300)

            buf = io.BytesIO()
            result_img.save(buf, format="JPEG", quality=95)
            st.download_button(label="💾 下載證件相", data=buf.getvalue(), file_name="enhanced_id_photo.jpg", mime="image/jpeg")

    except Exception as e:
        st.error("處理失敗")
        st.expander("詳細報告").code(traceback.format_exc())