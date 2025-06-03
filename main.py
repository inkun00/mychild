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

# 강제적으로 모든 contextmenu, copy, paste, cut, select, drag 이벤트 차단
st.components.v1.html("""
    <script>
    // 오른쪽 마우스 클릭(context menu) 및 드래그, 복사, 붙여넣기 등 차단
    document.addEventListener('DOMContentLoaded', function() {
        // 오른쪽 마우스 클릭, context menu 차단
        document.body.addEventListener('contextmenu', function(e) {
            e.preventDefault();
            return false;
        }, true);

        // 키보드(Ctrl/Meta+C/V/X/A/Insert, Shift+Insert, PrintScreen 등) 차단
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

        // 드래그, 텍스트 선택 차단
        document.body.addEventListener('selectstart', function(e) {
            e.preventDefault();
            return false;
        }, true);
        document.body.addEventListener('dragstart', function(e) {
            e.preventDefault();
            return false;
        }, true);

        // 복사/붙여넣기 API 차단
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
