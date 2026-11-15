(()=>{
'use strict';
const API='https://jbro-security-guardian-api.onrender.com/api/https-check';
const form=document.getElementById('quickcheck-form');
const input=document.getElementById('quickcheck-domain');
const result=document.getElementById('https-results');
const status=document.getElementById('https-status');
const reportBtn=document.getElementById('download-report');
let lastDomain='',lastReport=null;
const guidance={
'HTTPS 인증서':'유효기간이 짧다면 자동 갱신과 인증서 발급 설정을 점검하세요.',
'HSTS':'HTTPS 전환이 안정적으로 작동하는지 확인한 뒤 HSTS max-age 적용을 검토하세요.',
'CSP':'서비스가 사용하는 스크립트와 외부 리소스를 조사한 뒤 Content-Security-Policy 적용을 검토하세요.',
'X-Content-Type-Options':'지원되는 서버 또는 CDN에서 X-Content-Type-Options: nosniff 설정을 검토하세요.',
'프레임 삽입 제한':'서비스 요구사항에 맞춰 CSP frame-ancestors 또는 X-Frame-Options를 설정하세요.'
};
function normalize(s){try {const u=new URL(/^https?:\/\//i.test(s)?s:'https://'+s);return u.hostname.toLowerCase().replace(/\.$/,'');}catch{return '';}}
function makeLine(f){const e=document.createElement('div');e.className='check-row';const h=document.createElement('div');h.className='check-head';const name=document.createElement('strong');name.textContent=f.name;const badge=document.createElement('span');badge.className='check-pill '+(f.status||'unknown');badge.textContent=f.status==='good'?'양호':f.status==='warn'?'개선 권장':'확인 불가';h.append(name,badge);const p=document.createElement('p');p.className='check-desc muted';p.textContent=f.note;const g=document.createElement('p');g.className='fine';g.textContent=guidance[f.name]||'';e.append(h,p,g);return e;}
form.addEventListener('submit',async event=>{
event.preventDefault();
result.replaceChildren();reportBtn.hidden=true;lastReport=null;
const host=normalize(input.value);
if(!host)return;
lastDomain=host;
status.textContent='HTTPS 인증서 및 메인 페이지 보안 헤더 점검 중... 무료 서버 절전 상태에서는 초기 응답이 느릴 수 있습니다.';
const ctrl=new AbortController();const timer=setTimeout(()=>ctrl.abort(),78000);
try{
const resp=await fetch(API+'?domain='+encodeURIComponent(host),{signal:ctrl.signal,headers:{Accept:'application/json'},cache:'no-store'});
const data=await resp.json();
if(!resp.ok)throw Error(data.error||'HTTPS 조회 실패');
if(lastDomain!==host)return;
status.textContent='HTTPS 점검 완료 · '+data.http_status+' · 프로토콜 '+(data.tls_protocol||'확인 불가');
for(const f of data.findings||[])result.append(makeLine(f));
const n=document.createElement('p');n.className='fine';n.textContent=data.limitations||'';result.append(n);
lastReport=data;
reportBtn.hidden=false;
}catch(e){status.textContent=e.name==='AbortError'?'HTTPS 서비스 응답시간을 초과했습니다. 다시 시도해 주세요.':'HTTPS 확인 불가: '+e.message;
}finally{clearTimeout(timer);}
});
reportBtn.addEventListener('click',()=>{
const dns=document.getElementById('quickcheck-results').innerText;
const https=lastReport?lastReport.findings.map(f=>f.name+' ['+f.status+'] '+f.note).join('\n'):'HTTPS 진단 없음';
const lines=['JBRO AI Security Guardian — 무료 공개 설정 점검','점검 도메인: '+lastDomain,'생성 시각: '+new Date().toLocaleString('ko-KR'),'','[공개 DNS 점검]',dns,'','[HTTPS/보안 헤더 점검]',https,'','[주의사항]','공개 DNS 및 HTTPS 첫 페이지의 제한적 설정 확인 결과입니다. 완전한 취약점 진단, 모의침투, 보안 보증이 아닙니다.'];
const blob=new Blob([lines.join('\n')],{type:'text/plain;charset=utf-8'});
const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='JBRO_Security_Check_'+lastDomain.replace(/[^a-z0-9.-]/g,'_')+'.txt';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
})();