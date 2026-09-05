# 投稿カード画像の生成

X投稿に添付するカード画像（1200×675）を、HTMLテンプレートから生成します。外部の画像生成サービスは使いません。同じテンプレートから作るので、毎回まったく同じデザインで量産できます。

## 生成タイミング

**実機検証が終わってから**です。カードには `⏱` の実測値が入るので、検証前には作れません。

```
朝7時 Routine: 下書き生成 → Slack + メール通知
      ↓
あなた: PowerPointで実機検証、Before/Afterの所要時間を実測
      ↓
カード画像を生成 ← ここ
      ↓
Xへ手動投稿
```

## 使い方

### 1. フォントを用意する（初回のみ）

`template.html` はサイトと同じ Noto Sans JP を使います。npm から取得します。

```bash
npm install @fontsource/noto-sans-jp
```

`node_modules/` が `template.html` と同じ階層にある状態にしてください。

### 2. テンプレートの値を差し替える

`template.html` 内の以下を書き換えます。

| 箇所 | 内容 |
|---|---|
| `.pill` | 柱のラベル（例: PowerPoint 時短Tips） |
| `.no` | テーマ番号（themes.md の # と対応） |
| `.key` | ショートカットキー・機能名 |
| `.headline` | 見出し。`<em>` で囲んだ部分がアクセント色になる |
| `.row.before` の名前とバー | Before の操作名・実測時間 |
| `.row.after` の名前とバー | After の操作名・実測時間 |
| `.foot` 左 | 計測条件（例: 図形10個の色を変える場合） |
| `.foot .acct` | アカウント名 |

**バーの `style="width:..."` は実測値に比例させてください。** 例: 12秒→600px、2秒→100px。長さの差そのものが訴求なので、ここを実際の比率から外さないこと。

### 3. PNGに書き出す

```bash
/opt/pw-browsers/chromium-1194/chrome-linux/chrome \
  --headless --no-sandbox --disable-gpu --hide-scrollbars \
  --force-device-scale-factor=1 --window-size=1200,675 \
  --screenshot=card.png template.html
```

`--force-device-scale-factor=2` にすると2400×1350の高解像度版が出ます。

## デザインの決めごと

- **地の色・作法** は SMILESTOCK.LAB サイトから継承（チャコール `#2e2e2e` / サーフェス / ヘアライン / 角丸16px / ピル型 / Noto Sans JP）
- **アクセントは別系統**（オレンジ `#ffa22b`）。サイトの紫は使わない。ブランドを分離するため
- **時短の数字が主役**。見出しより視覚的重量を上げてある。これがこのアカウントの差別化の核
- 色だけで情報を伝えない（バーの長さでも時短が伝わる）
- コントラストはWCAG AA以上、最小文字サイズ22px

## レイアウト上の注意

縦方向は `justify-content: space-between` ではなく**固定余白**で組んでいます。space-betweenはビューポート高さに依存してフッターが描画されない事象があったためです。要素を増減するときは margin の合計が675pxを超えないよう調整してください。

## 注意

- 「PowerPoint」はMicrosoftの登録商標です。ロゴ・ブランドカラーは使っていませんが、Microsoft公式と誤認させない配慮をしてください（プロフィールに非公式である旨を記載するなど）
- X投稿時は画像のaltテキストを設定してください
