import requests

url = "http://localhost:8081/generate"
payload = {
    "prompts": [
        "1 + 1 equals:",
        "The capital of Japan is",
        "Hello, what is your name?",
        "Hello, what is my name?",
        "Hello, where are you from?",
        "500 + 500 = ?",
        "the capital of China is",
        "the capital of USA is",
    ]
}

response = requests.post(url, json=payload)

if response.status_code == 200:
    data = response.json()
    for item in data["outputs"]:
        print("-" * 70)
        print(f"Prompt: {str(item['prompt'])}\n")
        print(f"Output: {str(item['output'])}\n")
else:
    print("Request failed with status code:", response.status_code)
    print(response.text)