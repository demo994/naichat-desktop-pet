# -*- coding: utf-8 -*-
"""用法：把 mp3 放进 奶猫音乐盒 文件夹，然后运行本脚本，
自动从 lrclib.net 下载对应的同步歌词 .lrc（同名同目录）。
桌宠播放没有歌词的歌时也会用同样的规则自动补歌词。"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request

MD = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])),
                  "奶猫音乐盒")

ALIAS = {"陶喆": ("david tao",),
         "孙燕姿": ("stefanie sun", "yanzi sun"),
         "张惠妹": ("a-mei", "amei"),
         "许嵩": ("vae",),
         "李玖哲": ("eric li",),
         "吕彦良": ("matt lv", "matt lu")}


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "naichat-pet/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def norm(s):
    return re.sub(r"[\s\-_()\[\]]", "", s.lower())


def fetch(title, artist):
    q = urllib.parse.urlencode({"q": title})
    try:
        rows = get_json("https://lrclib.net/api/search?" + q)
    except Exception:
        rows = []
    if not rows:
        return None
    tn, ar = norm(title), norm(artist)
    cand = [r for r in rows
            if tn in norm(r.get("trackName", "")) or
            norm(r.get("trackName", "")) in tn] or rows

    def hit(r):
        a = norm(r.get("artistName", ""))
        if not a:
            return False
        names = [ar] + [norm(x) for x in ALIAS.get(artist, ())]
        return any(n and (n in a or a in n) for n in names)

    def pick(pool):
        exact = [r for r in pool if hit(r)]
        if not exact:
            if len(pool) > 3:
                return None
        else:
            pool = exact
        full = [r for r in pool
                if "live" not in r.get("trackName", "").lower() and
                r.get("duration", 0) >= 60]
        if not full:
            full = [r for r in pool if r.get("duration", 0) >= 60] or pool
        full.sort(key=lambda r: r.get("duration", 0))
        return full[-1]

    best = pick([r for r in cand if r.get("syncedLyrics")])
    if best:
        return best["syncedLyrics"]
    best = pick([r for r in cand if r.get("plainLyrics")])
    if best:
        lines = [l.strip() for l in best["plainLyrics"].splitlines()
                 if l.strip()]
        start = 20000
        span = max(3000, min(5200, (int(best.get("duration", 240) * 850)
                                    - start) // max(1, len(lines))))
        t = start
        out = []
        for l in lines:
            out.append("[{:02d}:{:02d}.{:02d}]{}".format(
                t // 60000, t // 1000 % 60, t // 10 % 60, l))
            t += span
        return "\n".join(out)
    return None


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
    txt = fetch(title, artist)
    if txt:
        open(lrc_path, "w", encoding="utf-8").write(txt + "\n")
        ok.append(title)
    else:
        fail.append(title)
print("已下载歌词:", ok)
print("没找到的:", fail)
