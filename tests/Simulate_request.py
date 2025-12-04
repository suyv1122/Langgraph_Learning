import requests
import json

url = "http://localhost:11434/api/chat"

payload = {
    "model": "llama3.2:3b",  # 先用确定能跑的小模型
    "messages": [
        {"role": "user", "content": "用一句话说明年假如何申请？"}
    ],
    "stream": False
}

resp = requests.post(url, data=json.dumps(payload), headers={"Content-Type":"application/json"})

print("status:", resp.status_code)
print("body:", resp.text)