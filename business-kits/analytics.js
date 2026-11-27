/* JBRO analytics adapter. GA4 analytics with optional visitor consent. */
(function(){
const id='G-F0EZXJ8M8M';
window.dataLayer=window.dataLayer||[];
window.jbroTrack=function(name,params){
 const query=new URLSearchParams(location.search);
 const details={...(params||{}),page_path:location.pathname};
 for(const key of ['utm_source','utm_medium','utm_campaign','utm_content']){
  const value=query.get(key);
  if(value)details[key]=value;
 }
 window.dataLayer.push({event:name,...details});
 if(typeof window.gtag==='function')window.gtag('event',name,details);
};
function enableAnalytics(){
 window['ga-disable-'+id]=false;
 if(window.gtag)return;
 if(!/^G-[A-Z0-9]+$/.test(id))return;
 const s=document.createElement('script');s.async=true;s.src='https://www.googletagmanager.com/gtag/js?id='+encodeURIComponent(id);document.head.appendChild(s);
 window.gtag=function(){window.dataLayer.push(arguments)};window.gtag('js',new Date());window.gtag('config',id,{send_page_view:true,allow_google_signals:false,allow_ad_personalization_signals:false});
}
document.addEventListener('DOMContentLoaded',()=>{
 let choice=null;
 try{choice=localStorage.getItem('jbro_analytics_consent_v1')}catch(_){}
 if(choice==='yes')enableAnalytics();
 const panel=document.createElement('section');
 panel.setAttribute('aria-label','방문 통계 설정');
 panel.style.cssText='max-width:980px;margin:12px auto;padding:16px;border:1px solid #35546a;border-radius:10px;color:inherit;background:inherit;font-size:14px';
 function setChoice(value){
  try{localStorage.setItem('jbro_analytics_consent_v1',value)}catch(_){}
  if(value==='yes'){enableAnalytics();panel.hidden=true}
  else {window['ga-disable-'+id]=true;panel.hidden=true;if(window.gtag)location.reload()}
 }
 const text=document.createElement('p');text.textContent='서비스 개선을 위해 Google Analytics 방문 통계를 사용할 수 있습니다. 동의하지 않아도 무료 도구를 이용할 수 있습니다. 계산 입력값은 분석 이벤트로 보내지 않습니다.';
 panel.appendChild(text);
 [['동의','yes'],['거부','no']].forEach(([label,value])=>{const b=document.createElement('button');b.textContent=label;b.style.cssText='padding:8px 16px;margin-right:8px;border:1px solid #4b5d73;border-radius:6px;cursor:pointer';b.addEventListener('click',()=>setChoice(value));panel.appendChild(b)});
 document.body.appendChild(panel);panel.hidden=choice==='yes'||choice==='no';
 const settings=document.createElement('button');settings.textContent='방문 통계 설정';settings.style.cssText='display:block;margin:8px auto 20px;padding:6px 10px;cursor:pointer';settings.addEventListener('click',()=>{panel.hidden=!panel.hidden});document.body.appendChild(settings);
});
document.addEventListener('DOMContentLoaded',()=>{
 const params=new URLSearchParams(location.search);
 const campaign=params.get('utm_campaign')||'';
 const source=params.get('utm_source')||'';
 const content=params.get('utm_content')||'';
 // Preserve attribution in links between our own HTML pages without cookies or storage.
 if(source || content || campaign){
  document.querySelectorAll('a[href]').forEach(a=>{
   if(a.href.startsWith('mailto:')) return;
   try {
    const dest=new URL(a.href,location.href);
    if(dest.origin!==location.origin || !/\.html$/.test(dest.pathname))return;
    ['utm_source','utm_medium','utm_campaign','utm_content'].forEach(k=>{
     const v=params.get(k);
     if(v && !dest.searchParams.has(k))dest.searchParams.set(k,v);
    });
    a.href=dest.href;
   }catch(_){}
  });
 }
 // Leave mailto links untouched: URLSearchParams serializes spaces as '+',
 // which Gmail's mailto handler may display literally. Attribution remains
 // available through the consented purchase_interest_email_click event.

});
document.addEventListener('click',function(e){
 const a=e.target.closest('a');if(!a)return;
 if(a.dataset.trackEvent==='dp001_sample_download')window.jbroTrack('dp001_sample_download',{item_id:'DP-001'});
 else if(a.dataset.trackEvent==='dp001_purchase_inquiry_click')window.jbroTrack('dp001_purchase_inquiry_click',{item_id:'DP-001'});
 else if(a.href.includes('JBRO_Free_Quote_Sample.csv'))window.jbroTrack('sample_download',{file_name:'JBRO_Free_Quote_Sample.csv'});
 else if(a.hostname==='open.kakao.com')window.jbroTrack('kakao_contact_click');
 else if(a.hostname==='www.instagram.com'||a.hostname==='instagram.com')window.jbroTrack('instagram_profile_click');
 else if(a.href.startsWith('mailto:'))window.jbroTrack('purchase_interest_email_click',{link_text:(a.textContent||'').trim()});
 else if(/(?:free-quote|target-price|fx-breakeven|import-landed-cost|sales-commission|order-breakeven)-calculator\.html/.test(a.href))window.jbroTrack('calculator_link_click',{link_text:(a.textContent||'').trim()});
 else if(a.href.includes('free-trade-tools.html'))window.jbroTrack('tools_directory_click');
 else if(a.href.includes('index.html'))window.jbroTrack('product_details_click',{link_text:(a.textContent||'').trim()});
});
document.addEventListener('DOMContentLoaded',()=>{
 const fields=document.querySelectorAll('input[type=number]');
 if(fields.length){let once=false;fields.forEach(el=>el.addEventListener('input',()=>{if(!once){once=true;window.jbroTrack('calculator_used')}}))}
});
})();