# LINE通知の準備（ご本人にお願いする10分の作業）

通知は「LINE公式アカウント（Bot）」から奥様のLINEへ送ります。
Botを作る＝LINEアカウントでのログインとアカウント新規作成が必要なため、この部分だけご本人の操作が必要です。

## 1. LINE公式アカウントを作る（3分）
1. https://developers.line.biz/console/ を開き「LINEアカウントでログイン」（ご自身のLINE）
2. 初回は開発者名・メールを入力して登録
3. 「プロバイダー」を作成 → 名前は何でも可（例: `family`）
4. 「チャネルを作成」→「Messaging API」を選択
   - 2024年9月以降は、この画面から **LINE公式アカウントの作成** に誘導されます。案内に従って公式アカウントを作成（アカウント名 例: `ロッツォ空席番`、業種は「個人」でOK）
   - 作成後、LINE Official Account Manager の **設定 → Messaging API → 「Messaging APIを利用する」** を押し、先ほどのプロバイダーを選択

## 2. チャネルアクセストークンを発行（1分）
1. https://developers.line.biz/console/ に戻り、プロバイダー → 作ったチャネル → **「Messaging API設定」タブ**
2. 一番下の **「チャネルアクセストークン（長期）」→「発行」**
3. 表示された長い文字列をコピー

## 3. GitHubに登録（1分）
ターミナルで下を実行し、貼り付けて Enter（画面には表示されません）:

```bash
bash ~/Documents/genai-workspace/_tools/tdr-lotso-watch/setup_line_secret.sh
```

## 4. 奥様にBotを友だち追加してもらう（1分）
- 「Messaging API設定」タブの上部にある **QRコード** を奥様に送り、LINEで読み取って友だち追加
- （通知を自分でも受けたい場合は、ご自身も友だち追加）
- 同じ画面の「応答メッセージ」は **オフ**、「あいさつメッセージ」も オフ にしておくと余計な自動返信が出ません
  （LINE Official Account Manager → 設定 → 応答設定）

## 5. 完了の合図
「LINE設定できました」と教えてください。テスト通知を送って届くことを確認し、監視を開始します。
