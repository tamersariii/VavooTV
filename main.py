#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vavoo_resolver.py - TÜRKİYE ÖZEL VERSİYON
Sadece Türkiye kanallarını çeker ve M3U oluşturur.
"""

import sys
import requests
import json
import os
import re

# config/domains.json dosyasından ayarları oku
try:
    with open(os.path.join(os.path.dirname(__file__), 'config/domains.json'), encoding='utf-8') as f:
        DOMAINS = json.load(f)
except Exception:
    DOMAINS = {}

VAVOO_DOMAIN = DOMAINS.get("vavoo", "vavoo.to")

def getAuthSignature():
    headers = {
        "user-agent": "okhttp/4.11.0",
        "accept": "application/json",
        "content-type": "application/json; charset=utf-8",
        "accept-encoding": "gzip"
    }
    data = {
        "token": "tosFwQCJMS8qrW_AjLoHPQ41646J5dRNha6ZWHnijoYQQQoADQoXYSo7ki7O5-CsgN4CH0uRk6EEoJ0728ar9scCRQW3ZkbfrPfeCXW2VgopSW2FWDqPOoVYIuVPAOnXCZ5g",
        "reason": "app-blur",
        "locale": "de",
        "theme": "dark",
        "metadata": {
            "device": {"type": "Handset", "brand": "google", "model": "Nexus", "name": "21081111RG", "uniqueId": "d10e5d99ab665233"},
            "os": {"name": "android", "version": "7.1.2", "abis": ["arm64-v8a", "armeabi-v7a", "armeabi"], "host": "android"},
            "app": {"platform": "android", "version": "3.1.20", "buildId": "289515000", "engine": "hbc85", "signatures": ["6e8a975e3cbf07d5de823a760d4c2547f86c1403105020adee5de67ac510999e"], "installer": "app.revanced.manager.flutter"},
            "version": {"package": "tv.vavoo.app", "binary": "3.1.20", "js": "3.1.20"}
        },
        "appFocusTime": 0,
        "playerActive": False,
        "playDuration": 0,
        "devMode": False,
        "hasAddon": True,
        "castConnected": False,
        "package": "tv.vavoo.app",
        "version": "3.1.20",
        "process": "app",
        "firstAppStart": 1743962904623,
        "lastAppStart": 1743962904623,
        "ipLocation": "",
        "adblockEnabled": True,
        "proxy": {"supported": ["ss", "openvpn"], "engine": "ss", "ssVersion": 1, "enabled": True, "autoServer": True, "id": "pl-waw"},
        "iap": {"supported": False}
    }
    try:
        resp = requests.post("https://www.vavoo.tv/api/app/ping", json=data, headers=headers, timeout=15)
        resp.raise_for_status()
        return resp.json().get("addonSig")
    except Exception as e:
        print(f"[DEBUG] Signature error: {e}", file=sys.stderr)
        return None

def get_channels(group=None):
    signature = getAuthSignature()
    if not signature:
        return []
    headers = {
        "user-agent": "okhttp/4.11.0",
        "accept": "application/json",
        "content-type": "application/json; charset=utf-8",
        "accept-encoding": "gzip",
        "mediahubmx-signature": signature
    }
    all_channels = []
    
    # SADECE TÜRKİYE KANALLARI İÇİN AYARLANDI
    groups = ["Turkey"]
    
    for g in groups:
        cursor = 0
        while True:
            data = {
                "language": "de", "region": "AT", "catalogId": "iptv", "id": "iptv",
                "adult": False, "search": "", "sort": "name", "filter": {"group": g},
                "cursor": cursor, "clientVersion": "3.0.2"
            }
            try:
                resp = requests.post(f"https://{VAVOO_DOMAIN}/mediahubmx-catalog.json", json=data, headers=headers, timeout=12)
                resp.raise_for_status()
                r = resp.json()
                items = r.get("items", [])
                all_channels.extend(items)
                cursor = r.get("nextCursor")
                if not cursor:
                    break
            except Exception:
                break
    return all_channels

def resolve_to_vavoo_iptv(url, channel_data):
    if isinstance(channel_data.get("ids"), dict) and channel_data["ids"].get("id"):
        return f"https://vavoo.to/vavoo-iptv/play/{channel_data['ids']['id']}"
    return re.sub(r'https?://[^/]+/play/', 'https://vavoo.to/vavoo-iptv/play/', url)

def normalize_vavoo_name(name):
    name = name.strip()
    name = re.sub(r'\s+\.[a-zA-Z]$', '', name)
    return name.upper()

if __name__ == "__main__":
    # GitHub Actions üzerinden çalışırken genelde --full-m3u parametresi kullanılır
    if "--full-m3u" in sys.argv or len(sys.argv) == 1:
        print("[INFO] Türkiye kanalları çekiliyor...")
        channels = get_channels()
        
        if not channels:
            print("[ERROR] Kanal bulunamadı!", file=sys.stderr)
            sys.exit(1)

        with open("vavoo_full.m3u", "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for ch in channels:
                name = ch.get("name", "Bilinmeyen").strip()
                url = ch.get("url")
                if not url:
                    continue
                real_link = resolve_to_vavoo_iptv(url, ch)
                group = ch.get("group", "Turkey")
                f.write(f'#EXTINF:-1 group-title="{group}",{name}\n')
                f.write(f"{real_link}\n")
        print(f"✅ vavoo_full.m3u (Türkiye) başarıyla oluşturuldu! ({len(channels)} kanal)")
    else:
        # Tek kanal arama modu (Opsiyonel kullanım için)
        input_arg = sys.argv[1]
        wanted = normalize_vavoo_name(input_arg)
        channels = get_channels()
        found = next((ch for ch in channels if normalize_vavoo_name(ch.get('name', '')) == wanted), None)
        if found and found.get('url'):
            print(resolve_to_vavoo_iptv(found['url'], found))
        else:
            print("NOT_FOUND", file=sys.stderr)
