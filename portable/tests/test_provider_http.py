"""Live HTTP contract tests against an in-process mock; no model is claimed."""
import http.server
import json
import threading
import unittest

from autofab.providers import Ollama, ProviderError

class MockOllama(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args):
        return
    def do_GET(self):
        if self.path != "/api/tags":
            self.send_error(404);return
        raw=json.dumps({"models":[{"name":"test-model:1","digest":"sha256:0123456789abcdef","size":1}]}).encode()
        self.send_response(200);self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_POST(self):
        if self.path != "/api/chat":
            self.send_error(404);return
        size=int(self.headers["Content-Length"])
        body=json.loads(self.rfile.read(size))
        if body.get("model")!="test-model:1" or body.get("stream") is not False:
            self.send_error(422);return
        raw=json.dumps({"done":True,"message":{"content":json.dumps({"files":{
            "sample.py":"def increment(x): return x+1\n",
            "test_sample.py":"import unittest\nfrom sample import increment\nclass TestInc(unittest.TestCase):\n    def test_inc(self): self.assertEqual(increment(1),2)\n"}})},
            "prompt_eval_count":120,"eval_count":55,"total_duration":100000000}).encode()
        self.send_response(200);self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(raw)));self.end_headers();self.wfile.write(raw)

class LocalTransport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=http.server.ThreadingHTTPServer(("127.0.0.1",0),MockOllama)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join(timeout=3)
    def test_real_http_transport_but_mocked_model(self):
        endpoint="http://127.0.0.1:"+str(self.server.server_port)
        client=Ollama(endpoint,"test-model:1",timeout=5)
        self.assertEqual(client.available_model()["digest"],"sha256:0123456789abcdef")
        response,usage=client.generate("Test only","Make source",200)
        self.assertIn("test_sample.py",response["files"])
        self.assertEqual(usage["promptTokens"],120)
        self.assertEqual(usage["completionTokens"],55)
    def test_missing_model_rejected(self):
        endpoint="http://127.0.0.1:"+str(self.server.server_port)
        with self.assertRaisesRegex(ProviderError,"PINNED_MODEL_NOT_AVAILABLE"):
            Ollama(endpoint,"not-there").available_model()

if __name__=="__main__":
    unittest.main()
