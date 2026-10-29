# Ir de compras（幫媽媽買東西）

> 幫媽媽買東西的中文語音遊戲：看購物清單，對著麥克風說出「數量＋量詞＋物品」

- **網址：** https://wangchiapin.github.io/irdecompras/
- **Firebase 專案：** memorma-24dab（排行榜，集合 `mama_shopping_leaderboard`，匿名登入；與 Memorama、色數消消樂等共用）
- **登入方式：** 匿名登入
- **狀態：** 使用中（2026-10-20 正式上線，分享區有卡片）

## 內容
- 商品清單 100 項，每項有繁／簡、拼音、量詞、價格。
- 唯一有語音辨識的遊戲（zh-TW，按住說話或點一下）；手機不支援語音辨識時改用打字。
- 設定與其他遊戲共用：繁／簡體、介面語言（中＋西／中＋英／只有中文）、拼音／注音、語速。
- 排行榜前 10 名，每台裝置一筆最高分。

## 讀音
依 GoodTeacher 規則維護，例如「洗髮精」髮念 3 聲 fǎ（2026-10-27）、葡萄 pútáo。

## 遊玩紀錄
2026-10-21 起記錄訪客、開始、玩完，寫到 `memorma-24dab` 的 `plays`、`visits`（GA 不動），在分享區後台「📈 遊玩紀錄」查看。

## 分享連結預覽（2026-10-28）
把網址貼到 LINE、WhatsApp 時，會顯示遊戲名稱「幫媽媽買東西 · Ir de compras」和縮圖。縮圖是根目錄的 `og.jpg`（1200x630）；名稱與說明文字寫在 `index.html` `<head>` 的 `og:title`、`og:description`。

## 手機瀏覽器備註：捲動後回不到頂端（2026-10-24）
iPhone 版 Chrome 上，頁面可以捲動時，往下捲之後有時回不到最上面（Safari 正常）。
本遊戲原本已設 `maximum-scale=1`（保留原有 viewport 設定），另補上 `html{color-scheme:light}`。新增頁面請兩項都有（見 game-kit README）。
