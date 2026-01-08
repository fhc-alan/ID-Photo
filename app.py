import streamlit as st
from rembg import remove
from PIL import Image, ImageFilter, ImageOps
import io

# 1. 網頁基本設定
st.set_page_config(page_title="專業 AI 證件相工具", page_icon="👤")

st.title("📸 專業證件相自動轉換器")
st.markdown("使用 AI 技術自動優化邊緣，讓證件相看起來更自然。")

# --- 側邊欄設定 ---
st.sidebar.header("自定義選項")
bg_choice = st.sidebar.selectbox(
    "選擇背景顏色",
    ["白色", "藍色", "粉紅色"]
)

# 定義顏色數值
color_dict = {
    "白色": (255, 255, 255),
    "藍色": (0, 191, 255),
    "粉紅色": (255, 192, 203)
}

# 讓用家微調自然度
edge_smoothness = st.sidebar.slider("邊緣平滑度 (羽化)", 0, 5, 2)

# --- 主介面 ---
uploaded_file = st.file_uploader("上傳自拍照 (建議背景簡單、光線均勻)", type=["jpg", "png", "jpeg"])

if uploaded_file:
    with st.spinner('正在進行 AI 邊緣優化處理...'):
        # 讀取原始圖片
        input_image = Image.open(uploaded_file)
        
        # 將 PIL 轉為 bytes 以供 rembg 使用
        img_byte_arr = io.BytesIO()
        input_image.save(img_byte_arr, format='PNG')
        image_bytes = img_byte_arr.getvalue()

        # 2. 執行 AI 去背 (啟用 Alpha Matting 提升自然度)
        # alpha_matting=True 會特別處理頭髮和細節邊緣
        output_bytes = remove(
            image_bytes,
            alpha_matting=True,
            alpha_matting_foreground_threshold=240,
            alpha_matting_background_threshold=10,
            alpha_matting_erode_size=10
        )
        
        # 轉回 RGBA 格式進行後續處理
        foreground = Image.open(io.BytesIO(output_bytes)).convert("RGBA")

        # 3. 邊緣羽化處理 (Edge Feathering)
        # 提取透明通道並進行輕微模糊，讓邊緣不那麼生硬
        if edge_smoothness > 0:
            r, g, b, a = foreground.split()
            a = a.filter(ImageFilter.GaussianBlur(radius=edge_smoothness))
            foreground.putalpha(a)

        # 4. 建立 3:4 背景 (標準尺寸 600x800)
        target_w, target_h = 600, 800
        bg_rgb = color_dict[bg_choice]
        final_bg = Image.new("RGBA", (target_w, target_h), bg_rgb + (255,))

        # 5. 調整人像大小與置中
        # 邏輯：確保人頭佔據畫面約 70% 高度
        fg_w, fg_h = foreground.size
        scale = (target_h * 0.75) / fg_h
        new_w, new_h = int(fg_w * scale), int(fg_h * scale)
        foreground_res = foreground.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # 計算貼上位置 (水平置中，貼近底部)
        paste_x = (target_w - new_w) // 2
        paste_y = target_h - new_h
        final_bg.paste(foreground_res, (paste_x, paste_y), foreground_res)

        # 6. 輸出結果
        result_img = final_bg.convert("RGB")
        
        st.subheader("處理完成")
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.image(input_image, caption="原始相片", use_container_width=True)
        with col2:
            st.image(result_img, caption="優化後的證件相", width=250)

        # 下載按鈕
        buf = io.BytesIO()
        result_img.save(buf, format="JPEG", quality=95)
        st.download_button(
            label="💾 下載高畫質證件相",
            data=buf.getvalue(),
            file_name="id_photo_pro.jpg",
            mime="image/jpeg"
        )

st.divider()
st.info("💡 小貼士：若頭髮邊緣仍有雜色，請嘗試在更簡單的背景前重新拍攝，或調整側邊欄的「平滑度」。")