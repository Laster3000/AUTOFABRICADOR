"""Local Ollama provider. No remote requests, redirects, or cloud credentials."""
from __future__ import annotations
import http.client
import json
import time
from urllib.parse import urlparse

class ProviderError(RuntimeError):
    pass

def validate_endpoint(endpoint):
    url = urlparse(endpoint)
    if url.scheme != "http" or url.hostname not in ("127.0.0.1", "localhost", "::1") or url.username or url.password or url.path not in ("", "/") or url.query or url.fragment:
        raise ProviderError("ONLY_LOCAL_HTTP_OLLAMA_ALLOWED")
    return url.hostname, url.port or 11434

class Ollama:
    def __init__(self, endpoint, model, *, timeout=180, max_response_bytes=500000):
        self.host, self.port = validate_endpoint(endpoint)
        self.model = model
        self.timeout = timeout
        self.max_response_bytes = max_response_bytes

    def _request(self, method, path, payload=None):
        conn = http.client.HTTPConnection(self.host, self.port, timeout=self.timeout)
        try:
            body = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
            conn.request(method, path, body=body, headers={"Content-Type":"application/json"} if body is not None else {})
            response = conn.getresponse()
            raw = response.read(self.max_response_bytes + 1)
            if len(raw) > self.max_response_bytes:
                raise ProviderError("MODEL_RESPONSE_TOO_LARGE")
            if response.status != 200:
                raise ProviderError(f"OLLAMA_HTTP_{response.status}:{raw[:120]!r}")
            return json.loads(raw)
        except (OSError, TimeoutError, ValueError, json.JSONDecodeError) as error:
            raise ProviderError(f"OLLAMA_UNAVAILABLE_OR_INVALID:{type(error).__name__}:{str(error)[:200]}") from error
        finally:
            conn.close()

    def available_model(self):
        tags = self._request("GET", "/api/tags")
        for item in tags.get("models", []):
            if item.get("name") == self.model and item.get("digest"):
                return {"model":self.model,"digest":item["digest"],"size":item.get("size")}
        raise ProviderError("PINNED_MODEL_NOT_AVAILABLE")

    def generate(self, instructions, request, max_tokens=1200):
        body = {
            "model":self.model,"stream":False,"format":"json",
            "messages":[{"role":"system","content":instructions},{"role":"user","content":request}],
            "options":{"temperature":0.1,"num_ctx":8192,"num_predict":max_tokens}
        }
        started = time.monotonic()
        response = self._request("POST", "/api/chat", body)
        elapsed_ms = int((time.monotonic()-started)*1000)
        if response.get("done") is not True or not isinstance(response.get("message",{}).get("content"),str):
            raise ProviderError("INCOMPLETE_MODEL_RESPONSE")
        try:
            payload = json.loads(response["message"]["content"])
        except json.JSONDecodeError as error:
            raise ProviderError("MODEL_DID_NOT_RETURN_JSON") from error
        return payload, {
            "provider":"ollama","model":self.model,
            "promptTokens":response.get("prompt_eval_count"),
            "completionTokens":response.get("eval_count"),
            "totalDurationNs":response.get("total_duration"),
            "elapsedMs":elapsed_ms,
            "requestId":response.get("created_at"),
        }


class LlamaCpp(Ollama):
    """Real llama.cpp OpenAI-compatible localhost adapter, with pinned GGUF sha."""
    def __init__(self,endpoint,model,model_path,expected_sha,*,timeout=180,max_response_bytes=500000):
        super().__init__(endpoint,model,timeout=timeout,max_response_bytes=max_response_bytes)
        self.model_path=__import__("pathlib").Path(model_path)
        self.expected_sha=expected_sha.lower()
        if len(self.expected_sha)!=64 or any(c not in "0123456789abcdef" for c in self.expected_sha):
            raise ProviderError("MODEL_SHA256_REQUIRED")

    def available_model(self):
        import hashlib
        if not self.model_path.is_file():
            raise ProviderError("LOCAL_MODEL_NOT_FOUND")
        sha=hashlib.sha256()
        with self.model_path.open("rb") as f:
            for chunk in iter(lambda:f.read(1024*1024),b""):
                sha.update(chunk)
        if sha.hexdigest()!=self.expected_sha:
            raise ProviderError("LOCAL_MODEL_SHA256_MISMATCH")
        data=self._request("GET","/v1/models")
        models=[m for m in data.get("data",[]) if m.get("id")==self.model]
        if len(models)!=1:
            raise ProviderError("LOCAL_LLAMACPP_ALIAS_NOT_AVAILABLE")
        return {"model":self.model,"digest":"sha256:"+self.expected_sha,"size":self.model_path.stat().st_size}

    def generate(self,instructions,request,max_tokens=1200):
        import time
        body={"model":self.model,
              "messages":[{"role":"system","content":instructions},{"role":"user","content":request}],
              "response_format":{"type":"json_object"},
              "stream":False,"temperature":0.1,"max_tokens":max_tokens}
        started=time.monotonic()
        envelope=self._request("POST","/v1/chat/completions",body)
        try:
            choice=envelope["choices"][0]
            if choice.get("finish_reason") in ("length","max_tokens"):
                raise ProviderError("LOCAL_MODEL_OUTPUT_TRUNCATED")
            text=choice["message"]["content"]
            payload=json.loads(text)
        except (KeyError,IndexError,TypeError,ValueError) as error:
            raise ProviderError("LOCAL_LLAMACPP_DID_NOT_RETURN_VALID_JSON") from error
        usage=envelope.get("usage") or {}
        return payload,{"provider":"llama_cpp","model":self.model,
                        "promptTokens":usage.get("prompt_tokens"),
                        "completionTokens":usage.get("completion_tokens"),
                        "elapsedMs":int((time.monotonic()-started)*1000),
                        "requestId":envelope.get("id")}
