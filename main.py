import streamlit as st
import requests
import re

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

# 모든 이벤트 차단을 위해 강제 js injection
st.components.v1.html("""
    <script>
    document.addEventListener('DOMContentLoaded', function() {
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
""", height=0)

# --------- 이하 기존 챗봇/Streamlit 코드 (동일) ---------
# (CompletionExecutor, render_chat_with_scroll, 세션상태, system_prompt, 채팅UI 등 기존코드 전체 붙여넣기)
# --------- (위의 모든 답변 코드와 완전히 동일) ---------
# 예시로 아래는 챗봇 render/입력/지식수준 부분 일부만 요약

# ... (중략, 앞서 제공된 챗봇 코드와 동일하게 삽입) ...

# 예시:
class CompletionExecutor:
    def __init__(self, host: str, api_key: str, request_id: str):
        self._host = host
        self._api_key = api_key
        self._request_id = request_id
    def get_response(self, completion_request: dict) -> str:
        headers = {...} # (생략: 앞서 답변과 동일)
        # ... 이하 동일

# 이하 전체 챗봇 코드(대화 기록, 입력, 오른쪽 요약 등) 기존 답변과 동일하게 붙여넣으시면 됩니다.

# (생략)
