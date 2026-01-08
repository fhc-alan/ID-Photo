import streamlit as st
from rembg import remove
from PIL import Image
import io

# 設定網頁標題與圖示
st.set_page_config(page_title="AI 證件相轉換器", page_icon="📸")

st.title("📸 自拍轉證件相 (3:4)")
st.write("上傳一張自拍照，AI 會自動為你換背景並裁切尺寸！")

# 側邊欄設定
st.sidebar.header("設定")
bg_choice = st.sidebar.selectbox(
    "選擇背景顏色",
    ["白色", "藍色", "粉紅色"]
)

color_dict = {
    "白色": (255, 255, 255),
    "藍色": (0, 191, 255),
    "粉紅色": (255, 192, 203)
}

# 上傳元件
uploaded_file = st.file_uploader("請選擇你的自拍照 (JPG/PNG)...", type=["jpg", "png", "jpeg"])

if uploaded_file:
    # 顯示處理中的進度條
    with st.spinner('AI 正在努力去背與調色中...'):
        # 讀取圖片
        input_image = Image.open(uploaded_file)
        
        # 執行去背
        image_bytes = uploaded_file.getvalue()
        output_bytes = remove(image_bytes)
        foreground = Image.open(io.BytesIO(output_bytes)).convert("RGBA")
        
        # 製作 3:4 背景
        target_w, target_h = 600, 800
        bg_color = color_dict[bg_choice]
        background = Image.new("RGBA", (target_w, target_h), bg_color + (255,))
        
        # 縮放人像並置中
        scale = (target_h * 0.75) / foreground.size[1]
        new_w = int(foreground.size[0] * scale)
        new_h = int(foreground.size[1] * scale)
        foreground_res = foreground.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        paste_x = (target_w - new_w) // 2
        paste_y = target_h - new_h
        background.paste(foreground_res, (paste_x, paste_y), foreground_res)
        
        # 轉換為最終結果
        final_img = background.convert("RGB")
        
        # 顯示結果
        st.subheader("處理結果")
        st.image(final_img, caption=f"3:4 {bg_choice}背景證件相", width=300)
        
        # 下載按鈕
        buf = io.BytesIO()
        final_img.save(buf, format="JPEG")
        byte_im = buf.getvalue()
        
        st.download_button(
            label="點此下載證件相",
            data=byte_im,
            file_name="my_id_photo.jpg",
            mime="image/jpeg"
        )