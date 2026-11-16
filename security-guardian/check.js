(() => {
  'use strict';
  const form = document.getElementById('quickcheck-form');
  const field = document.getElementById('quickcheck-domain');
  const button = document.getElementById('quickcheck-submit');
  const summary = document.getElementById('quickcheck-summary');
  const results = document.getElementById('quickcheck-results');
  const checkedAt = document.getElementById('quickcheck-time');
  const detail = document.getElementById('quickcheck-detail');
  function normalize(value) {
    const raw = value.trim();
    if (!raw || raw.length > 300 || /[\s@?#]/.test(raw)) throw Error('도메인 이름만 입력해 주세요. 예: example.com');
    let parsed;
    try { parsed = new URL(/^[a-z]+:\/\//i.test(raw) ? raw : 'https://' + raw); } catch { throw Error('올바른 도메인을 입력해 주세요.'); }
    if (!['http:', 'https:'].includes(parsed.protocol) || parsed.username || parsed.password || parsed.port || (parsed.pathname !== '/' && parsed.pathname !== '') || parsed.search || parsed.hash) throw Error('도메인 이름만 입력해 주세요. 경로와 포트는 지원하지 않습니다.');
    let host = parsed.hostname.toLowerCase().replace(/\.$/, '');
    const labels = host.split('.');
    if (host.length > 253 || labels.length < 2 || !labels.every(s => s.length >= 1 && s.length <= 63 && /^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$/.test(s)) || !/[a-z]/.test(labels.at(-1))) throw Error('공개 도메인 이름을 입력해 주세요.');
    return host;
  }
  const stripTxt = s => String(s || '').replace(/"\s*"/g, '').replace(/^"|"$/g, '');
  function timeoutFetch(url) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 10000);
    return fetch(url, {signal: controller.signal, headers:{Accept:'application/json'}, cache:'no-store'})
      .then(async r => { if (!r.ok) throw Error('DNS 서비스 응답 오류'); const j = await r.json(); if (j.Status !== 0 && j.Status !== 3) throw Error('DNS 조회 실패'); return j; })
      .finally(() => clearTimeout(timer));
  }
  async function query(name,type) {
    const url = 'https://dns.google/resolve?name=' + encodeURIComponent(name) + '&type=' + encodeURIComponent(type) + '&edns_client_subnet=0.0.0.0/0';
    const data = await timeoutFetch(url);
    return (data.Answer || []).filter(x => x.type === ({TXT:16,MX:15,CAA:257,DS:43}[type])).map(x => String(x.data || ''));
  }
  const statusLabels = {good:'양호',warn:'개선 권장',info:'참고',unknown:'확인 불가'};
  function line(title,state,description,evidence) {
    const outer=document.createElement('div'); outer.className='check-row';
    const heading=document.createElement('div'); heading.className='check-head';
    const strong=document.createElement('strong'); strong.textContent=title;
    const pill=document.createElement('span'); pill.className='check-pill '+state; pill.textContent=statusLabels[state];
    heading.append(strong,pill);
    const desc=document.createElement('p'); desc.textContent=description;desc.className='muted check-desc';
    outer.append(heading,desc);
    if (evidence) { const small=document.createElement('p');small.className='check-evidence';small.textContent=evidence.slice(0,210);outer.append(small); }
    return outer;
  }
  const looksLikeNullMx = x => /^0\s+\.$/.test(x.trim());
  form.addEventListener('submit', async event => {
    event.preventDefault();
    results.replaceChildren();detail.hidden=true;checkedAt.textContent='';
    let domain;try {domain=normalize(field.value);} catch(e) {summary.textContent=e.message;return;}
    document.dispatchEvent(new CustomEvent('guardian:scan-start'));
    button.disabled=true;button.textContent='공개 DNS 확인 중...';
    summary.textContent=domain+'의 공개 DNS 레코드를 조회하고 있습니다. HTTPS 검사에서는 해당 웹서버에 HEAD 요청 1회가 발생합니다.';
    const specs=[['txt',domain,'TXT'],['dmarc','_dmarc.'+domain,'TXT'],['mx',domain,'MX'],['caa',domain,'CAA'],['ds',domain,'DS']];
    const outcomes=await Promise.allSettled(specs.map(([key,name,type])=>query(name,type)));
    const get=i => outcomes[i].status==='fulfilled' ? outcomes[i].value : null;
    let checked=0,good=0,warn=0,unknown=0;
    const add=(name,state,message,evidence='')=>{checked++;if(state==='good')good++;if(state==='warn')warn++;if(state==='unknown')unknown++;results.append(line(name,state,message,evidence));};
    const txt=get(0),dmarcTxt=get(1),mx=get(2),caa=get(3),ds=get(4);
    if(txt===null){add('SPF 이메일 발신 정책','unknown','DNS 조회에 실패했습니다. 잠시 후 다시 확인해 주세요.');}
    else { const spf=txt.map(stripTxt).filter(x=>/^v=spf1(?:\s|$)/i.test(x));
      if (spf.length>1) add('SPF 이메일 발신 정책','warn','SPF 레코드가 여러 개입니다. 구성 오류 가능성이 있습니다.',spf[0]);
      else if(spf.length===1) {
        const policy=spf[0];
        const tokens=policy.toLowerCase().split(/\s+/).slice(1);
        const all=tokens.find(x=>/^[+~?-]?all$/.test(x));
        if(all==='+all'||all==='all'||all==='?all') add('SPF 이메일 발신 정책','warn','SPF 정책이 존재하지만 전체 발신자를 허용하거나 중립 처리하는 종료 규칙입니다. 정책 강화가 필요합니다.',policy);
        else if(all==='~all') add('SPF 이메일 발신 정책','info','SPF 소프트페일(~all) 정책이 있습니다. 발신 시스템 검증 후 강화 가능성을 검토하세요.',policy);
        else if(all==='-all') add('SPF 이메일 발신 정책','good','SPF 제한 정책(-all)이 확인됩니다. 실제 발신 시스템과 포함 규칙은 별도 검증이 필요합니다.',policy);
        else add('SPF 이메일 발신 정책','info','SPF 레코드가 있지만 명확한 all 종료 규칙은 확인되지 않습니다. 정책 전문가 검토를 권장합니다.',policy);
      }
      else add('SPF 이메일 발신 정책','warn','SPF 정책을 찾지 못했습니다. 이메일 위조 방어 설정을 확인하세요.');
    }
    if(dmarcTxt===null){add('DMARC 이메일 인증 정책','unknown','DNS 조회에 실패했습니다.');}
    else {const records=dmarcTxt.map(stripTxt).filter(x=>/^v=dmarc1(?:\s|;|$)/i.test(x));
      if(records.length>1) add('DMARC 이메일 인증 정책','warn','DMARC 레코드가 여러 개입니다. 하나의 유효한 정책으로 정리해야 합니다.');
      else if(!records.length) add('DMARC 이메일 인증 정책','warn','DMARC 정책이 확인되지 않았습니다.');
      else {const policy=(records[0].match(/(?:^|;)\s*p\s*=\s*(none|quarantine|reject)\b/i)||[])[1];
        if(policy==='reject'||policy==='quarantine')add('DMARC 이메일 인증 정책','good','DMARC 차단 또는 격리 정책이 설정되어 있습니다. 실제 정렬·전달률은 별도 검증이 필요합니다.',records[0]);
        else if(policy==='none')add('DMARC 이메일 인증 정책','warn','DMARC 모니터링 정책(p=none)입니다. 보고서를 점검한 뒤 단계적 강화를 검토하세요.',records[0]);
        else add('DMARC 이메일 인증 정책','warn','DMARC 정책이 존재하지만 유효한 p= 설정을 확인하지 못했습니다.',records[0]);
      }
    }
    if(mx===null) add('메일 수신 설정(MX)','unknown','DNS 조회에 실패했습니다.');
    else if(mx.length===0) add('메일 수신 설정(MX)','info','MX 레코드가 없습니다. 이메일을 사용하지 않는 도메인일 수 있습니다.');
    else if(mx.every(looksLikeNullMx)) add('메일 수신 설정(MX)','info','메일 미수신을 뜻하는 Null MX 정책으로 보입니다.',mx[0]);
    else add('메일 수신 설정(MX)','good','메일 수신 대상이 설정되어 있습니다. 이것만으로 메일 보안이 보장되지는 않습니다.',mx[0]);
    if(caa===null) add('인증서 발급 제한(CAA)','unknown','DNS 조회에 실패했습니다.');
    else if(caa.length) add('인증서 발급 제한(CAA)','good','CAA 정책이 확인됩니다. 정책 내용과 상위 도메인 상속은 별도 검증이 필요합니다.',caa[0]);
    else add('인증서 발급 제한(CAA)','info','도메인에 직접 설정된 CAA 레코드가 보이지 않습니다. 상위 도메인의 설정은 확인하지 않았습니다.');
    if(ds===null) add('DNSSEC 위임 레코드(DS)','unknown','DNS 조회에 실패했습니다.');
    else if(ds.length) add('DNSSEC 위임 레코드(DS)','good','DS 레코드가 확인됩니다. 전체 DNSSEC 검증 성공을 의미하지는 않습니다.');
    else add('DNSSEC 위임 레코드(DS)','info','DS 레코드가 확인되지 않았습니다. 상위 도메인 위임 상태와 검증은 별도 확인이 필요합니다.');
    summary.textContent=domain+' 공개 DNS 점검 완료 · '+good+'개 양호 · '+warn+'개 개선 권장 · '+unknown+'개 확인 불가';
    checkedAt.textContent='조회 시각: '+new Date().toLocaleString('ko-KR')+' · 총 '+checked+'개 항목';
    detail.hidden=false;
    button.disabled=false;button.textContent='무료 보안 점검 시작';
    document.dispatchEvent(new CustomEvent('guardian:dns-done',{detail:{domain,good,warn,unknown}}));
  });
})();