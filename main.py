import streamlit as st
import requests
import re

st.set_page_config(page_title="HyperCLOVA 유치원 챗봇", layout="wide")
st.markdown("""
    <style>
        .main .block-container {max-width: 1800px;}
    </style>
""", unsafe_allow_html=True)

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
        border: 1.5px solid #E
