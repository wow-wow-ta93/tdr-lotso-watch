#!/usr/bin/env bash
# launchd から15分おきに呼ばれる。Mac が起きている間だけ動く（スリープ中は実行されず、復帰後に1回だけ実行される）
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$HOME/.config/tdr-lotso-watch/env"
LOG="$DIR/logs/watch.log"
mkdir -p "$DIR/logs"
[ -f "$ENV_FILE" ] && set -a && . "$ENV_FILE" && set +a
export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"

# 前回がまだ動いていたら重ねて起動しない
LOCK="$DIR/logs/.lock"
if [ -f "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
  echo "$(date '+%F %T') skip: previous run still active" >> "$LOG"; exit 0
fi
echo $$ > "$LOCK"

{
  echo "===== $(date '+%F %T')"
  cd "$DIR" && python3 check.py "$@"
  echo "exit=$?"
} >> "$LOG" 2>&1
rm -f "$LOCK"
# ログは直近2000行だけ残す
tail -n 2000 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
