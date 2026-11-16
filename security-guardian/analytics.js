(()=>{
'use strict';
const ENDPOINT='https://jbro-security-guardian-api.onrender.com/api/event';
const allowed=new Set(['page_view','scan_start','dns_complete','https_complete','https_error','report_download_click','consult_click']);
function record(type){
  if(!allowed.has(type))return;
  // An event label only; no entered domain, identity, cookie, device fingerprint or URL.
  try{fetch(ENDPOINT,{method:'POST',mode:'cors',headers:{'Content-Type':'text/plain'},body:type,keepalive:true,cache:'no-store'}).catch(()=>{});}catch(_){}
}
document.addEventListener('guardian:scan-start',()=>record('scan_start'));
document.addEventListener('guardian:dns-done',()=>record('dns_complete'));
document.addEventListener('guardian:https-done',()=>record('https_complete'));
document.addEventListener('guardian:https-error',()=>record('https_error'));
document.getElementById('download-report')?.addEventListener('click',()=>record('report_download_click'));
document.querySelectorAll('a[href^="mailto:"]').forEach(a=>a.addEventListener('click',()=>record('consult_click')));
record('page_view');
})();