import streamlit as st
from rembg import remove
from PIL import Image, ImageFilter, ImageOps, ImageEnhance
import io
import traceback

st.set_page_config(page_title="AI 專業證件相 (完全體)", page_icon="👤")

st.title("📸 專業證件相自動轉換器")
st.markdown("現在已整合：邊緣羽化、光暗調校、縮放位移及旋轉修正。")

# --- 側邊欄：全方位調校工具 ---
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

# --- 主程式 ---
uploaded_file = st.file_uploader("上傳相片", type=["jpg", "png", "jpeg"])

if uploaded_file:
    try:
        with st.spinner('正在精細處理影像...'):
            # 1. 讀取並校正旋轉 (EXIF)
            raw_img = Image.open(uploaded_file)
            input_image = ImageOps.exif_transpose(raw_img)
            
            # 2. 預壓縮節省雲端記憶體
            MAX_SIZE = 1200
            if max(input_image.size) > MAX_SIZE:
                input_image.thumbnail((MAX_SIZE, MAX_SIZE), Image.Resampling.LANCZOS)
            
            # 3. AI 去背
            img_byte_arr = io.BytesIO()
            input_image.save(img_byte_arr, format='PNG')
            # 這裡我們稍微降低 alpha_matting 參數以配合手動羽化，達到最自然效果
            output_bytes = remove(img_byte_arr.getvalue(), alpha_matting=True)
            
            foreground = Image.open(io.BytesIO(output_bytes)).convert("RGBA")

            # 4. 【亮度與對比度調校】
            if brightness_val != 1.0:
                foreground = ImageEnhance.Brightness(foreground).enhance(brightness_val)
            if contrast_val != 1.0:
                foreground = ImageEnhance.Contrast(foreground).enhance(contrast_val)

            # 5. 【關鍵：邊緣羽化處理】
            if feather_val > 0:
                # 分離通道，對 Alpha 通道執行高斯模糊
                r, g, b, a = foreground.split()
                a = a.filter(ImageFilter.GaussianBlur(radius=feather_val))
                foreground.putalpha(a)

            # 6. 自動裁掉多餘透明邊緣
            bbox = foreground.getbbox()
            if bbox:
                foreground = foreground.crop(bbox)

            # 7. 建立標準背景與合成
            target_w, target_h = 600, 800
            bg_rgb = color_dict[bg_choice]
            final_bg = Image.new("RGB", (target_w, target_h), bg_rgb).convert("RGBA")

            # 計算縮放
            fg_w, fg_h = foreground.size
            base_scale = (target_h * 0.75) / fg_h
            final_scale = base_scale * person_scale
            
            new_w, new_h = int(fg_w * final_scale), int(fg_h * final_scale)
            foreground_res = foreground.resize((new_w, new_h), Image.Resampling.LANCZOS)

            # 計算位置
            paste_x = (target_w - new_w) // 2
            paste_y = (target_h - new_h) + vertical_move
            
            # 合成圖層
            temp_layer = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
            temp_layer.paste(foreground_res, (paste_x, paste_y), foreground_res)
            final_bg = Image.alpha_composite(final_bg, temp_layer)

            # 8. 輸出結果
            result_img = final_bg.convert("RGB")
            st.image(result_img, caption="最終效果預覽", width=300)

            # 下載按鈕
            buf = io.BytesIO()
            result_img.save(buf, format="JPEG", quality=95)
            st.download_button(
                label="💾 下載這張證件相",
                data=buf.getvalue(),
                file_name="pro_id_photo.jpg",
                mime="image/jpeg"
            )

    except Exception as e:
        st.error("處理過程中發生錯誤")
        st.expander("詳細日誌").code(traceback.format_exc())