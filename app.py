import streamlit as st
from rembg import remove
from PIL import Image, ImageFilter
import io
import traceback

st.set_page_config(page_title="AI 證件相穩定版", page_icon="👤")

st.title("📸 專業證件相自動轉換器")

# --- 側邊欄：安全參數設定 ---
st.sidebar.header("自定義選項")
bg_choice = st.sidebar.selectbox(
    "選擇背景顏色",
    ["白色", "藍色", "粉紅色"]
)

# 使用更精確的 RGB 數值
color_dict = {
    "白色": (255, 255, 255),
    "藍色": (0, 191, 255),
    "粉紅色": (255, 192, 203)
}

edge_smoothness = st.sidebar.slider("邊緣平滑度", 0, 5, 1)

# --- 主介面 ---
uploaded_file = st.file_uploader("上傳自拍照", type=["jpg", "png", "jpeg"])

if uploaded_file:
    try:
        with st.spinner('正在進行 AI 去背與合成...'):
            # 1. 讀取並轉為 bytes
            input_image = Image.open(uploaded_file)
            img_byte_arr = io.BytesIO()
            input_image.save(img_byte_arr, format='PNG')
            image_bytes = img_byte_arr.getvalue()

            # 2. 執行去背 (調整 Alpha Matting 參數以提高穩定性)
            # 在雲端伺服器，過高的 erode_size 有時會導致出錯，我們調低一點
            output_bytes = remove(
                image_bytes,
                alpha_matting=True,
                alpha_matting_foreground_threshold=240,
                alpha_matting_background_threshold=10,
                alpha_matting_erode_size=5  # 調低數值以增加穩定性
            )
            
            foreground = Image.open(io.BytesIO(output_bytes)).convert("RGBA")

            # 3. 邊緣羽化
            if edge_smoothness > 0:
                r, g, b, a = foreground.split()
                a = a.filter(ImageFilter.GaussianBlur(radius=edge_smoothness))
                foreground.putalpha(a)

            # 4. 建立 3:4 背景 (改用更穩定的合成方式)
            target_w, target_h = 600, 800
            bg_rgb = color_dict[bg_choice]
            # 先建立一個純色 RGB 背景，再轉為 RGBA
            final_bg = Image.new("RGB", (target_w, target_h), bg_rgb).convert("RGBA")

            # 5. 調整人像大小
            fg_w, fg_h = foreground.size
            scale = (target_h * 0.75) / fg_h
            new_w, new_h = int(fg_w * scale), int(fg_h * scale)
            foreground_res = foreground.resize((new_w, new_h), Image.Resampling.LANCZOS)

            # 6. 合成
            paste_x = (target_w - new_w) // 2
            paste_y = target_h - new_h
            final_bg.paste(foreground_res, (paste_x, paste_y), foreground_res)

            # 7. 最終轉換
            result_img = final_bg.convert("RGB")
            
            # 顯示結果
            st.image(result_img, caption="處理結果", width=300)

            # 下載按鈕
            buf = io.BytesIO()
            result_img.save(buf, format="JPEG", quality=95)
            st.download_button(
                label="💾 下載證件相",
                data=buf.getvalue(),
                file_name="id_photo.jpg",
                mime="image/jpeg"
            )

    except Exception as e:
        # 如果出錯，將真正的錯誤訊息印在網頁上，方便除錯
        st.error("處理過程中發生錯誤！")
        st.expander("查看詳細錯誤報告").code(traceback.format_exc())
        st.info("提示：如果持續失敗，請嘗試關閉側邊欄的『邊緣平滑度』或上傳較小的照片。")