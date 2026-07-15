#!/usr/bin/env python3
# scripts/generate_brief.py
# 作用：抓取新闻 RSS，生成三段式简报（全球 / 中国 / 大A），将简报写入 Supabase 表 briefs

import feedparser
import requests
import datetime
import random
import string
import json
from dateutil import tz

# 配置：每个板块使用 Google News RSS 搜索（无需 API key）
QUERIES = {
    "global": "global news",
    "china": "China OR 中国",
    "market": "A股 OR 大A OR 上证 OR 深证"
}

MAX_HEADLINES_PER_SECTION = 6
MAX_TOTAL_CHARS = 1000  # 最终简报不超过 1000 字符

SUPS_URL = None
SUPS_KEY = None


def random_uid(n=8):
    choices = string.ascii_letters + string.digits
    return ''.join(random.choice(choices) for _ in range(n))


def fetch_google_news(query, language='zh-CN', max_items=6):
    q = requests.utils.requote_uri(query)
    rss_url = f"https://news.google.com/rss/search?q={q}&hl={language}&gl=US&ceid=US:{language}"
    d = feedparser.parse(rss_url)
    items = []
    for e in d.entries[:max_items]:
        title = e.get('title', '')
        link = e.get('link', '')
        summary = e.get('summary', '')
        items.append({'title': title, 'link': link, 'summary': summary})
    return items


def build_section(entries, heading):
    lines = [f"{heading}:" ]
    for i, e in enumerate(entries, start=1):
        title = e.get('title','').strip()
        link = e.get('link','').strip()
        # keep it short
        lines.append(f"{i}. {title} ({link})")
    return "\n".join(lines)


def generate_brief():
    sections = {}
    sources = []
    # fetch each section
    for k, q in QUERIES.items():
        items = fetch_google_news(q, max_items=MAX_HEADLINES_PER_SECTION)
        sections[k] = items
        for it in items:
            if it.get('link'):
                sources.append(it['link'])

    uid = random_uid(8)
    # a short reflection sentence in Chinese
    reflection = "信息瞬息万变，谨慎甄别与及时跟进是关键。"
    header = f"{reflection} [ID: {uid}]"

    # build textual content for three blocks
    global_block = build_section(sections['global'], "全球要闻")
    china_block = build_section(sections['china'], "中国要闻")
    market_block = build_section(sections['market'], "大A相关")

    full_content = f"{header}\n\n{global_block}\n\n{china_block}\n\n{market_block}"

    # trim to MAX_TOTAL_CHARS characters (unicode-aware)
    if len(full_content) > MAX_TOTAL_CHARS:
        full_content = full_content[:MAX_TOTAL_CHARS - 3] + '...'

    # prepare payload for Supabase
    payload = {
        'uid': uid,
        'date': datetime.datetime.now(tz.tzlocal()).date().isoformat(),
        'title': f"每日要闻 {datetime.datetime.now(tz.tzlocal()).date().isoformat()}",
        'content': full_content,
        'source_urls': list(dict.fromkeys(sources)),
        'raw': { 'sections': sections }
    }

    return payload


def insert_to_supabase(payload, sup_url, sup_key):
    url = sup_url.rstrip('/') + '/rest/v1/briefs'
    headers = {
        'apikey': sup_key,
        'Authorization': f'Bearer {sup_key}',
        'Content-Type': 'application/json',
        'Prefer': 'return=representation'
    }
    r = requests.post(url, headers=headers, data=json.dumps(payload))
    return r


if __name__ == '__main__':
    import os
    SUPS_URL = os.environ.get('SUPS_URL')
    SUPS_KEY = os.environ.get('SUPS_KEY')
    if not SUPS_URL or not SUPS_KEY:
        print('Missing SUPS_URL or SUPS_KEY environment variables')
        raise SystemExit(1)

    payload = generate_brief()
    print('Generated brief uid=', payload['uid'])
    r = insert_to_supabase(payload, SUPS_URL, SUPS_KEY)
    if r.status_code in (200,201):
        print('Insert succeeded:', r.status_code)
        # print returned row id if available
        try:
            print('Inserted row:', r.json())
        except Exception:
            pass
    else:
        print('Insert failed:', r.status_code, r.text)
        raise SystemExit(2)
