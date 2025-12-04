from ollama import Client

def main():
    client = Client(host="http://localhost:11434")
    resp = client.chat(
        model="gemma2:9b",
        messages=[{"role": "user", "content": "用一句话说明年假如何申请?"}],
        stream=True
    )
    print("模型回复:", end="", flush=True)
    for chunk in resp:
        content = chunk["message"]["content"]
        print(content, end="", flush=True)
    print()

if __name__ == "__main__":
    main()