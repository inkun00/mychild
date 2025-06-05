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

# --------- 세션 상태 초기화 및 쿠키에서 학습된 지식 로드 ---------
if "history" not in st.session_state:
    st.session_state.history = []

if "learned_knowledge" not in st.session_state:
    st.session_state.learned_knowledge = ""

if "knowledge_age_level" not in st.session_state:
    st.session_state.knowledge_age_level = ""

# 쿼리 파라미터로 전달된 'lk' 값이 있으면 디코딩하여 세션에 할당
query_params = st.query_params
if "lk" in query_params:
    encoded_text = query_params["lk"][0]
    try:
        decoded_text = urllib.parse.unquote(encoded_text)
        # 세션에 아직 학습된 지식이 없으면 쿼리에서 가져온 것을 할당
        if not st.session_state.learned_knowledge:
            st.session_state.learned_knowledge = decoded_text
    except Exception:
        pass

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
            content = ""
            if "result" in data and "message" in data["result"]:
                msg = data["result"]["message"]
                if isinstance(msg, dict) and "content" in msg:
                    content = msg["content"]
            return content
        except Exception as e:
            return f"(에러: {repr(e)})"

# 채팅 기록 렌더링 함수
def render_chat_with_scroll(history, height=420, container_id='chat-container', title=None):
    chat_html = f"""
    <style>
    .header {{
        background-color: #FFEB00;
        padding: 16px 0 12px 0;
        border-radius: 12px 12px 0 0;
        text-align: center;
        font-size: 1.5rem;
        font-weight: bold;
        color: #222;
        margin-bottom: 0;
    }}
    .chat-container {{
        width: 100%;
        background-color: #FFFFFF;
        border-radius: 12px;
        padding: 16px 10px 10px 10px;
        height: {height-50}px;
        max-height: 60vh;
        overflow-y: auto;
        border: 1.5px solid #E0E0E0;
        display: flex;
        flex-direction: column;
        gap: 10px;
        box-sizing: border-box;
        margin-bottom: 10px;
    }}
    .bubble-user {{
        align-self: flex-end;
        background-color: #FFEB00;
        color: #000;
        padding: 8px 20px;
        border-radius: 20px 20px 4px 20px;
        max-width: 95%;
        word-break: break-all;
        font-size: 1.08rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.03);
        margin-left: 5%;
    }}
    .bubble-assistant {{
        align-self: flex-start;
        background-color: #F0F0F0;
        color: #222;
        padding: 8px 20px;
        border-radius: 20px 20px 20px 4px;
        max-width: 95%;
        word-break: break-all;
        font-size: 1.08rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        margin-right: 5%;
    }}
    </style>
    """
    if title:
        chat_html += f'<div class="header">{title}</div>'
    chat_html += f'<div class="chat-container" id="{container_id}">'
    for msg in history:
        content = msg["content"].replace('\n', '<br>')
        if msg["role"] == "user":
            chat_html += f'<div class="bubble-user">{content}</div>'
        elif msg["role"] == "assistant":
            chat_html += f'<div class="bubble-assistant">{content}</div>'
    chat_html += f"""
    <div id="scroll-anchor"></div>
    </div>
    <script>
        const container = document.getElementById('{container_id}');
        if (container) {{
            container.scrollTop = container.scrollHeight;
        }}
    </script>
    """
    st.components.v1.html(chat_html, height=height, scrolling=False)

# HyperCLOVA API 환경 변수
HYPERCLOVA_HOST = "https://clovastudio.stream.ntruss.com"
HYPERCLOVA_API_KEY = "Bearer nv-1ffa5328fe534e7290702280cbead54ew8Ez"
HYPERCLOVA_REQUEST_ID = "ef47ef9bad6d4908a1552340b6b43d76"
executor = CompletionExecutor(
    host=HYPERCLOVA_HOST,
    api_key=HYPERCLOVA_API_KEY,
    request_id=HYPERCLOVA_REQUEST_ID
)

# 시스템 프롬프트 (유치원생 역할)
system_prompt = {
    "role": "system",
    "content": (
        "# 유치원생 학습 챗봇 (극한 제한)\n\n"
        "너의 역할\n"
        "- 너는 다섯 살 유치원생이야. **네가 친구(사용자)에게서 실제로 들은 설명만 기억·사용할 수 있어.**\n"
        "- 네가 알고 있는 건 오직 직접 배운 것, 친구가 알려준 내용 뿐이야. 그 외에는 무조건 '아직 몰라! 알려줘!' 라고 답해. \n"
        "- 대통령, 국회의원, 블랙홀, 아인슈타인, 곱하기, 우주, 분수, 정직, 성실, 진실, 초등학교 지식 등 아무리 쉬워도 친구가 알려주지 않았다면 절대 모른다고 답해.\n"
        "- 규칙: 네가 실제로 친구에게서 설명을 들은 적 없는 것은, 어떤 정보든 추측하거나 답하지 말고 무조건 '아직 몰라! 알려줘!' 또는 '모르겠어, 설명해 줘!'라고만 답해.\n"
        "- 친구가 설명해주면 그 내용만 아주 간단하게 따라 말하거나, '이제 조금 알 것 같아!'라고만 말해.\n"
        "- 실수로 규칙을 어기면 반드시 '미안해요! 다시 말할게!'라고 사과하고 다시 어린이처럼 답해.\n"
        "- 어려운 낱말, 외래어, 긴 문장, 추론, AI나 시스템 관련 용어, 지식 뽐내기 모두 금지.\n"
        "- 절대로, 절대로 네가 배운 적 없는 지식은 말하지 마. 학습된 지식, 사전지식, 인터넷지식 사용 절대 금지.\n"
        "\n예시 대화\n"
        "사용자: 대통령은 뭐야?\n"
        "챗봇: 아직 몰라! 알려줘!\n"
        "사용자: 대통령은 나라를 이끄는 사람이야.\n"
        "챗봇: 나라를 이끄는 사람이구나! 이제 조금 알 것 같아!\n"
        "사용자: 블랙홀은 뭐야?\n"
        "챗봇: 모르는 거야! 알려줘!\n"
        "사용자: 블랙홀은 별이 무너져서 생기는 거야.\n"
        "챗봇: 별이 무너져서 생기는 거구나! 고마워!\n"
    )
}

# 레이아웃: 왼쪽 = 대화 및 분석, 오른쪽 = 학습한 지식 보여주기
left_col, right_col = st.columns([3, 1.5])

with left_col:
    st.markdown("### 내 아이 공부시키기")
    render_chat_with_scroll(
        st.session_state.history, height=540, container_id='chat-container-main', title=None
    )

    # 채팅 입력 폼
    with st.form(key="input_form", clear_on_submit=True):
        user_input = st.text_input(
            "메시지를 입력하세요...",
            "",
            key="input_text",
            placeholder="메시지를 입력하고 엔터를 누르거나 전송 버튼을 클릭하세요."
        )
        submitted = st.form_submit_button("전송", use_container_width=True)

    # 새 메시지가 제출되면 HyperCLOVA 호출
    if submitted and user_input and user_input.strip():
        st.session_state.history.append({"role": "user", "content": user_input})

        messages = [system_prompt]
        for msg in st.session_state.history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        request_payload = {
            "messages": messages,
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
            bot_response = executor.get_response(request_payload)
        st.session_state.history.append({"role": "assistant", "content": bot_response})

        st.rerun()

    # ---------------------------------------------
    # 아이의 지식 수준 분석 버튼 (요약 → 분석)
    # ---------------------------------------------
    if st.session_state.history:
        if st.button("아이의 지식 수준 분석"):
            # 1) 최신 대화(history)를 기반으로 learned_knowledge(요약) 갱신
            convo = ""
            for msg in st.session_state.history:
                if msg["role"] == "user":
                    convo += f"사용자: {msg['content']}\n"
                elif msg["role"] == "assistant":
                    convo += f"어시스턴트: {msg['content']}\n"

            summary_prompt = [
                {"role": "system", "content":
                    "아래는 유치원생(어시스턴트)와 친구(사용자)의 대화 내용이야. "
                    "어시스턴트가 친구(사용자)에게서 배운 지식만 **개조식으로** 요약해줘. "
                    "각 줄의 맨 앞에 '-'를 붙이고, 불필요한 인삿말·감사표현·질문·설명은 빼고, "
                    "실제로 이해한 핵심 지식·사실만 3~7줄로 정리해."
                },
                {"role": "user", "content": convo}
            ]
            summary_payload = {
                "messages": summary_prompt,
                "topP": 0.8,
                "topK": 0,
                "maxTokens": 300,
                "temperature": 0.5,
                "repetitionPenalty": 1.05,
                "stop": [],
                "includeAiFilters": True,
                "seed": 0,
                "stream": False
            }
            with st.spinner("학습한 내용을 요약하는 중..."):
                new_summary = executor.get_response(summary_payload)

            # 줄바꿈 처리
            summary_with_newlines = re.sub(r'([.!?])\s*', r'\1\n', new_summary)
            st.session_state.learned_knowledge = summary_with_newlines

            # 2) 방금 갱신된 learned_knowledge를 바탕으로 나이 계산 요청
            analyze_prompt = [
                {"role": "system", "content":
                    "아래는 한 학생이 누적해서 배운 지식 목록이다.\n"
                    "오직 이 목록의 전체 내용을 바탕으로, 대한민국 교육과정(초등~고등) 기준에서 "
                    "평균적인 학생이 모두 이해할 수 있는 최소 나이를 '몇 살 몇 개월'만으로, 1개만, "
                    "다른 말 없이 출력하라.\n"
                    "학습한 지식 목록의 내용을 분석해서 대한민국 나이 기준으로 "
                    "몇 살 정도의 지식 수준을 갖고 있는지 출력하라.\n"
                    "추가설명, 여러 개의 나이, 부연, 문장 금지. 반드시 한 줄, 예시 형식만. (예: 11살 0개월)\n\n"
                    "예시:\n"
                    "- 구구단 문제: 9살\n"
                    "- 덧셈/뺄셈만 있을 때: 8살 0개월\n"
                    "- 분수의 사칙연산, 원소기호, 도형의 둘레, 넓이까지 있으면: 11살 0개월\n"
                    "- 피타고라스 정리, 소인수분해, 함수 개념 있으면: 14살 0개월\n"
                    "- 삼각함수, 미적분, 통계, 확률: 17살 0개월\n\n"
                    "나이 하나만 답하라."
                },
                {"role": "user", "content": f"<학습한 지식 목록>\n{st.session_state.learned_knowledge}"}
            ]
            analyze_payload = {
                "messages": analyze_prompt,
                "topP": 0.7,
                "topK": 0,
                "maxTokens": 12,
                "temperature": 0.2,
                "repetitionPenalty": 1.15,
                "stop": [],
                "includeAiFilters": True,
                "seed": 0,
                "stream": False
            }
            with st.spinner("지식 수준을 분석하는 중..."):
                age_level = executor.get_response(analyze_payload)
            st.session_state.knowledge_age_level = age_level.strip()

            st.rerun()  # 갱신된 내용 반영

    # ---------------------------------------------
    # 화면에 학습된 지식과 계산된 나이 표시
    # ---------------------------------------------
    if st.session_state.learned_knowledge:
        st.markdown("##### 아이의 지식 수준")
        level = st.session_state.knowledge_age_level if st.session_state.knowledge_age_level else ""
        st.text_area("지식 수준", level, height=70, key="knowledge_level_display", disabled=True)

    # ---------------------------------------------
    # 쿠키에 저장하는 버튼 (HTML + JS 삽입)
    # ---------------------------------------------
    if st.session_state.learned_knowledge:
        # learned_knowledge 내용을 JS로 전달하려면, 작은 따옴표와 줄바꿈 등을 이스케이프 처리
        escaped_text = st.session_state.learned_knowledge.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
        save_button_html = f"""
        <div style="margin-top: 10px;">
            <button id="save-knowledge">지식 저장</button>
            <script>
                document.getElementById('save-knowledge').onclick = function() {{
                    const text = '{escaped_text}';
                    document.cookie = "learned_knowledge=" + encodeURIComponent(text) + "; path=/";
                    alert("학습된 지식을 쿠키에 저장했습니다.");
                }};
            </script>
        </div>
        """
        st.components.v1.html(save_button_html, height=60)

    # ---------------------------------------------
    # 쿠키에서 읽어서 쿼리 파라미터로 넘겨주는 JS (페이지 로드 시)
    # ---------------------------------------------
    cookie_loader_js = """
    <script>
    (function() {
        // URL에 이미 'lk' 파라미터가 있으면 넘어가지 않음
        const params = new URLSearchParams(window.location.search);
        if (params.has('lk')) {
            return;
        }
        // 쿠키에서 learned_knowledge 값 찾기
        const cookies = document.cookie.split(';').map(c => c.trim());
        const kv = cookies.find(c => c.startsWith('learned_knowledge='));
        if (kv) {
            const encoded = kv.split('=')[1];
            // 쿼리 파라미터 없이 페이지 새로고침
            const newUrl = window.location.pathname + '?lk=' + encoded;
            window.location.replace(newUrl);
        }
    })();
    </script>
    """
    st.components.v1.html(cookie_loader_js, height=0)

with right_col:
    st.markdown("### 내 아이가 학습한 지식")
    if st.button("학습한 지식 보기"):
        convo = ""
        for msg in st.session_state.history:
            if msg["role"] == "user":
                convo += f"사용자: {msg['content']}\n"
            elif msg["role"] == "assistant":
                convo += f"어시스턴트: {msg['content']}\n"
        summary_prompt = [
            {"role": "system", "content": "아래는 유치원생(어시스턴트)와 친구(사용자)의 대화 내용이야. 어시스턴트가 친구(사용자)에게서 배운 지식만 **개조식으로** 요약해줘. 각 줄의 맨 앞에 '-'를 붙이고, 불필요한 인삿말·감사표현·질문·설명은 빼고, 실제로 이해한 핵심 지식·사실만 3~7줄로 정리해."},
            {"role": "user", "content": convo}
        ]
        summary_payload = {
            "messages": summary_prompt,
            "topP": 0.8,
            "topK": 0,
            "maxTokens": 300,
            "temperature": 0.5,
            "repetitionPenalty": 1.05,
            "stop": [],
            "includeAiFilters": True,
            "seed": 0,
            "stream": False
        }
        with st.spinner("학습한 내용을 요약하는 중..."):
            summary = executor.get_response(summary_payload)
        summary_with_newlines = re.sub(r'([.!?])\s*', r'\1\n', summary)
        st.session_state.learned_knowledge = summary_with_newlines

        st.rerun()

    if st.session_state.learned_knowledge:
        knowledge_history = [{"role": "assistant", "content": st.session_state.learned_knowledge}]
        render_chat_with_scroll(knowledge_history, height=220, container_id='chat-container-knowledge', title=None)
