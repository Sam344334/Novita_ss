from flask import Flask, request, jsonify, Response, stream_with_context
import requests
import os
import json

app = Flask(__name__)

NOVITA_API_URL = "https://api.novita.ai/v3/openai/chat/completions"
NOVITA_API_KEY_DEFAULT = "session_czG-t1PK_spR1TcCZ44AGyKe7rvJ95jWgNQfz2FbjFm43qFr6Cnfl9w2HXT9OeQPYvRTA9QgkfGgn3cl0Z-YDg=="
NOVITA_API_KEY_KIMI = NOVITA_API_KEY_DEFAULT  # Same key for now

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

@app.route("/v1/models", methods=["GET"])
def list_models():
    models = [{"id": model, "object": "model", "owned_by": "novita"} for model in SUPPORTED_MODELS]
    return jsonify({"object": "list", "data": models})

@app.route("/v1/chat/completions", methods=["POST"])
def chat_completions():
    try:
        data = request.get_json()
        model = data.get("model", "qwen/qwen3-235b-a22b-thinking-2507")

        if model not in SUPPORTED_MODELS:
            return jsonify({"error": {"message": f"Model '{model}' is not supported."}}), 400

        api_key = NOVITA_API_KEY_KIMI if model == "moonshotai/kimi-k2-instruct" else NOVITA_API_KEY_DEFAULT

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

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
            "repetition_penalty": data.get("repetition_penalty", 1),
            "stream": data.get("stream", False),
            "tools": data.get("tools"),
            "tool_choice": data.get("tool_choice"),
            "functions": data.get("functions"),
            "function_call": data.get("function_call")
        }

        payload = {k: v for k, v in payload.items() if v is not None}

        # ====== Streaming response handling ======
        if payload.get("stream"):
            def event_stream():
                try:
                    r = requests.post(NOVITA_API_URL, headers=headers, json=payload, stream=True)
                    for line in r.iter_lines(decode_unicode=True):
                        if line and line.strip().startswith("{"):
                            chunk = json.loads(line)
                            # Normalize assistant message for stream chunks
                            if "message" not in chunk and "content" in chunk:
                                chunk["message"] = {
                                    "role": "assistant",
                                    "content": chunk["content"]
                                }
                            yield f"data: {json.dumps(chunk)}\n\n"
                    yield "data: [DONE]\n\n"
                except Exception as e:
                    yield f"data: {{\"error\": \"Stream failed\", \"details\": \"{str(e)}\"}}\n\n"

            return Response(stream_with_context(event_stream()), mimetype='text/event-stream')

        # ====== Normal (non-streaming) response ======
        r = requests.post(NOVITA_API_URL, headers=headers, json=payload)
        r.raise_for_status()
        novita_response = r.json()

        # Ensure every choice has a valid assistant message
        choices = novita_response.get("choices", [])
        for choice in choices:
            if "message" not in choice and "content" in choice:
                choice["message"] = {
                    "role": "assistant",
                    "content": choice["content"]
                }

        response_payload = {
            "id": novita_response.get("id", ""),
            "object": "chat.completion",
            "created": novita_response.get("created", 0),
            "model": model,
            "choices": choices,
            "usage": novita_response.get("usage", {})
        }

        return jsonify(response_payload)

    except requests.exceptions.RequestException as e:
        return jsonify({"error": {"message": "Request to Novita API failed", "details": str(e)}}), 502
    except Exception as e:
        return jsonify({"error": {"message": "Internal Server Error", "details": str(e)}}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    app.run(host="0.0.0.0", port=port)
