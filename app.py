import streamlit as st
from rembg import remove
from PIL import Image, ImageFilter
import io
import traceback

st.set_page_config(page_title="AI 證件相穩定版", page_icon="👤")

st.title("📸 專業證件相自動轉換器")

# --- 側邊欄設定 ---
st.sidebar.header("自定義選項")
bg_choice = st.sidebar.selectbox("選擇背景顏色", ["白色", "藍色", "粉紅色"])

color_dict = {
    "白色": (255, 255, 255),
    "藍色": (0, 191, 255),
    "粉紅色": (255, 192, 203)
}

edge_smoothness = st.sidebar.slider("邊緣平滑度", 0, 5, 1)

# --- 主程式 ---
uploaded_file = st.file_uploader("上傳相片 (支援手機大圖)", type=["jpg", "png", "jpeg"])

if uploaded_file:
    try:
        with st.spinner('正在優化相片大小並執行 AI 去背...'):
            # 1. 讀取圖片
            input_image = Image.open(uploaded_file)
            
            # 【關鍵修復：預處理壓縮】
            # 如果圖片寬或高超過 1500 像素，先縮小它以節省記憶體
            MAX_SIZE = 1500
            if max(input_image.size) > MAX_SIZE:
                input_image.thumbnail((MAX_SIZE, MAX_SIZE), Image.Resampling.LANCZOS)
            
            # 2. 轉為 Bytes
            img_byte_arr = io.BytesIO()
            input_image.save(img_byte_arr, format='PNG')
            image_bytes = img_byte_arr.getvalue()

            # 3. 執行去背 (降低 erode_size 以節省運算資源)
            output_bytes = remove(
                image_bytes,
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

            # 5. 建立 3:4 背景
            target_w, target_h = 600, 800
            bg_rgb = color_dict[bg_choice]
            final_bg = Image.new("RGB", (target_w, target_h), bg_rgb).convert("RGBA")

            # 6. 調整人像比例 (頭部佔比優化)
            fg_w, fg_h = foreground.size
            scale = (target_h * 0.7) / fg_h
            new_w, new_h = int(fg_w * scale), int(fg_h * scale)
            
            # 相容性縮放寫法
            try:
                res_method = Image.Resampling.LANCZOS
            except AttributeError:
                res_method = Image.LANCZOS
                
            foreground_res = foreground.resize((new_w, new_h), resample=res_method)

            # 7. 合成
            paste_x = (target_w - new_w) // 2
            paste_y = target_h - new_h
            final_bg.paste(foreground_res, (paste_x, paste_y), foreground_res)

            # 8. 輸出結果
            result_img = final_bg.convert("RGB")
            st.image(result_img, caption="處理成功！", width=300)

            # 下載
            buf = io.BytesIO()
            result_img.save(buf, format="JPEG", quality=90) # 稍微降低 quality 減少下載體積
            st.download_button(
                label="💾 下載證件相",
                data=buf.getvalue(),
                file_name="id_photo.jpg",
                mime="image/jpeg"
            )

    except Exception as e:
        st.error("處理失敗。這通常是因為圖片過大導致伺服器記憶體不足。")
        with st.expander("詳細錯誤報告"):
            st.code(traceback.format_exc())