"""Local desktop demo. No network, no email account connection."""
import hashlib
from email.message import EmailMessage
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from automation import build, run_raw
from catalog import load_catalog

SAMPLES = {
    '정상 요청': 'DEMO-T01 300개 인쇄: 1도\nDEMO-P01 500개 인쇄: 없음\n납기: 2026-11-30',
    '인쇄 조건 누락': 'DEMO-T01 300개\n납기: 2026-11-30',
    '최소수량 미달': 'DEMO-T01 20개 인쇄: 없음\n납기: 2026-11-30',
    '상품 불명확': '텀블러 300개, 로고 인쇄 희망\n납기: 2026-11-30',
}


def as_email(body):
    if len(body.encode('utf-8')) > 50000:
        raise ValueError('붙여넣기 본문은 UTF-8 기준 50KB 이내로 입력해 주세요.')
    message = EmailMessage()
    fingerprint = hashlib.sha256(body.encode('utf-8')).hexdigest()
    message['Message-ID'] = f'<paste-{fingerprint}@example.invalid>'
    message.set_content(body, charset='utf-8')
    return message.as_string()


def display_money(value):
    return '검토 보류' if value is None else f'{value:,}원'


class DemoApp:
    def __init__(self, root):
        self.root = root
        root.title('JB AI Automation | 견적 검토 데모')
        root.geometry('1120x760')
        root.minsize(850, 650)
        self.result = None
        self.reviewed_body = None
        self.catalog_options = {}
        shell = ttk.Frame(root, padding=24)
        shell.pack(fill='both', expand=True)
        ttk.Label(shell, text='메일 문의를 견적 검토본으로', font=('Malgun Gothic', 20, 'bold')).pack(anchor='w')
        ttk.Label(shell, text='규칙 기반 · 가상 단가표 · 외부 전송 없음', foreground='#1b6664').pack(anchor='w', pady=(4, 12))
        ttk.Label(shell, text='합성 샘플로 시연하세요. 실제 고객의 이름·주소·연락처·기밀은 입력 전에 제거하세요.').pack(anchor='w')
        toolbar = ttk.Frame(shell)
        toolbar.pack(fill='x', pady=12)
        self.sample = ttk.Combobox(toolbar, values=list(SAMPLES), state='readonly', width=24)
        self.sample.set('정상 요청')
        self.sample.pack(side='left')
        ttk.Button(toolbar, text='샘플 불러오기', command=self.load_sample).pack(side='left', padx=8)
        ttk.Button(toolbar, text='견적 검토하기', command=self.analyze).pack(side='left')
        ttk.Button(toolbar, text='단가표 불러오기', command=self.select_catalog).pack(side='left', padx=8)
        ttk.Button(toolbar, text='결과 저장', command=self.save).pack(side='right')
        ttk.Label(shell, text='본문 입력 — 예: DEMO-T01 300개 인쇄: 1도 / 납기: YYYY-MM-DD').pack(anchor='w')
        self.input = tk.Text(shell, height=8, wrap='word', font=('Malgun Gothic', 11), undo=True)
        self.input.pack(fill='x', pady=(6, 12))
        self.status = tk.StringVar(value='샘플을 불러온 뒤 견적 검토하기를 누르세요.')
        ttk.Label(shell, textvariable=self.status, font=('Malgun Gothic', 12, 'bold'), wraplength=1000).pack(anchor='w', pady=6)
        columns = ('product', 'quantity', 'unit_price', 'print_each', 'setup', 'net')
        self.table = ttk.Treeview(shell, columns=columns, show='headings', height=5)
        for key, label in zip(columns, ('상품', '수량', '상품 단가', '개당 인쇄비', '판비', '품목 공급가')):
            self.table.heading(key, text=label)
            self.table.column(key, width=140, anchor='e' if key != 'product' else 'w')
        self.table.pack(fill='both', expand=True)
        self.totals = tk.StringVar(value='')
        ttk.Label(shell, textvariable=self.totals, font=('Malgun Gothic', 12)).pack(anchor='w', pady=10)
        self.notes = tk.StringVar(value='')
        ttk.Label(shell, textvariable=self.notes, wraplength=1000, foreground='#8a4e09').pack(anchor='w')
        ttk.Label(shell, text='재고·납기·배송비·단가표 유효성은 담당자가 확인합니다. 저장 결과는 확정 주문이 아닙니다.').pack(anchor='w', pady=(10, 0))
        self.load_sample()

    def load_sample(self):
        self.input.delete('1.0', 'end')
        self.input.insert('1.0', SAMPLES[self.sample.get()])
        self.result = None
        self.reviewed_body = None
        for item in self.table.get_children():
            self.table.delete(item)
        self.status.set('샘플 입력 완료 · 견적 검토하기를 누르세요.')
        self.totals.set('')
        self.notes.set('')

    def analyze(self):
        try:
            body = self.input.get('1.0', 'end-1c').strip()
            result = build(as_email(body), **self.catalog_options)
        except (ValueError, UnicodeError) as error:
            self.result = None
            messagebox.showerror('입력 확인', str(error), parent=self.root)
            return
        self.result, self.reviewed_body = result, body
        for item in self.table.get_children():
            self.table.delete(item)
        for item in result['items']:
            self.table.insert('', 'end', values=(item['product'], item['quantity'], *[f"{item[k]:,}" for k in ('unit_price', 'print_each', 'setup', 'net')]))
        self.status.set('조건 누락 · 전체 견적 합계 보류' if result['status'] == 'BLOCKED' else '견적 초안 생성 · 담당자 검토 필요')
        self.totals.set(f"공급가 {display_money(result['net'])}   VAT {display_money(result['vat'])}   합계 {display_money(result['total'])} (배송비 제외)")
        self.notes.set(' / '.join(result['issues']) or '단가표·재고·시안·납기·배송비 확인 후 실제 견적을 확정하세요.')

    def save(self):
        body = self.input.get('1.0', 'end-1c').strip()
        if self.result is None or body != self.reviewed_body:
            messagebox.showinfo('다시 검토', '현재 본문으로 견적 검토하기를 먼저 눌러 주세요.', parent=self.root)
            return
        folder = filedialog.askdirectory(title='검토 결과를 저장할 폴더 선택', parent=self.root)
        if not folder:
            return
        try:
            directory, _ = run_raw(as_email(body), Path(folder), **self.catalog_options)
        except (ValueError, OSError) as error:
            messagebox.showerror('저장 확인', str(error), parent=self.root)
            return
        messagebox.showinfo('저장 완료', f'{directory}\n\n견적 HTML · 구조화 JSON · 주문 CSV를 저장했습니다.\n같은 본문은 같은 폴더에 중복 저장하지 않습니다.', parent=self.root)

    def select_catalog(self):
        path = filedialog.askopenfilename(title='승인된 JSON 단가표 선택', filetypes=[('JSON 단가표', '*.json')], parent=self.root)
        if not path:
            return
        try:
            data = load_catalog(path)
        except (ValueError, OSError) as error:
            messagebox.showerror('단가표 오류', str(error), parent=self.root)
            return
        self.catalog_options = {'catalog': data['products'], 'catalog_id': data['id'], 'synthetic': data['synthetic']}
        self.result = None
        self.reviewed_body = None
        self.status.set('단가표 변경: ' + data['id'] + ' · 본문을 다시 검토하세요.')
        for row in self.table.get_children():
            self.table.delete(row)
        self.totals.set('')
        self.notes.set('상품코드는 불러온 단가표의 코드를 사용하세요. VAT 별도 원화 단가만 지원합니다.')


if __name__ == '__main__':
    window = tk.Tk()
    ttk.Style().theme_use('clam')
    DemoApp(window)
    window.mainloop()
