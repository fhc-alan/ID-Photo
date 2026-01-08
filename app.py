import streamlit as st
from rembg import remove
from PIL import Image, ImageFilter
import io
import numpy as np
import traceback

# 網頁設定
st.set_page_config(page_title="專業 AI 證件相工具", page_icon="👤")

st.title("📸 專業證件相自動轉換器")
st.markdown("針對邊緣細節與背景合成進行了穩定性優化。")

# --- 側邊欄設定 ---
st.sidebar.header("自定義選項")
bg_choice = st.sidebar.selectbox(
    "選擇背景顏色",
    ["白色", "藍色", "粉紅色"]
)

color_dict = {
    "白色": (255, 255, 255),
    "藍色": (0, 191, 255),
    "粉紅色": (255, 192, 203)
}

edge_smoothness = st.sidebar.slider("邊緣平滑度 (羽化)", 0, 5, 1)

# --- 主程式邏輯 ---
uploaded_file = st.file_uploader("上傳自拍照 (JPG/PNG)", type=["jpg", "png", "jpeg"])

if uploaded_file:
    try:
        with st.spinner('AI 正在處理中，請稍候...'):
            # 1. 讀取圖片
            input_image = Image.open(uploaded_file)
            
            # 2. 轉為 Bytes
            img_byte_arr = io.BytesIO()
            input_image.save(img_byte_arr, format='PNG')
            image_bytes = img_byte_arr.getvalue()

            # 3. 執行 AI 去背 (調整參數以適應雲端環境)
            output_bytes = remove(
                image_bytes,
                alpha_matting=True,
                alpha_matting_foreground_threshold=240,
                alpha_matting_background_threshold=10,
                alpha_matting_erode_size=5
            )
            
            foreground = Image.open(io.BytesIO(output_bytes)).convert("RGBA")

            # 4. 邊緣羽化處理
            if edge_smoothness > 0:
                r, g, b, a = foreground.split()
                a = a.filter(ImageFilter.GaussianBlur(radius=edge_smoothness))
                foreground.putalpha(a)

            # 5. 建立 3:4 背景 (先建 RGB 再轉 RGBA 確保白色不報錯)
            target_w, target_h = 600, 800
            bg_rgb = color_dict[bg_choice]
            final_bg = Image.new("RGB", (target_w, target_h), bg_rgb).convert("RGBA")

            # 6. 處理人像縮放 (加入版本相容性寫法)
            fg_w, fg_h = foreground.size
            scale = (target_h * 0.75) / fg_h
            new_w, new_h = int(fg_w * scale), int(fg_h * scale)
            
            try:
                # 嘗試新版 Pillow 寫法
                resample_method = Image.Resampling.LANCZOS
            except AttributeError:
                # 舊版 Pillow 寫法
                resample_method = Image.LANCZOS
                
            foreground_res = foreground.resize((new_w, new_h), resample=resample_method)

            # 7. 合成圖像
            paste_x = (target_w - new_w) // 2
            paste_y = target_h - new_h
            final_bg.paste(foreground_res, (paste_x, paste_y), foreground_res)

            # 8. 最終輸出
            result_img = final_bg.convert("RGB")
            
            # 介面顯示
            st.subheader("處理完成")
            st.image(result_img, caption=f"3:4 {bg_choice}背景結果", width=300)

            # 下載功能
            buf = io.BytesIO()
            result_img.save(buf, format="JPEG", quality=95)
            st.download_button(
                label="💾 下載證件相",
                data=buf.getvalue(),
                file_name="id_photo.jpg",
                mime="image/jpeg"
            )

    except Exception as e:
        st.error("發生非預期錯誤！")
        # 顯示詳細錯誤，方便截圖給我看
        st.expander("詳細錯誤日誌").code(traceback.format_exc())