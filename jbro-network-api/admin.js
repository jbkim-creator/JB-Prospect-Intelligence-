(() => {
'use strict';
let token = null, applications = [];
const $ = id => document.getElementById(id);
const login=$('login'), dashboard=$('dashboard'), loginMessage=$('login-message'), dashMessage=$('dashboard-message');
const statusOptions=['pending','reviewing','approved','rejected'];
function showLogin(message=''){ token=null;applications=[];$('token').value='';$('issued-key').value='';$('issued-key-panel').hidden=true;dashboard.hidden=true;login.hidden=false;loginMessage.textContent=message; }
async function api(path,opts={}){
 const res=await fetch(path,{...opts,headers:{...(opts.headers||{}),'Authorization':'Bearer '+token},cache:'no-store',credentials:'omit'});
 let data={};try{data=await res.json()}catch(e){}
 if(res.status===401){showLogin('Access denied or session expired.');throw new Error('Not authorized')}
 if(!res.ok) throw new Error(data.error||'Request failed');
 return data;
}
function putText(el,content){const span=document.createElement('span');span.textContent=content??'';el.append(span);return span;}
function make(tag,cl,text){const el=document.createElement(tag);if(cl)el.className=cl;if(text!==undefined)el.textContent=text;return el;}
function render(){
 const list=applications.filter(x=>!$('filter').value||x.status===$('filter').value);
 const cards=$('cards');cards.replaceChildren();
 $('total').textContent=String(applications.length);
 for(const s of ['pending','reviewing','approved'])$(s).textContent=String(applications.filter(x=>x.status===s).length);
 if(!list.length){cards.append(make('div','empty','No applications in this view.'));return;}
 for(const a of list){
   const card=make('article','application');
   const top=make('div','top'),ttl=make('div');
   ttl.append(make('div','id','JBRO-P-'+String(a.id).padStart(6,'0')),make('h2','',a.organization));
   top.append(ttl,make('span','badge',a.status));card.append(top);
   const info=make('div','details');
   for(const item of [a.role,a.country||'Country not specified',a.email,new Date(a.created_at).toLocaleString()])putText(info,item+'  ·  ');
   card.append(info,make('div','summarytext',a.summary));
   const ops=make('div','ops');
   for(const s of statusOptions){
     if(s===a.status)continue;
     const btn=make('button',s==='rejected'?'quiet':'',s==='reviewing'?'Mark reviewing':s==='approved'?'Approve':s==='rejected'?'Reject':'Reset pending');
     btn.type='button';btn.addEventListener('click',async()=>{
       if(!confirm('Set application '+a.id+' to '+s+'?'))return;
       btn.disabled=true;dashMessage.textContent='Saving change...';
       try{await api('/api/admin/applications/'+a.id,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({status:s})});dashMessage.textContent='Status saved: '+a.id+' → '+s;await refresh();}
       catch(e){dashMessage.textContent='Update failed: '+e.message;}
       finally{btn.disabled=false;}
     });ops.append(btn);
   }
   if(a.status==='approved'){
     const issue=make('button','','Issue / rotate partner key');
     issue.type='button';
     issue.addEventListener('click',async()=>{
       if(!confirm('Generate or rotate access for '+a.organization+'? Prior keys will stop working.'))return;
       issue.disabled=true;
       try{
         const result=await api('/api/admin/applications/'+a.id+'/issue-access',{method:'POST'});
         $('issued-key').value=result.access_token;
         $('issued-key-panel').hidden=false;
         dashMessage.textContent='Key issued for application '+a.id+'. Share securely with the approved partner.';
         $('issued-key-panel').scrollIntoView({behavior:'smooth'});
       }catch(err){dashMessage.textContent='Key issuance failed: '+err.message}
       finally{issue.disabled=false}
     });ops.append(issue);
   }
   const revoke=make('button','quiet','Revoke partner access');
   revoke.type='button';
   revoke.addEventListener('click',async()=>{
     if(!confirm('Revoke access for application '+a.id+'?'))return;
     revoke.disabled=true;
     try{const result=await api('/api/admin/applications/'+a.id+'/revoke-access',{method:'POST'});dashMessage.textContent=result.revoked?'Access revoked.':'No active access for this application.';$('issued-key').value='';$('issued-key-panel').hidden=true}
     catch(err){dashMessage.textContent='Revocation failed: '+err.message}
     finally{revoke.disabled=false}
   });ops.append(revoke);
   card.append(ops);cards.append(card);
 }
}
async function refresh(){const [data,opps,missions,claims,rewards]=await Promise.all([api('/api/admin/applications'),api('/api/admin/opportunities'),api('/api/admin/tradequest/missions'),api('/api/admin/tradequest/claims'),api('/api/admin/rewards')]);applications=data.applications||[];render();renderOpportunities(opps.opportunities||[]);renderQuestAdmin(missions.missions||[],claims.claims||[]);renderRewards(rewards.deals||[]);}
function renderOpportunities(items){
 const root=$('opportunity-cards');root.replaceChildren();
 $('opportunity-message').textContent=items.length+' opportunity submissions';
 if(!items.length){root.append(make('div','empty','No opportunities submitted.'));return}
 const statuses=['submitted','reviewing','qualified','closed','rejected'];
 for(const item of items){
   const card=make('article','application');
   card.append(make('div','id','JBRO-O-'+String(item.id).padStart(6,'0')),make('h2','',item.title));
   card.append(make('div','details',item.organization+' · '+item.category+' · '+item.country+' · '+item.status));
   card.append(make('p','summarytext',item.summary));
   const actions=make('div','ops');
   for(const st of statuses){
     if(st===item.status)continue;
     const btn=make('button',st==='rejected'?'quiet':'',st);
     btn.type='button';
     btn.addEventListener('click',async()=>{
       if(!confirm('Set opportunity '+item.id+' to '+st+'?'))return;
       btn.disabled=true;
       try{await api('/api/admin/opportunities/'+item.id,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({status:st})});await refresh();}
       catch(err){$('opportunity-message').textContent='Review failed: '+err.message}
       finally{btn.disabled=false}
     });
     actions.append(btn);
   }
   card.append(actions);root.append(card);
 }
}

function renderQuestAdmin(missions,claims){
 const msg=$('quest-admin-message'),mr=$('quest-admin-missions'),cr=$('quest-admin-claims');
 mr.replaceChildren();cr.replaceChildren();
 if(!missions.length)mr.append(make('div','empty','No missions created.'));
 for(const m of missions){
   const card=make('article','application');card.append(make('div','id','Mission '+m.id+' · '+m.category+' · '+m.reward_xp+' XP · '+m.state),make('h2','',m.title),make('p','summarytext',m.description));
   for(const state of ['draft','open','closed']){
     if(m.state===state)continue;
     const button=make('button',state==='closed'?'quiet':'',state==='open'?'Publish mission':state==='closed'?'Close mission':'Return to draft');
     button.addEventListener('click',async()=>{
       if(!confirm('Change mission '+m.id+' to '+state+'?'))return;
       button.disabled=true;
       try{await api('/api/admin/tradequest/missions/'+m.id,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({state})});await refresh();}
       catch(e){msg.textContent=e.message}finally{button.disabled=false}
     });card.append(button);
   }mr.append(card);
 }
 if(!claims.length)cr.append(make('div','empty','No mission contributions yet.'));
 for(const claim of claims){
   const card=make('article','application');card.append(make('div','id','Claim '+claim.id+' · '+claim.state),make('h2','',claim.title),make('div','details',claim.organization+' · '+claim.reward_xp+' XP'),make('p','summarytext',claim.contribution));
   if(claim.state==='pending')for(const state of ['verified','rejected']){
     const button=make('button',state==='rejected'?'quiet':'',state==='verified'?'Verify and award XP':'Reject claim');
     button.addEventListener('click',async()=>{
       if(!confirm(state==='verified'?'Verify this contribution and credit XP?':'Reject this contribution?'))return;
       button.disabled=true;
       try{await api('/api/admin/tradequest/claims/'+claim.id,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({state})});await refresh();}
       catch(e){msg.textContent=e.message}finally{button.disabled=false}
     });card.append(button);
   }cr.append(card);
 }
}
$('quest-create').addEventListener('submit',async e=>{
 e.preventDefault();const b=$('quest-create').querySelector('button');b.disabled=true;
 try{await api('/api/admin/tradequest/missions',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:$('quest-title').value.trim(),description:$('quest-desc').value.trim(),category:$('quest-category').value,reward_xp:Number($('quest-reward').value)})});$('quest-create').reset();$('quest-admin-message').textContent='Draft mission created. Publish explicitly when ready.';await refresh();}
 catch(err){$('quest-admin-message').textContent='Create failed: '+err.message}
 finally{b.disabled=false}
});
function renderRewards(deals){
 const root=$('reward-deals');root.replaceChildren();
 const text=$('reward-message');
 if(!deals.length){root.append(make('div','empty','No commission pools created yet.'));return;}
 for(const d of deals){
  const card=make('article','application');
  card.append(make('div','id','Deal '+d.id+' · '+d.status),make('h2','',d.title));
  card.append(make('div','details','Contract value '+Number(d.deal_value_won).toLocaleString('ko-KR')+' KRW · Commission '+d.fee_bps/100+'% · Reward share '+d.reward_share_pct+'%'));
  card.append(make('p','', 'Received: '+Number(d.commission_received_won).toLocaleString('ko-KR')+' KRW · Reward pool: '+Number(d.reward_pool_won).toLocaleString('ko-KR')+' KRW · Allocated: '+d.allocation_total_pct+'%'));
  for(const c of d.contributors)card.append(make('div','details',c.organization+' / '+c.role+' / '+c.allocation_pct+'% / '+(c.settlement_status||'not approved')+' / '+(c.approved_won===null?'—':Number(c.approved_won).toLocaleString('ko-KR')+' KRW')));
  const control=(label,fields,submit,confirmation)=>{
    const f=make('form','');f.style.marginTop='15px';
    const inputs={};
    for(const field of fields){
      const l=make('label','',field.label);const el=document.createElement('input');
      el.required=true;el.type=field.type||'text';el.placeholder=field.placeholder||'';if(field.min)el.min=field.min;if(field.max)el.max=field.max;
      l.append(el);f.append(l);inputs[field.key]=el;
    }
    const b=make('button','',label);b.type='submit';f.append(b);
    f.addEventListener('submit',async e=>{
      e.preventDefault();if(!f.reportValidity()||!confirm(confirmation))return;
      b.disabled=true;
      try{await submit(Object.fromEntries(Object.entries(inputs).map(([key,value])=>[key,value.value])));text.textContent='Saved. This application has not transferred any funds.';await refresh();}
      catch(err){text.textContent='Not saved: '+err.message}finally{b.disabled=false}
    });
    card.append(f);
  };
  if(d.status==='draft'){
    control('Add contributor',[
      {key:'application_id',label:'Approved partner application ID',type:'number',min:'1'},
      {key:'role',label:'Contribution role (buyer_introduction / supplier_introduction / verification / execution)'},
      {key:'allocation_pct',label:'Percentage of reward pool',type:'number',min:'1',max:'100'},
      {key:'agreement_reference',label:'Individual written terms reference'}
    ],v=>api('/api/admin/rewards/'+d.id+'/contributors',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({application_id:Number(v.application_id),role:v.role,allocation_pct:Number(v.allocation_pct),agreement_reference:v.agreement_reference})}),'Add this contributor and allocation?');
    control('Record agreement as signed',[{key:'signed_reference',label:'Signed reward agreement / evidence reference'}],v=>api('/api/admin/rewards/'+d.id+'/sign',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(v)}),'Confirm that all participants have signed the relevant agreement and allocations total 100%?');
  }
  if(d.status==='signed' && !d.contributors.some(c=>c.settlement_status)){
    control('Record received commission',[{key:'amount_won',label:'Actual JBRO commission received (KRW)',type:'number',min:'1'},{key:'bank_reference',label:'Verifiable bank receipt reference'}],v=>api('/api/admin/rewards/'+d.id+'/receipts',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...v,amount_won:Number(v.amount_won),confirm_bank_received:true})}),'Confirm bank statement proves JBRO received this commission?');
    const approve=make('button','', 'Approve partner ledger amounts (no transfer)');
    approve.type='button';approve.addEventListener('click',async()=>{
      if(!confirm('Confirm all contractual, identity, tax and compliance checks are complete? This approves ledger amounts only.'))return;
      approve.disabled=true;
      try{await api('/api/admin/rewards/'+d.id+'/approve-settlements',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({confirm_compliance_review:true})});text.textContent='Settlement ledger approved. No payments sent.';await refresh()}
      catch(e){text.textContent='Not approved: '+e.message}finally{approve.disabled=false}
    });card.append(approve);
  }
  root.append(card);
 }
}
$('reward-create').addEventListener('submit',async e=>{
 e.preventDefault();const b=$('reward-create').querySelector('button[type=submit]');b.disabled=true;
 try{await api('/api/admin/rewards',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:$('reward-title').value.trim(),deal_value_won:Number($('reward-value').value),reward_share_pct:Number($('reward-share').value)})});$('reward-create').reset();$('reward-message').textContent='Draft created; does not establish a contractual obligation.';await refresh();}
 catch(err){$('reward-message').textContent=err.message}finally{b.disabled=false}
});
$('login-form').addEventListener('submit',async e=>{
 e.preventDefault();token=$('token').value.trim();loginMessage.textContent='Verifying access...';
 try{await refresh();$('token').value='';login.hidden=true;dashboard.hidden=false;loginMessage.textContent='';}catch(err){showLogin(err.message);}
});
$('filter').addEventListener('change',render);
$('clear-issued-key').addEventListener('click',()=>{$('issued-key').value='';$('issued-key-panel').hidden=true;});
$('refresh').addEventListener('click',async()=>{dashMessage.textContent='Refreshing...';try{await refresh();dashMessage.textContent='Up to date.';}catch(e){dashMessage.textContent=e.message;}});
$('logout').addEventListener('click',()=>showLogin('Dashboard locked. Token cleared from memory.'));
window.addEventListener('pagehide',()=>{token=null});
})();