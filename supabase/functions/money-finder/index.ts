import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2";

const cors = {"Access-Control-Allow-Origin":"*","Access-Control-Allow-Headers":"authorization,content-type","Access-Control-Allow-Methods":"GET,POST,OPTIONS","Content-Type":"application/json; charset=utf-8"};
const allowedEmails = new Set(["jbkim@jbrocap.com"]);
const supabase = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!, {auth:{persistSession:false}});
const json=(data:unknown,status=200)=>new Response(JSON.stringify(data),{status,headers:cors});
const norm=(s:string)=>s.trim().toLowerCase();
function domainOf(value:string){try{return new URL(value.includes("://")?value:`https://${value}`).hostname.toLowerCase().replace(/^www\./,"")}catch{return ""}}

Deno.serve(async req=>{
 if(req.method==="OPTIONS")return new Response("ok",{headers:cors});
 const auth=req.headers.get("Authorization")||"";
 if(!auth.startsWith("Bearer "))return json({error:"A valid Supabase access token is required."},401);
 const {data:{user},error:userError}=await supabase.auth.getUser(auth.slice(7));
 if(userError||!user||!allowedEmails.has((user.email||"").toLowerCase()))return json({error:"Only the allowlisted JBRO operator account can access this service."},403);
 try {
  const path=new URL(req.url).pathname.replace(/\/$/,"");
  if(req.method==="GET"&&(path===""||path.endsWith("/money-finder"))){
    const [leadsR,rewardsR,tasksR,outboxR,programsR]=await Promise.all([
    supabase.from("mf_leads").select("*").order("created_at",{ascending:false}).limit(250),
    supabase.from("mf_rewards").select("*").order("created_at",{ascending:false}).limit(500),
    supabase.from("mf_research_tasks").select("*").order("created_at",{ascending:false}).limit(100),
     supabase.from("mf_engine_outbox").select("*").order("created_at",{ascending:false}).limit(100),
     supabase.from("mf_partner_registry").select("*").order("display_name")
   ]);
    const err=[leadsR.error,rewardsR.error,tasksR.error,outboxR.error,programsR.error].find(Boolean);if(err)throw err;
   const rewards=rewardsR.data||[], leads=(leadsR.data||[]).map((l:any)=>({...l,reward_status:rewards.find((r:any)=>r.lead_id===l.id)?.status||null}));
    return json({leads,programs:programsR.data||[],activities:[...(tasksR.data||[]).map((t:any)=>({...t,kind:"research"})),...(outboxR.data||[]).map((o:any)=>({...o,kind:o.target_engine}))],metrics:{leads:leads.length,ready:leads.filter((l:any)=>l.review_status==="eligible").length,blocked:leads.filter((l:any)=>["duplicate","protected","dnc","needs_review"].includes(l.review_status)).length,paid:rewards.filter((r:any)=>r.status==="paid").length}})
  }
  if(req.method!=="POST")return json({error:"Method not allowed"},405);
  const input=await req.json();
   if(path.endsWith("/protection/import")){
    const rows=Array.isArray(input.rows)?input.rows:[];
    if(!input.complete||rows.length===0||rows.length>5000)return json({error:"Upload 1-5000 records and confirm the list is complete."},400);
    const types=new Set(["customer","dnc","existing_contact","active_deal"]),unique=new Map<string,any>();
    for(const row of rows){const name=String(row.entity_name||row.company||"").trim(),type=String(row.protection_type||row.type||"").trim(),domain=domainOf(String(row.domain||row.website||"")),email=norm(String(row.email||""));if(!name||!types.has(type))return json({error:"Each record needs an entity_name and a valid type: customer, dnc, existing_contact, or active_deal."},400);const key=[type,domain,email,name.toLowerCase()].join("|");unique.set(key,{entity_name:name,normalized_domain:domain||null,normalized_email:email||null,protection_type:type,source_ref:"operator_import"})}
    const items=[...unique.values()];const ins=await supabase.from("mf_protected_entities").insert(items);if(ins.error)throw ins.error;
    const state=await supabase.from("mf_system_state").update({protection_seeded:true,updated_at:new Date().toISOString()}).eq("id",true);if(state.error)throw state.error;
    return json({imported:items.length,protection_seeded:true,message:"Protection list loaded. Review blocked leads before changing their status."},201)
   }
   if(path.endsWith("/program-status")){
    const ids=new Set(["visual_factories","indeavor","dev_partners"]),statuses=new Set(["not_contacted","draft_saved","inquiry_sent","terms_received","eligible","registered","paused","not_eligible"]);
    if(!ids.has(input.id)||!statuses.has(input.status))return json({error:"Unsupported partner program or status."},400);
    const r=await supabase.from("mf_partner_registry").update({status:input.status,fee_notes:String(input.fee_notes||"").slice(0,2000),contact_email:String(input.contact_email||"").slice(0,200),updated_at:new Date().toISOString()}).eq("id",input.id).select("id,status,fee_notes,contact_email,updated_at").single();if(r.error)throw r.error;return json({program:r.data})
   }
  if(path.endsWith("/leads")){
   const company=String(input.company||"").trim(), program=String(input.program||""), fitReason=String(input.fitReason||"").trim();
   if(!company||!fitReason||!(["Visual Factories","Indeavor","Dev Partners"].includes(program)))return json({error:"\uD68C\uC0AC, \uD504\uB85C\uADF8\uB7A8, \uC801\uD569 \uADFC\uAC70\uB97C \uD655\uC778\uD558\uC138\uC694."},400);
   const email=norm(String(input.email||"")), domain=domainOf(String(input.website||"")), companyKey=company.toLowerCase().replace(/[%,()]/g,"");
   const state=await supabase.from("mf_system_state").select("protection_seeded").eq("id",true).single();if(state.error)throw state.error;
   const [sameR,protectedR]=await Promise.all([
    supabase.from("mf_leads").select("id,company,program").or([domain?`normalized_domain.eq.${domain}`:"",email?`normalized_email.eq.${email}`:"",`company.ilike.${companyKey}`].filter(Boolean).join(",")).limit(1),
    supabase.from("mf_protected_entities").select("id,protection_type,entity_name").or([domain?`normalized_domain.eq.${domain}`:"",email?`normalized_email.eq.${email}`:"",`entity_name.ilike.${companyKey}`].filter(Boolean).join(",")).limit(1)
   ]);
   if(sameR.error)throw sameR.error;if(protectedR.error)throw protectedR.error;
   let review=state.data.protection_seeded?"eligible":"needs_review";if(sameR.data?.length)review="duplicate";
   const protection=protectedR.data?.[0];if(protection)review=protection.protection_type==="dnc"?"dnc":"protected";
   const ins=await supabase.from("mf_leads").insert({company,normalized_domain:domain||null,normalized_email:email||null,contact_email:email||null,website:input.website||null,country:input.country||null,program,fit_reason:fitReason,source:input.source||null,reward_terms:input.rewardTerms||null,review_status:review,stage:review==="eligible"?"registration_draft":"identified",registration_data:{external_submission_allowed:false}}).select("id,review_status,stage").single();
   if(ins.error)throw ins.error;
   if(review==="eligible")for(const engine of ["REFERRAL ENGINE","CASH ENGINE","Revenue Race"]){const eventKey=`money-finder:${ins.data.id}:${engine}:qualified`;const out=await supabase.from("mf_engine_outbox").upsert({lead_id:ins.data.id,event_key:eventKey,target_engine:engine,event_type:"qualified_lead_prepared",payload:{program,company,review_status:review},approval_required:true},{onConflict:"event_key",ignoreDuplicates:true});if(out.error)throw out.error}
   return json({lead:ins.data,message:review==="eligible"?"Eligible draft saved. External submission remains disabled.":`Registration paused by protection policy: ${review}`},201)
  }
  if(path.endsWith("/research")){
   const title=String(input.title||"").trim(),question=String(input.question||"").trim();if(!title||!question)return json({error:"Research title and question are required."},400);
   const r=await supabase.from("mf_research_tasks").insert({title,question,output_format:String(input.format||"Summary memo"),status:"queued"}).select("id,title,status").single();if(r.error)throw r.error;return json({task:r.data},201)
  }
  if(path.endsWith("/research-result")){
   const id=String(input.id||""),output=String(input.outputMarkdown||"").trim(),sources=Array.isArray(input.sources)?input.sources:[];
   if(!id||!output)return json({error:"Task id and research output are required."},400);
   const r=await supabase.from("mf_research_tasks").update({output_markdown:output,sources,status:"needs_review",updated_at:new Date().toISOString()}).eq("id",id).select("id,title,status,output_markdown,sources").single();if(r.error)throw r.error;return json({task:r.data})
  }
  if(path.endsWith("/rewards")){
   const leadId=String(input.leadId||"");if(!leadId)return json({error:"Lead ID is required."},400);
   const allowed=["potential","qualified","earned","payable","paid","disputed"];if(!allowed.includes(input.status))return json({error:"Unsupported reward status."},400);
   const lead=await supabase.from("mf_leads").select("id,review_status").eq("id",leadId).maybeSingle();if(lead.error)throw lead.error;if(!lead.data)return json({error:"Lead not found."},404);
   if(lead.data.review_status!=="eligible")return json({error:"Rewards cannot be tracked for duplicate, DNC, protected, or unreviewed leads."},409);
   const r=await supabase.from("mf_rewards").insert({lead_id:leadId,status:input.status,amount:input.amount===""||input.amount==null?null:Number(input.amount),currency:String(input.currency||"USD").toUpperCase(),evidence:String(input.evidence||""),approval_required:true}).select("id,status,lead_id").single();if(r.error)throw r.error;return json({reward:r.data},201)
  }
  return json({error:"Not found"},404)
 }catch(e){console.error(e);return json({error:e.message||"\uC694\uCCAD \uCC98\uB9AC \uC2E4\uD328"},500)}
});
