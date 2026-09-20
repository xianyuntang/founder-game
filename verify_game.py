"""Check every citation in founder-game/index.html against the two playbooks.

The game hand-authors its question bank, so a wrong 人數, a case ID pasted from
the neighbouring pattern, or an invented founder quote would be invisible to a
reader. This checks all of it. Balance is NOT checked here -- that lives in the
page itself at index.html#selftest, so it can reuse the real settle().

    python3 verify_game.py            # 檢查預設路徑
    python3 verify_game.py --demo     # 只跑自我檢查
"""
import argparse, json, re, sys, tempfile, pathlib

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / 'data'
GAME = HERE / 'index.html'
FAIL_BOOK = DATA / 'playbook.md'
WIN_BOOK = DATA / 'success-playbook.md'
UPGRADE = DATA / 'upgrade-rate.json'

BANK_RE = re.compile(r'<script type="application/json" id="bank">(.*?)</script>', re.S)
CASE_ID_RE = re.compile(r'1[a-z0-9]+:[FC]\d+')


def load_bank(html_path):
    m = BANK_RE.search(html_path.read_text(encoding='utf-8'))
    if not m:
        raise SystemExit(f'{html_path}: 找不到 <script id="bank">')
    return json.loads(m.group(1))


def index_book(text):
    """{(章節, 模式N): (標題, 區塊文字)} — 章節取 '## ' 後第一段，模式取 '### 模式N：標題'."""
    # 兩本手冊的章節標題長得不一樣：失敗手冊是「## 需求／價值不足 demand_value」或
    # 「## AI 時代的失敗情境」，成功手冊是「## 驗證：怎麼找到真問題與願意付錢的人」。
    out = {}
    for part in re.split(r'\n(?=## )', text):
        head = re.match(r'## (.+)', part)
        if not head:
            continue
        chapter = re.sub(r'\s+[a-z_]+$', '', head.group(1).strip())
        chapter = re.split(r'[：:]', chapter)[0].strip()
        for block in re.split(r'\n(?=### 模式)', part):
            h = re.match(r'### (模式\d+)[：:](.+)', block)
            if h:
                out[(chapter, h.group(1))] = (h.group(2).strip(), block)
    return out


def lookup(idx, key):
    """成功手冊的章節標題是「產品與轉向」，但 upgrade-rate.json 與遊戲都叫它「產品」。"""
    if key in idx:
        return idx[key]
    ch, pat = key
    for (c, p), v in idx.items():
        if p == pat and c.startswith(ch):
            return v
    return None


def norm(s):
    """比對敘述時忽略空白與全半形差異 —— 這些是排版，不是內容。"""
    return re.sub(r'[\s,，、「」『』]', '', s)


def check(bank, fail_idx, win_idx, upgrade, say):
    failed = 0
    seen_refs = 0

    def bad(msg):
        nonlocal failed
        failed += 1
        say('FAIL  ' + msg)

    upmap = {(r['章節'], r['模式']): r for r in upgrade}

    for q in bank['questions']:
        for opt in q['options']:
            r = opt.get('src') or opt.get('ref')
            if not r:
                if opt['tier'] in ('bad', 'kill'):
                    bad(f"{q['id']} / {opt['tier']} 沒有 ref")
                continue
            seen_refs += 1
            is_win = bool(opt.get('src') and opt['src']['kind'] == 'success')
            idx = win_idx if is_win else fail_idx
            book = 'success-playbook.md' if is_win else 'playbook.md'
            key = (r['ch'], r['pat'])
            where = f"{q['id']} 〈{r['ch']} {r['pat']}〉"

            hit = lookup(idx, key)
            if not hit:
                bad(f'{where} 在 {book} 找不到這個模式')
                continue
            title, block = hit

            # 2. 標題逐字相符
            if r['name'] != title:
                bad(f'{where} 標題不符\n        game: {r["name"]}\n        book: {title}')

            # 3. 人數
            if is_win:
                row = upmap.get(key)
                if not row:
                    bad(f'{where} upgrade-rate.json 沒有這一列')
                else:
                    if r['n'] != row['人數']:
                        bad(f'{where} n={r["n"]}，upgrade-rate.json 是 {row["人數"]}')
                    if r.get('up') is not None and r['up'] != row['升級']:
                        bad(f'{where} up={r["up"]}，upgrade-rate.json 是 {row["升級"]}')
            else:
                m = re.search(r'出現次數\*\*[：:]\s*約\s*(\d+)\s*人', block)
                if not m:
                    bad(f'{where} 讀不到出現次數')
                elif r['n'] != int(m.group(1)):
                    bad(f'{where} n={r["n"]}，手冊是 {m.group(1)}')

            # 4. 案例 ID 必須出現在「這個模式自己的」區塊裡
            for cid, gist in r['cases']:
                if not CASE_ID_RE.fullmatch(cid):
                    bad(f'{where} 案例 ID 格式不對：{cid}')
                    continue
                want_f = cid.split(':')[1][0] == 'F'
                if want_f == is_win:
                    bad(f'{where} 案例 {cid} 的 F/C 前綴與引用的手冊不符')
                if cid not in block:
                    bad(f'{where} 案例 {cid} 不在這個模式的區塊裡')
                    continue
                # 7. gist 開頭必須在區塊裡找得到，擋掉改寫成手冊沒說的內容
                head = norm(gist)[:8]
                if head and head not in norm(block):
                    bad(f'{where} 案例 {cid} 的敘述開頭「{gist[:12]}」在區塊裡找不到')

            # 5. 加了「」的教訓必須逐字出自該區塊
            for quoted in re.findall(r'「([^」]{6,})」', opt.get('lesson') or ''):
                if norm(quoted) not in norm(block):
                    bad(f'{where} 引號內的教訓不在區塊裡：「{quoted[:24]}…」')

            # 6. caution 必須出自成功模式的區塊
            if r.get('caution') and norm(r['caution'])[:10] not in norm(block):
                bad(f'{where} caution 開頭在區塊裡找不到：{r["caution"][:20]}…')

    n_need = sum(1 for q in bank['questions'] for o in q['options']
                 if o['tier'] in ('bad', 'kill', 'good'))
    if seen_refs < n_need:
        bad(f'只讀到 {seen_refs} 個引用，但有 {n_need} 個 good/bad/kill 選項')

    say(f'\n題目 {len(bank["questions"])} 題 · 引用 {seen_refs} 個 · 失敗 {failed} 項')
    return failed


def demo():
    """自我檢查：乾淨的通過，每一種造假都要被抓到。"""
    book = ('## 需求／價值不足 demand_value\n\n'
            '### 模式1：閉門開發\n\n'
            '- **出現次數**：約 85 人（另有低信任 33 人）\n'
            '- **當事人教訓**：\n  - 「先驗證再開發」\n'
            '- **代表案例**：\n  - [1aaa:F1] 2026：做了六個月零用戶\n\n'
            '### 模式2：別的坑\n\n'
            '- **出現次數**：約 45 人\n'
            '- **代表案例**：\n  - [1bbb:F1] 2026：另一個故事\n')
    good = {'ch': '需求／價值不足', 'pat': '模式1', 'n': 85, 'name': '閉門開發',
            'cases': [['1aaa:F1', '做了六個月零用戶']]}

    def run(ref, lesson='「先驗證再開發」'):
        bank = {'questions': [{'id': 'q', 'options': [
            {'tier': 'bad', 'ref': ref, 'lesson': lesson},
            {'tier': 'good', 'src': dict(ref, kind='lesson'), 'lesson': ''},
            {'tier': 'ok'}, {'tier': 'ok'}]}]}
        return check(bank, index_book(book), {}, [], lambda _m: None)

    assert run(good) == 0, '乾淨的引用應該通過'
    assert run(dict(good, n=86)) > 0, '人數不符要被抓到'
    assert run(dict(good, name='別的標題')) > 0, '標題不符要被抓到'
    assert run(dict(good, cases=[['1bbb:F1', '另一個故事']])) > 0, '借用隔壁模式的案例要被抓到'
    assert run(dict(good, cases=[['1zzz:F1', '不存在']])) > 0, '不存在的案例要被抓到'
    assert run(dict(good, cases=[['1aaa:F1', '手冊沒說的內容']])) > 0, '改寫過頭的敘述要被抓到'
    assert run(good, lesson='「這句話手冊裡沒有」') > 0, '捏造的引述要被抓到'
    assert run(dict(good, pat='模式9')) > 0, '不存在的模式要被抓到'

    with tempfile.NamedTemporaryFile('w', suffix='.html', delete=False, encoding='utf-8') as f:
        f.write('<script type="application/json" id="bank">{"questions":[]}</script>')
        tmp = pathlib.Path(f.name)
    assert load_bank(tmp) == {'questions': []}, '應該讀得出內嵌的題庫'
    tmp.unlink()
    print('demo OK')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('game', nargs='?', default=str(GAME))
    p.add_argument('--demo', action='store_true', help='只跑自我檢查')
    a = p.parse_args()
    if a.demo:
        demo()
        return 0
    demo()
    bank = load_bank(pathlib.Path(a.game))
    failed = check(bank,
                   index_book(FAIL_BOOK.read_text(encoding='utf-8')),
                   index_book(WIN_BOOK.read_text(encoding='utf-8')),
                   json.load(open(UPGRADE, encoding='utf-8')),
                   print)
    return int(failed > 0)


if __name__ == '__main__':
    sys.exit(main())
