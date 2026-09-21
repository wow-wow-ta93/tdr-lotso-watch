#!/usr/bin/env bash
# LINE のチャネルアクセストークンを GitHub Secrets に登録する（貼り付けた内容は画面に表示されません）
set -e
REPO="wow-wow-ta93/tdr-lotso-watch"
echo "LINE Developers で発行した「チャネルアクセストークン（長期）」を貼り付けて Enter："
read -rs TOKEN
[ -z "$TOKEN" ] && { echo "空でした。中止します"; exit 1; }
printf '%s' "$TOKEN" | gh secret set LINE_CHANNEL_TOKEN -R "$REPO"
echo "登録しました → $REPO の Secrets: LINE_CHANNEL_TOKEN"
