"""Offline pilot: email text -> reviewable quote -> order CSV. No network or sending.

Explicit product codes only; catalog prices are synthetic, VAT-exclusive demo data.
Unstructured/ambiguous requests are held for human review, never guessed.
"""
import argparse
import csv
import hashlib
import html
import json
import re
from decimal import Decimal, ROUND_HALF_UP
from email import policy
from email.parser import BytesParser
from pathlib import Path

CATALOG = {
    'DEMO-T01': {'name': '데모 텀블러', 'tiers': [(100, 5000), (300, 4700)], 'print_each': 300, 'setup': 30000},
    'DEMO-P01': {'name': '데모 볼펜', 'tiers': [(100, 800), (500, 700)], 'print_each': 100, 'setup': 10000},
}


def money(n):
    return int(Decimal(str(n)).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def mask(text):
    text = re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', '[EMAIL]', text)
    text = re.sub(r'(?<!\d)01[016789][- .]?\d{3,4}[- .]?\d{4}(?!\d)', '[PHONE]', text)
    return text


def parse_email(raw):
    message = BytesParser(policy=policy.default).parsebytes(raw.encode('utf-8'))
    if message.is_multipart():
        part = message.get_body(preferencelist=('plain',))
        if part is None:
            raise ValueError('HTML-only MIME is unsupported; provide plain text.')
        text = part.get_content()
    else:
        if message.get_content_type() != 'text/plain':
            raise ValueError('Only plain text email is supported.')
        text = message.get_content()
    # Exclude quoted replies so old requests cannot become new order rows.
    text = re.split(r'(?m)^>.*|^-----Original Message-----|^On .+wrote:', text)[0]
    return message, text


def build(raw):
    message, body = parse_email(raw)
    issues, lines = [], []
    # Deliberately small deterministic extraction; a future LLM adapter is separate.
    for source in body.splitlines():
        codes = re.findall(r'\bDEMO-[A-Z]\d{2}\b', source)
        quantities = re.findall(r'(?<![\d.,])([+-]?\d[\d,]*)\s*개', source)
        if not codes:
            if quantities:
                issues.append('상품코드 없는 수량 요청: ' + mask(source))
            continue
        if len(codes) != 1 or len(quantities) != 1:
            issues.append('상품 또는 수량 모호: ' + mask(source))
            continue
        if not re.fullmatch(r'(?:[1-9]\d*|[1-9]\d{0,2}(?:,\d{3})+)', quantities[0]):
            issues.append('수량 표기 오류: ' + mask(source))
            continue
        code, qty = codes[0], int(quantities[0].replace(',', ''))
        if code not in CATALOG or qty <= 0 or qty > 100000:
            issues.append('미등록 상품 또는 수량 범위 오류: ' + mask(source))
            continue
        item = CATALOG[code]
        tiers = [price for threshold, price in item['tiers'] if qty >= threshold]
        if not tiers:
            issues.append('최소수량 미달: ' + code)
            continue
        printing = re.search(r'인쇄\s*:\s*(없음|1도)', source)
        if not printing:
            issues.append('인쇄 옵션 확인 필요: ' + code)
            continue
        printed = printing.group(1) == '1도'
        unit = tiers[-1]
        print_each = item['print_each'] if printed else 0
        setup = item['setup'] if printed else 0
        lines.append({'code': code, 'product': item['name'], 'quantity': qty,
                      'unit_price': unit, 'print_each': print_each, 'setup': setup,
                      'net': qty * (unit + print_each) + setup,
                      'source': mask(source)})
    if not lines:
        issues.append('계산 가능한 품목 없음')
    dates = re.findall(r'납기\s*:\s*(\d{4}-\d{2}-\d{2})', body)
    requested_date = dates[0] if len(set(dates)) == 1 else None
    if not requested_date:
        issues.append('요청 납기 확인 필요')
    elif requested_date:
        from datetime import date
        try:
            date.fromisoformat(requested_date)
        except ValueError:
            issues.append('유효하지 않은 납기')
            requested_date = None
    # A partial price must never masquerade as a complete quote.
    net = sum(x['net'] for x in lines) if not issues else None
    vat = money(Decimal(net) * Decimal('0.10')) if net is not None else None
    key = str(message.get('Message-ID', '')).strip() or hashlib.sha256(raw.encode()).hexdigest()
    return {'schema': 1, 'request_id': hashlib.sha256(key.encode()).hexdigest()[:20],
            'status': 'BLOCKED' if issues else 'REVIEW_REQUIRED',
            'catalog': 'SYNTHETIC-DEMO-v1', 'requested_delivery': requested_date,
            'delivery_confirmed': False, 'stock_confirmed': False,
            'issues': issues, 'items': lines, 'net': net, 'vat': vat,
            'total': net + vat if net is not None else None,
            'shipping': '미산정 · 별도 확인', 'automatic_send': False}


def csv_safe(value):
    value = str(value)
    return "'" + value if value.lstrip().startswith(('=', '+', '-', '@')) else value


def export(result, directory):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'quote.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    headers = ['status', 'request_id', 'code', 'product', 'quantity', 'unit_price', 'print_each', 'setup', 'net', 'requested_delivery']
    with (directory / 'order.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for line in result['items']:
            row = {**result, **line}
            writer.writerow([csv_safe(row.get(k, '')) for k in headers])
    esc = lambda x: html.escape(str(x))
    rows = ''.join('<tr>' + ''.join('<td>' + esc(x[k]) + '</td>' for k in ['product', 'quantity', 'unit_price', 'print_each', 'setup', 'net']) + '</tr>' for x in result['items'])
    quote = f'''<!doctype html><html lang="ko"><meta charset="utf-8"><title>JB 견적 검토본</title>
<style>body{{font:16px system-ui;max-width:1000px;margin:48px auto;color:#183047}}h1{{color:#135d61}}table{{border-collapse:collapse;width:100%}}td,th{{padding:14px;border-bottom:1px solid #ccd8df;text-align:left}}aside{{background:#fff1cf;padding:18px}}small{{color:#536a78}}</style>
<h1>JB AI Automation · 견적 검토본</h1><aside>합성 데이터 데모 / {esc(result['status'])} / 확정 주문이 아닙니다. 재고·납기·배송비는 담당자 확인이 필요합니다.</aside>
<p>요청 ID {esc(result['request_id'])} · 요청 납기 {esc(result['requested_delivery'])}</p>
<table><tr><th>상품</th><th>수량</th><th>단가</th><th>개당 인쇄비</th><th>판비</th><th>공급가</th></tr>{rows}</table>
<p>공급가 {esc(result['net'])}원 · VAT {esc(result['vat'])}원 · 합계 {esc(result['total'])}원 (배송비 미포함)</p>
<p>검토사항: {esc(' / '.join(result['issues']) or '단가표 유효성, 재고, 시안, 납기, 배송비 승인')}</p>
<small>가격은 실제 업체 가격이 아닌 가상 단가표입니다. 이메일·거래처 데이터 외부 전송 없음.</small></html>'''
    (directory / 'quote.html').write_text(quote, encoding='utf-8')


def run(input_file, out):
    raw = Path(input_file).read_text(encoding='utf-8')
    return run_raw(raw, out)


def run_raw(raw, out):
    if len(raw.encode('utf-8')) > 100000:
        raise ValueError('100KB limit; attachments are not processed.')
    result = build(raw)
    directory = Path(out) / result['request_id']
    # Persisted idempotency: same Message-ID cannot create a second order.
    directory.parent.mkdir(parents=True, exist_ok=True)
    try:
        directory.mkdir()
    except FileExistsError:
        raise ValueError('Duplicate request ID: output already exists; no new order created.')
    export(result, directory)
    return directory, result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', help='UTF-8 plain text .eml')
    parser.add_argument('--out', default='outputs')
    args = parser.parse_args()
    try:
        directory, result = run(args.input, args.out)
        print(json.dumps({'directory': str(directory), 'status': result['status'], 'total': result['total']}, ensure_ascii=False))
    except (ValueError, OSError) as e:
        parser.exit(2, str(e) + '\n')
