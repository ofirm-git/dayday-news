#!/usr/bin/env python3
# scripts/render_index.py
# 拉取 Supabase 最近 7 日的 briefs 并渲染为静态 index.html

import os
import requests
import datetime
from dateutil import tz

TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>每日要闻简报</title>
  <style>
    body {{ font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial; max-width:900px; margin: 20px auto; padding: 0 16px; line-height:1.6; }}
    header {{ text-align:center; }}
    img.logo {{ max-width:200px; }}
    section.brief {{ border-bottom:1px solid #ddd; padding: 12px 0; }}
    .meta {{ color: #666; font-size: 0.9em; }}
    a {{ color: #0366d6; text-decoration: none; }}
  </style>
</head>
<body>
<header>
  <img class="logo" src="jinpng.png" alt="logo"/>
  <h1>每日要闻简报（最近一周）</h1>
  <p class="meta">自动生成，来源：公开新闻 RSS / Google News</p>
</header>
<main>
{items}
</main>
<footer>
  <p class="meta">更新于 {updated_at}（本地时间）</p>
</footer>
</body>
</html>
"""


def fetch_last_week(sup_url, sup_key):
    today = datetime.datetime.now(tz=tz.tzlocal()).date()
    since = (today - datetime.timedelta(days=6)).isoformat()
    url = sup_url.rstrip('/') + "/rest/v1/briefs"
    params = {
        'date': f'gte.{since}',
        'order': 'date.desc',
        'limit': '7',
        'select': '*'
    }
    headers = {
        'apikey': sup_key,
        'Authorization': f'Bearer {sup_key}',
    }
    r = requests.get(url, headers=headers, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def build_items(records):
    parts = []
    for rec in records:
        title = rec.get('title') or ''
        content_html = rec.get('html') or (rec.get('content') or '').replace("\n","<br/>")
        date = rec.get('date') or ''
        uid = rec.get('uid') or ''
        parts.append(f'<section class="brief"><h2>{title}</h2><p class="meta">{date} — ID: {uid}</p>{content_html}</section>')
    return "\n".join(parts)


if __name__ == '__main__':
    SUPS_URL = os.environ.get('SUPS_URL')
    SUPS_KEY = os.environ.get('SUPS_KEY')
    if not SUPS_URL or not SUPS_KEY:
        print('Missing SUPS_URL or SUPS_KEY environment variables')
        raise SystemExit(1)
    recs = fetch_last_week(SUPS_URL, SUPS_KEY)
    items_html = build_items(recs)
    updated_at = datetime.datetime.now(tz=tz.tzlocal()).strftime("%Y-%m-%d %H:%M:%S %Z")
    page = TEMPLATE.format(items=items_html, updated_at=updated_at)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(page)
    print("Rendered index.html with", len(recs), "items")
