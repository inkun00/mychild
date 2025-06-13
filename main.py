import streamlit as st
import requests
import re
import urllib.parse

# --- 페이지 wide 설정 및 최대 폭 확장 + 복사/붙여넣기/마우스 차단 ---
st.set_page_config(page_title="HyperCLOVA 유치원 챗봇", layout="wide")
st.markdown("""
    <style>
        .main .block-container {max-width: 1800px;}
        html, body, textarea, input, .chat-container {
            user-select: none !important;
            -webkit-user-select: none !important;
            -moz-user-select: none !important;
            -ms-user-select: none !important;
        }
    </style>
""", unsafe_allow_html=True)

# 이벤트 차단(오른쪽클릭/복붙/드래그/선택/키 단축키 등)
st.components.v1.html("""
    <script>
    window.addEventListener('DOMContentLoaded', function() {
        document.body.addEventListener('contextmenu', function(e) {
            e.preventDefault();
            return false;
        }, true);
        document.body.addEventListener('keydown', function(e) {
            if ((e.ctrlKey || e.metaKey) && (
                e.key.toLowerCase() === 'c' || e.key.toLowerCase() === 'v' ||
                e.key.toLowerCase() === 'x' || e.key.toLowerCase() === 'a' ||
                e.key === 'Insert'
            )) {
                e.preventDefault();
                return false;
            }
            if (e.shiftKey && e.key === 'Insert') {
                e.preventDefault();
                return false;
            }
            if (e.key === 'PrintScreen') {
                e.preventDefault();
                return false;
            }
        }, true);
        document.body.addEventListener('selectstart', function(e) {
            e.preventDefault();
            return false;
        }, true);
        document.body.addEventListener('dragstart', function(e) {
            e.preventDefault();
            return false;
        }, true);
        document.body.addEventListener('copy', function(e) {
            e.preventDefault();
            return false;
        }, true);
        document.body.addEventListener('paste', function(e) {
            e.preventDefault();
            return false;
        }, true);
        document.body.addEventListener('cut', function(e) {
            e.preventDefault();
            return false;
        }, true);
    });
    </script>
""", height=10)

# --------- 세션 상태 초기화 ---------
if "history" not in st.session_state:
    st.session_state.history = []
if "learned_knowledge" not in st.session_state:
    st.session_state.learned_knowledge = ""
if "knowledge_age_level" not in st.session_state:
    st.session_state.knowledge_age_level = ""

# --- 페이지 로드시 쿠키에 'learned_knowledge' 값이 있으면, URL에 '?lk=...' 붙여 리로딩 ---
cookie_loader_js = """
<script>
(function() {
    const params = new URLSearchParams(window.location.search);
    if (params.has('lk')) return;
    const cookies = document.cookie.split(';').map(c => c.trim());
    const kv = cookies.find(c => c.startsWith('learned_knowledge='));
    if (kv) {
        const encoded = kv.split('=')[1];
        const newUrl = window.location.pathname + '?lk=' + encoded;
        window.location.replace(newUrl);
    }
})();
</script>
"""
st.components.v1.html(cookie_loader_js, height=0)

# --- 쿼리 파라미터 'lk'가 있으면 세션 상태로 복원 ---
query_params = st.query_params
if "lk" in query_params:
    try:
        decoded = urllib.parse.unquote(query_params["lk"][0])
        if not st.session_state.learned_knowledge:
            st.session_state.learned_knowledge = decoded
    except:
        pass

# Helper: learned_knowledge를 쿠키에 업데이트하는 JS 삽입
def update_cookie_js(text: str):
    esc = text.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
    js = f"""
    <script>
        const expires = new Date();
        expires.setDate(expires.getDate() + 7);
        document.cookie = "learned_knowledge=" + encodeURIComponent('{esc}') + "; expires=" + expires.toUTCString() + "; path=/";
    </script>
    """
    st.components.v1.html(js, height=0)

# HyperCLOVA API 호출용 클래스
class CompletionExecutor:
    def __init__(self, host: str, api_key: str, request_id: str):
        self._host = host
        self._api_key = api_key
        self._request_id = request_id

    def get_response(self, completion_request: dict) -> str:
        headers = {
            "Authorization": self._api_key,
            "X-NCP-CLOVASTUDIO-REQUEST-ID": self._request_id,
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json"
        }
        try:
            r = requests.post(
                self._host + "/testapp/v3/chat-completions/HCX-005",
                headers=headers,
                json=completion_request,
                stream=False,
                timeout=30
            )
            r.raise_for_status()
            data = r.json()
            msg = data.get("result", {}).get("message", {})
            return msg.get("content", "") if isinstance(msg, dict) else ""
        except Exception as e:
            return f"(에러: {repr(e)})"

# 채팅 기록 렌더링 함수
def render_chat_with_scroll(history, height=420, container_id='chat-container', title=None):
    chat_html = f"""
    <style>
    .header {{ background-color: #FFEB00; padding:16px; border-radius:12px 12px 0 0; text-align:center; font-size:1.5rem; font-weight:bold; color:#222; margin-bottom:0; }}
    .chat-container {{ width:100%; background:#fff; border-radius:12px; padding:16px; height:{height-50}px; max-height:60vh; overflow-y:auto; border:1.5px solid #E0E0E0; display:flex; flex-direction:column; gap:10px; box-sizing:border-box; margin-bottom:10px; }}
    .bubble-user {{ align-self:flex-end; background:#FFEB00; color:#000; padding:8px 20px; border-radius:20px 20px 4px 20px; max-width:95%; word-break:break-all; font-size:1.08rem; box-shadow:0 2px 4px rgba(0,0,0,0.03); margin-left:5%; }}
    .bubble-assistant {{ align-self:flex-start; background:#F0F0F0; color:#222; padding:8px 20px; border-radius:20px 20px 20px 4px; max-width:95%; word-break:break-all; font-size:1.08rem; box-shadow:0 2px 4px rgba(0,0,0,0.02); margin-right:5%; }}
    </style>
    """
    if title:
        chat_html += f'<div class="header">{title}</div>'
    chat_html += f'<div class="chat-container" id="{container_id}">'
    for msg in history:
        html = msg["content"].replace('\n', '<br>')
        cls = "bubble-user" if msg["role"]=="user" else "bubble-assistant"
        chat_html += f'<div class="{cls}">{html}</div>'
    chat_html += '<div id="scroll-anchor"></div></div>'
    chat_html += f"""
    <script>
      const c = document.getElementById('{container_id}');
      if(c) c.scrollTop = c.scrollHeight;
    </script>
    """
    st.components.v1.html(chat_html, height=height, scrolling=False)

# HyperCLOVA 환경변수
HYPERCLOVA_HOST = "https://clovastudio.stream.ntruss.com"
HYPERCLOVA_API_KEY = "Bearer nv-1ffa5328fe534e7290702280cbead54ew8Ez"
HYPERCLOVA_REQUEST_ID = "ef47ef9bad6d4908a1552340b6b43d76"
executor = CompletionExecutor(HYPERCLOVA_HOST, HYPERCLOVA_API_KEY, HYPERCLOVA_REQUEST_ID)

# 시스템 프롬프트
system_prompt = {
    "role":"system","content":(
        "# 유치원생 학습 챗봇 (극한 제한)\n\n"
        "너의 역할\n"
        "- 너는 다섯 살 유치원생이야. **네가 친구(사용자)에게서 실제로 들은 설명만 기억·사용할 수 있어.**\n"
        "- 네가 알고 있는 건 오직 직접 배운 것, 친구가 알려준 내용 뿐이야. 그 외에는 무조건 '아직 몰라! 알려줘!' 라고 답해.\n"
        "- 대통령, 국회의원, 블랙홀, 아인슈타인, 곱하기, 우주, 분수, 정직, 성실, 진실, 초등학교 지식 등 아무리 쉬워도 친구가 알려주지 않았다면 절대 모른다고 답해.\n"
        "- 규칙: 네가 실제로 친구에게서 설명을 들은 적 없는 것은, 어떤 정보든 추측하거나 답하지 말고 무조건 '아직 몰라! 알려줘!' 또는 '모르겠어, 설명해 줘!'라고만 답해.\n"
        "- 친구가 설명해주면 그 내용만 아주 간단하게 따라 말하거나, '이제 조금 알 것 같아!'라고만 말해.\n"
        "- 실수로 규칙을 어기면 반드시 '미안해요! 다시 말할게!'라고 사과하고 다시 어린이처럼 답해.\n"
        "- 어려운 낱말, 외래어, 긴 문장, 추론, AI나 시스템 관련 용어, 지식 뽐내기 모두 금지.\n"
        "- 절대로, 절대로 네가 배운 적 없는 지식은 말하지 마. 학습된 지식, 사전지식, 인터넷지식 사용 절대 금지.\n"
        "\n예시 대화\n"
        "사용자: 대통령은 뭐야?\n챗봇: 아직 몰라! 알려줘!\n"
        "사용자: 대통령은 나라를 이끄는 사람이야.\n챗봇: 나라를 이끄는 사람이구나! 이제 조금 알 것 같아!\n"
    )
}

# 레이아웃: 왼쪽=대화, 오른쪽=학습 지식
left, right = st.columns([3,1.5])

with left:
    st.markdown("### 내 아이 공부시키기")
    render_chat_with_scroll(st.session_state.history, height=540, container_id='chat-container-main')

    # 입력 폼
    with st.form("input_form", clear_on_submit=True):
        user_input = st.text_input("메시지를 입력하세요...", placeholder="입력 후 전송")
        submitted = st.form_submit_button("전송", use_container_width=True)

    if submitted and user_input.strip():
        st.session_state.history.append({"role":"user","content":user_input})
        msgs = [system_prompt] + [{"role":m["role"],"content":m["content"]} for m in st.session_state.history]
        payload = {
            "messages": msgs, "topP":0.8, "topK":0, "maxTokens":256,
            "temperature":0.5, "repetitionPenalty":1.1,
            "stop":[], "includeAiFilters":True, "seed":0, "stream":False
        }
        with st.spinner("응답을 받고 있습니다..."):
            resp = executor.get_response(payload)
        st.session_state.history.append({"role":"assistant","content":resp})
        st.rerun()

    # 지식 수준 분석
    if st.session_state.history and st.button("아이의 지식 수준 분석"):
        convo = "".join(
            f"{'사용자' if m['role']=='user' else '어시스턴트'}: {m['content']}\n"
            for m in st.session_state.history
        )
        summary_prompt = [
            {"role":"system","content":
             "아래는 유치원생(어시스턴트)와 친구(사용자)의 대화 내용이다. "
             "어시스턴트가 친구(사용자)에게서 배운 지식만 개조식으로 요약해줘. "
             "각 줄 맨 앞에 '-' 붙이고, 불필요한 인삿말·감사·질문·설명 빼고 3~7줄로 정리."},
            {"role":"user","content":convo}
        ]
        payload = {
            "messages": summary_prompt, "topP":0.8, "topK":0, "maxTokens":300,
            "temperature":0.5, "repetitionPenalty":1.05,
            "stop":[], "includeAiFilters":True, "seed":0, "stream":False
        }
        with st.spinner("요약 생성 중..."):
            summ = executor.get_response(payload)
        summ_nl = re.sub(r'([.!?])\s*', r'\1\n', summ)
        st.session_state.learned_knowledge = summ_nl
        update_cookie_js(summ_nl)

        # 나이 분석
        analyze_prompt = [
            {"role":"system","content":
             "아래는 한 학생이 배운 지식 목록이다. "
             "대한민국 교육과정 기준에서 평균 학생이 이해 가능한 최소 나이를 "
             "'몇 살 몇 개월'만으로 한 줄로 출력하라. 예: 11살 0개월"},
            {"role":"user","content":f"<학습한 지식 목록>\n{st.session_state.learned_knowledge}"}
        ]
        apayload = {
            "messages": analyze_prompt, "topP":0.7, "topK":0,
            "maxTokens":12, "temperature":0.2, "repetitionPenalty":1.15,
            "stop":[], "includeAiFilters":True, "seed":0, "stream":False
        }
        with st.spinner("나이 분석 중..."):
            age = executor.get_response(apayload).strip()
        st.session_state.knowledge_age_level = age
        st.rerun()

    # 학습된 지식과 나이 표시
    if st.session_state.learned_knowledge:
        st.markdown("##### 아이의 지식 수준")
        st.text_area("지식 수준", st.session_state.knowledge_age_level, height=70, disabled=True)

    # 수동 저장 버튼(보조)
    if st.session_state.learned_knowledge:
        esc = st.session_state.learned_knowledge.replace("\\","\\\\").replace("'", "\\'").replace("\n","\\n")
        manual_js = f"""
        <div style="margin-top:10px;">
          <button id="save-knowledge">지식 저장</button>
          <script>
            document.getElementById('save-knowledge').onclick = ()=>{{
              const expires=new Date();expires.setDate(expires.getDate()+7);
              document.cookie="learned_knowledge="+encodeURIComponent('{esc}')+";expires="+expires.toUTCString()+";path=/";
              alert("저장 완료");
            }};
          </script>
        </div>
        """
        st.components.v1.html(manual_js, height=60)

with right:
    st.markdown("### 내 아이가 학습한 지식")
    if st.button("학습한 지식 보기"):
        convo = "".join(
            f"{'사용자' if m['role']=='user' else '어시스턴트'}: {m['content']}\n"
            for m in st.session_state.history
        )
        summary_prompt = [
            {"role":"system","content":
             "아래는 유치원생(어시스턴트)와 친구(사용자) 대화이다. "
             "배운 지식만 개조식으로 3~7줄 요약해줘."},
            {"role":"user","content":convo}
        ]
        payload = {
            "messages": summary_prompt, "topP":0.8, "topK":0, "maxTokens":300,
            "temperature":0.5, "repetitionPenalty":1.05,
            "stop":[], "includeAiFilters":True, "seed":0, "stream":False
        }
        with st.spinner("요약 생성 중..."):
            summ = executor.get_response(payload)
        summ_nl = re.sub(r'([.!?])\s*', r'\1\n', summ)
        st.session_state.learned_knowledge = summ_nl
        update_cookie_js(summ_nl)
        st.rerun()

    if st.session_state.learned_knowledge:
        render_chat_with_scroll(
            [{"role":"assistant","content":st.session_state.learned_knowledge}],
            height=220, container_id='chat-container-knowledge'
        )
