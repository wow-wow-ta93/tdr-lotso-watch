#!/usr/bin/env bash
# LINE のチャネルアクセストークンをこの Mac の設定ファイル（自分だけ読める）に保存する。貼り付けた内容は画面に表示されません。
set -e
CFG_DIR="$HOME/.config/tdr-lotso-watch"; ENV_FILE="$CFG_DIR/env"
mkdir -p "$CFG_DIR"; chmod 700 "$CFG_DIR"
echo "LINE Developers で発行した「チャネルアクセストークン（長期）」を貼り付けて Enter："
read -rs TOKEN; echo
[ -z "$TOKEN" ] && { echo "空でした。中止します"; exit 1; }
grep -v '^LINE_CHANNEL_TOKEN=' "$ENV_FILE" 2>/dev/null > "$ENV_FILE.tmp" || true
printf 'LINE_CHANNEL_TOKEN=%s\n' "$TOKEN" >> "$ENV_FILE.tmp"
mv "$ENV_FILE.tmp" "$ENV_FILE"; chmod 600 "$ENV_FILE"
echo "保存しました → $ENV_FILE"
