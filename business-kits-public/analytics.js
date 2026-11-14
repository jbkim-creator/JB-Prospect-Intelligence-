/* JBRO analytics adapter. No transmission until a GA4 measurement ID is configured. */
(function(){
const id=window.JBRO_GA4_ID || '';
window.dataLayer=window.dataLayer||[];
window.jbroTrack=function(name,params){
 const event={event:name,...(params||{}),page_path:location.pathname,utm_source:new URLSearchParams(location.search).get('utm_source')||'',utm_content:new URLSearchParams(location.search).get('utm_content')||''};
 window.dataLayer.push(event);
 if(id && typeof window.gtag==='function') window.gtag('event',name,params||{});
};
if(id && /^G-[A-Z0-9]+$/.test(id)){
 const s=document.createElement('script');s.async=true;s.src='https://www.googletagmanager.com/gtag/js?id='+encodeURIComponent(id);document.head.appendChild(s);
 window.gtag=function(){window.dataLayer.push(arguments)};window.gtag('js',new Date());window.gtag('config',id,{send_page_view:true});
}
document.addEventListener('click',function(e){
 const a=e.target.closest('a');if(!a)return;
 if(a.href.includes('JBRO_Free_Quote_Sample.csv'))window.jbroTrack('sample_download',{file_name:'JBRO_Free_Quote_Sample.csv'});
 else if(a.href.startsWith('mailto:'))window.jbroTrack('purchase_interest_email_click',{link_text:(a.textContent||'').trim()});
 else if(a.href.includes('free-quote-calculator.html'))window.jbroTrack('calculator_link_click',{link_text:(a.textContent||'').trim()});
 else if(a.href.includes('index.html'))window.jbroTrack('product_details_click',{link_text:(a.textContent||'').trim()});
});
document.addEventListener('DOMContentLoaded',()=>{
 const fields=document.querySelectorAll('input[type=number]');
 if(fields.length){let once=false;fields.forEach(el=>el.addEventListener('input',()=>{if(!once){once=true;window.jbroTrack('calculator_used')}}))}
});
})();