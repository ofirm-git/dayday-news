#!/usr/bin/env python3
# coding: utf-8

import os
import json
import random
import string
import datetime
import requests
import feedparser
from dateutil import tz

# 查询设置（可按需调整）
QUERIES = {
    "global": "global news",
    "china": "China OR 中国",
    "market": "A股 OR 大A OR 上证 OR 深证"
}
MAX_HEADLINES_PER_SECTION = 20
MAX_TOTAL_CHARS = 1000

def random_uid(n=8):
    choices = string.ascii_letters + string.digits
    return ''.join(random.choice(choices) for _ in range(n))

def fetch_google_news(query, language='zh-CN', max_items=20):
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
    lines = [f"{heading}:"]
    for i, e in enumerate(entries, start=1):
        title = e.get('title','').strip()
        link = e.get('link','').strip()
        lines.append(f"{i}. {title} ({link})")
    return "\n".join(lines)

def generate_brief():
    # ---------- 修改开始 ----------
    # 明确使用北京时间 (UTC+8)
    beijing_tz = tz.gettz('Asia/Shanghai')
    now_beijing = datetime.datetime.now(beijing_tz)
    # 生成带时间的日期字符串
    datetime_str = now_beijing.strftime('%Y-%m-%d %H:%M:%S')
    # ---------- 修改结束 ----------

    sections = {}
    sources = []
    for k, q in QUERIES.items():
        items = fetch_google_news(q, max_items=MAX_HEADLINES_PER_SECTION)
        sections[k] = items
        for it in items:
            if it.get('link'):
                sources.append(it['link'])

    uid = random_uid(8)
    reflection = "信息瞬息万变，谨慎甄别与及时跟进是关键。"
    header = f"{reflection} [ID: {uid}]"

    global_block = build_section(sections['global'], "全球要闻")
    china_block = build_section(sections['china'], "中国要闻")
    market_block = build_section(sections['market'], "大A相关")

    full_text = f"{header}\n\n{global_block}\n\n{china_block}\n\n{market_block}"

    if len(full_text) > MAX_TOTAL_CHARS:
        full_text = full_text[:MAX_TOTAL_CHARS - 3] + "..."

    html_block = f"<p>{header}</p>\n<h3>全球要闻</h3>\n<ul>\n"
    for e in sections['global'][:MAX_HEADLINES_PER_SECTION]:
        html_block += f'<li><a href="{e.get("link","")}" target="_blank" rel="noopener noreferrer">{e.get("title","")}</a></li>\n'
    html_block += "</ul>\n"
    html_block += "<h3>中国要闻</h3>\n<ul>\n"
    for e in sections['china'][:MAX_HEADLINES_PER_SECTION]:
        html_block += f'<li><a href="{e.get("link","")}" target="_blank" rel="noopener noreferrer">{e.get("title","")}</a></li>\n'
    html_block += "</ul>\n"
    html_block += "<h3>大A相关</h3>\n<ul>\n"
    for e in sections['market'][:MAX_HEADLINES_PER_SECTION]:
        html_block += f'<li><a href="{e.get("link","")}" target="_blank" rel="noopener noreferrer">{e.get("title","")}</a></li>\n'
    html_block += "</ul>\n"

    payload = {
        'uid': uid,
        # ---------- 修改开始 ----------
        'date': datetime_str,   # 现在包含具体时间
        'title': f"每日要闻 {datetime_str}",  # 标题也加上时间
        # ---------- 修改结束 ----------
        'content': full_text,
        'html': html_block,
        'source_urls': list(dict.fromkeys(sources)),
        'raw': {'sections': sections}
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
    r = requests.post(url, headers=headers, json=payload, timeout=30)
    return r

if __name__ == '__main__':
    SUPS_URL = os.environ.get('SUPS_URL')
    SUPS_KEY = os.environ.get('SUPS_KEY')
    if not SUPS_URL or not SUPS_KEY:
        print("Missing SUPS_URL or SUPS_KEY environment variables")
        raise SystemExit(1)

    payload = generate_brief()
    print("Generated brief uid=", payload['uid'])
    r = insert_to_supabase(payload, SUPS_URL, SUPS_KEY)
    if r.status_code in (200, 201):
        print("Insert succeeded:", r.status_code)
        try:
            print("Inserted row:", r.json())
        except Exception:
            pass
        raise SystemExit(0)
    else:
        print("Insert failed:", r.status_code, r.text)
        raise SystemExit(2)
