(() => {
'use strict';
let token = null, applications = [];
const $ = id => document.getElementById(id);
const login=$('login'), dashboard=$('dashboard'), loginMessage=$('login-message'), dashMessage=$('dashboard-message');
const statusOptions=['pending','reviewing','approved','rejected'];
function showLogin(message=''){ token=null;applications=[];$('token').value='';dashboard.hidden=true;login.hidden=false;loginMessage.textContent=message; }
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
   card.append(ops);cards.append(card);
 }
}
async function refresh(){const data=await api('/api/admin/applications');applications=data.applications||[];render();}
$('login-form').addEventListener('submit',async e=>{
 e.preventDefault();token=$('token').value.trim();loginMessage.textContent='Verifying access...';
 try{await refresh();$('token').value='';login.hidden=true;dashboard.hidden=false;loginMessage.textContent='';}catch(err){showLogin(err.message);}
});
$('filter').addEventListener('change',render);
$('refresh').addEventListener('click',async()=>{dashMessage.textContent='Refreshing...';try{await refresh();dashMessage.textContent='Up to date.';}catch(e){dashMessage.textContent=e.message;}});
$('logout').addEventListener('click',()=>showLogin('Dashboard locked. Token cleared from memory.'));
window.addEventListener('pagehide',()=>{token=null});
})();