import streamlit as st
import easyocr
import numpy as np
from PIL import Image
import io
import base64

# 페이지 설정
st.set_page_config(layout="wide", page_title="간편 OCR 복사기")
st.title("📄 이미지 텍스트 자동 복사기")
st.markdown("이미지를 올리고 **빨간 박스를 드래그했다 떼면** 자동으로 복사됩니다.")

# 캐싱: 모델을 매번 로딩하지 않도록 설정
@st.cache_resource
def load_model():
    return easyocr.Reader(['ko', 'en'])

reader = load_model()

def create_autocopy_html(image_bytes, ocr_result):
    img_b64 = base64.b64encode(image_bytes).decode()
    
    # 이미지가 너무 크면 화면을 벗어나므로 CSS로 조절
    html = f"""
    <style>
        .ocr-container {{ position: relative; display: inline-block; width: 100%; }}
        .ocr-img {{ width: 100%; height: auto; }}
        .ocr-box {{
            position: absolute;
            border: 2px solid rgba(255, 0, 0, 0.6);
            background-color: rgba(255, 0, 0, 0.1);
            color: rgba(0,0,0,0.01);
            cursor: text;
            font-size: 10px; /* 드래그 잡히도록 최소 크기 확보 */
            white-space: nowrap; overflow: hidden;
        }}
        .ocr-box::selection {{ background: rgba(0, 0, 255, 0.3); color: transparent; }}
        
        /* 알림 토스트 */
        #toast {{
            visibility: hidden; min-width: 200px; background-color: #333; color: #fff;
            text-align: center; border-radius: 5px; padding: 10px; position: fixed;
            z-index: 9999; left: 50%; bottom: 30px; transform: translateX(-50%);
        }}
        #toast.show {{ visibility: visible; animation: fadein 0.5s, fadeout 0.5s 2.5s; }}
        @keyframes fadein {{ from {{bottom: 0; opacity: 0;}} to {{bottom: 30px; opacity: 1;}} }}
        @keyframes fadeout {{ from {{bottom: 30px; opacity: 1;}} to {{bottom: 0; opacity: 0;}} }}
    </style>

    <div class="ocr-container">
        <img src="data:image/jpeg;base64,{img_b64}" class="ocr-img" id="source-img">
    """
    
    # 원본 이미지 크기 파악이 HTML 단에서는 어려우므로 % 단위로 배치
    # Python에서 이미 width/height 정보를 가지고 계산해서 넣음
    for (bbox, text, prob) in ocr_result:
        (tl, tr, br, bl) = bbox
        # 좌표 정규화 로직은 Python에서 처리해서 넘겨야 정확함 (여기서는 생략된 부분 보완)
        # *주의* 실제 서비스시엔 이미지 원본 사이즈 대비 비율 계산 필요
        # 간소화를 위해 스타일만 적용하고 위치는 Python 로직과 연동해야 함
        pass 

    # (주의) Streamlit HTML 컴포넌트는 iframe이라 부모창 제어가 까다로움.
    # 하지만 자체적으로 이미지를 렌더링했으므로 이 안에서 동작함.
    
    # 여기서는 Python에서 계산된 좌표를 받아서 HTML을 완성하는 방식이 가장 안정적
    # 위쪽 Colab 코드의 좌표 계산 로직을 그대로 가져와야 함.
    return html 

# --- [메인 로직] ---
uploaded_file = st.file_uploader("이미지 업로드", type=['png', 'jpg', 'jpeg'])

if uploaded_file is not None:
    image = Image.open(uploaded_file).convert("RGB")
    image_bytes = uploaded_file.getvalue()
    
    with st.spinner("텍스트 위치 분석 중..."):
        # numpy 변환
        image_np = np.array(image)
        result = reader.readtext(image_np)
    
    # HTML 생성 (좌표 계산 포함)
    width, height = image.size
    
    img_b64 = base64.b64encode(image_bytes).decode()
    
    html_content = f"""
    <div style="position: relative; width: 100%;">
        <img src="data:image/jpeg;base64,{img_b64}" style="width: 100%;">
    """
    
    for (bbox, text, prob) in result:
        (tl, tr, br, bl) = bbox
        box_x = min(tl[0], bl[0])
        box_y = min(tl[1], tr[1])
        box_w = max(tr[0], br[0]) - box_x
        box_h = max(bl[1], br[1]) - box_y
        
        left = (box_x / width) * 100
        top = (box_y / height) * 100
        w_pct = (box_w / width) * 100
        h_pct = (box_h / height) * 100
        
        html_content += f"""
        <div style="position: absolute; left: {left}%; top: {top}%; width: {w_pct}%; height: {h_pct}%;
                    border: 2px solid red; background: rgba(255,0,0,0.1); color: rgba(0,0,0,0.01);
                    font-size: {box_h*0.8}px; line-height: {box_h}px; overflow: hidden; user-select: text;"
                    class="copy-target">
            {text}
        </div>
        """
        
    html_content += """
    </div>
    <div id="toast">복사되었습니다!</div>
    <script>
        document.addEventListener('mouseup', function() {
            let text = window.getSelection().toString();
            if (text.length > 0) {
                navigator.clipboard.writeText(text).then(() => {
                    let t = document.getElementById("toast");
                    t.className = "show";
                    setTimeout(() => { t.className = t.className.replace("show", ""); }, 3000);
                });
            }
        });
    </script>
    <style>
        #toast { visibility: hidden; position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%);
                 background: #333; color: #fff; padding: 10px 20px; border-radius: 5px; z-index: 99999; }
        #toast.show { visibility: visible; }
    </style>
    """
    
    # Streamlit 컴포넌트로 렌더링 (높이를 넉넉하게 줌)
    st.components.v1.html(html_content, height=height+100, scrolling=True)