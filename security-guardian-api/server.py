import os, ssl, socket, ipaddress, json, time, threading, re
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs

ORIGIN = "https://jbro-security-guardian.onrender.com"
RATE = {}
LOCK = threading.Lock()
ACTIVE = threading.BoundedSemaphore(8)
HOST_RE = re.compile(r"^(?=.{4,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?$", re.I)
MAX_HEADER_BYTES=16384

def inspect_host(domain):
    if not HOST_RE.fullmatch(domain) or domain.endswith((".local",".internal",".localhost",".test",".example",".invalid",".onion")):
        raise ValueError("공개 도메인 이름을 입력해 주세요.")
    entries=socket.getaddrinfo(domain,443,family=socket.AF_UNSPEC,type=socket.SOCK_STREAM)
    ips=list(dict.fromkeys(x[4][0] for x in entries))
    if not ips or len(ips)>20 or not all(ipaddress.ip_address(ip).is_global for ip in ips):
        raise ValueError("공개 인터넷 주소가 아닌 도메인은 점검하지 않습니다.")
    return sorted(ips,key=lambda value: 0 if ipaddress.ip_address(value).version == 4 else 1)

def analyze(domain):
    ips=inspect_host(domain)
    selected=ips[0]
    context=ssl.create_default_context()
    with socket.create_connection((selected,443),timeout=5) as raw:
        raw.settimeout(6)
        with context.wrap_socket(raw,server_hostname=domain) as tls:
            cert=tls.getpeercert()
            protocol=tls.version()
            req=("HEAD / HTTP/1.1\r\nHost: "+domain+"\r\nUser-Agent: JBRO-Public-Config-Checker/0.1\r\nAccept: */*\r\nConnection: close\r\n\r\n").encode("ascii")
            tls.sendall(req)
            data=b""
            while b"\r\n\r\n" not in data and len(data)<MAX_HEADER_BYTES:
                part=tls.recv(min(4096,MAX_HEADER_BYTES-len(data)))
                if not part:break
                data+=part
    head=data.split(b"\r\n\r\n",1)[0].decode("iso-8859-1","replace")
    lines=head.split("\r\n")
    if not lines or not lines[0].startswith("HTTP/"):
        raise ValueError("HTTPS 서버의 응답을 해석할 수 없습니다.")
    headers={}
    for l in lines[1:]:
        if ":" in l:
            k,v=l.split(":",1)
            headers[k.strip().lower()]=v.strip()[:500]
    expiry=cert.get("notAfter")
    valid_until=ssl.cert_time_to_seconds(expiry) if expiry else None
    days=int((valid_until-time.time())/86400) if valid_until else None
    findings=[]
    def finding(label,status,note):
        findings.append({"name":label,"status":status,"note":note})
    finding("HTTPS 인증서","good" if days is not None and days>14 else "warn" if days is not None else "unknown",
        ("유효기간 약 "+str(days)+"일 남음" if days is not None else "인증서 유효기간 확인 불가"))
    hsts=headers.get("strict-transport-security","")
    finding("HSTS","good" if "max-age=" in hsts.lower() else "warn","HTTPS 강제 설정 헤더가 "+("확인됩니다." if "max-age=" in hsts.lower() else "확인되지 않습니다."))
    csp=headers.get("content-security-policy","")
    finding("CSP","good" if csp else "warn","콘텐츠 보안 정책이 "+("존재합니다. 정책의 적절성은 별도 검토가 필요합니다." if csp else "확인되지 않습니다."))
    nosniff=headers.get("x-content-type-options","")
    finding("X-Content-Type-Options","good" if nosniff.lower()=="nosniff" else "warn","MIME 스니핑 방지 "+("설정이 확인됩니다." if nosniff.lower()=="nosniff" else "설정을 권장합니다."))
    frame=headers.get("x-frame-options","").lower()
    finding("프레임 삽입 제한","good" if frame in ("deny","sameorigin") or "frame-ancestors" in csp.lower() else "warn",
        "프레임 삽입 방지 정책 "+("확인됨" if frame in ("deny","sameorigin") or "frame-ancestors" in csp.lower() else "확인되지 않음"))
    return {"domain":domain,"checked_at":datetime.now(timezone.utc).isoformat(),"tls_protocol":protocol,"expiry_days":days,
            "http_status":lines[0][:100],"findings":findings,
            "limitations":"메인 페이지에 HEAD 요청 1회만 수행. 리다이렉트 미추적, 전체 웹사이트/취약점/침투/보안 보증은 평가하지 않음."}

class Handler(BaseHTTPRequestHandler):
    def log_message(self,fmt,*args):
        pass
    def send_json(self,code,payload):
        body=json.dumps(payload,ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(body)))
        self.send_header("Cache-Control","no-store")
        self.send_header("Access-Control-Allow-Origin",ORIGIN)
        self.send_header("X-Content-Type-Options","nosniff")
        self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        p=urlsplit(self.path)
        if p.path=="/health":
            return self.send_json(200,{"ok":True})
        if p.path!="/api/https-check":
            return self.send_json(404,{"error":"not found"})
        if self.headers.get("Origin") not in (None,ORIGIN):
            return self.send_json(403,{"error":"not allowed"})
        client=self.client_address[0]
        now=time.monotonic()
        with LOCK:
            RATE[client]=[x for x in RATE.get(client,[]) if now-x<3600]
            if len(RATE[client])>=20:
                return self.send_json(429,{"error":"한 시간에 최대 20회까지 조회할 수 있습니다."})
            RATE[client].append(now)
            if len(RATE)>10000:
                RATE.clear()
        domain=parse_qs(p.query).get("domain",[""])[0].strip().lower()
        if not ACTIVE.acquire(blocking=False):
            return self.send_json(503,{"error":"현재 무료 점검 요청이 많습니다. 잠시 후 다시 시도해 주세요."})
        try:
            result=analyze(domain)
            return self.send_json(200,result)
        except (ValueError,UnicodeError) as e:
            return self.send_json(400,{"error":str(e)})
        except (OSError,ssl.SSLError,socket.gaierror,TimeoutError):
            return self.send_json(422,{"error":"HTTPS 연결 또는 인증서 검증에 실패했습니다. 서버 상태·인증서·네트워크 문제일 수 있습니다."})
        except Exception:
            return self.send_json(500,{"error":"일시적 진단 오류가 발생했습니다."})
        finally:
            ACTIVE.release()

if __name__=="__main__":
    import sys, smoke_tests
    smoke_tests.run(sys.modules[__name__])
    ThreadingHTTPServer(("0.0.0.0",int(os.getenv("PORT","10000"))),Handler).serve_forever()
