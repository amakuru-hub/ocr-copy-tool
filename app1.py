import streamlit as st
import easyocr
import numpy as np
from PIL import Image
import io
import base64

# --- [1. 페이지 설정] ---
st.set_page_config(layout="wide", page_title="AI 텍스트 복사기")

st.title("🖱️ 이미지 텍스트 드래그 & 복사")
st.markdown("""
1. 이미지를 업로드하세요.
2. 빨간색 박스로 표시된 **글자 위를 드래그** 하세요.
3. 마우스를 떼면 **자동으로 복사**되고 알림이 뜹니다.
""")

# --- [2. OCR 모델 로드 (캐싱 적용)] ---
@st.cache_resource
# --- [수정 전] ---
# def load_ocr_model():
#     return easyocr.Reader(['ko', 'en'])

# --- [수정 후: 이걸로 바꾸세요] ---
@st.cache_resource
def load_ocr_model():
    # Streamlit Cloud 무료 서버는 GPU가 없으므로 gpu=False 필수!
    return easyocr.Reader(['ko', 'en'], gpu=False)

reader = load_ocr_model()

# --- [3. 메인 로직] ---
uploaded_file = st.file_uploader("이미지 파일 업로드", type=['png', 'jpg', 'jpeg'])

if uploaded_file is not None:
    # 이미지 처리
    image = Image.open(uploaded_file).convert("RGB")
    image_bytes = uploaded_file.getvalue()
    width, height = image.size
    
    with st.spinner("텍스트 위치를 분석 중입니다... (잠시만 기다려주세요)"):
        # EasyOCR 실행
        image_np = np.array(image)
        result = reader.readtext(image_np)

    # --- [4. HTML/CSS/JS 생성 (핵심 부분)] ---
    
    # 이미지를 Base64로 변환 (HTML 안에 넣기 위함)
    img_b64 = base64.b64encode(image_bytes).decode()
    
    # HTML 시작
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        /* 기본 컨테이너 */
        .ocr-container {{
            position: relative;
            display: inline-block;
            width: 100%;
            max-width: 100%;
        }}
        
        /* 원본 이미지 */
        .ocr-image {{
            width: 100%;
            height: auto;
            display: block;
        }}

        /* 텍스트 박스 (투명 글자 + 빨간 테두리) */
        .ocr-box {{
            position: absolute;
            border: 2px solid rgba(255, 0, 0, 0.6); /* 빨간 테두리 */
            background-color: rgba(255, 0, 0, 0.1); /* 약간 붉은 배경 */
            color: rgba(0,0,0,0.01); /* 글자는 거의 투명하게 (드래그용) */
            white-space: nowrap;
            overflow: hidden;
            user-select: text;
            cursor: text;
        }}
        
        /* 드래그 했을 때 색상 (파란색 블록) */
        .ocr-box::selection {{
            background: rgba(0, 0, 255, 0.3);
            color: transparent;
        }}

        /* --- [알림창(Toast) 스타일] --- */
        #toast {{
            visibility: hidden; /* 기본은 숨김 */
            min-width: 250px;
            background-color: #333; /* 검은색 배경 */
            color: #fff; /* 흰색 글자 */
            text-align: center;
            border-radius: 8px; /* 둥근 모서리 */
            padding: 16px;
            position: fixed;
            z-index: 9999;
            left: 50%;
            bottom: 30px; /* 하단에서 30px 위 */
            transform: translateX(-50%);
            font-size: 16px;
            box-shadow: 0px 4px 10px rgba(0,0,0,0.3);
        }}

        /* 알림창 애니메이션 (페이드 인/아웃) */
        #toast.show {{
            visibility: visible;
            -webkit-animation: fadein 0.5s, fadeout 0.5s 2.5s;
            animation: fadein 0.5s, fadeout 0.5s 2.5s;
        }}

        @-webkit-keyframes fadein {{
            from {{bottom: 0; opacity: 0;}} 
            to {{bottom: 30px; opacity: 1;}}
        }}

        @keyframes fadein {{
            from {{bottom: 0; opacity: 0;}}
            to {{bottom: 30px; opacity: 1;}}
        }}

        @-webkit-keyframes fadeout {{
            from {{bottom: 30px; opacity: 1;}} 
            to {{bottom: 0; opacity: 0;}}
        }}

        @keyframes fadeout {{
            from {{bottom: 30px; opacity: 1;}}
            to {{bottom: 0; opacity: 0;}}
        }}
    </style>
    </head>
    <body>

    <div class="ocr-container">
        <img src="data:image/jpeg;base64,{img_b64}" class="ocr-image">
    """

    # OCR 결과 좌표를 HTML div로 변환
    for (bbox, text, prob) in result:
        (tl, tr, br, bl) = bbox
        
        # 좌표 계산
        box_x = min(tl[0], bl[0])
        box_y = min(tl[1], tr[1])
        box_w = max(tr[0], br[0]) - box_x
        box_h = max(bl[1], br[1]) - box_y
        
        # % 단위로 변환 (반응형 대응)
        left = (box_x / width) * 100
        top = (box_y / height) * 100
        w_pct = (box_w / width) * 100
        h_pct = (box_h / height) * 100
        
        # 폰트 크기 자동 조절
        font_size = box_h * 0.7 
        
        html_content += f"""
        <div class="ocr-box" 
             style="left: {left}%; top: {top}%; width: {w_pct}%; height: {h_pct}%; 
                    font-size: {font_size}px; line-height: {box_h}px;"
             title="{text}">
             {text}
        </div>
        """

    # 알림창 div와 자바스크립트 추가
    html_content += """
    </div>
    
    <div id="toast">복사되었습니다.</div>

    <script>
        // 마우스 버튼을 뗐을 때(mouseup) 이벤트 감지
        document.addEventListener('mouseup', function() {
            // 현재 선택된(드래그된) 텍스트 가져오기
            let selection = window.getSelection().toString();
            
            // 선택된 텍스트가 있다면
            if (selection.length > 0) {
                // 클립보드에 쓰기
                navigator.clipboard.writeText(selection).then(function() {
                    // 성공 시 알림창 띄우기 함수 호출
                    showToast();
                }, function(err) {
                    console.error('복사 실패:', err);
                });
            }
        });

        // 알림창 표시 함수
        function showToast() {
            var x = document.getElementById("toast");
            x.className = "show"; // .show 클래스 추가 (보이게 함)
            
            // 3초(3000ms) 뒤에 .show 클래스 제거 (사라지게 함)
            setTimeout(function(){ x.className = x.className.replace("show", ""); }, 3000);
        }
    </script>
    </body>
    </html>
    """
    
    # Streamlit에 HTML 렌더링
    # height를 넉넉하게 주어 스크롤 없이 보이게 함
    st.components.v1.html(html_content, height=height + 100, scrolling=True)

    st.success(f"분석 완료! {len(result)}개의 텍스트 영역을 찾았습니다.")