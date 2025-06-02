# -*- coding: utf-8 -*-
import streamlit as st
import requests
import json
import random

# ----------------------------------------
# 1) CompletionExecutor (HCX-005 호출용 기본 코드)
# ----------------------------------------
class CompletionExecutor:
    def __init__(self, host, api_key, request_id):
        self._host = host
        self._api_key = api_key
        self._request_id = request_id

    def execute(self, completion_request):
        headers = {
            'Authorization': self._api_key,                     # 기존에 사용 중인 API 키
            'X-NCP-CLOVASTUDIO-REQUEST-ID': self._request_id,   # 기존에 사용 중인 REQUEST ID
            'Content-Type': 'application/json; charset=utf-8',
            'Accept': 'text/event-stream'
        }

        # 실제 HCX-005 엔드포인트 호출 (stream=True 로 SSE 방식 수신)
        with requests.post(
            self._host + '/testapp/v3/chat-completions/HCX-005',
            headers=headers,
            json=completion_request,
            stream=True
        ) as r:
            # HTTP 상태 코드 검사
            if r.status_code == 401:
                st.warning("⚠️ 인증 오류 (401): API 키 혹은 REQUEST ID를 확인하세요.")
                return
            if r.status_code != 200:
                st.warning(f"서버 응답이 성공적이지 않습니다. 상태 코드: {r.status_code}")
                return

            # SSE(Event Stream) 형태로 들어오는 data: { ... } 를 파싱
            buffer_json = None
            for raw_line in r.iter_lines(decode_unicode=True):
                if raw_line is None:
                    continue
                line = raw_line.strip()

                # 스트림 종료 신호
                if line == "data: [DONE]":
                    break

                # data: 으로 시작하는 줄만 JSON 파싱 시도
                if line.startswith("data: "):
                    json_str = line[len("data: "):]
                    try:
                        chat_data = json.loads(json_str)
                        buffer_json = chat_data
                    except json.JSONDecodeError as e:
                        st.warning(f"일부 응답(JSON) 파싱 실패: {e}")
                        continue

            # 파싱된 최종 JSON이 있으면 챗 히스토리에 추가
            if buffer_json and "message" in buffer_json and "content" in buffer_json["message"]:
                content = buffer_json["message"]["content"]
                st.session_state.chat_history.append(
                    {"role": "assistant", "content": content}
                )
            else:
                st.warning("JSON 데이터가 없습니다. 아래 서버 응답을 확인하세요.")

# ----------------------------------------
# 2) Streamlit UI 설정
# ----------------------------------------

# 2-1) 이미지 URL 목록 (로봇 프로필 사진 등)
image_urls = [
    "https://th.bing.com/th/id/OIG4.sbvsXcpjpETlz2LO_4g6?w=1024&h=1024&rs=1&pid=ImgDetMain",
    "https://th.bing.com/th/id/OIG4.sbvsXcpjpETlz2LO_4g6?w=1024&h=1024&rs=1&pid=ImgDetMain",
    "https://th.bing.com/th/id/OIG4.fmafTjPZwEX17n9E4H49?pid=ImgGn",
    "https://th.bing.com/th/id/OIG4.fmafTjPZwEX17n9E4H49?pid=ImgGn",
    "https://th.bing.com/th/id/OIG4.0ugOUMKI2F1pZFRxpgfU?pid=ImgGn",
    "https://th.bing.com/th/id/OIG4.0ugOUMKI2F1pZFRxpgfU?pid=ImgGn",
    "https://th.bing.com/th/id/OIG4.fD.2uF_znryBJ9P_dlkH?pid=ImgGn",
    "https://th.bing.com/th/id/OIG4.fD.2uF_znryBJ9P_dlkH?pid=ImgGn",
    "https://th.bing.com/th/id/OIG3.fppMpx_V9bOB3msD.EbQ?w=1024&h=1024&rs=1&pid=ImgDetMain",
    "https://th.bing.com/th/id/OIG3.dMg4p1gEo.bpqfkgQyQr?w=1024&h=1024&rs=1&pid=ImgDetMain"
]

# 2-2) Streamlit 세션 상태 초기화
if "selected_image" not in st.session_state:
    st.session_state.selected_image = random.choice(image_urls)
selected_image = st.session_state.selected_image

if "chat_history" not in st.session_state:
    # 초기 대화 히스토리 (system / assistant 첫 메시지)
    st.session_state.chat_history = [
        {
            'role': 'user',
            'content': '너는 8살의 지능을 갖고 있어. 알고있는 지식도 초등학교에 입학하기 전 8살의 상태야. '
                       '다음 규칙에 따라서 응답해. 초등학교 입학 전이기 때문에 너의 지식과 지능 유치원 수준이야. '
                       '그 이상의 지식이나 기능을 묻는 질문에는 모른다고 답해. 예를 들면 유치원에서는 사칙연산을 배우지 않아. 그래서 너는 몰라. '
                       '2. 너는 8살이기 때문에 거기에 맞는 말투로 응답해. '
                       '3. 사용자가 알려주는 지식은 학습해. 사용자가 입력을 해주는 지식만 갖을 수 있어. '
                       '사용자가 지식을 많이 알려주고 설명해줄수록 너는 똑똑해지는거야. '
                       '4. 사용자가 설명을 했을 때 너는 어린 아이이기 때문에 이해할 수가 없어. 이해가 안되는 부분은 질문해. '
                       '5. 너에게 지적 수준이 어느 정도 되는지 물어보면 사용자가 알려준 지식을 평가해서 몇 살 정도의 지능이 되었는지 알려줘.'
        },
        {'role': 'assistant', 'content': '알겠어. 난 아무것도 몰라.'}
    ]

if "input_message" not in st.session_state:
    st.session_state.input_message = ""

if "copied_chat_history" not in st.session_state:
    st.session_state.copied_chat_history = ""

# 2-3) CompletionExecutor 인스턴스 생성 (API 키와 REQUEST ID는 “원래 거”로 세팅)
completion_executor = CompletionExecutor(
    host='https://clovastudio.stream.ntruss.com',
    api_key='Bearer <nv-bf4b622fd7f849b7bea4e9b0daab0098OVpu>', # ← 원래 사용 중인  api key
    request_id='b103b212f8db458989ff8d6a7d44eaa1'              # ← 원래 사용 중인 REQUEST ID
)

# 2-4) Streamlit 레이아웃/스타일 정의
st.markdown('<h1 class="title">지렁이 챗봇</h1>', unsafe_allow_html=True)
bot_profile_url = selected_image

st.markdown(f"""
    <style>
    body, .main, .block-container {{
        background-color: #BACEE0 !important;
    }}
    .title {{
        font-size: 28px !important;
        font-weight: bold;
        text-align: center;
        padding-top: 10px;
    }}
    .message-container {{
        display: flex;
        margin-bottom: 10px;
        align-items: center;
    }}
    .message-user {{
        background-color: #FFEB33 !important;
        color: black;
        text-align: right;
        padding: 10px;
        border-radius: 10px;
        margin-left: auto;
        max-width: 60%;
        box-shadow: 2px 2px 10px rgba(0, 0, 0, 0.1);
    }}
    .message-assistant {{
        background-color: #FFFFFF !important;
        text-align: left;
        padding: 10px;
        border-radius: 10px;
        margin-right: auto;
        max-width: 60%;
        box-shadow: 2px 2px 10px rgba(0, 0, 0, 0.1);
    }}
    .profile-pic {{
        width: 40px;
        height: 40px;
        border-radius: 50%;
        margin-right: 10px;
    }}
    .chat-box {{
        background-color: #BACEE0 !important;
        border: none;
        padding: 20px;
        border-radius: 10px;
        max-height: 400px;
        overflow-y: scroll;
        margin: 0 auto;
        width: 80%;
    }}
    .stTextInput > div > div > input {{
        height: 38px;
        width: 100%;
    }}
    .stButton button {{
        height: 38px !important;
        width: 70px !important;
        padding: 0px 10px;
        margin-right: 0px !important;
    }}
    .input-container {{
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        background-color: #BACEE0;
        padding: 10px;
        box-shadow: 0 -2px 5px rgba(0, 0, 0, 0.1);
    }}
    </style>
""", unsafe_allow_html=True)

# 채팅 히스토리 영역
st.markdown('<div class="chat-box">', unsafe_allow_html=True)

# 2-5) 사용자가 메시지를 입력했을 때 실행될 함수 정의
def send_message():
    if st.session_state.input_message:
        user_message = st.session_state.input_message
        # ① 사용자가 보낸 메시지를 세션 상태에 추가
        st.session_state.chat_history.append({"role": "user", "content": user_message})

        # ② Completion 요청용 payload 생성
        completion_request = {
            'messages': st.session_state.chat_history,
            'topP': 0.8,
            'topK': 0,
            'maxTokens': 256,
            'temperature': 0.5,
            'repetitionPenalty': 1.1,
            'stop': [],
            'includeAiFilters': True,
            'seed': 0
        }

        # ③ HCX-005 호출 (SSE 파싱 로직 포함)
        completion_executor.execute(completion_request)

        # ④ 입력란 초기화
        st.session_state.input_message = ""

# 2-6) 기존 대화 히스토리를 화면에 렌더링
for message in st.session_state.chat_history[2:]:
    role = "User" if message["role"] == "user" else "Chatbot"
    profile_url = bot_profile_url if role == "Chatbot" else None
    message_class = 'message-user' if role == "User" else 'message-assistant'

    if role == "Chatbot":
        st.markdown(f'''
            <div class="message-container">
                <img src="{profile_url}" class="profile-pic" alt="프로필 이미지">
                <div class="{message_class}">
                    {message["content"]}
                </div>
            </div>''', unsafe_allow_html=True)
    else:
        st.markdown(f'''
            <div class="message-container">
                <div class="{message_class}">
                    {message["content"]}
                </div>
            </div>''', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)  # chat-box 닫기

# 2-7) 입력란 및 버튼 영역
st.markdown('<div class="input-container">', unsafe_allow_html=True)
with st.form(key="input_form", clear_on_submit=True):
    cols = st.columns([7.5, 1, 1])
    with cols[0]:
        user_message = st.text_input("메시지를 입력하세요:", key="input_message", placeholder="")
    with cols[1]:
        submit_button = st.form_submit_button(label="전송", on_click=send_message)
    with cols[2]:
        def copy_chat_history():
            filtered_chat_history = [
                msg for msg in st.session_state.chat_history[2:]
            ]
            chat_history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in filtered_chat_history])
            st.session_state.copied_chat_history = chat_history_text

        copy_button = st.form_submit_button(label="복사", on_click=copy_chat_history)
st.markdown('</div>', unsafe_allow_html=True)

# 2-8) 복사된 대화 보여주기(클립보드 복사 기능)
if st.session_state.copied_chat_history:
    st.markdown("<h3>대화 내용 정리</h3>", unsafe_allow_html=True)
    st.text_area("", value=st.session_state.copied_chat_history, height=200, key="copied_chat_history_text_area")
    chat_history = st.session_state.copied_chat_history.replace("\n", "\\n").replace('"', '\\"')
    st.components.v1.html(f"""
        <textarea id="copied_chat_history_text_area" style="display:none;">{chat_history}</textarea>
        <button onclick="copyToClipboard()" class="copy-button">클립보드로 복사</button>
        <script>
        function copyToClipboard() {{
            var text = document.getElementById('copied_chat_history_text_area').value.replace(/\\\\n/g, '\\n');
            navigator.clipboard.writeText(text).then(function() {{
                alert('클립보드로 복사되었습니다!');
            }}, function(err) {{
                console.error('복사 실패: ', err);
            }});
        }}
        </script>
    """, height=100)
