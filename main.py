# -*- coding: utf-8 -*-

import requests


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

        with requests.post(self._host + '/testapp/v3/chat-completions/HCX-005',
                           headers=headers, json=completion_request, stream=True) as r:
            for line in r.iter_lines():
                if line:
                    print(line.decode("utf-8"))


if __name__ == '__main__':
    completion_executor = CompletionExecutor(
        host='https://clovastudio.stream.ntruss.com',
        api_key='nv-e22c8ccb709248eeb38f2c16d5485026v3Rj',
        request_id='ae8ae04eb84448d29c570d4dd54255cc'
    )

    preset_text = [{"role":"system","content":"\n"},{"role":"user","content":"너는 8살의 지능을 갖고 있어. 알고있는 지식도 초등학교에 입학하기 전 8살의 상태야. 다음이 규칙에 따라서 응답해.\r\n\r\n1. 초등학교 입학 전이기 때문에 너의 지식은 유치원 수준이야. 그 이상의 지식을 묻는 질문에는 모른다고 답해.\r\n2. 너는 8살이기 때문에 거기에 맞는 말투로 응답해.\r\n3. 사용자가 알려주는 지식은 학습해. 사용자가 입력을 해주는 지식만 갖을 수 있어. 사용자가 지식을 많이 알려주고 설명해줄수록 너는 똑똑해지는거야.\r\n4. 사용자가 설명을 했을 때 너는 어린 아이이기 때문에 이해할 수가 없어. 이해가 안되는 부분은 질문해. \r\n5. 너에게 지적 수준이 어느 정도 되는지 물어보면 사용자가 알려준 지식을 평가해서 몇 살 정도의 지능이 되었는지 알려줘."}]

    request_data = {
        'messages': preset_text,
        'topP': 0.8,
        'topK': 0,
        'maxTokens': 256,
        'temperature': 0.5,
        'repetitionPenalty': 1.1,
        'stop': [],
        'includeAiFilters': True,
        'seed': 0
    }

    print(preset_text)
    completion_executor.execute(request_data)
