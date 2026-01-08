import streamlit as st
from rembg import remove
from PIL import Image, ImageFilter, ImageOps, ImageEnhance, ImageDraw
import io
import gc
import requests
from streamlit_lottie import st_lottie # 新增
import traceback

# 1. 頁面配置
st.set_page_config(page_title="AI Pro ID Photo", page_icon="📸", layout="wide")

# 2. 載入 Lottie 動畫函數
def load_lottieurl(url):
    r = requests.get(url)
    if r.status_code != 200: return None
    return r.json()

# 準備兩個動畫：一個是首頁歡迎，一個是處理中
lottie_hello = load_lottieurl("https://lottie.host/7c9a4a7a-62f9-4670-8e7c-89758f407519/U8JvD2Wv5v.json") # 相機動畫
lottie_loading = load_lottieurl("https://lottie.host/80e9803b-c564-44b4-8393-02f89643d9f3/fWpU6O0XyX.json") # 處理動畫

# 3. 注入強化版 CSS
def inject_custom_css():
    st.markdown("""
    <style>
        .stApp { background-color: #f8fafc !important; color: #1e293b !important; }
        .stApp p, .stApp span, .stApp label, .stApp h1, .stApp h2, .stApp h3 { color: #1e293b !important; }
        
        /* 步驟指引卡片 */
        .step-container {
            display: flex;
            justify-content: space-around;
            background-color: #ffffff;
            padding: 20px;
            border-radius: 15px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
            margin-bottom: 30px;
            border: 1px solid #e2e8f0;
        }
        .step-box { text-align: center; flex: 1; }
        .step-icon { font-size: 24px; margin-bottom: 5px; }
        .step-text { font-size: 14px; font-weight: 600; color: #64748b; }
        .step-active { color: #2563eb !important; border-bottom: 3px solid #2563eb; }

        /* 下載按鈕強化 */
        div.stDownloadButton > button {
            background-color: #2563eb !important;
            color: white !important;
            border-radius: 10px !important;
            padding: 15px 30px !important;
            font-size: 18px !important;
            transition: 0.3s;
        }
    </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# --- 側邊欄控制 ---
with st.sidebar:
    st.title("🎨 編輯選項")
    layout_choice = st.radio("排版模式", ["單張相片", "一圖四格 (2x2)", "一圖八格 (4x2)"])
    st.divider()
    with st.expander("✨ 影像美化", expanded=True):
        feather_val = st.slider("邊緣羽化", 0.0, 3.0, 1.0, 0.5)
        brightness_val = st.slider("亮度", 0.7, 1.3, 1.0, 0.05)
        contrast_val = st.slider("對比度", 0.7, 1.3, 1.0, 0.05)
    with st.expander("📏 尺寸微調"):
        person_scale = st.slider("人像縮放", 0.5, 2.0, 1.0, 0.05)
        vertical_move = st.slider("上下移動", -200, 200, 0, 10)
        bg_choice = st.selectbox("背景顏色", ["白色", "藍色", "粉紅色"])

color_dict = {"白色": (255, 255, 255), "藍色": (0, 191, 255), "粉紅色": (255, 192, 203)}

# --- 主畫面佈局 ---
st.title("📸 專業 AI 證件相工坊")

# 視覺化步驟指引
uploaded_file = st.file_uploader("", type=["jpg", "png", "jpeg"])

step_status = ["", "", ""]
if not uploaded_file:
    step_status[0] = "step-active"
elif uploaded_file:
    step_status[1] = "step-active"

st.markdown(f"""
    <div class="step-container">
        <div class="step-box {step_status[0]}"><div class="step-icon">📤</div><div class="step-text">1. 上傳相片</div></div>
        <div class="step-box {step_status[1]}"><div class="step-icon">⚙️</div><div class="step-text">2. 調整細節</div></div>
        <div class="step-box {step_status[2]}"><div class="step-icon">💾</div><div class="step-text">3. 下載成品</div></div>
    </div>
    """, unsafe_allow_html=True)

if not uploaded_file:
    col1, col2 = st.columns([1, 1])
    with col1:
        st_lottie(lottie_hello, height=300, key="hello")
    with col2:
        st.write("### 歡迎使用！")
        st.write("請在上方區域上傳您的正面相片，AI 將會自動完成剩餘的工作。")
        st.info("💡 提示：使用純色背景或光線充足的地方拍攝，效果最佳。")

if uploaded_file:
    try:
        # 顯示處理中的動畫
        loading_placeholder = st.empty()
        with loading_placeholder.container():
            st_lottie(lottie_loading, height=200, key="loading")
            st.center_text = st.markdown("<p style='text-align: center;'>AI 正在努力修圖中，請稍候...</p>", unsafe_allow_html=True)

        # --- AI 處理核心 (保持輕量化邏輯) ---
        raw_img = ImageOps.exif_transpose(Image.open(uploaded_file))
        if max(raw_img.size) > 1000:
            raw_img.thumbnail((1000, 1000), Image.Resampling.LANCZOS)
        
        temp_buf = io.BytesIO()
        raw_img.convert("RGB").save(temp_buf, format="JPEG", quality=80)
        output_bytes = remove(temp_buf.getvalue())
        foreground = Image.open(io.BytesIO(output_bytes)).convert("RGBA")
        
        # 影像強化
        if brightness_val != 1.0: foreground = ImageEnhance.Brightness(foreground).enhance(brightness_val)
        if contrast_val != 1.0: foreground = ImageEnhance.Contrast(foreground).enhance(contrast_val)
        if feather_val > 0:
            r, g, b, a = foreground.split()
            a = a.filter(ImageFilter.GaussianBlur(radius=feather_val))
            foreground.putalpha(a)
        
        bbox = foreground.getbbox()
        if bbox: foreground = foreground.crop(bbox)

        # 合成單張
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

        # 移除載入動畫，顯示結果
        loading_placeholder.empty()

        res_col1, res_col2 = st.columns([1, 1])
        with res_col1:
            st.markdown("### 🔍 預覽")
            if layout_choice == "單張相片":
                st.image(single_result, width=400)
                final_output = single_result
            else:
                # 這裡調用之前的 create_print_layout 函數
                # (為了精簡空間，假設函數已在上方定義)
                from PIL import ImageDraw
                def create_layout(img, mode):
                    c_w, c_h = 1800, 1200
                    can = Image.new("RGB", (c_w, c_h), (255, 255, 255))
                    draw = ImageDraw.Draw(can)
                    sw, sh = img.size
                    if "四格" in mode:
                        tw, th = 500, int(500*(sh/sw))
                        for r in range(2):
                            for c in range(2):
                                x, y = 400+c*600, 100+r*550
                                can.paste(img.resize((tw,th)), (x,y))
                    return can
                
                final_output = create_layout(single_result, layout_choice)
                st.image(final_output, use_container_width=True)

        with res_col2:
            st.markdown("### 🚀 完成！")
            st.success("相片已準備就緒，您可以點擊下方按鈕下載。")
            
            buf = io.BytesIO()
            final_output.save(buf, format="JPEG", quality=95)
            st.download_button(f"📥 下載 {layout_choice}", buf.getvalue(), "id_photo.jpg", "image/jpeg")
            
            st.warning("⚠️ 記得：在列印時選擇 '100% 原始大小' 才能獲得正確尺寸。")

    except Exception as e:
        st.error(f"處理失敗：{e}")