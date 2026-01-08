import streamlit as st
from rembg import remove
from PIL import Image, ImageFilter, ImageOps
import io
import traceback

st.set_page_config(page_title="AI 證件相專業版", page_icon="👤")

st.title("📸 專業證件相自動轉換器")
st.markdown("請使用側邊欄的 **「人像縮放」** 功能來調整到合適的大小。")

# --- 側邊欄：微調工具 ---
st.sidebar.header("📏 尺寸與位置微調")
person_scale = st.sidebar.slider("人像縮放 (Zoom)", 0.5, 2.0, 1.0, 0.05)
vertical_move = st.sidebar.slider("上下移動 (Move Up/Down)", -300, 300, 0, 10)

st.sidebar.divider()
st.sidebar.header("🎨 背景設定")
bg_choice = st.sidebar.selectbox("選擇背景顏色", ["白色", "藍色", "粉紅色"])
color_dict = {"白色": (255, 255, 255), "藍色": (0, 191, 255), "粉紅色": (255, 192, 203)}
edge_smoothness = st.sidebar.slider("邊緣平滑度", 0, 5, 1)

# --- 主程式 ---
uploaded_file = st.file_uploader("上傳相片", type=["jpg", "png", "jpeg"])

if uploaded_file:
    try:
        with st.spinner('正在處理中...'):
            # 1. 讀取並校正旋轉
            raw_img = Image.open(uploaded_file)
            input_image = ImageOps.exif_transpose(raw_img)
            
            # 2. 預壓縮節省記憶體
            MAX_SIZE = 1200
            if max(input_image.size) > MAX_SIZE:
                input_image.thumbnail((MAX_SIZE, MAX_SIZE), Image.Resampling.LANCZOS)
            
            # 3. AI 去背
            img_byte_arr = io.BytesIO()
            input_image.save(img_byte_arr, format='PNG')
            output_bytes = remove(img_byte_arr.getvalue(), alpha_matting=True)
            
            # 4. 取得去背後的人像並【自動裁掉透明邊緣】
            foreground = Image.open(io.BytesIO(output_bytes)).convert("RGBA")
            # 這一行會抓到人像的真正邊界，去掉周圍沒用的透明區域
            bbox = foreground.getbbox()
            if bbox:
                foreground = foreground.crop(bbox)

            # 5. 邊緣羽化
            if edge_smoothness > 0:
                r, g, b, a = foreground.split()
                a = a.filter(ImageFilter.GaussianBlur(radius=edge_smoothness))
                foreground.putalpha(a)

            # 6. 建立標準 3:4 背景 (600x800)
            target_w, target_h = 600, 800
            bg_rgb = color_dict[bg_choice]
            final_bg = Image.new("RGB", (target_w, target_h), bg_rgb).convert("RGBA")

            # 7. 【計算縮放】：結合自動比例與手動縮放
            fg_w, fg_h = foreground.size
            # 基礎縮放：讓高度佔滿畫面的 75%
            base_scale = (target_h * 0.75) / fg_h
            # 套用手動微調
            final_scale = base_scale * person_scale
            
            new_w, new_h = int(fg_w * final_scale), int(fg_h * final_scale)
            foreground_res = foreground.resize((new_w, new_h), Image.Resampling.LANCZOS)

            # 8. 【計算位置】：置中並加上手動位移
            paste_x = (target_w - new_w) // 2
            # 預設底部對齊，加上 vertical_move (負值向上)
            paste_y = (target_h - new_h) + vertical_move
            
            # 合成
            temp_layer = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
            temp_layer.paste(foreground_res, (paste_x, paste_y), foreground_res)
            final_bg = Image.alpha_composite(final_bg, temp_layer)

            # 9. 輸出
            result_img = final_bg.convert("RGB")
            st.image(result_img, caption="調整預覽 (請使用左側滑桿微調大小與位置)", width=300)

            buf = io.BytesIO()
            result_img.save(buf, format="JPEG", quality=95)
            st.download_button(label="💾 下載最終版證件相", data=buf.getvalue(), file_name="pro_id_photo.jpg", mime="image/jpeg")

    except Exception as e:
        st.error("處理失敗")
        st.expander("詳細報告").code(traceback.format_exc())