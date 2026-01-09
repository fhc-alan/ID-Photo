import streamlit as st
from rembg import remove
from PIL import Image, ImageFilter, ImageOps, ImageEnhance, ImageDraw, ImageStat
import io
import gc
import requests
from streamlit_lottie import st_lottie
import traceback

# 1. 頁面配置
st.set_page_config(page_title="AI Pro 證件相大師", page_icon="📸", layout="wide")

# 2. 載入 Lottie 動畫
def load_lottieurl(url):
    try:
        r = requests.get(url, timeout=5)
        if r.status_code != 200: return None
        return r.json()
    except: return None

lottie_hello = load_lottieurl("https://lottie.host/7c9a4a7a-62f9-4670-8e7c-89758f407519/U8JvD2Wv5v.json")
lottie_loading = load_lottieurl("https://lottie.host/80e9803b-c564-44b4-8393-02f89643d9f3/fWpU6O0XyX.json")

# 3. 核心功能：白平衡處理引擎
def apply_color_correction(img, auto_wb=False, temp_val=0.0):
    """
    img: PIL Image
    auto_wb: 是否啟用自動白平衡 (Gray World Assumption)
    temp_val: 手動色溫偏移 (-100 到 100)
    """
    res = img.convert("RGB")
    
    # A. 自動白平衡 (修正環境光偏色)
    if auto_wb:
        # 使用 Gray World 算法
        stat = ImageStat.Stat(res)
        avg = sum(stat.mean[:3]) / 3
        # 計算 R, G, B 各頻道的增益
        r_gain = avg / stat.mean[0] if stat.mean[0] > 0 else 1.0
        g_gain = avg / stat.mean[1] if stat.mean[1] > 0 else 1.0
        b_gain = avg / stat.mean[2] if stat.mean[2] > 0 else 1.0
        
        r, g, b = res.split()
        r = r.point(lambda i: i * r_gain)
        g = g.point(lambda i: i * g_gain)
        b = b.point(lambda i: i * b_gain)
        res = Image.merge("RGB", (r, g, b))

    # B. 手動色溫調節 (模擬冷暖色調)
    if temp_val != 0:
        r, g, b = res.split()
        # temp_val > 0 為暖色 (加紅/減藍), < 0 為冷色 (加藍/減紅)
        r = r.point(lambda i: i * (1 + temp_val/200))
        b = b.point(lambda i: i * (1 - temp_val/200))
        res = Image.merge("RGB", (r, g, b))
        
    return res

# 4. 注入 CSS (維持專業 UI)
def inject_custom_css():
    st.markdown("""
    <style>
        .stApp { background-color: #f8fafc !important; color: #1e293b !important; }
        .stApp p, .stApp span, .stApp label, .stApp h1, .stApp h2, .stApp h3 { color: #1e293b !important; }
        .step-container { display: flex; justify-content: space-around; background-color: #ffffff; padding: 20px; border-radius: 15px; margin-bottom: 25px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
        .step-box { text-align: center; flex: 1; }
        .step-text { font-size: 14px; font-weight: 600; color: #94a3b8; }
        .step-active { color: #2563eb !important; border-bottom: 3px solid #2563eb; }
        .step-active .step-text { color: #2563eb !important; }
        div.stDownloadButton > button { background-color: #2563eb !important; color: white !important; border-radius: 10px !important; width: 100%; height: 50px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# 5. 側邊欄控制
with st.sidebar:
    st.title("🎨 影像處理面板")
    layout_choice = st.radio("排版模式", ["單張相片", "一圖四格 (2x2)", "一圖八格 (4x2)"])
    
    st.divider()
    with st.expander("⚖️ 白平衡與色彩", expanded=True):
        auto_wb = st.checkbox("自動白平衡 (AI 修正)", value=False)
        temp_val = st.slider("手動色溫 (冷 ↔ 暖)", -100, 100, 0, 5)
        brightness_val = st.slider("亮度", 0.7, 1.3, 1.0, 0.05)
        contrast_val = st.slider("對比度", 0.7, 1.3, 1.0, 0.05)
    
    with st.expander("📏 構圖與背景"):
        feather_val = st.slider("邊緣羽化", 0.0, 3.0, 1.0, 0.5)
        person_scale = st.slider("人像縮放", 0.5, 2.0, 1.0, 0.05)
        vertical_move = st.slider("上下移動", -200, 200, 0, 10)
        bg_choice = st.selectbox("背景顏色", ["白色", "藍色", "粉紅色"])
        color_dict = {"白色": (255, 255, 255), "藍色": (0, 191, 255), "粉紅色": (255, 192, 203)}

# 6. 排版函數
def create_layout(single_img, mode):
    canvas_w, canvas_h = 1800, 1200
    canvas = Image.new("RGB", (canvas_w, canvas_h), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    sw, sh = single_img.size
    aspect = sw/sh
    if "四格" in mode:
        tw = 500
        th = int(tw / aspect)
        img = single_img.resize((tw, th), Image.Resampling.LANCZOS)
        for r in range(2):
            for c in range(2):
                x, y = 400+c*600, 100+r*550
                canvas.paste(img, (x, y))
                draw.rectangle([x, y, x+tw, y+th], outline=(220, 220, 220))
    elif "八格" in mode:
        tw = 350
        th = int(tw / aspect)
        img = single_img.resize((tw, th), Image.Resampling.LANCZOS)
        for r in range(2):
            for c in range(4):
                x, y = 150+c*400, 150+r*500
                canvas.paste(img, (x, y))
                draw.rectangle([x, y, x+tw, y+th], outline=(220, 220, 220))
    return canvas

# 7. 主程式
st.title("專業 AI 證件相工坊")

uploaded_file = st.file_uploader("", type=["jpg", "png", "jpeg"])
s1, s2, s3 = ("step-active", "", "") if not uploaded_file else ("", "step-active", "")

st.markdown(f"""
    <div class="step-container">
        <div class="step-box {s1}"><div class="step-text">1. 上傳照片</div></div>
        <div class="step-box {s2}"><div class="step-text">2. AI 處理與白平衡</div></div>
        <div class="step-box {s3}"><div class="step-text">3. 下載成品</div></div>
    </div>
""", unsafe_allow_html=True)

if not uploaded_file:
    if lottie_hello: st_lottie(lottie_hello, height=300)
else:
    try:
        loading_area = st.empty()
        with loading_area.container():
            if lottie_loading: st_lottie(lottie_loading, height=200)
            st.markdown("<p style='text-align: center;'>正在套用白平衡並去背...</p>", unsafe_allow_html=True)

        # 讀取並預處理
        raw_img = ImageOps.exif_transpose(Image.open(uploaded_file))
        if max(raw_img.size) > 1000: raw_img.thumbnail((1000, 1000), Image.Resampling.LANCZOS)
        
        # --- A. 執行色彩校正 (白平衡) ---
        corrected_img = apply_color_correction(raw_img, auto_wb, temp_val)

        # --- B. 去背處理 ---
        temp_io = io.BytesIO()
        corrected_img.save(temp_io, format="PNG") # 使用 PNG 保持色彩精度
        output_bytes = remove(temp_io.getvalue())
        foreground = Image.open(io.BytesIO(output_bytes)).convert("RGBA")
        
        del raw_img
        gc.collect()

        # 微調
        if brightness_val != 1.0: foreground = ImageEnhance.Brightness(foreground).enhance(brightness_val)
        if contrast_val != 1.0: foreground = ImageEnhance.Contrast(foreground).enhance(contrast_val)
        if feather_val > 0:
            r, g, b, a = foreground.split()
            a = a.filter(ImageFilter.GaussianBlur(radius=feather_val))
            foreground.putalpha(a)
        
        bbox = foreground.getbbox()
        if bbox: foreground = foreground.crop(bbox)

        # 合成
        target_w, target_h = 600, 800
        single_photo = Image.new("RGBA", (target_w, target_h), color_dict[bg_choice] + (255,))
        fg_w, fg_h = foreground.size
        final_scale = ((target_h * 0.75) / fg_h) * person_scale
        nw, nh = int(fg_w * final_scale), int(fg_h * final_scale)
        foreground_res = foreground.resize((nw, nh), Image.Resampling.LANCZOS)
        px, py = (target_w - nw)//2, (target_h - nh) + vertical_move
        
        tmp = Image.new("RGBA", (target_w, target_h), (0,0,0,0))
        tmp.paste(foreground_res, (px, py), foreground_res)
        final_single = Image.alpha_composite(single_photo, tmp).convert("RGB")

        loading_area.empty()
        
        col_res, col_btn = st.columns([1.2, 0.8])
        with col_res:
            if layout_choice == "單張相片":
                final_output = final_single
                st.image(final_output, width=400)
            else:
                final_output = create_layout(final_single, layout_choice)
                st.image(final_output, use_container_width=True)

        with col_btn:
            st.success("✅ 影像處理完成")
            buf = io.BytesIO()
            final_output.save(buf, format="JPEG", quality=95)
            st.download_button("📥 點擊下載成品照片", buf.getvalue(), "id_photo.jpg", "image/jpeg")
            st.info("💡 如果臉部太黃，請勾選「自動白平衡」或將色溫滑桿向左移動（變藍）。")

    except Exception as e:
        st.error("處理發生錯誤")
        st.expander("日誌").code(traceback.format_exc())