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

# 이벤트 차단 스크립트
st.components.v1.html("""
<script>
window.addEventListener('DOMContentLoaded', function() {
    document.body.addEventListener('contextmenu', e => e.preventDefault(), true);
    document.body.addEventListener('keydown', e => {
        if ((e.ctrlKey||e.metaKey) && ['c','v','x','a'].includes(e.key.toLowerCase())) e.preventDefault();
        if (['Insert','PrintScreen'].includes(e.key)) e.preventDefault();
    }, true);
    document.body.addEventListener('selectstart', e => e.preventDefault(), true);
    document.body.addEventListener('dragstart', e => e.preventDefault(), true);
    document.body.addEventListener('copy', e => e.preventDefault(), true);
    document.body.addEventListener('paste', e => e.preventDefault(), true);
    document.body.addEventListener('cut', e => e.preventDefault(), true);
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

# --- 1) 페이지 로드시 쿠키에서 learned_knowledge 읽어 URL 파라미터로 삽입 ---
cookie_loader_js = """
<script>
(function() {
    const params = new URLSearchParams(window.location.search);
    if (params.has('lk')) return;
    const ck = document.cookie.split(';').map(c=>c.trim())
                  .find(c=>c.startsWith('learned_knowledge='));
    if (!ck) return;
    const val = ck.split('=')[1];
    const newUrl = window.location.pathname + '?lk=' + val;
    window.history.replaceState(null, '', newUrl);
    window.dispatchEvent(new Event('streamlit:refresh'));
})();
</script>
"""
st.components.v1.html(cookie_loader_js, height=0)

# --- 2) URL 쿼리파라미터에서 lk 값을 가져와 세션에 복원 ---
params = st.experimental_get_query_params()
if "lk" in params and params["lk"]:
    try:
        decoded = urllib.parse.unquote(params["lk"][0])
        if not st.session_state.learned_knowledge:
            st.session_state.learned_knowledge = decoded
    except Exception:
        pass

# --- 쿠키에 learned_knowledge를 저장하는 JS 헬퍼 ---
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

# --- HyperCLOVA API 호출용 클래스 ---
class CompletionExecutor:
    def __init__(self, host: str, api_key: str, request_id: str):
        self.host = host
        self.key = api_key
        self.rid = request_id

    def get_response(self, req: dict) -> str:
        headers = {
            "Authorization": self.key,
            "X-NCP-CLOVASTUDIO-REQUEST-ID": self.rid,
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json"
        }
        resp = requests.post(self.host + "/testapp/v3/chat-completions/HCX-005",
                             headers=headers, json=req, timeout=30)
        resp.raise_for_status()
        data = resp.json().get("result", {}).get("message", {})
        return data.get("content", "") if isinstance(data, dict) else ""

# --- 채팅 기록 렌더링 함수 ---
def render_chat(history, height, container_id, title=None):
    style = f"""
    <style>
    .header {{ background:#FFEB00; padding:12px; text-align:center; font-weight:bold; border-radius:12px 12px 0 0; }}
    .chat {{ width:100%; background:#FFF; border:1px solid #E0E0E0; border-radius:12px; padding:12px; height:{height-50}px; overflow-y:auto; box-sizing:border-box; display:flex; flex-direction:column; gap:8px; }}
    .user {{ align-self:flex-end; background:#FFEB00; color:#000; padding:6px 14px; border-radius:20px 20px 4px 20px; max-width:90%; word-break:break-all; }}
    .bot {{ align-self:flex-start; background:#F0F0F0; color:#222; padding:6px 14px; border-radius:20px 20px 20px 4px; max-width:90%; word-break:break-all; }}
    </style>
    """
    html = style
    if title:
        html += f'<div class="header">{title}</div>'
    html += f'<div id="{container_id}" class="chat">'
    for m in history:
        cls = "user" if m["role"] == "user" else "bot"
        content = m["content"].replace("\n", "<br>")
        html += f'<div class="{cls}">{content}</div>'
    html += '</div>'
    html += f"""
    <script>
      const c = document.getElementById('{container_id}');
      if (c) c.scrollTop = c.scrollHeight;
    </script>
    """
    st.components.v1.html(html, height=height, scrolling=False)

# --- HyperCLOVA 환경변수 및 실행기 생성 ---
HYPERCLOVA_HOST = "https://clovastudio.stream.ntruss.com"
HYPERCLOVA_API_KEY = "Bearer nv-1ffa5328fe534e7290702280cbead54ew8Ez"
HYPERCLOVA_REQUEST_ID = "ef47ef9bad6d4908a1552340b6b43d76"
executor = CompletionExecutor(HYPERCLOVA_HOST, HYPERCLOVA_API_KEY, HYPERCLOVA_REQUEST_ID)

# --- 시스템 프롬프트(유치원생 역할) ---
system_prompt = {
    "role": "system",
    "content": """# 유치원생 학습 챗봇 (극한 제한)

너는 다섯 살 유치원생이야. **친구가 설명해준 내용만** 기억·사용할 수 있어.
모르는 건 절대 모른다고만 답하고, 친구가 알려주면 "이제 조금 알 것 같아!" 등 간단히 따라 말해.
"""
}

# --- 레이아웃: 왼쪽=대화, 오른쪽=학습 지식 ---
left, right = st.columns([3, 1.5])

with left:
    st.markdown("### 내 아이 공부시키기")
    render_chat(st.session_state.history, height=540, container_id="chat-main")

    # 입력 폼
    with st.form("input_form", clear_on_submit=True):
        ui = st.text_input("메시지를 입력하세요...", placeholder="입력 후 전송")
        send = st.form_submit_button("전송", use_container_width=True)

    if send and ui.strip():
        st.session_state.history.append({"role": "user", "content": ui})
        msgs = [system_prompt] + st.session_state.history
        payload = {
            "messages": msgs,
            "topP": 0.8,
            "topK": 0,
            "maxTokens": 256,
            "temperature": 0.5,
            "repetitionPenalty": 1.1,
            "stop": [],
            "includeAiFilters": True,
            "seed": 0,
            "stream": False
        }
        with st.spinner("응답을 받고 있습니다..."):
            bot = executor.get_response(payload)
        st.session_state.history.append({"role": "assistant", "content": bot})

        # **3) 대화로 학습된 지식이 업데이트되면 쿠키에도 추가 반영**
        if st.session_state.learned_knowledge:
            # 기존 learned_knowledge 뒤에 새 요약을 덧붙이려면 여기서 처리
            # 예: st.session_state.learned_knowledge += "\n" + "<새로 배운 내용>"
            update_cookie_js(st.session_state.learned_knowledge)

        st.experimental_rerun()

    # 지식 수준 분석 버튼
    if st.session_state.history and st.button("아이의 지식 수준 분석"):
        convo = "\n".join(
            f"{'사용자' if m['role']=='user' else '어시스턴트'}: {m['content']}"
            for m in st.session_state.history
        )
        summary_req = [
            {"role": "system", "content":
             "대화에서 배운 지식만 3~7줄 개조식으로 요약해줘. 불필요한 말 빼고 핵심만."},
            {"role": "user", "content": convo}
        ]
        with st.spinner("요약 생성 중..."):
            summ = executor.get_response({
                "messages": summary_req,
                "topP": 0.8, "topK": 0,
                "maxTokens": 300,
                "temperature": 0.5,
                "repetitionPenalty": 1.05,
                "stop": [],
                "includeAiFilters": True,
                "seed": 0,
                "stream": False
            })
        summ_nl = re.sub(r'([.!?])\s*', r'\1\n', summ).strip()
        st.session_state.learned_knowledge = summ_nl

        # ① 쿠키에 저장, ② URL 쿼리에도 심기
        update_cookie_js(summ_nl)
        enc = urllib.parse.quote(summ_nl)
        st.experimental_set_query_params(lk=enc)

        # 나이 분석은 생략(기존 로직 유지)
        st.experimental_rerun()

    # 학습된 지식 & 나이 표시
    if st.session_state.learned_knowledge:
        st.markdown("##### 아이의 지식 수준")
        st.text_area("지식 수준", st.session_state.knowledge_age_level, height=70, disabled=True)

with right:
    st.markdown("### 내 아이가 학습한 지식")
    # “학습한 지식 보기” 버튼을 누르면 세션에 이미 복원된 상태 → 단순 rerun
    if st.button("학습한 지식 보기"):
        st.experimental_rerun()

    if st.session_state.learned_knowledge:
        render_chat(
            [{"role": "assistant", "content": st.session_state.learned_knowledge}],
            height=220, container_id="chat-knowledge"
        )
