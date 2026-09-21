# tdr-lotso-watch — 東京ディズニーリゾート レストラン空席監視 → LINE通知

東京ディズニーリゾートのオンライン予約サイトのレストランカレンダー（ログイン不要ページ）を
**この Mac 上で** 15分おきに実ブラウザで開き、指定日・指定時間帯に「予約する」枠が出たら
LINE（Messaging API の broadcast）で通知します。予約そのものは行いません。

- Mac が起きている間だけ動きます（スリープ中は止まり、復帰後に1回実行されます）
- クラウド（GitHub Actions 等）からは予約サイトの CDN に拒否されるため、自宅回線の Mac で動かします

## 構成
- `check.py` … Playwright（Chromium・通常モード）でカレンダーを開き、対象行の枠を判定 → LINE 通知 → `state.json` 更新
- `run.sh` … launchd から呼ばれるラッパー（設定読込・多重起動防止・ログ）
- `com.takumitada.tdr-lotso-watch.plist` … launchd 設定（`StartInterval` 900秒）
- `~/.config/tdr-lotso-watch/env` … `LINE_CHANNEL_TOKEN` と `WATCH_CONFIG`（監視条件 JSON。`check.py` 冒頭のコメント参照）
- 同じ空き状況では再通知しない。3回連続で取得失敗したら1回だけ警告、復旧時にも1回通知
- サイトのメンテナンス時間（3:00〜5:00 JST）と、`deadline` 以降は何もしない

## 操作
```bash
# 状態を見る
tail -n 40 logs/watch.log
# 一時停止 / 再開
launchctl unload ~/Library/LaunchAgents/com.takumitada.tdr-lotso-watch.plist
launchctl load   ~/Library/LaunchAgents/com.takumitada.tdr-lotso-watch.plist
# 手動で1回（通知なし）
python3 check.py --dry-run
# LINEに試験通知
bash run.sh --test-notify
```

※ ヘッドレスではサイト側の対策で応答が返らないため、通常モードのウィンドウを画面外に出して動かします。
