#!/usr/bin/env python3
"""東京ディズニーリゾート レストラン空席監視 → LINE通知

東京ディズニーリゾートのオンライン予約サイトのレストランカレンダー（ログイン不要）を
Playwright で開き、対象日・対象時間帯に「予約する」枠があれば LINE (Messaging API broadcast)
で通知する。状態は state.json に保存し、同じ空きで繰り返し通知しない。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ===== 監視条件 =====
# 実際の条件は環境変数 WATCH_CONFIG（JSON）で渡す（GitHub Secrets に置き、リポジトリには含めない）。
# 例: {"restaurant_name":"レストラン名","name_cd":"RXXX0","contents_cd":"03","use_date":"20261231",
#      "meal":"夕食","window":["17:00","18:30"],"adult_num":2,"child_ages":["03","00"],
#      "deadline":"2026-12-31T17:00"}
# 未指定時は下のダミー値（動作確認用）。
_CFG = json.loads(os.environ.get("WATCH_CONFIG") or "{}")
RESTAURANT_NAME = _CFG.get("restaurant_name", "レストラン")
NAME_CD = _CFG.get("name_cd", "RLGC0")        # レストランコード（検索画面の toDetail(...) 第2引数）
CONTENTS_CD = _CFG.get("contents_cd", "03")   # 03 = ディズニーホテルのレストラン / 04 = パーク内
USE_DATE = _CFG.get("use_date", "20261015")   # 対象日 (YYYYMMDD)
MEAL = _CFG.get("meal", "夕食")               # 朝食 / 昼食 / 夕食
WINDOW = tuple(_CFG.get("window", ["17:00", "18:30"]))  # この時間帯（両端含む）に空きが出たら通知
ADULT_NUM = int(_CFG.get("adult_num", 2))
CHILD_AGES = list(_CFG.get("child_ages", []))  # 子どもの年齢コード（"00"=0才 … "06D"=6才未就学）
DEADLINE_JST = datetime.fromisoformat(_CFG.get("deadline", "2026-10-15T17:00"))  # これを過ぎたら監視終了
# ====================

JST = timezone(timedelta(hours=9))
BASE = "https://reserve.tokyodisneyresort.jp"
STATE_PATH = Path(__file__).with_name("state.json")
FAIL_ALERT_AFTER = 3  # 連続失敗がこの回数に達したら1回だけ警告通知


def calendar_url(use_date: str = USE_DATE) -> str:
    child_age = ("%7C".join(CHILD_AGES) + "%7C") if CHILD_AGES else ""
    return (
        f"{BASE}/restaurant/calendar/?nameCd={NAME_CD}&contentsCd={CONTENTS_CD}"
        f"&useDate={use_date}&adultNum={ADULT_NUM}&childNum={len(CHILD_AGES)}"
        f"&childAgeInform={child_age}&wheelchairCount=0&stretcherCount=0&reservationStatus=1"
    )


def now_jst() -> datetime:
    return datetime.now(JST).replace(tzinfo=None)


# ---------- state ----------
def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {"last_notified": [], "fail_count": 0, "alerted_down": False, "started": False, "log": []}


def save_state(st: dict) -> None:
    st["log"] = st.get("log", [])[-96:]  # 直近1日分だけ残す
    STATE_PATH.write_text(json.dumps(st, ensure_ascii=False, indent=2) + "\n")


# ---------- LINE ----------
def line_broadcast(text: str, dry_run: bool = False) -> None:
    token = os.environ.get("LINE_CHANNEL_TOKEN")
    if dry_run or not token:
        print("[LINE dry-run]" if dry_run else "[LINE skipped: no LINE_CHANNEL_TOKEN]")
        print(text)
        return
    req = urllib.request.Request(
        "https://api.line.me/v2/bot/message/broadcast",
        data=json.dumps({"messages": [{"type": "text", "text": text}]}).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        print("LINE broadcast:", r.status)


def fmt_date(use_date: str) -> str:
    d = datetime.strptime(use_date, "%Y%m%d")
    return f"{d.month}/{d.day}({'月火水木金土日'[d.weekday()]})"


def vacancy_message(slots: list[str]) -> str:
    first = slots[0]
    return (
        f"🚨【至急】{RESTAURANT_NAME} {fmt_date(USE_DATE)} {first} に空きが出ました！今すぐ予約を\n"
        f"空いた枠：{' / '.join(slots)}（{MEAL}・大人{ADULT_NUM}・子ども{len(CHILD_AGES)}）\n"
        f"▼この画面から予約（ログインが必要です）\n{calendar_url()}\n"
        f"※キャンセル枠はすぐ埋まります。確認時刻 {now_jst():%-m/%-d %H:%M}"
    )


# ---------- fetch ----------
def fetch_week(use_date: str, headless: bool = False, timeout_sec: int = 300) -> dict[str, dict[str, list[dict]]]:
    """カレンダーページを開き {meal: {date_label: [{time, ok}]}} を返す。待合室は順番待ちする。"""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        # ヘッドレスはサイトのボット対策で応答が返らないため、通常モード（CIでは xvfb-run 経由）で開く
        browser = p.chromium.launch(
            headless=headless, channel="chromium", args=["--disable-blink-features=AutomationControlled"]
        )
        ctx = browser.new_context(
            locale="ja-JP",
            timezone_id="Asia/Tokyo",
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
            ),
        )
        page = ctx.new_page()
        t0 = datetime.now()
        page.goto(calendar_url(use_date), wait_until="domcontentloaded", timeout=90_000)
        deadline = datetime.now() + timedelta(seconds=timeout_sec)
        while True:
            # 全セクション（朝食/夕食…）に空席表（li.full / li.reservationAble）が描画されたら完了
            boxes = page.locator(".boxRestaurant04").count()
            done = page.locator(".boxRestaurant04:has(.restaurantCalendarWeek li)").count()
            if boxes and done == boxes:
                page.wait_for_timeout(1000)
                print(f"calendar rendered in {(datetime.now() - t0).seconds}s")
                break
            if datetime.now() > deadline:
                snap = page.content()[:3000]
                browser.close()
                raise RuntimeError(f"timeout waiting for calendar. url={page.url}\n{snap}")
            page.wait_for_timeout(3000)

        data = page.evaluate(
            """() => {
              const out = {};
              for (const box of document.querySelectorAll('.boxRestaurant04')) {
                const meal = box.querySelector('.header img')?.alt || box.querySelector('.header')?.textContent.trim();
                const dates = [...box.querySelectorAll('.date li')].map(l => l.textContent.trim());
                const rows = [...box.querySelectorAll('.slider ul.cf')].map(u =>
                  [...u.querySelectorAll('li')].map(l => ({
                    time: l.querySelector('.time')?.textContent.trim(),
                    ok: l.classList.contains('reservationAble'),
                  })));
                const m = {};
                dates.forEach((d, i) => { m[d] = rows[i] || []; });
                out[meal] = m;
              }
              return out;
            }"""
        )
        browser.close()
    return data


def date_key(use_date: str) -> str:
    d = datetime.strptime(use_date, "%Y%m%d")
    return f"{d.month}/{d.day}"


def find_open_slots(week: dict, use_date: str, meal: str, window: tuple[str, str]) -> tuple[list[str], list[dict]]:
    meal_data = week.get(meal)
    if meal_data is None:
        raise RuntimeError(f"meal section '{meal}' not found. sections={list(week)}")
    key = date_key(use_date)
    row = None
    for label, slots in meal_data.items():
        # ラベル例: "20261009\n  10/9(金)"（非表示のYYYYMMDDを含む）
        if use_date in label or re.sub(r"[（(].*", "", label.split()[-1]) == key:
            row = slots
            break
    if row is None:
        raise RuntimeError(f"date {key} not found in {[l.split()[-1] for l in meal_data]}")
    lo, hi = window
    opens = [s["time"] for s in row if s["ok"] and s["time"] and lo <= s["time"] <= hi]
    return opens, row


# ---------- main ----------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="通知せず結果表示のみ・stateも更新しない")
    ap.add_argument("--date", default=USE_DATE)
    ap.add_argument("--meal", default=MEAL)
    ap.add_argument("--window", default=f"{WINDOW[0]}-{WINDOW[1]}")
    ap.add_argument("--test-notify", action="store_true", help="LINEに試験通知を送って終了")
    ap.add_argument("--headless", action="store_true", help="（検証用）ヘッドレスで開く。通常は弾かれる")
    args = ap.parse_args()
    window = tuple(args.window.split("-"))

    if args.test_notify:
        line_broadcast(
            f"✅ {RESTAURANT_NAME} 空席監視のテスト通知です\n{RESTAURANT_NAME} {fmt_date(USE_DATE)} {MEAL} "
            f"{WINDOW[0]}〜{WINDOW[1]} を15分おきに確認しています。\n空きが出たらこのトークに🚨で届きます。"
        )
        return 0

    st = load_state()
    now = now_jst()
    if now >= DEADLINE_JST:
        print("deadline passed; nothing to do")
        return 0
    if 3 <= now.hour < 5:
        print("site maintenance window (03:00-05:00 JST); skip")
        return 0

    try:
        week = fetch_week(args.date, headless=args.headless)
        opens, row = find_open_slots(week, args.date, args.meal, window)
    except Exception as e:  # noqa: BLE001
        print("FETCH FAILED:", e, file=sys.stderr)
        if args.dry_run:
            return 1
        st["fail_count"] = st.get("fail_count", 0) + 1
        st["log"].append({"t": now.isoformat(timespec="minutes"), "err": str(e)[:200]})
        if st["fail_count"] >= FAIL_ALERT_AFTER and not st.get("alerted_down"):
            line_broadcast(
                f"⚠️ {RESTAURANT_NAME} 空席監視が{st['fail_count']}回連続で失敗しています\n"
                f"サイト側の変更かブロックの可能性。手動で確認してください：\n{calendar_url()}"
            )
            st["alerted_down"] = True
        save_state(st)
        return 1

    print(f"{args.date} {args.meal}: " + " ".join(("OK" if s["ok"] else "x") + ":" + str(s["time"]) for s in row))
    print(f"open slots in {window[0]}-{window[1]}: {opens or 'none'}")
    if args.dry_run:
        return 0

    if st.get("alerted_down"):
        line_broadcast(f"✅ {RESTAURANT_NAME} 空席監視が復旧しました")
    st["fail_count"], st["alerted_down"] = 0, False
    if not st.get("started"):
        line_broadcast(
            f"👀 {RESTAURANT_NAME} 空席監視を開始しました\n{fmt_date(USE_DATE)} {MEAL} {WINDOW[0]}〜{WINDOW[1]}"
            f"（大人{ADULT_NUM}・子ども{len(CHILD_AGES)}）を15分おきに確認します。"
        )
        st["started"] = True

    if opens and opens != st.get("last_notified"):
        line_broadcast(vacancy_message(opens))
        st["last_notified"] = opens
    elif not opens:
        st["last_notified"] = []
    st["log"].append({"t": now.isoformat(timespec="minutes"), "open": opens})
    save_state(st)
    return 0


if __name__ == "__main__":
    sys.exit(main())
