# 幫媽媽買東西 測試：名字必填、清單產生、語音比對、算分、結帳找零、結果星等、排行榜、設定、重新開始
import sys, re, json
from playwright.sync_api import sync_playwright
import common
from common import *

R = Runner()

FAKE_FB = r"""
(function(){
  window.__db = window.__db || {}; window.__ops = window.__ops || [];
  if (window.firebase && window.firebase.__fake) return;
  const DB = window.__db, ops = window.__ops, clone = x => JSON.parse(JSON.stringify(x));
  const depth = p => p.split('/').length;
  function docRef(path){ return { path, id: path.split('/').pop(),
    async get(){ return { exists: path in DB, data: () => DB[path] && clone(DB[path]) }; },
    async set(d){ ops.push({k:'set', p:path, d:clone(d)}); DB[path] = clone(d); },
    async update(d){ ops.push({k:'update', p:path, d:clone(d)}); DB[path] = Object.assign(DB[path]||{}, clone(d)); } }; }
  function colRef(path){ const q = { doc: id => docRef(path + '/' + id),
    async add(d){ ops.push({k:'add', p:path, d:clone(d)}); const id = 'A' + ops.length; DB[path + '/' + id] = clone(d); return { id }; },
    where(){ return q; }, orderBy(){ return q; }, limit(){ return q; },
    async get(){ const ks = Object.keys(DB).filter(k => k.startsWith(path + '/') && depth(k) === depth(path) + 1);
      const rows = ks.map(k => clone(DB[k])).sort((a,b)=>(b.score||0)-(a.score||0));
      return { docs: rows.map(r => ({ id:'x', data: () => r })), size: rows.length }; } };
    return q; }
  const auth = { currentUser: null, async signInAnonymously(){ auth.currentUser = { uid: window.__uid || 'UID1' }; return { user: auth.currentUser }; } };
  const fsInst = { collection: colRef };
  const fire = () => fsInst; fire.FieldValue = { serverTimestamp: () => 'TS' };
  window.firebase = { __fake: true, apps: [], auth: () => auth, firestore: fire,
    initializeApp(c, n){ const a = { name: n || '[DEFAULT]', auth: () => auth, firestore: () => fsInst }; this.apps.push(a); return a; } };
})();
"""
NOFB = False
def route(r):
    u = r.request.url
    if u.startswith('file:'): return r.continue_()
    if 'gstatic.com/firebasejs' in u:
        if NOFB: return r.abort()
        return r.fulfill(status=200, content_type='application/javascript', body=FAKE_FB if 'firebase-app-compat' in u else '')
    r.abort()
common.route = route

def page(p, query='', settings=None, name=None, **kw):
    init = "window.confirm=()=>true;"
    if name is not None: init += "localStorage.setItem('irdecompras.playerName',%s);" % json.dumps(name)
    return open_page(p, query, settings=settings, wait=1500, extra_init=init, **kw)

def scr(pg): return pg.evaluate("currentScreen")
def to_list(pg, name='Ana'):
    pg.fill('#nameInput', name); pg.click('#startBtn'); pg.wait_for_timeout(300)
    pg.click('#skipIntroBtn'); pg.wait_for_timeout(200)
def to_shopping(pg, name='Ana'):
    to_list(pg, name); pg.click('#startShoppingBtn'); pg.wait_for_timeout(200)
def set_list(pg, items_qty):
    # items_qty: [(漢字簡體名稱, 數量)]；直接指定清單，讓比對結果可預期
    pg.evaluate("""(a)=>{ shoppingList=a.map(([n,q])=>({item:ITEMS.find(i=>i.h.join('')===n),qty:q,done:false,attempts:0}));
      score=0; maxScore=shoppingList.length*20+10+15+25; TOTAL_PRICE=shoppingList.reduce((s,e)=>s+e.item.price*e.qty,0); renderShoppingList2(); }""", items_qty)
def spend(pg, ids):
    # 真的點皮包裡的鈔票硬幣（有 0.43 秒飛過去的動畫，要等）
    for i in ids:
        pg.click('#walletPieces .cash-piece[data-id="%s"]' % i); pg.wait_for_timeout(520)

def say(pg, text):
    pg.evaluate("t=>processAnswer(t)", text)
def entry(pg, i=0): return pg.evaluate("(i)=>({done:shoppingList[i].done,attempts:shoppingList[i].attempts})", i)
def score(pg): return pg.evaluate("score")

with sync_playwright() as p:
    # ───── 1) 名字必填 ─────
    b, pg, errs = page(p)
    R.check(scr(pg) == 'screen-start', '開頁在開始畫面')
    R.check(pg.is_disabled('#startBtn'), '沒填名字：「開始」鈕是停用的')
    pg.fill('#nameInput', '   '); R.check(pg.is_disabled('#startBtn'), '只填空白：仍停用')
    pg.fill('#nameInput', 'Ana'); R.check(not pg.is_disabled('#startBtn'), '填了名字：可以按')
    R.check(pg.evaluate("localStorage.getItem('irdecompras.playerName')") == 'Ana', '名字記在本機')
    pg.fill('#nameInput', 'x' * 30); R.check(len(pg.input_value('#nameInput')) <= 12, '名字最多 12 字：%d' % len(pg.input_value('#nameInput')))
    pg.fill('#nameInput', ''); pg.press('#nameInput', 'Enter'); pg.wait_for_timeout(200)
    R.check(scr(pg) == 'screen-start', '沒名字按 Enter 不會開始')
    pg.fill('#nameInput', 'Ana'); pg.press('#nameInput', 'Enter'); pg.wait_for_timeout(300)
    R.check(scr(pg) == 'screen-intro', '有名字按 Enter：進到開場對話')
    pg.click('#skipIntroBtn'); pg.wait_for_timeout(200)
    R.check(scr(pg) == 'screen-list', '略過對話：進到購物清單')
    R.check(not errs, '沒有網頁錯誤 %s' % errs)
    b.close()
    b, pg, errs = page(p, name='Mimi')
    R.check(pg.input_value('#nameInput') == 'Mimi' and not pg.is_disabled('#startBtn'), '重新整理後名字還在、可直接開始')
    b.close()

    # ───── 2) 清單產生：3–5 項、不重複、數量 1–4 ─────
    b, pg, errs = page(p)
    to_list(pg)
    bad = pg.evaluate("""()=>{ const out={sizes:new Set(),dup:0,qty:new Set()};
      for(let i=0;i<300;i++){ buildShoppingList(); out.sizes.add(shoppingList.length);
        if(new Set(shoppingList.map(e=>e.item.h.join(''))).size!==shoppingList.length) out.dup++;
        shoppingList.forEach(e=>out.qty.add(e.qty)); }
      return {sizes:[...out.sizes].sort(),dup:out.dup,qty:[...out.qty].sort()}; }""")
    R.check(bad['sizes'] == [3, 4, 5], '清單長度只會是 3、4、5 項：%s' % bad['sizes'])
    R.check(bad['dup'] == 0, '清單裡的物品不重複')
    R.check(bad['qty'] == [1, 2, 3, 4], '數量只會是 1–4：%s' % bad['qty'])
    R.check(pg.evaluate("document.querySelectorAll('#shoppingItemsList li').length === shoppingList.length"), '畫面清單項數＝資料項數')
    b.close()

    # ───── 3) 語音比對 ─────
    b, pg, errs = page(p)
    to_shopping(pg)
    set_list(pg, [('牛奶', 2), ('米', 3), ('苹果', 1)])
    say(pg, '兩瓶牛奶'); R.check(entry(pg, 0)['done'] and score(pg) == 20, '「兩瓶牛奶」→ 牛奶 2 瓶：答對 +20')
    set_list(pg, [('牛奶', 2)]); say(pg, '二瓶牛奶'); R.check(entry(pg)['done'], '數量 2 說「二」也算')
    set_list(pg, [('牛奶', 2)]); say(pg, '2瓶牛奶'); R.check(entry(pg)['done'], '數量說阿拉伯數字 2 也算')
    set_list(pg, [('牛奶', 2)]); say(pg, '兩 瓶 牛 奶'); R.check(entry(pg)['done'], '辨識結果每字中間有空白也算')
    set_list(pg, [('牛奶', 3)]); say(pg, '兩瓶牛奶'); R.check(not entry(pg)['done'] and entry(pg)['attempts'] == 1 and score(pg) == 0, '數量說錯（要 3 說 2）：不算，記 1 次嘗試，不扣分')
    R.check('數量' in pg.inner_text('#feedbackMsg'), '數量錯：提示「數量好像不對」')
    set_list(pg, [('牛奶', 2)]); say(pg, '兩杯牛奶'); R.check(not entry(pg)['done'] and '量詞' in pg.inner_text('#feedbackMsg'), '量詞說錯（杯）：不算，提示量詞不對')
    set_list(pg, [('牛奶', 2)]); say(pg, '兩個牛奶'); R.check(entry(pg)['done'] and score(pg) == 17, '用「個」代替量詞：算對但少 3 分（17），並提示正確量詞：%d' % score(pg))
    R.check('瓶' in pg.inner_text('#feedbackMsg'), '用「個」時提示正確量詞「瓶」')
    set_list(pg, [('牛奶', 2)]); say(pg, '你好嗎'); R.check(entry(pg)['attempts'] == 0 and '清單上沒有' in pg.inner_text('#feedbackMsg'), '完全不相關的話：不記嘗試，提示請再說一次')
    set_list(pg, [('牛奶', 2)]); say(pg, '兩瓶牛奶'); say(pg, '兩瓶牛奶')
    R.check(score(pg) >= 20 and score(pg) <= 20 + 50, '同一項說兩次不會重複加分（%d）' % score(pg))
    # 第二次才對 = 15
    set_list(pg, [('牛奶', 2), ('米', 1)]); say(pg, '三瓶牛奶'); say(pg, '兩瓶牛奶')
    R.check(entry(pg, 0)['done'] and score(pg) == 15, '第二次才說對：+15（不是 20）：%d' % score(pg))
    # 簡繁
    set_list(pg, [('面包', 1)]); say(pg, '一條麵包'); R.check(entry(pg)['done'], '繁體「一條麵包」＝面包 1 条')
    set_list(pg, [('面包', 1)]); say(pg, '一条面包'); R.check(entry(pg)['done'], '簡體「一条面包」也算')
    # 短名稱不被長名稱誤判
    set_list(pg, [('米', 2)]); say(pg, '兩包玉米'); R.check(not entry(pg)['done'], '「米」不會被「玉米」誤判')
    # 辨識出多個候選
    set_list(pg, [('牛奶', 2)]); pg.evaluate("processAnswerAlternatives(['你好','兩瓶牛奶','三杯牛奶'])")
    R.check(entry(pg)['done'], '語音辨識有多個候選：用能對上的那個')
    # 全部買齊 → 完成獎勵
    set_list(pg, [('牛奶', 2)]); pg.evaluate("startTime=Date.now()-5000; shoppingEndTime=0;"); say(pg, '兩瓶牛奶')
    R.check(score(pg) == 20 + 10 + 15, '買齊且 90 秒內：20＋完成 10＋速度 15 ＝ 45：%d' % score(pg))
    set_list(pg, [('牛奶', 2)]); pg.evaluate("startTime=Date.now()-120000; shoppingEndTime=0;"); say(pg, '兩瓶牛奶')
    R.check(score(pg) == 20 + 10 + 8, '買齊且 90–150 秒：速度加分 8：%d' % score(pg))
    set_list(pg, [('牛奶', 2)]); pg.evaluate("startTime=Date.now()-200000; shoppingEndTime=0;"); say(pg, '兩瓶牛奶')
    R.check(score(pg) == 20 + 10, '買齊但超過 150 秒：沒有速度加分：%d' % score(pg))
    R.check(not errs, '沒有網頁錯誤 %s' % errs)
    b.close()

    # 打字備援（不用麥克風）
    b, pg, errs = page(p)
    to_shopping(pg)
    set_list(pg, [('牛奶', 2)])
    pg.evaluate("document.getElementById('screen-shopping').classList.add('kb-open')")
    pg.fill('#textFallback', '兩瓶牛奶'); pg.click('#sendFallback'); pg.wait_for_timeout(300)
    R.check(entry(pg)['done'], '打字備援：輸入「兩瓶牛奶」按送出 → 答對')
    b.close()

    # ───── 4) 結帳／找零／結果 ─────
    def checkout_flow(p, exact, change_choice=None):
        b, pg, errs = page(p)
        to_shopping(pg)
        set_list(pg, [('牛奶', 2), ('苹果', 1)])
        say(pg, '兩瓶牛奶'); say(pg, '一顆蘋果')
        R.check(pg.evaluate("checkAllDone()"), '兩項都買齊')
        pg.evaluate("startTime=Date.now()-5000")
        pg.click('#goCheckoutBtn') if scr(pg) == 'screen-shopping' else None
        pg.wait_for_timeout(300)
        return b, pg, errs
    b, pg, errs = checkout_flow(p, True)
    R.check(scr(pg) == 'screen-checkout', '按結帳：進入付錢畫面')
    total = pg.evaluate("TOTAL_PRICE")
    R.check(total == 60 * 2 + 15 * 1, f'應付金額＝牛奶 60×2＋蘋果 15×1＝135：{total}')
    R.check(pg.evaluate("walletPieces.reduce((s,x)=>s+x.denom,0)") > total, '皮包總額大於應付金額')
    pg.click('#payBtn'); pg.wait_for_timeout(200)
    R.check('金額不足' in pg.inner_text('#checkoutMsg') and scr(pg) == 'screen-checkout', '一毛都沒拿就付錢：提示金額不足，不離開')
    # 湊出剛剛好
    ids = pg.evaluate("""()=>{ const t=TOTAL_PRICE, w=walletPieces; // 動態規劃找剛好的組合
      const best={0:[]}; for(const p of w){ for(const s of Object.keys(best).map(Number).sort((a,b)=>b-a)){ const n=s+p.denom; if(n<=t && !(n in best)) best[n]=best[s].concat(p.id); } }
      return best[t]||null; }""")
    R.check(ids is not None, '皮包一定湊得出剛好的金額')
    spend(pg, ids)
    R.check(pg.evaluate("currentPaid()") == total, '拿出的錢＝應付金額')
    s0 = score(pg)
    pg.click('#payBtn'); pg.wait_for_timeout(300)
    R.check(score(pg) == s0 + 25, '剛剛好付款：+25（%d→%d）' % (s0, score(pg)))
    R.check('剛剛好' in pg.inner_text('#checkoutMsg'), '顯示「剛剛好」')
    R.check(pg.is_disabled('#payBtn'), '付款後「付錢」鈕停用')
    pg.evaluate("document.getElementById('payBtn').disabled=false; document.getElementById('payBtn').click()"); R.check(score(pg) == s0 + 25, '強行再按付錢也只算一次')
    pg.wait_for_timeout(1300)
    R.check(scr(pg) == 'screen-result', '剛好付款後 1 秒進入結果頁')
    info = pg.evaluate("resultInfo")
    full = pg.evaluate("maxScore")
    R.check(info['finalScore'] == min(100, round(pg.evaluate("score") / full * 100)), f'結果分數＝得分/滿分×100：{info["finalScore"]}')
    R.check(info['stars'] in ('★★★', '★★☆', '★☆☆'), '結果有星星 ' + info['stars'])
    sets = [o for o in pg.evaluate("window.__ops") if o['k'] == 'set' and o['p'].startswith('mama_shopping_leaderboard/')]
    R.check(len(sets) == 1 and sets[0]['d']['name'] == 'Ana' and sets[0]['d']['score'] == info['finalScore'], '排行榜寫入一筆：%s' % [s['d'] for s in sets])
    R.check(not errs, '沒有網頁錯誤 %s' % errs)
    # 看排行榜
    pg.click('#viewLeaderboardBtn'); pg.wait_for_timeout(500)
    R.check(scr(pg) == 'screen-leaderboard' and 'Ana' in pg.inner_text('#screen-leaderboard'), '排行榜畫面顯示 Ana')
    b.close()

    # 多付 → 找零小遊戲
    b, pg, errs = checkout_flow(p, False)
    total = pg.evaluate("TOTAL_PRICE")
    spend(pg, pg.evaluate("walletPieces.map(x=>x.id)"))
    R.check(pg.evaluate("currentPaid()") > total, '全部拿出：付的比應付多')
    s0 = score(pg)
    pg.click('#payBtn'); pg.wait_for_timeout(1300)
    R.check(scr(pg) == 'screen-change', '多付：進入「檢查找零」畫面')
    sc = pg.evaluate("currentChangeScenario")
    R.check(sc['correctChange'] == pg.evaluate("currentPaid()") - total, f'應找金額正確：{sc["correctChange"]}')
    R.check(sc['type'] in ('correct', 'over', 'under'), '情境種類：' + sc['type'])
    R.check((sc['type'] == 'correct') == (sc['givenChange'] == sc['correctChange']), '情境與實際找的錢一致：type=%s 找了 %s 應找 %s' % (sc['type'], sc['givenChange'], sc['correctChange']))
    # 答錯 -5
    wrong = {'correct': 'changeBtnOver', 'over': 'changeBtnUnder', 'under': 'changeBtnCorrect'}[sc['type']]
    right = {'correct': 'changeBtnCorrect', 'over': 'changeBtnOver', 'under': 'changeBtnUnder'}[sc['type']]
    pg.click('#' + wrong); pg.wait_for_timeout(200)
    R.check(score(pg) == max(0, s0 - 5), f'找零答錯：−5（{s0}→{score(pg)}）')
    R.check(pg.is_visible('#changeContinueBtn') and pg.is_disabled('#changeBtnCorrect'), '答完按鈕鎖住、出現「繼續」')
    pg.click('#changeContinueBtn'); pg.wait_for_timeout(300)
    R.check(scr(pg) == 'screen-result', '按繼續：結果頁')
    b.close()
    b, pg, errs = checkout_flow(p, False)
    spend(pg, pg.evaluate("walletPieces.map(x=>x.id)"))
    s0 = score(pg)
    pg.click('#payBtn'); pg.wait_for_timeout(1300)
    sc = pg.evaluate("currentChangeScenario")
    right = {'correct': 'changeBtnCorrect', 'over': 'changeBtnOver', 'under': 'changeBtnUnder'}[sc['type']]
    pg.click('#' + right); pg.wait_for_timeout(200)
    R.check(score(pg) == s0 + 15, f'找零答對：+15（{s0}→{score(pg)}）')
    b.close()

    # 星等門檻與送出分數
    b, pg, errs = page(p)
    for sc_pct, stars in ((100, '★★★'), (85, '★★★'), (84, '★★☆'), (55, '★★☆'), (54, '★☆☆'), (1, '★☆☆')):
        pg.evaluate("window.__ops.length=0")
        to_list(pg) if scr(pg) == 'screen-start' else None
        pg.evaluate("""(pct)=>{ goHome(); }""", sc_pct)
        to_shopping(pg)
        set_list(pg, [('牛奶', 1)])
        pg.evaluate("""(pct)=>{ maxScore=100; score=pct; shoppingEndTime=Date.now(); startTime=shoppingEndTime-60000; resultShown=false; showResult(); }""", sc_pct)
        R.check(pg.evaluate("resultInfo.stars") == stars and pg.evaluate("resultInfo.finalScore") == sc_pct, f'得分 {sc_pct}% → {stars}')
    pg.evaluate("goHome(); ")
    # 什麼都沒買 → 0 分，不上榜
    to_shopping(pg); set_list(pg, [('牛奶', 1)])
    pg.evaluate("window.__ops.length=0")
    pg.click('#goCheckoutBtn'); pg.wait_for_timeout(500)
    R.check(scr(pg) == 'screen-result' and pg.evaluate("resultInfo.finalScore") == 0, '一樣都沒買就結帳：直接結果頁、0 分')
    R.check(not [o for o in pg.evaluate("window.__ops") if o['k'] == 'set'], '0 分不寫排行榜')
    b.close()

    # 排行榜只留最高分（同一個人）
    b, pg, errs = page(p)
    to_shopping(pg)
    for val in (60, 40, 90):
        pg.evaluate("(v)=>submitScoreToLeaderboard('Ana', v)", val); pg.wait_for_timeout(200)
    row = pg.evaluate("window.__db['mama_shopping_leaderboard/UID1']")
    R.check(row['score'] == 90, f'同一人上傳 60、40、90：保留最高分 90（{row["score"]}）')
    pg.evaluate("submitScoreToLeaderboard('A'.repeat(30), 999)"); pg.wait_for_timeout(200)
    row = pg.evaluate("window.__db['mama_shopping_leaderboard/UID1']")
    R.check(row['score'] == 99 + 1 or row['score'] == 100, f'分數上限 100：{row["score"]}')
    R.check(len(row['name']) <= 12, '名字最多 12 字')
    b.close()

    # 沒有 Firebase：改用本機備援榜
    common_NOFB = True
    NOFB = True
    b, pg, errs = page(p)
    to_shopping(pg)
    pg.evaluate("submitScoreToLeaderboard('Ana', 70)"); pg.evaluate("submitScoreToLeaderboard('Bob', 80)")
    pg.wait_for_timeout(200)
    rows = pg.evaluate("fetchLeaderboard()")
    R.check([r['name'] for r in rows] == ['Bob', 'Ana'], '沒有 Firebase：備援榜依分數排序：%s' % rows)
    R.check(not errs, '沒有 Firebase：沒有網頁錯誤 %s' % errs)
    b.close()
    NOFB = False

    # ───── 5) 設定 ─────
    base = {'v': 1, 'script': 'trad', 'lang': 'es', 'phon': 'pinyin', 'rate': 'normal'}
    for rate, val in (('slow', 0.45), ('normal', 0.65), ('fast', 0.85)):
        b, pg, errs = page(p, settings=dict(base, rate=rate))
        to_shopping(pg); set_list(pg, [('牛奶', 2)]); say(pg, '兩瓶牛奶'); pg.wait_for_timeout(200)
        r = pg.evaluate("window.__spoken.map(s=>s.rate)")
        R.check(r and abs(r[-1] - val) < 1e-6, f'語速 {rate}：念出速度 {r[-1] if r else None}（應為 {val}）')
        b.close()
    for lang in ('es', 'en', 'zh'):
        b, pg, errs = page(p, settings=dict(base, lang=lang))
        txt = pg.inner_text('#screen-start')
        # 不看「語言」選項本身的按鈕字（那三顆永遠寫 Español／English），看標題、說明、按鈕
        es_marks = ['Ir de compras', 'Tu nombre', 'Empezar', 'Mamá está']
        en_marks = ['Shopping', 'Your name', 'Start']
        has_es = any(m in txt for m in es_marks); has_en = any(m in txt for m in en_marks)
        if lang == 'zh': ok = not has_es and not has_en
        elif lang == 'es': ok = has_es and not has_en
        else: ok = has_en and not has_es
        R.check(ok, f'語言 {lang}：開始畫面文字正確（有西文{has_es} 有英文{has_en}）')
        R.check(not errs, f'語言 {lang}：沒有網頁錯誤 {errs}')
        b.close()
    PY = re.compile('[āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ]'); ZY = re.compile('[ㄅ-ㄩ]')
    for phon in ('pinyin', 'zhuyin', 'both', 'off'):
        b, pg, errs = page(p, settings=dict(base, phon=phon))
        to_list(pg)
        txt = pg.evaluate("[...document.querySelectorAll('#shoppingItemsList .zhline')].map(e=>e.textContent).join(' ')")   # 只看清單品項的中文那行（西文行有重音字母會混進來）
        got = (bool(PY.search(txt)), bool(ZY.search(txt)))
        want = {'pinyin': (True, False), 'zhuyin': (False, True), 'both': (True, True), 'off': (False, False)}[phon]
        R.check(got == want, f'拼音注音 {phon}：清單頁 拼音{"有" if got[0] else "無"} 注音{"有" if got[1] else "無"}')
        R.check(not errs, f'拼音注音 {phon}：沒有網頁錯誤 {errs}')
        b.close()
    # 簡體：載不到轉換表時退回繁體，不會壞掉
    b, pg, errs = page(p, settings=dict(base, script='simp'))
    to_list(pg)
    R.check(scr(pg) == 'screen-list' and not errs, '字形=簡體（轉換表載不到）：仍能進清單，不報錯 %s' % errs)
    b.close()
    # 舊版設定搬家
    b, pg, errs = open_page(p, extra_init="localStorage.setItem('irdecompras_settings', JSON.stringify({script:'simp', lang:'en'}));", wait=1200)
    st = json.loads(pg.evaluate("localStorage.getItem('hanziGames.settings')"))
    R.check(st['lang'] == 'en' and st['script'] in ('simp', 'trad'), '舊版自己的設定搬到共用設定：%s' % st)
    b.close()

    # ───── 6) 重新開始／回首頁 ─────
    b, pg, errs = page(p)
    to_shopping(pg, 'Ana'); set_list(pg, [('牛奶', 2)]); say(pg, '兩瓶牛奶')
    R.check(score(pg) > 0, '先拿到分數')
    pg.evaluate("restartGame(true)"); pg.wait_for_timeout(200)
    R.check(scr(pg) == 'screen-list' and score(pg) == 0, '重新開始：分數歸零、回到新清單')
    R.check(pg.evaluate("playerName") == 'Ana', '重新開始：名字保留')
    pg.evaluate("goHome()"); pg.wait_for_timeout(200)
    R.check(scr(pg) == 'screen-start' and pg.input_value('#nameInput') == 'Ana', '回首頁：名字留在輸入框')
    R.check(not errs, '沒有網頁錯誤 %s' % errs)
    b.close()

print('FAILS', R.fails); sys.exit(1 if R.fails else 0)
