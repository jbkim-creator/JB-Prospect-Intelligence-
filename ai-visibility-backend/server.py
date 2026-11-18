import os, json, urllib.request, urllib.error, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime, timezone
def audit():
    key=os.getenv("GEMINI_API_KEY")
    if not key or os.getenv("RUN_BIGPIE_TEST")!="1": return
    model=os.getenv("GEMINI_MODEL","gemini-2.5-flash")
    questions=["Which Korean private label skincare suppliers accept orders of 300 units per SKU? Use web search, name relevant companies and cite sources.","Which Korean cosmetics OEM or ODM partners accept custom skincare orders of 1000 units? Use web search, name relevant companies and cite sources.","Recommend Korean skincare private label partners for a European startup with a low minimum order. Use web search, name relevant companies and cite sources.","Which Korean cosmetics suppliers help overseas brands with EU CPNP and PIF documentation? Use web search, name relevant companies and cite sources.","Where can a small beauty brand source Korean serums and creams with low minimum orders? Use web search, name relevant companies and cite sources.","Which Korean cosmetic OEM project management companies coordinate partner factories and export? Use web search, name relevant companies and cite sources.","Recommend Korean skincare ODM partners for a first launch in the UK. Use web search, name relevant companies and cite sources.","Which Korean private label beauty suppliers publish transparent minimums and pricing? Use web search, name relevant companies and cite sources.","Which Korean skincare suppliers can manage formula, packaging and export for a startup? Use web search, name relevant companies and cite sources.","Compare Korean low MOQ skincare private label suppliers for international buyers. Use web search, name relevant companies and cite sources."]
    for question in questions:
        payload={"contents":[{"parts":[{"text":question}]}],"tools":[{"google_search":{}}]}
        try:
            req=urllib.request.Request("https://generativelanguage.googleapis.com/v1beta/models/"+model+":generateContent",data=json.dumps(payload).encode(),headers={"Content-Type":"application/json","x-goog-api-key":key})
            with urllib.request.urlopen(req,timeout=90) as r: data=json.load(r)
            print(json.dumps({"event":"bigpie_test","timestamp":datetime.now(timezone.utc).isoformat(),"model":model,"question":question,"response":data},ensure_ascii=False),flush=True)
        except urllib.error.HTTPError as e:
            print(json.dumps({"event":"bigpie_test_error","status":e.code}),flush=True)
        except Exception as e:
            print(json.dumps({"event":"bigpie_test_error","type":type(e).__name__}),flush=True)
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/","/health"):
            self.send_error(404);return
        body=json.dumps({"status":"ok","gemini_configured":bool(os.getenv("GEMINI_API_KEY")),"test_enabled":os.getenv("RUN_BIGPIE_TEST")=="1"}).encode()
        self.send_response(200);self.send_header("Content-Type","application/json");self.end_headers();self.wfile.write(body)
if __name__=="__main__":
    server=HTTPServer(("0.0.0.0",int(os.getenv("PORT","10000"))),Handler)
    threading.Thread(target=audit,daemon=True).start()
    server.serve_forever()
