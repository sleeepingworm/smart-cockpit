import requests
import json

# ================= 配置区域 =================
API_KEY = "sk-d3e75777b10f665926fb0873bd48e6c7"
BASE_URL = "https://chat.cqjtu.edu.cn/ds/api/v1/"
MODEL_NAME = "deepseek-chat"
# ============================================

url = f"{BASE_URL.rstrip('/')}/chat/completions"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}
data = {
    "model": MODEL_NAME,
    "messages": [{"role": "user", "content": "你好"}],
    "stream": False
}

try:
    response = requests.post(url, headers=headers, data=json.dumps(data), timeout=10)
    print(f"状态码 (Status Code): {response.status_code}")

    try:
        result = response.json()
        print("\n中转站返回的完整数据如下:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

        # 再次尝试解析
        if 'choices' in result:
            print(f"\n✅ 成功！AI 回复: {result['choices'][0]['message']['content']}")
        else:
            print("\n❌ 失败：返回的数据中没有 'choices' 字段，请看上方返回的错误详情。")

    except json.JSONDecodeError:
        print(f"\n❌ 错误：中转站返回的不是 JSON 格式。原始内容为:\n{response.text}")

except Exception as e:
    print(f"\n❌ 请求发送失败: {e}")