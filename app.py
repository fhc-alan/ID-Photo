import streamlit as st
from rembg import remove
from PIL import Image, ImageFilter, ImageOps, ImageEnhance, ImageDraw
import io
import gc
import requests
from streamlit_lottie import st_lottie
import traceback

# 1. 頁面配置 (設定標題與佈局)
st.set_page_config(page_title="AI Pro 證件相大師", page_icon="📸", layout="wide")

# 2. 載入 Lottie 動畫 (具備超時與錯誤檢查機制)
def load_lottieurl(url):
    try:
        r = requests.get(url, timeout=5)
        if r.status_code != 200:
            return None
        return r.json()
    except:
        return None

lottie_hello = load_lottieurl("https://lottie.host/7c9a4a7a-62f9-4670-8e7c-89758f407519/U8JvD2Wv5v.json")
lottie_loading = load_lottieurl("https://lottie.host/80e9803b-c564-44b4-8393-02f89643d9f3/fWpU6O0XyX.json")

# 3. 注入自定義 CSS (強制淺色背景與深色文字，美化按鈕與卡片)
def inject_custom_css():
    st.markdown("""
    <style>
        /* 全局背景與文字顏色修正 */
        .stApp { background-color: #f8fafc !important; color: #1e293b !important; }
        .stApp p, .stApp span, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp li { 
            color: #1e293b !important; 
        }

        /* 側邊欄美化 */
        section[data-testid="stSidebar"] {
            background-color: #ffffff !important;
            border-right: 1px solid #e2e8f0;
        }

        /* 步驟指引樣式 */
        .step-container {
            display: flex;
            justify-content: space-around;
            background-color: #ffffff;
            padding: 20px;
            border-radius: 15px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
            margin-bottom: 25px;
            border: 1px solid #e2e8f0;
        }
        .step-box { text-align: center; flex: 1; padding: 10px; }
        .step-icon { font-size: 24px; margin-bottom: 5px; }
        .step-text { font-size: 14px; font-weight: 600; color: #94a3b8; }
        .step-active { color: #2563eb !important; border-bottom: 3px solid #2563eb; }
        .step-active .step-text { color: #2563eb !important; }

        /* 按鈕美化 */
        .stButton>button {
            width: 100%; border-radius: 8px; border: 1px solid #cbd5e1 !important;
            background-color: #ffffff !important; color: #1e293b !important;
            font-weight: 600; transition: 0.3s;
        }
        .stButton>button:hover { border-color: #2563eb !important; color: #2563eb !important; }

        /* 下載按鈕 (藍色高亮) */
        div.stDownloadButton > button {
            background-color: #2563eb !important; color: #ffffff !important;
            border: none !important; padding: 0.8rem !important; font-size: 1.1rem !important;
        }
        div.stDownloadButton > button:hover { background-color: #1d4ed8 !important; box-shadow: 0 4px 12px rgba(37,99,235,0.3); }

        /* 結果展示區域 */
        .result-card {
            background-color: #ffffff; padding: 25px; border-radius: 15px;
            border: 1px solid #e2e8f0; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
        }
    </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# 4. 輔助函數：建立 4R 排版
def create_print_layout(single_img, mode):
    # 4R 橫向畫布 (1800x1200 px @ 300DPI)
    canvas_w, canvas_h = 1800, 1200
    canvas = Image.new("RGB", (canvas_w, canvas_h), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    sw, sh = single_img.size
    aspect = sw / sh

    if "四格" in mode:
        tw = 500
        th = int(tw / aspect)
        img_resized = single_img.resize((tw, th), Image.Resampling.LANCZOS)
        gap_x, gap_y = 150, 100
        total_w = 2 * tw + gap_x
        total_h = 2 * th + gap_y
        offset_x, offset_y = (canvas_w - total_w)//2, (canvas_h - total_h)//2
        for r in range(2):
            for c in range(2):
                x, y = offset_x + c*(tw+gap_x), offset_y + r*(th+gap_y)
                canvas.paste(img_resized, (x, y))
                draw.rectangle([x, y, x+tw, y+th], outline=(230, 230, 230), width=2)
    
    elif "八格" in mode:
        tw = 350
        th = int(tw / aspect)
        img_resized = single_img.resize((tw, th), Image.Resampling.LANCZOS)
        gap_x, gap_y = 60, 80
        total_w = 4 * tw + 3 * gap_x
        total_h = 2 * th + gap_y
        offset_x, offset_y = (canvas_w - total_w)//2, (canvas_h - total_h)//2
        for r in range(2):
            for c in range(4):
                x, y = offset_x + c*(tw+gap_x), offset_y + r*(th+gap_y)
                canvas.paste(img_resized, (x, y))
                draw.rectangle([x, y, x+tw, y+th], outline=(230, 230, 230), width=1)
    
    return canvas

# 5. 側邊欄控制面版
with st.sidebar:
    st.markdown("### 🛠️ 編輯與排版")
    layout_choice = st.radio("選擇列印模式", ["單張相片", "一圖四格 (2x2)", "一圖八格 (4x2)"])
    
    st.divider()
    with st.expander("✨ 影像調校", expanded=True):
        feather_val = st.slider("邊緣柔和 (羽化)", 0.0, 3.0, 1.0, 0.5)
        brightness_val = st.slider("亮度補償", 0.7, 1.3, 1.0, 0.05)
        contrast_val = st.slider("對比強化", 0.7, 1.3, 1.0, 0.05)
    
    with st.expander("📏 構圖微調"):
        person_scale = st.slider("人像縮放", 0.5, 2.0, 1.0, 0.05)
        vertical_move = st.slider("垂直位置", -200, 200, 0, 10)
        bg_choice = st.selectbox("背景色彩", ["白色", "藍色", "粉紅色"])
        color_dict = {"白色": (255, 255, 255), "藍色": (0, 191, 255), "粉紅色": (255, 192, 203)}

# 6. 主畫面邏輯
st.title("📸 專業 AI 證件相工坊")

# 步驟指引狀態更新
uploaded_file = st.file_uploader("", type=["jpg", "png", "jpeg"])
s1, s2, s3 = ("step-active", "", "") if not uploaded_file else ("", "step-active", "")

st.markdown(f"""
    <div class="step-container">
        <div class="step-box {s1}"><div class="step-icon">📤</div><div class="step-text">1. 上傳照片</div></div>
        <div class="step-box {s2}"><div class="step-icon">⚙️</div><div class="step-text">2. AI 處理與微調</div></div>
        <div class="step-box {s3}"><div class="step-icon">💾</div><div class="step-text">3. 下載成品</div></div>
    </div>
""", unsafe_allow_html=True)

if not uploaded_file:
    c1, c2 = st.columns([1, 1])
    with c1:
        if lottie_hello: st_lottie(lottie_hello, height=300, key="hello")
    with c2:
        st.write("### 準備好您的專業形象了嗎？")
        st.write("請在上傳區放入您的正面照片，系統將自動進行 AI 去背與規格校正。")
        st.info("💡 建議：拍攝時請確保光線均勻，避免背光。")

else:
    try:
        # 動態載入畫面
        loading_area = st.empty()
        with loading_area.container():
            if lottie_loading: st_lottie(lottie_loading, height=200, key="loading")
            st.markdown("<p style='text-align: center;'>AI 正在精確去背與渲染，請稍候...</p>", unsafe_allow_html=True)

        # --- 核心處理流程 (記憶體優化版) ---
        raw_img = ImageOps.exif_transpose(Image.open(uploaded_file))
        if max(raw_img.size) > 1000:
            raw_img.thumbnail((1000, 1000), Image.Resampling.LANCZOS)
        
        # 轉換為 JPEG 處理以節省 RAM
        temp_io = io.BytesIO()
        raw_img.convert("RGB").save(temp_io, format="JPEG", quality=85)
        
        # AI 去背 (關閉耗能的 alpha_matting)
        processed_bytes = remove(temp_io.getvalue())
        foreground = Image.open(io.BytesIO(processed_bytes)).convert("RGBA")
        
        # 釋放原始大圖記憶體
        del raw_img
        gc.collect()

        # 色彩強化與羽化處理
        if brightness_val != 1.0: foreground = ImageEnhance.Brightness(foreground).enhance(brightness_val)
        if contrast_val != 1.0: foreground = ImageEnhance.Contrast(foreground).enhance(contrast_val)
        if feather_val > 0:
            r, g, b, a = foreground.split()
            a = a.filter(ImageFilter.GaussianBlur(radius=feather_val))
            foreground.putalpha(a)
        
        # 裁切透明邊緣
        bbox = foreground.getbbox()
        if bbox: foreground = foreground.crop(bbox)

        # 建立標準單張 (3:4 比例, 600x800 px)
        target_w, target_h = 600, 800
        bg_color = color_dict[bg_choice]
        single_photo = Image.new("RGBA", (target_w, target_h), bg_color + (255,))
        
        fg_w, fg_h = foreground.size
        # 計算縮放：以高度 75% 為基準人像大小
        final_scale = ((target_h * 0.75) / fg_h) * person_scale
        nw, nh = int(fg_w * final_scale), int(fg_h * final_scale)
        foreground_res = foreground.resize((nw, nh), Image.Resampling.LANCZOS)
        
        # 合成
        px, py = (target_w - nw)//2, (target_h - nh) + vertical_move
        tmp_layer = Image.new("RGBA", (target_w, target_h), (0,0,0,0))
        tmp_layer.paste(foreground_res, (px, py), foreground_res)
        final_single = Image.alpha_composite(single_photo, tmp_layer).convert("RGB")

        # 移除載入動畫並顯示結果
        loading_area.empty()
        
        res_col1, res_col2 = st.columns([1.2, 0.8])
        
        with res_col1:
            st.markdown("### 🖼️ 製作結果預覽")
            if layout_choice == "單張相片":
                final_render = final_single
                st.image(final_render, width=400)
            else:
                final_render = create_print_layout(final_single, layout_choice)
                st.image(final_render, use_container_width=True)

        with res_col2:
            st.markdown("""<div class="result-card">""", unsafe_allow_html=True)
            st.markdown("### ✅ 處理完成")
            st.write(f"目前模式：**{layout_choice}**")
            st.write("您可以根據預覽圖繼續調整左側的參數。")
            
            # 下載按鈕
            buf = io.BytesIO()
            final_render.save(buf, format="JPEG", quality=98)
            st.download_button(
                label=f"📥 立即下載檔案",
                data=buf.getvalue(),
                file_name=f"id_photo_{layout_choice}.jpg",
                mime="image/jpeg"
            )
            st.markdown("</div>", unsafe_allow_html=True)
            st.warning("🖨️ **列印提示**：請使用 4R (4x6吋) 相紙，列印設定請務必選擇「100% 原始大小」或「不縮放」。")

    except Exception as e:
        st.error("處理過程中出現問題。")
        with st.expander("查看錯誤詳情"):
            st.code(traceback.format_exc())