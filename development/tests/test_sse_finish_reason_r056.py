"""R056 synthetic original SSE framing: [DONE] alone cannot authorize PASS."""
from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from autofab import direct_agent
from autofab.storage import write_json,sha_bytes
class _Reply:
    status=200
    def __init__(self,reason="stop",done=True):
        self.lines=[
          ('data: '+json.dumps({"choices":[{"delta":{"content":"{\"source\":\"def slugify_ascii(x):\\n    return x\"}"},"finish_reason":reason}]})+'\n').encode("utf-8")]
        if done:self.lines.append(b"data: [DONE]\n")
    def readline(self,n):return self.lines.pop(0) if self.lines else b""
class _Conn:
    def __init__(self,response):self.response=response
    def request(self,*a,**k):pass
    def getresponse(self):return self.response
    def close(self):pass
class StreamFinishR056(unittest.TestCase):
    def fixture(self,reason,done=True):
        with tempfile.TemporaryDirectory(prefix="R056-SSE-") as temp:
            d=Path(temp);write_json(d/"control.json",{"command":"RUN"},new=True)
            with patch.object(direct_agent.http.client,"HTTPConnection",
                 side_effect=lambda *args,**kw:_Conn(_Reply(reason,done))):
                return direct_agent._stream_text(d,d,
                  {"model":"fixture","stream":True},deadline=3,port=54321)
    def test_length_reason_is_kept_even_with_done(self):
        v=self.fixture("length")
        self.assertTrue(v["done"])
        self.assertEqual(v["lastFinishReason"],"length")
        self.assertTrue(v["threadExited"])
        self.assertEqual(v["errors"],[])
        self.assertEqual(v["partialOrCompleteSha256"],sha_bytes(v["resultText"].encode()))
        self.assertFalse(v["lastFinishReason"]=="stop")
    def test_stop_reason_is_recorded(self):
        v=self.fixture("stop")
        self.assertTrue(v["done"] and v["threadExited"])
        self.assertEqual(v["lastFinishReason"],"stop")
        self.assertFalse(v["errors"])
    def test_missing_done_is_not_complete(self):
        v=self.fixture("stop",done=False)
        self.assertFalse(v["done"])
        self.assertEqual(v["lastFinishReason"],"stop")
        self.assertTrue(v["threadExited"])
