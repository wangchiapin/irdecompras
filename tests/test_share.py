# 幫媽媽買東西「分享成績」＋ ?ref=share 來訪追蹤 測試
import sys, json
from playwright.sync_api import sync_playwright
import common
from common import *

R = Runner()
_orig_route = common.route
def route(r):
    if 'opencc-js' in r.request.url: return r.fulfill(status=200, content_type='application/javascript', body='')
    return _orig_route(r)
common.route = route

SHARE_STUB = """(()=>{ window.__shared=[]; window.__copied=[]; window.__mode='share'; window.__shareDelay=0;
  Object.defineProperty(navigator,'share',{configurable:true,get(){ return window.__mode==='copy'||window.__mode==='fail' ? undefined : async d=>{ window.__shared.push(d);
    if(window.__mode==='abort'){ const e=new Error('x'); e.name='AbortError'; throw e; }
    if(window.__mode==='boom'){ throw new Error('boom'); }
    if(window.__shareDelay) await new Promise(r=>setTimeout(r,window.__shareDelay)); } }});
  const cb={ writeText: async t=>{ if(window.__mode==='fail') throw new Error('no'); window.__copied.push(t); } };
  Object.defineProperty(navigator,'clipboard',{configurable:true,value:cb});
  document.execCommand=()=>false;
  window.OpenCC={Converter:()=>s=>String(s).replace(/幫/g,'帮').replace(/買/g,'买').replace(/複/g,'复').replace(/製/g,'制').replace(/績/g,'绩').replace(/敗/g,'败').replace(/載/g,'载')};
})();"""
SIM = "window.__sim=1;"

def page(p, query='', settings=None, name='Ana'):
    init = "window.confirm=()=>true;localStorage.setItem('irdecompras.playerName',%s);" % json.dumps(name) + SHARE_STUB
    return open_page(p, query, settings=settings, wait=1500, extra_init=init)

def to_result(pg, pct=80, name='Ana'):
    pg.fill('#nameInput', name); pg.click('#startBtn'); pg.wait_for_timeout(300)
    pg.click('#skipIntroBtn'); pg.wait_for_timeout(200)
    pg.click('#startShoppingBtn'); pg.wait_for_timeout(200)
    pg.evaluate("""(pct)=>{ maxScore=100; score=pct; shoppingEndTime=Date.now(); startTime=shoppingEndTime-60000; resultShown=false; showResult(); }""", pct)
    pg.wait_for_timeout(300)

URL = 'https://wangchiapin.github.io/irdecompras/?ref=share'

with sync_playwright() as p:
    # 1) 基本：繁體＋西文，分享選單
    b, pg, errs = page(p, settings={'lang': 'es', 'script': 'trad'})
    to_result(pg, 80)
    R.check(pg.evaluate("currentScreen") == 'screen-result', '到結果頁')
    R.check(pg.is_visible('#shareBtn'), '分數 > 0：顯示分享鈕')
    txt = pg.inner_text('#shareBtn')
    R.check('分享成績' in txt and 'Compartir resultado' in txt, '鈕上有「分享成績」與西文小字：%r' % txt)
    order = pg.evaluate("[...document.querySelectorAll('#screen-result button')].filter(b=>b.offsetParent||b.id==='shareBtn').map(b=>b.id)")
    R.check(order.index('playAgainBtn') < order.index('shareBtn'), '分享鈕在「再玩一次」之後：%s' % order)
    R.check(pg.evaluate("document.getElementById('shareBtn').classList.contains('btn-restart')") is False, '不用 .btn-restart')
    R.check(pg.evaluate("getComputedStyle(document.getElementById('shareBtn')).borderTopWidth") == '2px', '空心外框 2px')
    pg.click('#shareBtn'); pg.wait_for_timeout(300)
    sh = pg.evaluate("window.__shared")
    R.check(len(sh) == 1 and sh[0]['url'] == URL, '分享網址是公開頁＋?ref=share：%s' % [s.get('url') for s in sh])
    R.check('80' in sh[0]['text'] and 'Ir de compras' in sh[0]['text'], '西文句子含分數與遊戲名：%s' % sh[0]['text'])
    R.check('幫媽媽買東西' in sh[0]['title'], '標題含中文遊戲名：%s' % sh[0]['title'])
    R.check(pg.inner_text('#shareBtn') == txt, '分享成功後按鈕文字不變')
    # 玩家自己關掉
    pg.evaluate("window.__mode='abort'"); pg.click('#shareBtn'); pg.wait_for_timeout(300)
    R.check('複製失敗' not in pg.inner_text('#shareBtn') and '已複製' not in pg.inner_text('#shareBtn'), '玩家關掉選單：不顯示失敗')
    R.check(pg.evaluate("window.__copied.length") == 0, '玩家關掉選單：不複製')
    # 分享出錯 → 改複製
    pg.evaluate("window.__mode='boom'"); pg.click('#shareBtn'); pg.wait_for_timeout(300)
    R.check(pg.evaluate("window.__copied.length") == 1 and URL in pg.evaluate("window.__copied[0]"), '分享出錯：改複製（含連結）')
    R.check('已複製' in pg.inner_text('#shareBtn') and 'Copiado' in pg.inner_text('#shareBtn'), '顯示「已複製 Copiado」')
    pg.wait_for_timeout(2500)
    R.check(pg.inner_text('#shareBtn') == txt, '2.2 秒後文字還原')
    # 不支援分享選單 → 複製
    pg.evaluate("window.__mode='copy'; window.__copied.length=0"); pg.click('#shareBtn'); pg.wait_for_timeout(300)
    R.check(pg.evaluate("window.__copied.length") == 1, '不支援分享選單：複製')
    pg.wait_for_timeout(2500)
    # 複製也失敗
    pg.evaluate("window.__mode='fail'"); pg.click('#shareBtn'); pg.wait_for_timeout(300)
    R.check('複製失敗' in pg.inner_text('#shareBtn') and 'No se pudo copiar' in pg.inner_text('#shareBtn'), '複製也失敗：顯示「複製失敗」')
    pg.wait_for_timeout(2500)
    # 連點只送一次
    pg.evaluate("window.__mode='share'; window.__shared.length=0; window.__shareDelay=600")
    pg.evaluate("document.getElementById('shareBtn').click(); document.getElementById('shareBtn').click(); document.getElementById('shareBtn').click()")
    pg.wait_for_timeout(900)
    R.check(pg.evaluate("window.__shared.length") == 1, '連點三下只送一次：%d' % pg.evaluate("window.__shared.length"))
    R.check(not errs, '沒有網頁錯誤 %s' % errs)
    b.close()

    # 2) 英文
    b, pg, errs = page(p, settings={'lang': 'en', 'script': 'trad'})
    to_result(pg, 55)
    pg.click('#shareBtn'); pg.wait_for_timeout(300)
    t = pg.evaluate("window.__shared[0].text")
    R.check('55' in t and 'points' in t, '英文句子：%s' % t)
    R.check('Share result' in pg.inner_text('#shareBtn'), '英文小字 Share result')
    b.close()

    # 3) 只有中文＋簡體
    b, pg, errs = page(p, settings={'lang': 'zh', 'script': 'simp'})
    pg.wait_for_timeout(500)
    to_result(pg, 90)
    pg.click('#shareBtn'); pg.wait_for_timeout(400)
    t = pg.evaluate("window.__shared[0].text")
    R.check('帮' in t and '买' in t and '90' in t, '簡體句子：%s' % t)
    R.check('幫' not in t and '買' not in t, '簡體句子沒有繁體字')
    pg.evaluate("window.__mode='boom'"); pg.click('#shareBtn'); pg.wait_for_timeout(300)
    R.check('已复制' in pg.inner_text('#shareBtn'), '簡體：已复制：%r' % pg.inner_text('#shareBtn'))
    b.close()

    # 4) 0 分不顯示
    b, pg, errs = page(p, settings={'lang': 'es', 'script': 'trad'})
    to_result(pg, 0)
    R.check(not pg.is_visible('#shareBtn'), '0 分：不顯示分享鈕')
    pg.evaluate("document.getElementById('shareBtn').click()"); pg.wait_for_timeout(200)
    R.check(pg.evaluate("window.__shared.length") == 0, '0 分：強行點也不分享')
    # 再玩一次拿高分後又出現
    pg.click('#playAgainBtn'); pg.wait_for_timeout(300)
    pg.click('#skipIntroBtn') if pg.is_visible('#skipIntroBtn') else None
    pg.evaluate("""()=>{ maxScore=100; score=70; shoppingEndTime=Date.now(); startTime=shoppingEndTime-60000; resultShown=false; showResult(); }""")
    pg.wait_for_timeout(300)
    R.check(pg.is_visible('#shareBtn'), '下一局拿到分數：分享鈕又出現')
    b.close()

    # 5) ?ref=share 追蹤
    def ops(pg): return pg.evaluate("window.__ops||[]")
    b, pg, errs = page(p, query='?ref=share', settings={'lang': 'es', 'script': 'trad'})
    pg.wait_for_timeout(2500)
    v = [o for o in ops(pg) if o['p'].startswith('visits/')]
    R.check(len(v) == 1 and v[0]['d'].get('ref') == 'share', '打開 ?ref=share：visit 帶 ref=share：%s' % [o['d'] for o in v])
    to_result(pg, 60)
    pg.wait_for_timeout(500)
    pl = [o for o in ops(pg) if o['p'] == 'plays']
    R.check(len(pl) >= 1 and pl[0]['d'].get('ref') == 'share', '開始玩：play 帶 ref=share：%s' % [o['d'] for o in pl])
    b.close()
    b, pg, errs = page(p, settings={'lang': 'es', 'script': 'trad'})
    pg.wait_for_timeout(2500)
    v = [o for o in ops(pg) if o['p'].startswith('visits/')]
    R.check(len(v) == 1 and 'ref' not in v[0]['d'], '沒帶 ref：visit 沒有 ref 欄位')
    b.close()
    for bad in ['?ref=SHARE', '?ref=a%20b', '?ref=' + 'x' * 17, '?ref=%3Cb%3E']:
        b, pg, errs = page(p, query=bad, settings={'lang': 'es', 'script': 'trad'})
        pg.wait_for_timeout(2500)
        v = [o for o in ops(pg) if o['p'].startswith('visits/')]
        want = 'share' if bad == '?ref=SHARE' else None
        R.check(len(v) == 1 and v[0]['d'].get('ref') == want, '記號 %s → %s：%s' % (bad, want, [o['d'].get('ref') for o in v]))
        b.close()

print('FAILS', R.fails); sys.exit(1 if R.fails else 0)
