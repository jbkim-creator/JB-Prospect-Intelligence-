(()=>{'use strict';
const $=id=>document.getElementById(id);
const kinds={
 buyer:{name:'바이어',help:'제품과 진출하려는 국가를 알려주세요.',country:'대상 국가 *',qty:'판매 가능 수량 (선택)',time:'희망 조사 일정 (선택)',required:['product','country']},
 stock:{name:'산업설비·재고 매각',help:'판매 권한이 있는 자산의 모델·수량·출고 가능일을 적고, 추가 조건에 상태·보관 위치·희망가격을 알려주세요.',country:'보관 국가·지역 (선택)',qty:'가용 수량 *',time:'출고 가능일 *',required:['product','quantity','timing']},
 sourcing:{name:'설비·부품 구매',help:'모델 또는 필수 사양·수량·도입 일정·납품 국가를 알려주세요.',country:'납품 국가 *',qty:'요청 수량 *',time:'희망 납기 *',required:['product','country','quantity','timing']}
};
const params=new URLSearchParams(location.search);
const kind=$('kind');kind.value=kinds[params.get('type')]?params.get('type'):'stock';
function track(name){if(typeof window.jbroTrack==='function')window.jbroTrack(name,{inquiry_type:kind.value});}
function configure(){const k=kinds[kind.value];$('help').textContent=k.help;$('country-label').textContent=k.country;$('quantity-label').textContent=k.qty;$('timing-label').textContent=k.time;for(const id of ['product','country','quantity','timing'])$(id).required=k.required.includes(id);$('send').hidden=true;const u=new URL(location.href);u.searchParams.set('type',kind.value);history.replaceState(null,'',u);track('inquiry_type_selected');}
kind.addEventListener('change',configure);configure();
$('inquiry').addEventListener('input',()=>{$('send').hidden=true;});
$('inquiry').addEventListener('submit',e=>{e.preventDefault();if(!$('inquiry').reportValidity())return;const k=kinds[kind.value];const lines=['['+k.name+' 상담]','품목·품번: '+$('product').value.trim(),k.country.replace(' *','')+': '+($('country').value.trim()||'협의'),k.qty.replace(' *','')+': '+($('quantity').value.trim()||'협의'),k.time.replace(' *','')+': '+($('timing').value.trim()||'협의')];if($('details').value.trim())lines.push('추가 조건: '+$('details').value.trim());lines.push('보고 온 영상: '+(params.get('episode')&&/^00[4-9]$/.test(params.get('episode'))?'EP.'+params.get('episode'):'직접 기재'),'조사·중개 범위와 비용·보수를 먼저 안내해 주세요.');const text=lines.join('\n');$('message').value=text;$('email').href='mailto:jbkim@jbrocap.com?subject='+encodeURIComponent('JBRO '+k.name+' 상담')+'&body='+encodeURIComponent(text);$('send').hidden=false;$('status').textContent='문구가 준비됐습니다. 복사 후 상담 채널에서 직접 전송해 주세요.';track('inquiry_text_prepared');$('send').scrollIntoView({behavior:'smooth',block:'start'});});
$('copy').addEventListener('click',async()=>{try{await navigator.clipboard.writeText($('message').value);$('status').textContent='복사했습니다. 카카오톡을 열고 붙여넣어 직접 보내주세요.';track('inquiry_text_copied');}catch(_){$('message').focus();$('message').select();$('status').textContent='자동 복사를 사용할 수 없습니다. 선택된 문구를 직접 복사해 주세요.';}});
$('kakao').addEventListener('click',()=>track('inquiry_kakao_open'));
$('email').addEventListener('click',()=>track('inquiry_email_open'));
})();