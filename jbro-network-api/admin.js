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
async function refresh(){const [data,opps]=await Promise.all([api('/api/admin/applications'),api('/api/admin/opportunities')]);applications=data.applications||[];render();renderOpportunities(opps.opportunities||[]);}
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