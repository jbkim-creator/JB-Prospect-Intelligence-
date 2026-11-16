(()=>{'use strict';let token=null;const $=id=>document.getElementById(id);const screen=$('signin'),workspace=$('workspace');function out(msg=''){token=null;$('key').value='';screen.hidden=false;workspace.hidden=true;$('login-status').textContent=msg;$('list').replaceChildren();}async function api(path,options={}){const resp=await fetch(path,{...options,credentials:'omit',cache:'no-store',headers:{'Authorization':'Bearer '+token,...(options.headers||{})}});let body={};try{body=await resp.json()}catch(_e){}if(resp.status===401){out('Access denied or revoked. Contact JBRO for an invitation.');throw Error('Unauthorized')}if(!resp.ok)throw Error(body.error||'Request failed');return body}
function el(tag,cls,text){const x=document.createElement(tag);if(cls)x.className=cls;if(text!==undefined)x.textContent=text;return x}
async function refreshQuests(){
 const data=await api('/api/partner/tradequest');
 $('quest-xp').textContent=String(data.xp)+' XP';$('quest-list').replaceChildren();
 if(!data.missions.length){$('quest-list').append(el('div','empty','No live missions yet. JBRO will publish verified, non-confidential missions here.'));return}
 for(const m of data.missions){
   const div=el('article','opp-card');
   div.append(el('div','ref','TRADEQUEST · '+m.category.toUpperCase()+' · '+m.reward_xp+' XP'),el('h3','',m.title),el('p','desc',m.description));
   const status=m.my_claim_state;
   if(status){div.append(el('div','meta','Your contribution: '+status));}
   else{
     const form=document.createElement('form');
     const label=el('label','','Your non-confidential contribution (30–900 characters)');
     const t=document.createElement('textarea');t.required=true;t.minLength=30;t.maxLength=900;t.placeholder='Describe evidence or capability without sharing secret customer information.';
     const checkbox=document.createElement('input');checkbox.type='checkbox';checkbox.required=true;
     const consent=el('label','check');consent.append(checkbox,document.createTextNode(' I am authorized to submit this non-confidential information.'));
     const b=el('button','','Submit mission contribution');b.type='submit';
     form.append(label,t,consent,b);
     form.addEventListener('submit',async e=>{
       e.preventDefault();if(!form.reportValidity())return;
       b.disabled=true;$('quest-message').textContent='Submitting for review...';
       try{await api('/api/partner/tradequest/'+m.id+'/claim',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({contribution:t.value.trim(),nonconfidential:checkbox.checked})});$('quest-message').textContent='Contribution submitted. XP is awarded only after verification.';await refreshQuests()}
       catch(err){$('quest-message').textContent='Not submitted: '+err.message}finally{b.disabled=false}
     });div.append(form);
   }
   $('quest-list').append(div);
 }
}
async function refreshRewards(){
  const root=$('reward-list');root.replaceChildren();
  const data=await api('/api/partner/rewards');
  if(!data.rewards.length){root.append(el('div','empty','No signed partner reward agreements yet.'));return}
  for(const r of data.rewards){
    const div=el('article','opp-card');
    div.append(el('h3','',r.title),el('div','meta',r.role.replaceAll('_',' ')+' · '+r.allocation_pct+'% of agreed reward pool'));
    div.append(el('p','',r.approved_won===null?'No payable amount approved yet.':'Ledger amount: '+Number(r.approved_won).toLocaleString('ko-KR')+' KRW · '+r.settlement_status));
    root.append(div);
  }
}
async function refresh(){await refreshQuests();await refreshRewards();const data=await api('/api/partner/opportunities');$('list').replaceChildren();if(!data.opportunities.length){$('list').append(el('div','empty','No opportunities submitted yet.'));return}for(const item of data.opportunities){const div=el('article','opp-card');div.append(el('div','ref','JBRO-O-'+String(item.id).padStart(6,'0')),el('h3','',item.title),el('div','meta',item.category.replaceAll('_',' ')+' · '+item.status+' · '+(item.country||'Region unspecified')),el('p','desc',item.summary));$('list').append(div)}}
$('login').addEventListener('submit',async e=>{e.preventDefault();token=$('key').value.trim();$('login-status').textContent='Verifying your invitation...';try{const me=await api('/api/partner/me');$('identity').textContent=me.partner.organization+' · '+me.partner.role;$('key').value='';screen.hidden=true;workspace.hidden=false;await refresh()}catch(err){$('login-status').textContent=err.message}});
$('opp').addEventListener('submit',async e=>{e.preventDefault();if(!$('opp').reportValidity())return;const btn=$('opp').querySelector('button[type=submit]');btn.disabled=true;$('submit-status').textContent='Submitting...';try{const body={category:$('category').value,title:$('title').value.trim(),country:$('country').value.trim(),summary:$('summary').value.trim(),confirm_nonconfidential:$('confirm').checked};const result=await api('/api/partner/opportunities',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});$('submit-status').textContent='Submitted for JBRO review: '+result.reference;$('opp').reset();await refresh()}catch(err){$('submit-status').textContent='Not submitted: '+err.message}finally{btn.disabled=false}});
$('refresh').addEventListener('click',async()=>{try{await refresh();$('list-status').textContent='Updated.'}catch(err){$('list-status').textContent=err.message}});
$('signout').addEventListener('click',()=>out('Workspace locked.'));
window.addEventListener('pagehide',()=>{token=null});
})();