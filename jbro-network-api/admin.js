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
async function refresh(){const [data,opps,missions,claims,rewards,sales,kpis,campaign]=await Promise.all([api('/api/admin/applications'),api('/api/admin/opportunities'),api('/api/admin/tradequest/missions'),api('/api/admin/tradequest/claims'),api('/api/admin/rewards'),api('/api/admin/deal-rooms'),api('/api/admin/gmv-kpis'),api('/api/admin/first10k-funnel')]);applications=data.applications||[];render();renderOpportunities(opps.opportunities||[]);renderQuestAdmin(missions.missions||[],claims.claims||[]);renderRewards(rewards.deals||[]);renderSales(sales.rooms||[]);renderGMVKpis(kpis);renderFirst10kFunnel(campaign);}
function renderFirst10kFunnel(data){
 const totals=$('coupon-funnel-totals');totals.replaceChildren();
 const t=data.totals||{};
 const usd=n=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(Number(n||0)/100);
 const fields=[
  ['Applications',t.applications||0],['Coupon requests',t.coupon_requests||0],
  ['Approved partners',t.approved_applications||0],['Coupons issued',t.issued_coupons||0],
  ['Completed coupon-linked orders',t.completed_coupon_deals||0],
  ['Completed coupon-linked GMV',usd(t.completed_coupon_gmv_usd_minor)],
  ['Recorded fee discount',usd(t.waived_usd_minor)]
 ];
 for(const [label,value] of fields){
  const c=make('div');c.append(make('strong','',String(value)),make('span','',label));totals.append(c);
 }
 const sources=$('coupon-funnel-sources');sources.replaceChildren();
 if(!(data.sources||[]).length){sources.append(make('div','empty','No submitted applications yet. No visitor analytics are collected.'));return;}
 for(const x of data.sources){
  const c=make('article','application');
  c.append(make('h3','',x.source),make('div','details',
   'Applications: '+x.applications+' · Coupon requests: '+x.coupon_requests+' · Approved: '+x.approved_applications+' · Coupons issued: '+x.issued_coupons));
  sources.append(c);
 }
}
function renderGMVKpis(data){
 const root=$('gmv-kpis');root.replaceChildren();
 const fmt=(v,cur)=>new Intl.NumberFormat('en-US',{style:'currency',currency:cur,maximumFractionDigits:cur==='KRW'?0:2}).format(Number(v)/(cur==='USD'?100:1));
 for(const cur of ['USD','KRW']){
   const k=(data.currencies||{})[cur]||{};
   const entries=[
     ['Completed GMV ('+cur+')',fmt(k.completed_gmv_minor||0,cur)],
     ['Signed pipeline ('+cur+')',fmt(k.signed_gmv_minor||0,cur)],
     ['Completed / signed deals',String(k.completed_deals||0)+' / '+String(k.signed_deals||0)],
     ['Recorded commission ('+cur+')',fmt(k.recorded_commission_minor||0,cur)]
   ];
   for(const [label,value] of entries){const cell=make('div');cell.append(make('strong','',value),make('span','',label));root.append(cell);}
 }
 const counts=data.counts||{};
 $('gmv-kpi-note').textContent='Approved partners: '+(counts.approved_partners||0)+' · Qualified opportunities: '+(counts.qualified_opportunities||0)+' · Draft rooms: '+(counts.draft_rooms||0)+' · FIRST10K coupons: '+(counts.first10k_coupons||0)+'. Amounts are lifetime and use original currency; commission entries require bank reconciliation.';
}
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
function displayMoney(minor,currency){const value=currency==='USD'?Number(minor)/100:Number(minor);return new Intl.NumberFormat('en-US',{style:'currency',currency:currency==='USD'?'USD':'KRW',minimumFractionDigits:currency==='USD'?2:0,maximumFractionDigits:currency==='USD'?2:0}).format(value)}
function parseMinor(raw,currency){const value=Number(raw);const amount=Math.round(value*(currency==='USD'?100:1));if(!Number.isFinite(value)||value<=0||!Number.isSafeInteger(amount)||(currency==='KRW'&&!Number.isInteger(value)))throw Error('Invalid amount for selected currency');return amount}
function renderRewards(deals){
 const root=$('reward-deals');root.replaceChildren();
 const text=$('reward-message');
 if(!deals.length){root.append(make('div','empty','No commission pools created yet.'));return;}
 for(const d of deals){
  const card=make('article','application');
  card.append(make('div','id','Deal '+d.id+' · '+d.status),make('h2','',d.title));
  card.append(make('div','details','Contract value '+displayMoney(d.deal_value_minor,d.currency)+' · Commission '+d.fee_bps/100+'% · Reward share '+d.reward_share_pct+'%'));
  card.append(make('p','', 'Received: '+displayMoney(d.commission_received_minor,d.currency)+' · Reward pool: '+displayMoney(d.reward_pool_minor,d.currency)+' · Allocated: '+d.allocation_total_pct+'%'));
  card.append(make('p','', 'FIRST10K USD discount: '+displayMoney(d.coupon_discount_minor||0,d.currency)+' · Net fee ceiling: '+displayMoney(d.commission_ceiling_minor,d.currency)));
  for(const c of d.contributors)card.append(make('div','details',c.organization+' / '+c.role+' / '+c.allocation_pct+'% / '+(c.settlement_status||'not approved')+' / '+(c.approved_won===null?'—':displayMoney(c.approved_won,d.currency))));
  const control=(label,fields,submit,confirmation)=>{
    const f=make('form','');f.style.marginTop='15px';
    const inputs={};
    for(const field of fields){
      const l=make('label','',field.label);const el=document.createElement('input');
      el.required=true;el.type=field.type||'text';el.placeholder=field.placeholder||'';if(field.min)el.min=field.min;if(field.max)el.max=field.max;if(field.step)el.step=field.step;
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
  if(d.status==='draft'&&!d.coupon_holder_id){
    control('Grant FIRST10K (up to US$250 fee waiver)',[
      {key:'application_id',label:'Approved first-time fee-paying buyer OR seller application ID',type:'number',min:'1'}
    ],v=>api('/api/admin/rewards/'+d.id+'/first-trade-coupon',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({application_id:Number(v.application_id),confirm_eligibility_and_fee_terms:true})
    }),'Verify this is the partner’s FIRST eligible deal, that they are an approved buyer or seller in the linked DRAFT Deal Room, and that their 2.5% JBRO fee stream is eligible for the one-time US$10,000 FIRST10K waiver (USD-denominated deals only). The contract must not already have been issued.');
  }
  if(d.status==='draft'){
    control('Add contributor',[
      {key:'application_id',label:'Approved partner application ID',type:'number',min:'1'},
      {key:'role',label:'Contribution role (buyer_introduction / supplier_introduction / verification / execution)'},
      {key:'allocation_pct',label:'Percentage of reward pool',type:'number',min:'1',max:'100'},
      {key:'agreement_reference',label:'Individual written terms reference'}
    ],v=>api('/api/admin/rewards/'+d.id+'/contributors',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({application_id:Number(v.application_id),role:v.role,allocation_pct:Number(v.allocation_pct),agreement_reference:v.agreement_reference})}),'Add this contributor and allocation?');
    const guide=make('p','','To sign this reward deal, issue and review participant contracts in the Platform Contract Signing section below. All parties must accept before finalization.');card.append(guide);
  }
  if(d.status==='signed' && !d.contributors.some(c=>c.settlement_status)){
    control('Record received commission',[{key:'amount',label:'Actual JBRO commission received ('+d.currency+')',type:'number',min:d.currency==='USD'?'0.01':'1',step:d.currency==='USD'?'0.01':'1'},{key:'bank_reference',label:'Verifiable bank receipt reference'}],v=>api('/api/admin/rewards/'+d.id+'/receipts',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({currency:d.currency,...(d.currency==='USD'?{amount_minor:parseMinor(v.amount,'USD')}:{amount_won:parseMinor(v.amount,'KRW')}),bank_reference:v.bank_reference,confirm_bank_received:true})}),'Confirm bank statement proves JBRO received this commission in the stated currency?');
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
async function loadContracts(dealId){
 const root=$('contract-admin-list'),status=$('contract-admin-status');root.replaceChildren();
 const data=await api('/api/admin/rewards/'+dealId+'/contracts');
 const contracts=data.contracts||[];
 status.textContent=contracts.length+' agreement(s) on reward deal '+dealId;
 if(!contracts.length){
   const info=make('p','', 'Add approved participants with allocations totaling 100%, then issue each frozen individual agreement.');
   const issue=make('button','','Issue immutable participation agreements');
   issue.type='button';issue.addEventListener('click',async()=>{
     if(!confirm('Confirm counsel reviewed all terms, participating entities and applicable law before issuing agreements?'))return;
     issue.disabled=true;try{await api('/api/admin/rewards/'+dealId+'/contracts/issue',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({confirm_legal_terms_reviewed:true})});await loadContracts(dealId);await refresh();}
     catch(e){status.textContent='Issue failed: '+e.message}finally{issue.disabled=false}
   });root.append(info,issue);return;
 }
 for(const d of contracts){
   const c=make('article','application');
   c.append(make('h2','',d.organization+' · '+d.role),make('div','id','Agreement '+d.id+' v'+d.version+' · '+d.status));
   c.append(make('p','', 'SHA-256: '+d.agreement_sha256),make('p','', 'Partner: '+(d.partner_signed?'Accepted':'Awaiting acceptance')+' · JBRO: '+(d.jbro_signed?'Accepted':'Awaiting countersign')));
   const pre=document.createElement('pre');pre.style.cssText='white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;background:#f4f6f4;padding:12px;border-radius:8px';pre.textContent=JSON.stringify(JSON.parse(d.agreement_text),null,2);c.append(pre);
   if(!d.jbro_signed){
     const form=make('form','');const lab=make('label','','Authorized JBRO representative (full name)');
     const input=document.createElement('input');input.required=true;input.minLength=2;input.maxLength=120;lab.append(input);
     const ck=make('label','check');const tick=document.createElement('input');tick.type='checkbox';tick.required=true;ck.append(tick,document.createTextNode(' I have authority to represent JBRO and accept the exact document shown above.'));
     const button=make('button','','Countersign on behalf of JBRO');button.type='submit';form.append(lab,ck,button);
     form.addEventListener('submit',async e=>{e.preventDefault();if(!form.reportValidity())return;if(!confirm('This records your affirmative acceptance of this exact SHA-256 agreement. Continue?'))return;button.disabled=true;
       try{await api('/api/admin/contracts/'+d.id+'/countersign',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({representative:input.value.trim(),document_sha256:d.agreement_sha256,confirm_company_authority:true,confirm_read_and_accept:true})});await loadContracts(dealId);}
       catch(err){status.textContent='Signing failed: '+err.message}finally{button.disabled=false}
     });c.append(form);
   }
   root.append(c);
 }
 if(contracts.every(c=>c.partner_signed&&c.jbro_signed)){
   const button=make('button','','Finalize all signed agreements and activate reward terms');
   button.type='button';button.addEventListener('click',async()=>{
     if(!confirm('Verify signatory authority, company registration, legal jurisdiction and all participants before finalizing?'))return;
     button.disabled=true;try{await api('/api/admin/rewards/'+dealId+'/contracts/finalize',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({confirm_all_party_authority_checked:true})});status.textContent='Reward deal marked signed. No money transferred.';await refresh();await loadContracts(dealId);}
     catch(e){status.textContent='Finalization failed: '+e.message}finally{button.disabled=false}
   });root.append(button);
 }
}
$('contract-lookup').addEventListener('submit',async e=>{e.preventDefault();try{await loadContracts(Number($('contract-deal-id').value))}catch(err){$('contract-admin-status').textContent=err.message}});
function saveContractRecord(filename, data) {
 const file=new Blob([JSON.stringify(data,null,2)],{type:'application/json'});
 const url=URL.createObjectURL(file);const link=document.createElement('a');
 link.href=url;link.download=filename;document.body.append(link);link.click();link.remove();
 setTimeout(()=>URL.revokeObjectURL(url),1500);
}
async function showExecutionAdmin(roomId,container,message){
 container.replaceChildren();
 const data=await api('/api/admin/deal-rooms/'+roomId+'/execution');
 if(!data.events.length){container.append(make('p','','No execution evidence recorded yet.'));return}
 for(const item of data.events){
   const box=make('div','application');
   box.append(make('div','id',item.stage+' · '+item.status+' · Event '+item.id),
      make('p','',item.organization+' · '+item.evidence_reference),make('p','summarytext',item.note));
   if(item.status==='submitted')for(const newStatus of ['verified','rejected']){
     const button=make('button',newStatus==='rejected'?'quiet':'',newStatus==='verified'?'Verify evidence':'Reject evidence');
     button.type='button';button.addEventListener('click',async()=>{
       if(!confirm('Have you reviewed the independent documents behind this evidence reference? Record status '+newStatus+'?'))return;
       button.disabled=true;
       try{await api('/api/admin/deal-rooms/'+roomId+'/execution/'+item.id,{
         method:'PATCH',headers:{'Content-Type':'application/json'},
         body:JSON.stringify({status:newStatus,confirm_reviewed_evidence:true})});
         message.textContent='Evidence review saved. This records a status, not a banking or logistics certification.';
         await showExecutionAdmin(roomId,container,message);
       }catch(err){message.textContent=err.message}finally{button.disabled=false}
     });box.append(button);
   }
   container.append(box);
 }
}
function renderSales(rooms){
 const root=$('sale-admin-rooms'),msg=$('sale-admin-status');root.replaceChildren();
 if(!rooms.length){root.append(make('div','empty','No buyer–seller deals created yet.'));return}
 for(const room of rooms){
  const c=make('article','application'),doc=room.contract;
  c.append(make('h2','',room.title),make('div','id','Deal Room '+room.id+' · '+room.status+' · linked Reward Deal '+(room.reward_deal_id||'none')));
  if(doc){
   c.append(make('p','', 'SHA-256: '+doc.document_sha256));
   c.append(make('div','details','Buyer signed: '+doc.signatures.some(x=>x.role==='buyer')+' · Seller signed: '+doc.signatures.some(x=>x.role==='seller')));
   const pre=document.createElement('pre');pre.style.cssText='white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f8f5;padding:14px;border-radius:8px;font-size:12px';
   pre.textContent=JSON.stringify(JSON.parse(doc.terms_json),null,2);c.append(pre);
  }
  if(room.status==='draft'){
   const btn=make('button','','Issue sale agreement to buyer and seller');btn.type='button';
   btn.addEventListener('click',async()=>{
    if(!confirm('Confirm counsel reviewed complete sale terms, counterparty identities, signatories, and applicable trade compliance?'))return;
    btn.disabled=true;
    try{await api('/api/admin/deal-rooms/'+room.id+'/issue',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({confirm_sale_terms_legal_review:true})});msg.textContent='Agreement issued to both approved counterparties.';await refresh();}
    catch(err){msg.textContent='Not issued: '+err.message}finally{btn.disabled=false}
   });c.append(btn);
  }
  if(doc){
   const btn=make('button','quiet','Download frozen contract record (JSON)');
   btn.type='button';btn.addEventListener('click',async()=>{
      try{const bundle=await api('/api/admin/deal-rooms/'+room.id+'/contract-export');saveContractRecord('JBRO-Deal-'+room.id+'-contract-record.json',bundle)}
      catch(err){msg.textContent='Download unavailable: '+err.message}
   });c.append(btn);
  }
  if(room.status==='signed'){
    const btn=make('button','quiet','View & review execution evidence');btn.type='button';
    const slot=make('div',''),status=make('p','','');
    btn.addEventListener('click',async()=>{
      try{await showExecutionAdmin(room.id,slot,status)}
      catch(err){status.textContent='Unable to load execution: '+err.message}
    });
    c.append(btn,status,slot);
  }
  root.append(c);
 }
}
$('sale-create').addEventListener('submit',async e=>{
 e.preventDefault();const form=$('sale-create');if(!form.reportValidity())return;
 const btn=form.querySelector('button[type=submit]');btn.disabled=true;const obj=Object.fromEntries(new FormData(form));
 const terms={};for(const key of ['buyer_legal_name','seller_legal_name','item_description','quantity_unit','delivery_terms','inspection_terms','payment_terms','governing_law','dispute_resolution','additional_terms'])terms[key]=(obj[key]||'').trim();
 terms.currency=obj.currency;const saleMinor=parseMinor(obj.total_contract_value,obj.currency);if(obj.currency==='USD')terms.total_contract_value_minor=saleMinor;else terms.total_contract_value_won=saleMinor;
 const payload={title:obj.title.trim(),buyer_application_id:Number(obj.buyer_application_id),seller_application_id:Number(obj.seller_application_id),reward_deal_id:obj.reward_deal_id?Number(obj.reward_deal_id):null,terms};
 try{const r=await api('/api/admin/deal-rooms',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});$('sale-admin-status').textContent='Private Deal Room '+r.room_id+' created in draft. Issue explicitly after review.';form.reset();await refresh();}
 catch(err){$('sale-admin-status').textContent='Create failed: '+err.message}finally{btn.disabled=false}
});
$('reward-create').addEventListener('submit',async e=>{
 e.preventDefault();const b=$('reward-create').querySelector('button[type=submit]');b.disabled=true;
 try{await api('/api/admin/rewards',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:$('reward-title').value.trim(),currency:$('reward-currency').value,...($('reward-currency').value==='USD'?{deal_value_minor:parseMinor($('reward-value').value,'USD')}:{deal_value_won:parseMinor($('reward-value').value,'KRW')}),reward_share_pct:Number($('reward-share').value)})});$('reward-create').reset();$('reward-message').textContent='Draft created; does not establish a contractual obligation.';await refresh();}
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