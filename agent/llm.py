"""Model interface: complete(messages) -> (text, tokens_used).

OllamaLLM talks to a local Ollama server. ScriptedLLM is a fake model for tests/demo.
LangGraph calls this interface directly; no LangChain model adapter is needed.
"""
import requests


class OllamaLLM:
    def __init__(self, model="llama3.1", url="http://localhost:11434", timeout=120):
        self.model, self.url, self.timeout = model, url, timeout

    def complete(self, messages):
        r = requests.post(
            f"{self.url}/api/chat",
            json={"model": self.model, "messages": messages,
                  "stream": False, "format": "json"},
            timeout=self.timeout,
        )
        r.raise_for_status()
        data = r.json()
        tokens = data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
        return data["message"]["content"], tokens


class ScriptedLLM:
    """Returns pre-written replies in order; repeats the last one if repeat_last."""

    def __init__(self, replies, tokens_per_call=100, repeat_last=False):
        self.replies, self.tokens, self.repeat_last = list(replies), tokens_per_call, repeat_last
        self.i = 0

    def complete(self, messages):
        if self.i < len(self.replies):
            text = self.replies[self.i]
        elif self.repeat_last:
            text = self.replies[-1]
        else:
            text = '{"action": "finish", "answer": "script ended"}'
        self.i += 1
        return text, self.tokens
