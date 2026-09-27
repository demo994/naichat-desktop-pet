# -*- coding: utf-8 -*-
"""用法：把 mp3 放进 奶猫音乐盒 文件夹，然后运行本脚本，
自动从 lrclib.net 下载对应的同步歌词 .lrc（同名同目录）。"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request

MD = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])),
                  "奶猫音乐盒")


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "naichat-pet/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def norm(s):
    return re.sub(r"[\s\-_()\[\]]", "", s.lower())


def artist_hit(row, artist):
    an = norm(row.get("artistName", ""))
    return an and (norm(artist) in an or an in norm(artist))


def title_hit(row, title):
    tn = norm(row.get("trackName", ""))
    return norm(title) in tn or tn in norm(title)


def synth_lrc(plain, total_ms):
    lines = [l.strip() for l in plain.splitlines() if l.strip()]
    start = 20000
    span = max(3000, min(5200, (int(total_ms * 0.85) - start) //
                         max(1, len(lines))))
    out = []
    t = start
    for l in lines:
        out.append("[{:02d}:{:02d}.{:02d}]{}".format(
            t // 60000, t // 1000 % 60, t // 10 % 60, l))
        t += span
    return "\n".join(out)


def fetch(title, artist):
    q = urllib.parse.urlencode({"q": title})
    try:
        rows = get_json("https://lrclib.net/api/search?" + q)
    except Exception:
        rows = []
    cand = [r for r in rows if title_hit(r, title)] or rows
    synced = [r for r in cand if r.get("syncedLyrics")]
    pool = [r for r in synced if artist_hit(r, artist)] or synced
    if pool:
        pool.sort(key=lambda r: r.get("duration", 0))
        return pool[-1]["syncedLyrics"], "synced"
    plain = [r for r in cand if r.get("plainLyrics")]
    pool = [r for r in plain if artist_hit(r, artist)] or plain
    if pool:
        pool.sort(key=lambda r: r.get("duration", 0))
        best = pool[-1]
        return synth_lrc(best["plainLyrics"],
                         best.get("duration", 240) * 1000), "synth"
    return None, "miss"


ok, fail = [], []
for fn in sorted(os.listdir(MD)):
    if not fn.lower().endswith(".mp3"):
        continue
    stem = os.path.splitext(fn)[0]
    parts = [p.strip() for p in stem.split(" - ")]
    title, artist = parts[0], parts[1] if len(parts) > 1 else ""
    lrc_path = os.path.join(MD, stem + ".lrc")
    if os.path.exists(lrc_path):
        continue
    txt, how = fetch(title, artist)
    if txt:
        open(lrc_path, "w", encoding="utf-8").write(txt + "\n")
        ok.append((title, how))
    else:
        fail.append(title)
print("已下载歌词:", ok)
print("没找到的:", fail)
