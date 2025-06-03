import streamlit as st
import requests
import json
import random

# ----------------------------------------
# 1) CompletionExecutor (디버깅용 로그 및 st.warning 출력 추가)
# ----------------------------------------
class CompletionExecutor:
    def __init__(self, host, api_key, request_id):
        self._host = host
        self._api_key = api_key
        self._request_id = request_id  # request_id를 멤버 변수로 저장

    def execute(self, completion_request):
        headers = {
            'Authorization': self._api_key,
            'X-NCP-CLOVASTUDIO-REQUEST-ID': self._request_id,  # self._request_id 사용
            'Content-Type': 'application/json; charset=utf-8',
            'Accept': 'text/event-stream'
        }

        # 호출 전에 로그 찍기 (Streamlit 콘솔 또는 터미널에서 확인 가능)
        print("▶▶▶ 요청 URL:", self._host + '/testapp/v3/chat-completions/HCX-005')
        print("▶▶▶ 헤더:", headers)
        print("▶▶▶ 페이로드:", json.dumps(completion_request, ensure_ascii=False, indent=2))

        with requests.post(
            self._host + '/testapp/v3/chat-completions/HCX-005',
            headers=headers,
            json=completion_request,
            stream=True
        ) as r:
            status_code = r.status_code
            # 먼저 상태 코드만 콘솔에 출력
            print("◀◀◀ 응답 상태 코드:", status_code)

            # ① 상태 코드가 200이 아니면, st.warning으로 상세 에러 정보를 출력
            if status_code != 200:
                # 응답 바디 일부(최대 1000자) 읽어오기
                try:
                    raw_body = r.text
                    body_snippet = raw_body[:1000]
                except Exception as e:
                    body_snippet = f"<바디 읽기 실패: {e}>"

                # JSON 형태로 파싱 시도
                try:
                    err_json = r.json()
                except Exception:
                    err_json = None

                # 401 에러일 때 경고 표시
                if status_code == 401:
                    st.warning("⚠️ 인증 오류 (401): API 키 혹은 REQUEST ID를 확인하세요.")
                else:
                    st.warning(f"⚠️ 서버 응답 오류: 상태 코드 {status_code}")

                # 응답 바디 텍스트 일부를 st.warning으로 출력
                st.warning(f"응답 바디 (최대 1000자):\n{body_snippet}")

                # JSON 파싱에 성공했다면, err_json 내부의 code/message를 st.warning으로 출력
                if isinstance(err_json, dict):
                    code_val = err_json.get("code") or err_json.get("errorCode") or err_json.get("status")
                    msg_val = err_json.get("message") or err_json.get("errorMessage") or err_json.get("detail")

                    if code_val is not None:
                        st.warning(f"에러 코드: {code_val}")
                    if msg_val is not None:
                        st.warning(f"에러 메시지: {msg_val}")

                    # 기타 추가 정보가 있을 경우 모두 출력
                    for k, v in err_json.items():
                        if k not in ("code", "errorCode", "status", "message", "errorMessage", "detail"):
                            st.warning(f"{k}: {v}")
                else:
                    st.warning("※ 응답이 JSON 형식이 아니거나, 파싱 실패하여 상세 에러 정보를 가져올 수 없습니다.")

                return  # 오류 시 이후 로직 실행하지 않음

            # ② status_code가 200일 때만 SSE 파싱 로직 실행
            # => 절대로 `r.text`를 먼저 호출하지 않고, 바로 iter_lines()로 읽어야 함
            print("◀◀◀ 스트림 응답을 iter_lines()로 처리합니다.")

            buffer_json = None
            # 만약 응답이 여러 덩어리로 나오는 경우를 대비해 content 누적용 변수
            content_accumulated = ""

            for raw_line in r.iter_lines(decode_unicode=True):
                if raw_line is None:
                    continue
                line = raw_line.strip()

                # 스트림 종료 신호
                if line == "data: [DONE]":
                    print("◀◀◀ 스트림 종료 신호([DONE])를 받았습니다.")
                    break

                # data: 으로 시작하는 줄만 JSON 파싱 시도
                if line.startswith("data: "):
                    json_str = line[len("data: "):]
                    # 디버깅용 출력
                    print("◀◀◀ 수신 라인:", json_str)

                    try:
                        chat_data = json.loads(json_str)
                        buffer_json = chat_data  # 마지막으로 파싱된 JSON을 저장

                        # 만약 응답이 여러 조각(parts)로 나오는 구조라면, 아래 주석을 참고하여 content_accumulated에 누적
                        # 예시:
                        # parts = chat_data.get("message", {}).get("content", {}).get("parts", [])
                        # if parts:
                        #     content_accumulated += parts[0]
                    except json.JSONDecodeError as e:
                        st.warning(f"일부 응답(JSON) 파싱 실패: {e}")
                        continue

            # 파싱된 최종 JSON에서 content를 꺼내 세션 상태에 추가
            if buffer_json and "message" in buffer_json and "content" in buffer_json["message"]:
                content = buffer_json["message"]["content"]
                
                # 만약 content가 dict 형태이고 "parts" 키를 가진다면, 실제 문자열을 합쳐야 할 수도 있음:
                # if isinstance(content, dict) and "parts" in content:
                #     actual_content = "".join(content["parts"])
                # else:
                #     actual_content = content
                #
                # 여기서는 단순 문자열이라 가정
                st.session_state.chat_history.append(
                    {"role": "assistant", "content": content}
                )
            else:
                st.warning("JSON 데이터가 없습니다. 아래 서버 응답을 확인하세요.")


# ----------------------------------------
# 2) Streamlit UI 설정 (나머지 코드는 동일)
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

# 2-3) CompletionExecutor 인스턴스 생성 (API 키와 request_id 전달)
completion_executor = CompletionExecutor(
    host='https://clovastudio.stream.ntruss.com',
    api_key='Bearer nv-bf4b622fd7f849b7bea4e9b0daab0098OVpu',
    request_id='a52fef7ad6f74857a7a7c290ca177798'
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

        # ③ HCX-005 호출 (상세 오류를 st.warning으로 출력)
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
