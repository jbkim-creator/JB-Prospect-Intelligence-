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
function downloadRecord(filename,data){
 const file=new Blob([JSON.stringify(data,null,2)],{type:'application/json'});
 const url=URL.createObjectURL(file),a=document.createElement('a');
 a.href=url;a.download=filename;document.body.append(a);a.click();a.remove();
 setTimeout(()=>URL.revokeObjectURL(url),1500);
}
async function showExecutionPartner(roomId,slot,status){
 slot.replaceChildren();const result=await api('/api/partner/deal-rooms/'+roomId+'/execution');
 if(!result.events.length){slot.append(el('p','','No evidence reported for this deal yet.'));return}
 for(const item of result.events){
  const card=el('div','opp-card');card.append(el('div','meta',item.stage+' · '+item.status+' · '+item.organization),el('p','',item.evidence_reference),el('p','desc',item.note));slot.append(card);
 }
}
async function refreshSaleRooms(){
 const root=$('sale-partner-rooms');root.replaceChildren();const status=$('sale-partner-status');
 const data=await api('/api/partner/deal-rooms');const rooms=data.rooms||[];
 if(!rooms.length){root.append(el('div','empty','No buyer–seller sale agreements assigned to your company yet.'));return}
 for(const room of rooms){
  const d=room.contract,card=el('article','opp-card');
  card.append(el('h3','',room.title+' · Deal Room '+room.id),el('div','meta','My role: '+room.my_role+' · '+room.status));
  if(d){
   card.append(el('div','meta','Document SHA-256: '+d.document_sha256));
   card.append(el('p','', 'Recorded signatures: '+d.signatures.map(x=>x.role).join(', ')||'None'));
   const pre=document.createElement('pre');pre.style.cssText='white-space:pre-wrap;overflow-wrap:anywhere;padding:12px;background:#f4faf6;border-radius:8px;font-size:12px';pre.textContent=JSON.stringify(JSON.parse(d.terms_json),null,2);card.append(pre);
   if(room.status==='issued'&&!d.signatures.some(x=>x.role===room.my_role)){
    const form=document.createElement('form');const label=el('label','','Full legal name and signing capacity');
    const input=document.createElement('input');input.required=true;input.minLength=2;input.maxLength=120;input.placeholder='e.g. Jane Doe, authorized director';label.append(input);
    const consent=el('label','check'),check=document.createElement('input');check.type='checkbox';check.required=true;consent.append(check,document.createTextNode(' I have authority to represent this buyer/seller and accept this exact sale contract.'));
    const btn=el('button','','Accept buyer–seller sale agreement');btn.type='submit';form.append(label,consent,btn);
    form.addEventListener('submit',async e=>{
      e.preventDefault();if(!form.reportValidity())return;
      if(!confirm('By proceeding, you affirmatively accept the complete document shown with its SHA-256 fingerprint.'))return;
      btn.disabled=true;try{await api('/api/partner/deal-rooms/'+room.id+'/accept',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({representative:input.value.trim(),document_sha256:d.document_sha256,confirm_authorized_signatory:true,confirm_read_and_accept:true})});status.textContent='Electronic acceptance saved. Both parties must accept for completion.';await refreshSaleRooms();}
      catch(err){status.textContent='Not accepted: '+err.message}finally{btn.disabled=false}
    });card.append(form);
   }
  }
  if(d){
    const btn=el('button','soft','Download contract record (JSON)');
    btn.type='button';btn.addEventListener('click',async()=>{
      try{const record=await api('/api/partner/deal-rooms/'+room.id+'/contract-export');
      downloadRecord('JBRO-Deal-'+room.id+'-contract-record.json',record)}
      catch(err){status.textContent='Download failed: '+err.message}
    });card.append(btn);
  }
  if(room.status==='signed'){
    const label=el('h3','','Execution evidence (pending independent review)');card.append(label);
    const form=document.createElement('form');
    const stageLabel=el('label','','Milestone');const select=document.createElement('select');
    for(const v of ['inspection','shipment','delivery','payment']){
      const option=document.createElement('option');option.value=v;option.textContent=v;select.append(option);
    }stageLabel.append(select);
    const refLabel=el('label','','Evidence reference or tracking number (no secrets)');const ref=document.createElement('input');
    ref.minLength=4;ref.maxLength=180;ref.required=true;refLabel.append(ref);
    const noteLabel=el('label','','Evidence description (no confidential documents)');const note=document.createElement('textarea');
    note.minLength=10;note.maxLength=900;note.required=true;noteLabel.append(note);
    const confirmLabel=el('label','check'),checkbox=document.createElement('input');
    checkbox.type='checkbox';checkbox.required=true;
    confirmLabel.append(checkbox,document.createTextNode(' I have authority to submit this truthful evidence. Submission does not certify completion.'));
    const submit=el('button','','Submit evidence for JBRO review');submit.type='submit';
    form.append(stageLabel,refLabel,noteLabel,confirmLabel,submit);
    form.addEventListener('submit',async e=>{
      e.preventDefault();if(!form.reportValidity())return;submit.disabled=true;
      try{await api('/api/partner/deal-rooms/'+room.id+'/execution',{method:'POST',
       headers:{'Content-Type':'application/json'},
       body:JSON.stringify({stage:select.value,evidence_reference:ref.value.trim(),note:note.value.trim(),confirm_accurate_and_authorized:checkbox.checked})});
       status.textContent='Evidence submitted; JBRO independent review pending.';form.reset();
       await showExecutionPartner(room.id,events,status);
      }catch(err){status.textContent='Submission failed: '+err.message}finally{submit.disabled=false}
    });
    card.append(form);
    const button=el('button','soft','Refresh execution history');button.type='button';
    const events=document.createElement('div');button.addEventListener('click',async()=>{try{await showExecutionPartner(room.id,events,status)}catch(err){status.textContent=err.message}});
    card.append(button,events);
  }
  root.append(card);
 }
}
async function refreshContracts(){
 const root=$('contracts-list');root.replaceChildren();const status=$('contracts-status');
 const data=await api('/api/partner/contracts');const docs=data.contracts||[];
 if(!docs.length){root.append(el('div','empty','No invitation to sign a participation agreement yet.'));return}
 for(const d of docs){
   const panel=el('article','opp-card');
   panel.append(el('h3','',d.title+' · Agreement '+d.id),el('div','meta','Version '+d.version+' · '+d.status+' · SHA-256 '+d.agreement_sha256));
   panel.append(el('p','', 'My signature: '+(d.partner_signed?'Recorded':'Required')+' · JBRO: '+(d.jbro_signed?'Recorded':'Pending')));
   const pre=document.createElement('pre');pre.style.cssText='white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;background:#f5faf7;border-radius:8px;padding:12px';
   pre.textContent=JSON.stringify(JSON.parse(d.agreement_text),null,2);panel.append(pre);
   if(!d.partner_signed){
     const form=document.createElement('form');const label=el('label','','Your full legal name and signatory capacity');
     const input=document.createElement('input');input.required=true;input.minLength=2;input.maxLength=120;input.placeholder='e.g. Jane Doe, authorized director';label.append(input);
     const confirm=el('label','check');const check=document.createElement('input');check.type='checkbox';check.required=true;confirm.append(check,document.createTextNode(' I have authority to represent this company and accept this exact document, including success-fee conditions.'));
     const submit=el('button','','Accept and record my agreement');submit.type='submit';form.append(label,confirm,submit);
     form.addEventListener('submit',async e=>{e.preventDefault();if(!form.reportValidity())return;if(!window.confirm('Confirm you have reviewed the complete document and are authorized to accept it?'))return;submit.disabled=true;
       try{await api('/api/partner/contracts/'+d.id+'/accept',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({representative:input.value.trim(),document_sha256:d.agreement_sha256,confirm_authorized_signatory:true,confirm_read_and_accept:true})});status.textContent='Electronic acceptance recorded against document hash. JBRO must countersign as applicable.';await refreshContracts();}
       catch(err){status.textContent='Acceptance not recorded: '+err.message}finally{submit.disabled=false}
     });panel.append(form);
   }
   root.append(panel);
 }
}
async function refreshFirstCoupon(){
 const data=await api('/api/partner/first-trade-coupon');
 const c=data.coupon;
 $('first-coupon-status').textContent=c
  ?('FIRST10K assigned to Deal Room '+c.deal_room_id+' · Fee discount: US
  :'FIRST10K (USD) offer available to request at partner screening. Eligibility and approval are not guaranteed.';
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
async function refresh(){await refreshQuests();await refreshFirstCoupon();await refreshSaleRooms();await refreshContracts();await refreshRewards();const data=await api('/api/partner/opportunities');$('list').replaceChildren();if(!data.opportunities.length){$('list').append(el('div','empty','No opportunities submitted yet.'));return}for(const item of data.opportunities){const div=el('article','opp-card');div.append(el('div','ref','JBRO-O-'+String(item.id).padStart(6,'0')),el('h3','',item.title),el('div','meta',item.category.replaceAll('_',' ')+' · '+item.status+' · '+(item.country||'Region unspecified')),el('p','desc',item.summary));$('list').append(div)}}
$('login').addEventListener('submit',async e=>{e.preventDefault();token=$('key').value.trim();$('login-status').textContent='Verifying your invitation...';try{const me=await api('/api/partner/me');$('identity').textContent=me.partner.organization+' · '+me.partner.role;$('key').value='';screen.hidden=true;workspace.hidden=false;await refresh()}catch(err){$('login-status').textContent=err.message}});
$('opp').addEventListener('submit',async e=>{e.preventDefault();if(!$('opp').reportValidity())return;const btn=$('opp').querySelector('button[type=submit]');btn.disabled=true;$('submit-status').textContent='Submitting...';try{const body={category:$('category').value,title:$('title').value.trim(),country:$('country').value.trim(),summary:$('summary').value.trim(),confirm_nonconfidential:$('confirm').checked};const result=await api('/api/partner/opportunities',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});$('submit-status').textContent='Submitted for JBRO review: '+result.reference;$('opp').reset();await refresh()}catch(err){$('submit-status').textContent='Not submitted: '+err.message}finally{btn.disabled=false}});
$('refresh').addEventListener('click',async()=>{try{await refresh();$('list-status').textContent='Updated.'}catch(err){$('list-status').textContent=err.message}});
$('signout').addEventListener('click',()=>out('Workspace locked.'));
window.addEventListener('pagehide',()=>{token=null});
})();+(Number(c.discount_minor)/100).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2}))
  :'FIRST10M offer available to request at partner screening. Eligibility and approval are not guaranteed.';
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
async function refresh(){await refreshQuests();await refreshFirstCoupon();await refreshSaleRooms();await refreshContracts();await refreshRewards();const data=await api('/api/partner/opportunities');$('list').replaceChildren();if(!data.opportunities.length){$('list').append(el('div','empty','No opportunities submitted yet.'));return}for(const item of data.opportunities){const div=el('article','opp-card');div.append(el('div','ref','JBRO-O-'+String(item.id).padStart(6,'0')),el('h3','',item.title),el('div','meta',item.category.replaceAll('_',' ')+' · '+item.status+' · '+(item.country||'Region unspecified')),el('p','desc',item.summary));$('list').append(div)}}
$('login').addEventListener('submit',async e=>{e.preventDefault();token=$('key').value.trim();$('login-status').textContent='Verifying your invitation...';try{const me=await api('/api/partner/me');$('identity').textContent=me.partner.organization+' · '+me.partner.role;$('key').value='';screen.hidden=true;workspace.hidden=false;await refresh()}catch(err){$('login-status').textContent=err.message}});
$('opp').addEventListener('submit',async e=>{e.preventDefault();if(!$('opp').reportValidity())return;const btn=$('opp').querySelector('button[type=submit]');btn.disabled=true;$('submit-status').textContent='Submitting...';try{const body={category:$('category').value,title:$('title').value.trim(),country:$('country').value.trim(),summary:$('summary').value.trim(),confirm_nonconfidential:$('confirm').checked};const result=await api('/api/partner/opportunities',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});$('submit-status').textContent='Submitted for JBRO review: '+result.reference;$('opp').reset();await refresh()}catch(err){$('submit-status').textContent='Not submitted: '+err.message}finally{btn.disabled=false}});
$('refresh').addEventListener('click',async()=>{try{await refresh();$('list-status').textContent='Updated.'}catch(err){$('list-status').textContent=err.message}});
$('signout').addEventListener('click',()=>out('Workspace locked.'));
window.addEventListener('pagehide',()=>{token=null});
})();