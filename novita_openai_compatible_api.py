from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

NOVITA_API_URL = "https://api.novita.ai/v3/openai/chat/completions"
NOVITA_API_KEY_DEFAULT = "session_czG-t1PK_spR1TcCZ44AGyKe7rvJ95jWgNQfz2FbjFm43qFr6Cnfl9w2HXT9OeQPYvRTA9QgkfGgn3cl0Z-YDg=="
NOVITA_API_KEY_KIMI = "session_czG-t1PK_spR1TcCZ44AGyKe7rvJ95jWgNQfz2FbjFm43qFr6Cnfl9w2HXT9OeQPYvRTA9QgkfGgn3cl0Z-YDg=="

SUPPORTED_MODELS = [
    "minimaxai/minimax-m1-80k",
    "qwen/qwen3-235b-a22b-instruct-2507",
    "qwen/qwen3-235b-a22b-thinking-2507",
    "qwen/qwen3-coder-480b-a35b-instruct",
    "qwen/qwen2.5-vl-72b-instruct",
    "baidu/ernie-4.5-vl-424b-a47b",
    "baidu/ernie-4.5-300b-a47b-paddle",
    "deepseek/deepseek-v3-0324",
    "deepseek/deepseek-r1-0528",
    "baidu/ernie-4.5-vl-28b-a3b",
    "baidu/ernie-4.5-21B-a3b",
    "baidu/ernie-4.5-0.3b",
    "moonshotai/kimi-k2-instruct"
]

@app.route("/v1/chat/completions", methods=["POST"])
def chat_completions():
    try:
        # Get the incoming request JSON (OpenAI chat completion format)
        data = request.get_json()

        # Validate model
        model = data.get("model", "qwen/qwen3-235b-a22b-thinking-2507")
        if model not in SUPPORTED_MODELS:
            return jsonify({"error": f"Model '{model}' is not supported."}), 400

        # Select API key based on model
        if model == "moonshotai/kimi-k2-instruct":
            api_key = NOVITA_API_KEY_KIMI
        else:
            api_key = NOVITA_API_KEY_DEFAULT

        # Prepare headers for Novita API
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        # Prepare payload for Novita API
        # Use the same model and messages from the incoming request
        # Add other parameters with defaults or from incoming request if present
        payload = {
            "model": model,
            "messages": data.get("messages", []),
            "response_format": {"type": "text"},
            "max_tokens": data.get("max_tokens", 65536),
            "temperature": data.get("temperature", 1),
            "top_p": data.get("top_p", 1),
            "min_p": data.get("min_p", 0),
            "top_k": data.get("top_k", 50),
            "presence_penalty": data.get("presence_penalty", 0),
            "frequency_penalty": data.get("frequency_penalty", 0),
            "repetition_penalty": data.get("repetition_penalty", 1)
        }

        # Send request to Novita API
        response = requests.post(NOVITA_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        novita_response = response.json()

        # Transform Novita response to OpenAI compatible response format
        # Assuming Novita response has a 'choices' list with 'message' containing 'role' and 'content'
        openai_response = {
            "id": novita_response.get("id", ""),
            "object": "chat.completion",
            "created": novita_response.get("created", 0),
            "model": payload["model"],
            "choices": novita_response.get("choices", []),
            "usage": novita_response.get("usage", {})
        }

        return jsonify(openai_response)


    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Request to Novita API failed", "details": str(e)}), 502
    except Exception as e:
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
