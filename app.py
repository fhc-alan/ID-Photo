import streamlit as st
from rembg import remove
from PIL import Image, ImageFilter, ImageOps  # 新增 ImageOps
import io
import traceback

st.set_page_config(page_title="AI 證件相修復版", page_icon="👤")

st.title("📸 專業證件相自動轉換器")
st.markdown("已修正手機照片旋轉與比例不正確的問題。")

# --- 側邊欄 ---
st.sidebar.header("設定")
bg_choice = st.sidebar.selectbox("選擇背景顏色", ["白色", "藍色", "粉紅色"])
color_dict = {"白色": (255, 255, 255), "藍色": (0, 191, 255), "粉紅色": (255, 192, 203)}
edge_smoothness = st.sidebar.slider("邊緣平滑度", 0, 5, 1)

# --- 主程式 ---
uploaded_file = st.file_uploader("上傳相片", type=["jpg", "png", "jpeg"])

if uploaded_file:
    try:
        with st.spinner('正在分析照片方向與去背...'):
            # 1. 讀取圖片並【自動校正旋轉】
            raw_img = Image.open(uploaded_file)
            input_image = ImageOps.exif_transpose(raw_img) # 關鍵：這行會修正手機拍攝的角度
            
            # 2. 預壓縮以節省記憶體
            MAX_SIZE = 1500
            if max(input_image.size) > MAX_SIZE:
                input_image.thumbnail((MAX_SIZE, MAX_SIZE), Image.Resampling.LANCZOS)
            
            # 3. 執行 AI 去背
            img_byte_arr = io.BytesIO()
            input_image.save(img_byte_arr, format='PNG')
            output_bytes = remove(
                img_byte_arr.getvalue(),
                alpha_matting=True,
                alpha_matting_foreground_threshold=240,
                alpha_matting_background_threshold=10,
                alpha_matting_erode_size=3
            )
            
            foreground = Image.open(io.BytesIO(output_bytes)).convert("RGBA")

            # 4. 邊緣羽化
            if edge_smoothness > 0:
                r, g, b, a = foreground.split()
                a = a.filter(ImageFilter.GaussianBlur(radius=edge_smoothness))
                foreground.putalpha(a)

            # 5. 建立標準 3:4 背景 (600x800)
            target_w, target_h = 600, 800
            bg_rgb = color_dict[bg_choice]
            final_bg = Image.new("RGB", (target_w, target_h), bg_rgb).convert("RGBA")

            # 6. 【優化縮放邏輯】：確保人像完整且置中
            fg_w, fg_h = foreground.size
            # 縮放至高度佔 75%，但若寬度超出則改以寬度為準
            scale_h = (target_h * 0.75) / fg_h
            scale_w = (target_w * 0.9) / fg_w
            scale = min(scale_h, scale_w)
            
            new_w, new_h = int(fg_w * scale), int(fg_h * scale)
            foreground_res = foreground.resize((new_w, new_h), Image.Resampling.LANCZOS)

            # 將人像置於背景正中央下方
            paste_x = (target_w - new_w) // 2
            paste_y = (target_h - new_h) // 2 + 50 # 稍微向下偏移更像證件照
            
            # 建立暫時圖層來合成，避免超出範圍的問題
            temp_layer = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
            temp_layer.paste(foreground_res, (paste_x, paste_y), foreground_res)
            final_bg = Image.alpha_composite(final_bg, temp_layer)

            # 7. 輸出結果
            result_img = final_bg.convert("RGB")
            st.image(result_img, caption="修正後的證件相", width=300)

            buf = io.BytesIO()
            result_img.save(buf, format="JPEG", quality=95)
            st.download_button(label="💾 下載修正版證件相", data=buf.getvalue(), file_name="fixed_id_photo.jpg", mime="image/jpeg")

    except Exception as e:
        st.error("處理失敗")
        st.expander("詳細報告").code(traceback.format_exc())