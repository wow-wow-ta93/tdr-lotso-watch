# tdr-lotso-watch — 東京ディズニーリゾート レストラン空席監視 → LINE通知

東京ディズニーリゾートのオンライン予約サイトのレストランカレンダー（ログイン不要ページ）を
GitHub Actions 上で15分おきに実ブラウザで開き、指定日・指定時間帯に「予約する」枠が出たら
LINE（Messaging API の broadcast）で通知します。予約そのものは行いません。

## 仕組み
- `check.py` … Playwright（Chromium・通常モード）でカレンダーを開き、対象行の枠を判定 → LINE 通知 → `state.json` 更新
- `.github/workflows/watch.yml` … `*/15 * * * *` の cron ＋ 手動実行（`run` / `dry-run` / `test-notify`）
- 監視条件は Secrets の `WATCH_CONFIG`（JSON）で渡す。リポジトリには個人の条件を置かない
- 同じ空き状況では再通知しない。3回連続で取得失敗したら1回だけ警告、復旧時にも1回通知
- サイトのメンテナンス時間（3:00〜5:00 JST）と、`deadline` 以降は何もしない

## Secrets
| 名前 | 内容 |
|---|---|
| `LINE_CHANNEL_TOKEN` | LINE Messaging API のチャネルアクセストークン（長期） |
| `WATCH_CONFIG` | 監視条件 JSON（`check.py` 冒頭のコメント参照） |

## 止め方
- 一時停止: Actions → `watch-lotso` → 「Disable workflow」
- 完全停止: リポジトリを Archive（または削除）

## ローカルで試す
```bash
pip install -r requirements.txt && python -m playwright install chromium
WATCH_CONFIG='{"use_date":"20261012","meal":"朝食","window":["06:30","07:00"],"adult_num":2,"child_ages":["03","00"]}' python check.py --dry-run
```
※ ヘッドレスではサイト側の対策で応答が返らないため、通常モード（Linux では `xvfb-run -a`）で動かします。
