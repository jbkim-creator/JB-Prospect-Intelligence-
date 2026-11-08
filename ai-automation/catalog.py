"""Strict catalog contract: KRW integer prices, VAT exclusive only."""
import json
import re
from pathlib import Path


def load_catalog(path):
    data = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if data.get('currency') != 'KRW' or data.get('vat_mode') != 'exclusive':
        raise ValueError('현재 단가표는 KRW / VAT 별도만 지원합니다. 포함가를 그대로 넣지 마세요.')
    if not isinstance(data.get('id'), str) or not data['id'].strip() or type(data.get('synthetic')) is not bool:
        raise ValueError('단가표 id와 synthetic 여부가 필요합니다.')
    products = data.get('products')
    if not isinstance(products, dict) or not 1 <= len(products) <= 1000:
        raise ValueError('상품은 1~1000개를 등록하세요.')
    for code, item in products.items():
        if not re.fullmatch(r'[A-Z0-9][A-Z0-9_-]{1,39}', code):
            raise ValueError('상품코드는 영문 대문자·숫자·하이픈·밑줄로 입력하세요.')
        if not isinstance(item, dict) or not isinstance(item.get('name'), str) or not item['name'].strip():
            raise ValueError('상품명이 필요합니다: ' + code)
        for key in ('print_each', 'setup'):
            if type(item.get(key)) is not int or not 0 <= item[key] <= 100000000:
                raise ValueError('인쇄비·판비는 0 이상의 정수여야 합니다: ' + code)
        tiers = item.get('tiers')
        if not isinstance(tiers, list) or not tiers:
            raise ValueError('수량구간이 필요합니다: ' + code)
        previous = 0
        for tier in tiers:
            if not isinstance(tier, list) or len(tier) != 2 or any(type(x) is not int for x in tier):
                raise ValueError('수량구간은 [최소수량, 단가] 정수 쌍입니다: ' + code)
            if not previous < tier[0] <= 100000 or not 0 <= tier[1] <= 100000000:
                raise ValueError('수량구간은 중복 없이 오름차순이고 단가는 음수가 아니어야 합니다: ' + code)
            previous = tier[0]
    return data
