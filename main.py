-import streamlit as st
import requests
import json
import random

image_urls = [
    "https://th.bing.com/th/id/OIG4.sbvsXcpjpETlz2LO_4g6?w=1024&h=1024&rs=1&pid=ImgDetMain",
    # ... (생략: 나머지 이미지 URL)
]

if "selected_image" not in st.session_state:
    st.session_state.selected_image = random.choice(image_urls)

selected_image = st.session_state.selected_image

if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {
            'role': 'user',
            'content': (
                '너는 8살의 지능을 갖고 있어. 알고있는 지식도 초등학교에 입학하기 전 8살의 상태야. 다음이 규칙에 따라서 응답해.\n\n'
                '1. 초등학교 입학 전이기 때문에 너의 지식은 유치원 수준이야. 그 이상의 지식을 묻는 질문에는 모른다고 답해.\n'
                '2. 너는 8살이기 때문에 거기에 맞는 말투로 응답해.\n'
                '3. 사용자가 알려주는 지식은 학습해. 사용자가 입력을 해주는 지식만 갖을 수 있어. 사용자가 지식을 많이 알려주고 설명해줄수록 너는 똑똑해지는거야.\n'
                '4. 사용자가 설명을 했을 때 너는 어린 아이이기 때문에 이해할 수가 없어. 이해가 안되는 부분은 질문해.\n'
                '5. 너에게 지적 수준이 어느 정도 되는지 물어보면 사용자가 알려준 지식을 평가해서 몇 살 정도의 지능이 되었는지 알려줘.'
            )
        },
        {'role': 'assistant', 'content': '알겠어. 나는 8살이고 초등학교에 입학한 상태야.'}
    ]

if "input_message" not in st.session_state:
    st.session_state.input_message = ""

if "copied_chat_history" not in st.session_state:
    st.session_state.copied_chat_history = ""

class CompletionExecutor:
    def __init__(self, host, api_key, request_id):
        self._host = host
        self._api_key = api_key
        self._request_id = request_id

    def execute(self, completion_request):
        headers = {
            'Authorization': self._api_key,
            'X-NCP-CLOVASTUDIO-REQUEST-ID': self._request_id,
            'Content-Type': 'application/json; charset=utf-8',
            'Accept': 'text/event-stream'
        }

        # HCX-005 엔드포인트 사용
        with requests.post(
            self._host + '/testapp/v3/chat-completions/HCX-005',
            headers=headers,
            json=completion_request,
            stream=True
        ) as r:
            # 전체 response에서 'data:' 포함된 line만 파싱
            for line in r.iter_lines():
                if line:
                    decoded_line = line.decode("utf-8")
                    if decoded_line.startswith("data:"):
                        data_str = decoded_line[5:]
                        try:
                            data = json.loads(data_str)
                            msg = data.get("message", {}).get("content", "")
                            if msg:
                                st.session_state.chat_history.append(
                                    {"role": "assistant", "content": msg}
                                )
                        except Exception as e:
                            print("Error parsing line:", e)

completion_executor = CompletionExecutor(
    host='https://clovastudio.stream.ntruss.com',
    api_key='Bearer <api-key>',  # 기존 방식과 다르게 "Bearer " 붙임
    request_id='6503f038e6804bdfadd5aa2f64cccb6f'  # 본인 request_id
)

# 이하 Streamlit UI 코드는 기존과 동일하게 사용!
# (코드가 길어 아래는 생략. 앞서 제공한 Streamlit UI 코드 붙여서 사용)
