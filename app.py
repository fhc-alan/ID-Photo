import streamlit as st
from rembg import remove
from PIL import Image, ImageFilter, ImageOps, ImageEnhance, ImageDraw
import io
import gc
import traceback

# 1. 頁面配置
st.set_page_config(page_title="AI Pro ID Photo", page_icon="👤", layout="wide")

# 2. 注入修正版 CSS
def inject_custom_css():
    st.markdown("""
    <style>
        /* 強制全局背景與文字顏色，防止深色模式衝突 */
        .stApp {
            background-color: #f8fafc !important;
            color: #1e293b !important;
        }
        
        /* 確保所有標籤、段落、span、Markdown 文字都是深色 */
        .stApp p, .stApp span, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp li {
            color: #1e293b !important;
        }

        /* 側邊欄背景與文字 */
        section[data-testid="stSidebar"] {
            background-color: #ffffff !important;
            border-right: 1px solid #e2e8f0;
        }
        section[data-testid="stSidebar"] .stText, section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] p {
            color: #1e293b !important;
        }

        /* 檔案上傳區塊文字 */
        .stApp [data-testid="stFileUploadDropzone"] div div {
            color: #475569 !important;
        }

        /* 按鈕樣式 */
        .stButton>button {
            width: 100%;
            border-radius: 8px;
            border: 1px solid #cbd5e1 !important;
            background-color: #ffffff !important;
            color: #1e293b !important;
            font-weight: 600;
        }
        
        /* 下載按鈕 (強烈藍色) */
        div.stDownloadButton > button {
            background-color: #2563eb !important;
            color: #ffffff !important;
            border: none !important;
        }

        /* 右側指南卡片 */
        .result-card {
            background-color: #ffffff;
            padding: 20px;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
            color: #1e293b !important;
        }
    </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# --- 側邊欄控制項 (邏輯不變，僅調整擺放) ---
with st.sidebar:
    st.title("⚙️ 控制面板")
    layout_choice = st.radio("排版模式", ["單張相片", "一圖四格 (2x2)", "一圖八格 (4x2)"])
    
    with st.expander("✨ 影像細節調校", expanded=True):
        feather_val = st.slider("邊緣羽化", 0.0, 3.0, 1.0, 0.5)
        brightness_val = st.slider("亮度", 0.7, 1.3, 1.0, 0.05)
        contrast_val = st.slider("對比度", 0.7, 1.3, 1.0, 0.05)
        
    with st.expander("📏 尺寸與位置"):
        person_scale = st.slider("人像縮放", 0.5, 2.0, 1.0, 0.05)
        vertical_move = st.slider("上下移動", -200, 200, 0, 10)
        bg_choice = st.selectbox("背景顏色", ["白色", "藍色", "粉紅色"])

color_dict = {"白色": (255, 255, 255), "藍色": (0, 191, 255), "粉紅色": (255, 192, 203)}

# --- 輔助函數 (維持穩定版邏輯) ---
def create_print_layout(single_img, mode):
    canvas_w, canvas_h = 1800, 1200
    canvas = Image.new("RGB", (canvas_w, canvas_h), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    sw, sh = single_img.size
    aspect = sw / sh

    if "四格" in mode:
        tw = 500
        th = int(tw / aspect)
        img = single_img.resize((tw, th), Image.Resampling.LANCZOS)
        gap_x, gap_y = 150, 100
        for r in range(2):
            for c in range(2):
                x = (canvas_w - (2*tw + gap_x))//2 + c*(tw+gap_x)
                y = (canvas_h - (2*th + gap_y))//2 + r*(th+gap_y)
                canvas.paste(img, (x, y))
                draw.rectangle([x, y, x+tw, y+th], outline=(230, 230, 230))
    elif "八格" in mode:
        tw = 350
        th = int(tw / aspect)
        img = single_img.resize((tw, th), Image.Resampling.LANCZOS)
        gap_x, gap_y = 60, 80
        for r in range(2):
            for c in range(4):
                x = (canvas_w - (4*tw + 3*gap_x))//2 + c*(tw+gap_x)
                y = (canvas_h - (2*th + gap_y))//2 + r*(th+gap_y)
                canvas.paste(img, (x, y))
                draw.rectangle([x, y, x+tw, y+th], outline=(230, 230, 230))
    return canvas

# --- 主畫面 ---
st.title("專業 AI 證件相生成器")

# 使用列佈局美化
main_col, side_info = st.columns([2, 1])

with main_col:
    uploaded_file = st.file_uploader("點擊或拖拽照片至此處", type=["jpg", "png", "jpeg"])

if uploaded_file:
    try:
        with st.spinner('AI 正在精確去背並渲染...'):
            # 輕量化處理邏輯
            raw_img = ImageOps.exif_transpose(Image.open(uploaded_file))
            if max(raw_img.size) > 1000:
                raw_img.thumbnail((1000, 1000), Image.Resampling.LANCZOS)
            
            temp_buffer = io.BytesIO()
            raw_img.convert("RGB").save(temp_buffer, format="JPEG", quality=85)
            
            output_bytes = remove(temp_buffer.getvalue())
            foreground = Image.open(io.BytesIO(output_bytes)).convert("RGBA")
            
            del raw_img
            gc.collect()

            # 調色與羽化
            if brightness_val != 1.0: foreground = ImageEnhance.Brightness(foreground).enhance(brightness_val)
            if contrast_val != 1.0: foreground = ImageEnhance.Contrast(foreground).enhance(contrast_val)
            if feather_val > 0:
                r, g, b, a = foreground.split()
                a = a.filter(ImageFilter.GaussianBlur(radius=feather_val))
                foreground.putalpha(a)

            bbox = foreground.getbbox()
            if bbox: foreground = foreground.crop(bbox)

            # 生成單張
            target_w, target_h = 600, 800
            single_photo = Image.new("RGBA", (target_w, target_h), color_dict[bg_choice] + (255,))
            fg_w, fg_h = foreground.size
            final_scale = ((target_h * 0.75) / fg_h) * person_scale
            nw, nh = int(fg_w * final_scale), int(fg_h * final_scale)
            foreground_res = foreground.resize((nw, nh), Image.Resampling.LANCZOS)
            
            px, py = (target_w - nw)//2, (target_h - nh) + vertical_move
            tmp = Image.new("RGBA", (target_w, target_h), (0,0,0,0))
            tmp.paste(foreground_res, (px, py), foreground_res)
            single_result = Image.alpha_composite(single_photo, tmp).convert("RGB")

            # 顯示結果
            if layout_choice == "單張相片":
                final_output = single_result
                st.image(final_output, caption="預覽結果", width=400)
            else:
                final_output = create_print_layout(single_result, layout_choice)
                st.image(final_output, caption=layout_choice, use_container_width=True)

            # 下載區域
            buf = io.BytesIO()
            final_output.save(buf, format="JPEG", quality=95)
            st.download_button(f"🚀 下載 {layout_choice} (JPEG)", buf.getvalue(), "output.jpg", "image/jpeg")

    except Exception as e:
        st.error("記憶體溢出，請換張較小的照片試試。")

with side_info:
    st.markdown("""
    <div class="result-card">
    <h3>📝 操作指南</h3>
    <ol>
        <li>上傳一張正面清晰照</li>
        <li>使用左側 <b>縮放</b> 滑桿調整頭部大小</li>
        <li>如有鋸齒，微調 <b>邊緣羽化</b></li>
        <li>選擇排版後點擊 <b>下載</b></li>
    </ol>
    <p style='color: #64748b; font-size: 0.8rem;'>提示：為了印製清晰，下載檔案預設為高品質 JPEG。</p>
    </div>
    """, unsafe_allow_html=True)