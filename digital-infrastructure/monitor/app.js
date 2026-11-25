(()=>{
"use strict";
const cfg=window.JBRO_MONITOR_CONFIG||{}, base=String(cfg.supabaseUrl||"").replace(/\/$/,""), key=cfg.supabaseAnonKey||"";
const $=id=>document.getElementById(id);let token=null,records=[];const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
function info(s,err=false){$("message").textContent=s;$("message").className=err?"error":""}
function ready(){return base.startsWith("https://")&&key.length>10}
async function request(path,method="GET",data){
 const r=await fetch(base+path,{method,headers:{"apikey":key,"Authorization":"Bearer "+token,"Content-Type":"application/json","Prefer":method==="POST"?"return=representation":"return=minimal"},body:data===undefined?undefined:JSON.stringify(data)});
 if(!r.ok){throw new Error("Request failed ("+r.status+"): "+(await r.text()).slice(0,150))}
 if(method==="GET"||method==="POST")return r.json();return null
}
async function login(e){e.preventDefault();if(!ready())return info("Supabase 연결이 아직 설정되지 않았습니다.",true);
 try{const r=await fetch(base+"/auth/v1/token?grant_type=password",{method:"POST",headers:{"apikey":key,"Content-Type":"application/json"},body:JSON.stringify({email:$("email").value,password:$("password").value})});
 if(!r.ok)throw Error("인증 실패");const auth=await r.json();const candidate=auth.access_token;
 token=candidate;const admin=await request("/rest/v1/dc_admin_users?select=user_id&limit=1");
 if(!admin.length)throw Error("관리자 권한이 없는 계정입니다");
 $("password").value="";$("login").classList.add("hidden");$("dashboard").classList.remove("hidden");$("who").textContent="관리자 접속";await load();info("연결 성공");
 }catch(err){token=null;info(err.message,true)}
}
async function load(){records=await request("/rest/v1/dc_opportunities?select=*&order=created_at.desc&limit=1000");render()}
const normalized=u=>u.trim().toLowerCase().replace(/\/$/,"");
async function add(e){e.preventDefault();const f=e.target;const data=Object.fromEntries(new FormData(f));
 data.title=String(data.title||"").trim();data.source_url=String(data.source_url||"").trim();data.brokerage_score=Number(data.brokerage_score||0);
 if(!data.title||!/^https:\/\//i.test(data.source_url))return info("공고명과 HTTPS 공식 출처 URL을 입력하세요.",true);
 for(const k of ["announcement_date","next_action_due"])if(!data[k])delete data[k];
 const duplicate=records.find(x=>normalized(x.source_url)===normalized(data.source_url));
 if(duplicate)return info("중복된 출처입니다: "+duplicate.title,true);
 try{await request("/rest/v1/dc_opportunities","POST",data);f.reset();await load();info("거래 후보 저장 완료 (기본 상태: 검증 필요)")}catch(err){info(err.message,true)}
}
function render(){const search=$("search").value.trim().toLowerCase(),ver=$("verification").value,cat=$("category").value;
 const showing=records.filter(x=>(!search||[x.title,x.asset_name,x.country].some(z=>String(z||"").toLowerCase().includes(search)))&&(!ver||x.verification_status===ver)&&(!cat||x.category===cat));
 $("stats").innerHTML="<span>전체 "+records.length+"</span><span>검증 필요 "+records.filter(x=>x.verification_status==="needs_review").length+"</span><span>공식 검증 "+records.filter(x=>x.verification_status==="verified").length+"</span><span>기한 도래 "+records.filter(x=>x.next_action_due&&x.next_action_due<=new Date().toISOString().slice(0,10)&&x.status!=="closed").length+"</span>";
 $("rows").innerHTML=showing.map(x=>'<tr data-id="'+esc(x.id)+'"><td><strong>'+esc(x.title)+'</strong><p>'+esc(x.asset_name)+'</p><a rel="noopener noreferrer" target="_blank" href="'+esc(x.source_url)+'">공식 출처</a></td><td>'+esc(x.country)+' / '+esc(x.transaction_type)+'</td><td>'+esc(x.announcement_date)+'</td><td><select data-field="verification_status">'+["needs_review","verified","rejected"].map(z=>'<option value="'+z+'" '+(x.verification_status===z?"selected":"")+'>'+({needs_review:"검증 필요",verified:"검증됨",rejected:"제외"}[z])+'</option>').join("")+'</select></td><td><input data-field="brokerage_score" type="number" min="0" max="100" value="'+Number(x.brokerage_score)+'"></td><td><input data-field="next_action" value="'+esc(x.next_action)+'"><input data-field="next_action_due" type="date" value="'+esc(x.next_action_due)+'"></td><td><button data-save>저장</button></td></tr>').join("")||'<tr><td colspan="7">조건에 해당하는 거래가 없습니다.</td></tr>'
}
async function save(e){const btn=e.target.closest("[data-save]");if(!btn)return;const tr=btn.closest("tr"),id=tr.dataset.id;
 const payload=Object.fromEntries([...tr.querySelectorAll("[data-field]")].map(el=>[el.dataset.field,el.value]));
 payload.brokerage_score=Number(payload.brokerage_score);if(!payload.next_action_due)payload.next_action_due=null;
 btn.disabled=true;try{await request("/rest/v1/dc_opportunities?id=eq."+encodeURIComponent(id),"PATCH",payload);await load();info("저장 완료")}catch(err){info(err.message,true)}finally{btn.disabled=false}
}
$("loginForm").addEventListener("submit",login);$("addForm").addEventListener("submit",add);$("rows").addEventListener("click",save);
$("reload").onclick=()=>load().catch(e=>info(e.message,true));
for(const id of ["search","verification","category"])$(id).addEventListener("input",render);
$("logout").onclick=()=>{token=null;records=[];$("dashboard").classList.add("hidden");$("login").classList.remove("hidden");info("로그아웃 완료")};
if(!ready())info("연결 준비 상태: monitor/config.js에 Supabase URL과 publishable/anon 키를 설정해야 합니다.");
})();
