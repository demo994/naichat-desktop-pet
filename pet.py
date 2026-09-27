# -*- coding: utf-8 -*-
"""奶龙进化桌宠：从奶龙宝宝养大，最终进化成奶猫。
会间隔追鼠标，追到会咬着拉扯光标。右键打开菜单。"""

import ctypes
import ctypes.wintypes
import json
import math
import os
import random
import sys
import time
import tkinter as tk

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

COLORKEY = "#ff00fe"
W, H = 240, 220
FPS_MS = 33


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def get_mouse():
    p = POINT()
    user32.GetCursorPos(ctypes.byref(p))
    return p.x, p.y


def set_mouse(x, y):
    user32.SetCursorPos(int(x), int(y))


def work_area():
    r = ctypes.wintypes.RECT()
    user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(r), 0)
    return r.left, r.top, r.right, r.bottom


def single_instance():
    kernel32.CreateMutexW(None, False, "NaichatPetMutex61")
    return kernel32.GetLastError() != 183


GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080


class Pet:
    def __init__(self):
        self.stage = 0
        self.progress = 0.0
        self.total_secs = 0.0
        self.hunger = 0.0
        self.load()
        self.follow_on = True
        self.pull_on = True
        self.scale = 1.0
        self.mood = "正常"
        self.evo_t = 0

        self.L, self.T, self.R, self.B = work_area()
        self.x = (self.L + self.R) // 2
        self.y = self.B - 56
        self.home_y = self.B - 56
        self.state = "rest"
        self.timer = 0
        self.t = 0
        self.facing = 1
        self.moving = False
        self.chase_dir = 1
        self.target = None
        self.pull_next = 0
        self.pull_left = 0
        self.blink = 0
        self.thinking = False
        self.think_until = 0
        self.fx = []
        self.say_text = ""
        self.say_until = 0
        self.squash = 0
        self.swipe = 0
        self.ball = None
        self.drag_dx = 0
        self.drag_dy = 0
        self.save_next = time.time() + 20
        self.evo_times = [600, 1800]
        self.evo_needs = [5, 12]

        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.wm_attributes("-transparentcolor", COLORKEY)
        self.cv = tk.Canvas(self.root, width=W, height=H, bg=COLORKEY,
                            highlightthickness=0)
        self.cv.pack()
        self.cv.bind("<Button-1>", self.on_press)
        self.cv.bind("<B1-Motion>", self.on_drag)
        self.cv.bind("<ButtonRelease-1>", self.on_release)
        self.cv.bind("<Double-Button-1>", self.on_double)
        self.cv.bind("<Button-3>", self.on_menu)
        self.place_window()
        self.root.after(FPS_MS, self.tick)

    def hwnd(self):
        h = user32.GetParent(self.root.winfo_id())
        return h or self.root.winfo_id()

    def force_topmost(self):
        h = self.hwnd()
        user32.SetWindowLongW(h, GWL_EXSTYLE,
                              user32.GetWindowLongW(h, GWL_EXSTYLE)
                              | WS_EX_TOOLWINDOW)
        user32.SetWindowPos(h, -1, 0, 0, 0, 0, 1 | 2 | 0x10)

    # ---------- persistence ----------
    def path(self):
        if getattr(sys, "frozen", False):
            base = os.path.dirname(sys.executable)
        else:
            base = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base, "pet_state.json")

    def load(self):
        try:
            with open(self.path(), encoding="utf-8") as f:
                d = json.load(f)
            self.stage = d.get("stage", 0)
            self.progress = d.get("progress", 0.0)
            self.total_secs = d.get("total_secs", 0.0)
            self.hunger = d.get("hunger", 0.0)
        except Exception:
            pass

    def save(self):
        try:
            with open(self.path(), "w", encoding="utf-8") as f:
                json.dump({"stage": self.stage, "progress": self.progress,
                           "total_secs": self.total_secs,
                           "hunger": self.hunger}, f, ensure_ascii=False)
        except Exception:
            pass

    # ---------- interaction ----------
    def say(self, text, dur=180):
        self.mood = text
        self.say_text = text
        self.say_until = self.t + dur

    def on_press(self, e):
        if self.state == "sleep":
            self.state = "rest"
            self.say("被吵醒啦")
            return
        self.drag_dx, self.drag_dy = e.x, e.y
        self.state = "drag"

    def on_drag(self, e):
        self.x = self.root.winfo_x() + e.x - W // 2
        self.y = self.root.winfo_y() + e.y - H + 80
        self.place_window()

    def on_release(self, e):
        self.state = "fall"

    def on_double(self, e):
        if self.state == "sleep":
            self.state = "rest"
            return
        self.fx.append({"type": "love", "x": 0, "y": -50, "life": 30})
        if random.random() < 0.6:
            self.thinking = True
            self.think_until = self.t + 90
        self.progress += 0.1
        self.say("被撸得好开心")

    def on_menu(self, e):
        m = tk.Menu(self.root, tearoff=0)
        m.add_command(label="喂清江鱼", command=self.feed)
        m.add_command(label="玩毛线球", command=self.start_play)
        m.add_command(label=("跟随模式：开" if self.follow_on else "跟随模式：关"),
                      command=self.toggle_follow)
        m.add_command(label=("干扰拉扯：开" if self.pull_on else "干扰拉扯：关"),
                      command=self.toggle_pull)
        m.add_command(label=("唤醒" if self.state == "sleep" else "睡觉"),
                      command=self.toggle_sleep)
        m.add_command(label="放大一点", command=lambda: self.set_scale(1.2))
        m.add_command(label="缩小一点", command=lambda: self.set_scale(0.83))
        m.add_command(label="保存到文件", command=self.save)
        m.add_command(label="退出", command=self.root.destroy)
        m.tk_popup(e.x_root, e.y_root)

    def toggle_pull(self):
        self.pull_on = not self.pull_on
        self.say("会乖乖不拽鼠标" if not self.pull_on else "准备好咬鼠标啦")

    def toggle_follow(self):
        self.follow_on = not self.follow_on
        if not self.follow_on and self.state == "chase":
            self.state = "rest"

    def toggle_sleep(self):
        self.state = "rest" if self.state == "sleep" else "sleep"

    def set_scale(self, k):
        self.scale = max(0.6, min(1.8, self.scale * k))

    def feed(self):
        self.hunger = max(0.0, self.hunger - 40)
        self.progress += 1.0
        self.fx.append({"type": "food", "x": 0, "y": -50, "life": 40})
        self.say("清江鱼！最爱了！")
        if self.state in ("idle", "rest", "wander"):
            self.state = "rest"
            self.timer = 40

    def start_play(self):
        if self.state == "sleep":
            return
        self.state = "play"
        self.timer = 360
        bx = self.x + random.choice((-1, 1)) * random.randint(60, 100)
        self.ball = {"x": bx, "y": self.home_y - 60,
                     "vx": random.uniform(-5, 5), "vy": -4}
        self.say("毛线球！！")

    # ---------- movement ----------
    def place_window(self):
        cx = self.x + W / 2 - (W / 2)
        self.root.geometry(f"+{int(self.x - W // 2)}+{int(self.y - H + 80)}")

    def dist_to_mouse(self):
        mx, my = get_mouse()
        return math.hypot(mx - self.x, my - self.y), mx, my

    def clamp_pos(self):
        self.x = max(self.L + 30, min(self.R - 30, self.x))
        self.y = min(self.y, self.home_y)

    def nudge(self, sp):
        if self.thinking:
            return False
        dx = self.target[0] - self.x
        dy = self.target[1] - self.y
        d = math.hypot(dx, dy)
        if d < 2:
            return False
        self.facing = 1 if dx >= 0 else -1
        self.x += dx / d * sp
        self.y += dy / d * sp * 0.5
        self.clamp_pos()
        return True

    # ---------- main loop ----------
    def tick(self):
        self.t += 1
        if self.t % 60 == 1:
            self.force_topmost()
        if self.t % 30 == 0:
            self.total_secs += 1
            self.hunger = min(100, self.hunger + 0.15)
        if self.thinking and self.t > self.think_until:
            self.thinking = False
        if self.t % 90 == 0:
            self.blink = 6
        elif self.blink:
            self.blink -= 1
        if time.time() > self.save_next:
            self.save()
            self.save_next = time.time() + 20
        if self.squash:
            self.squash *= 0.86
            if self.squash < 0.3:
                self.squash = 0

        self.moving = False
        if self.state == "sleep":
            pass
        elif self.state == "drag":
            pass
        elif self.state == "fall":
            if self.y < self.home_y:
                self.y = min(self.home_y, self.y + 9)
                self.moving = True
            else:
                self.state = "rest"
                self.timer = 30
                self.squash = 8
        elif self.state == "rest":
            self.timer -= 1
            if self.timer <= 0:
                self.state = "pick"
                self.timer = 1
        elif self.state == "pick":
            roll = random.random()
            if self.follow_on and roll < 0.55:
                self.state = "wiggle"
                self.timer = 22
                self.say("锁定目标！", 90)
            elif roll < 0.75:
                self.target = (random.randint(self.L + 60, self.R - 60),
                               self.home_y)
                self.state = "wander"
            else:
                self.state = random.choice(("groom", "stretch", "look"))
                self.timer = random.randint(90, 170)
        elif self.state in ("groom", "stretch", "look"):
            self.timer -= 1
            if self.timer <= 0:
                self.state = "rest"
                self.timer = random.randint(40, 120)
        elif self.state == "wiggle":
            self.timer -= 1
            if self.timer <= 0:
                self.start_chase()
        elif self.state == "wander":
            self.moving = self.nudge(3.2)
            if not self.moving or random.random() < 0.005:
                self.state = "rest"
                self.timer = random.randint(60, 200)
        elif self.state == "play":
            self.play_tick()
        elif self.state == "chase":
            d, mx, my = self.dist_to_mouse()
            self.target = (mx, min(my, self.home_y))
            sp = 6.5 if self.stage == 2 else (5.5 if self.stage == 1 else 4.5)
            self.moving = self.nudge(sp)
            self.timer -= 1
            if d < 46 and self.pull_on:
                self.state = "pounce"
                self.timer = 9
            elif d < 40 or self.timer <= 0 or d > 600:
                self.state = "rest"
                self.timer = random.randint(30, 90)
                self.say("没追上，好累")
        elif self.state == "pounce":
            self.timer -= 1
            if self.timer <= 0:
                self.state = "pull"
                self.pull_left = random.randint(12, 22)
                self.pull_next = 0
                self.say("抓到啦！别想好好用鼠标！")
        elif self.state == "pull":
            mx, my = get_mouse()
            if self.t >= self.pull_next:
                ang = random.uniform(-0.6, 0.6) + \
                    math.atan2(self.y + 30 - my, self.x - mx)
                step = random.randint(7, 15)
                nx = mx + math.cos(ang) * step
                ny = my + math.sin(ang) * step
                set_mouse(max(self.L, min(self.R, nx)),
                          max(self.T, min(self.B, ny)))
                self.pull_next = self.t + random.randint(2, 4)
                self.pull_left -= 1
                self.fx.append({"type": "bite", "x": random.randint(-14, 14),
                                "y": -34, "life": 14})
            if self.pull_left <= 0:
                self.state = "rest"
                self.timer = random.randint(60, 140)
                self.say("咬累了，歇一会")
                self.evo_check()

        self.update_mood()
        self.place_window()
        self.draw()
        self.root.after(FPS_MS, self.tick)

    def play_tick(self):
        self.timer -= 1
        b = self.ball
        b["vy"] += 0.35
        b["x"] += b["vx"]
        b["y"] += b["vy"]
        if b["x"] < self.x - 100:
            b["x"] = self.x - 100
            b["vx"] = abs(b["vx"])
        if b["x"] > self.x + 100:
            b["x"] = self.x + 100
            b["vx"] = -abs(b["vx"])
        if b["y"] < self.y - 150:
            b["y"] = self.y - 150
            b["vy"] = abs(b["vy"])
        if b["y"] > self.home_y:
            b["y"] = self.home_y
            b["vy"] = -abs(b["vy"]) * 0.72
            b["vx"] *= 0.9
            if abs(b["vy"]) < 1.5:
                b["vy"] = 0
        d = math.hypot(b["x"] - self.x, b["y"] - self.y)
        self.target = (b["x"], min(b["y"], self.home_y))
        self.moving = self.nudge(5.2)
        if d < 42:
            b["vx"] = (1 if b["x"] >= self.x else -1) * random.uniform(6, 9)
            b["vy"] = -random.uniform(4, 8)
            self.swipe = 8
            if random.random() < 0.25:
                self.say("拍！毛线球！")
        if self.swipe:
            self.swipe -= 1
        if self.timer <= 0:
            self.state = "rest"
            self.timer = 80
            self.ball = None
            self.say("玩毛线球好累好开心")

    def start_chase(self):
        if self.stage >= 2 and random.random() < 0.5:
            self.thinking = True
            self.think_until = self.t + random.randint(50, 110)
        self.state = "chase"
        self.timer = random.randint(160, 260)
        self.say("盯上你的鼠标了！")

    def evo_check(self):
        pass

    def evo_try(self):
        if self.stage >= 2:
            return
        need_time = self.total_secs >= self.evo_times[self.stage]
        need_feed = self.progress >= self.evo_needs[self.stage]
        if (need_time and need_feed) or self.progress >= self.evo_needs[self.stage] * 2:
            self.stage += 1
            self.fx.append({"type": "flash", "x": 0, "y": -20, "life": 45})
            names = ["", "你进化成了少年奶龙！", "你进化成了奶猫！！"]
            self.say(names[self.stage], 300)
            self.save()

    def update_mood(self):
        if self.state in ("pull", "pounce", "play"):
            return
        if self.hunger > 75 and self.t > self.say_until:
            self.say("好饿…想吃清江鱼", 240)
        elif self.total_secs > 100 and self.stage == 0 and \
                (self.progress >= self.evo_needs[0] or
                 self.total_secs >= self.evo_times[0]):
            self.say("感觉要进化了！", 240)
            self.evo_try()

    # ---------- drawing ----------
    def draw(self):
        c = self.cv
        c.delete("all")
        s = self.scale
        cx, cy = W // 2, H - 80
        if self.state in ("chase", "pounce"):
            bob = math.sin(self.t * 0.55) * 3 * s
        elif self.state == "sleep":
            bob = math.sin(self.t * 0.09) * 2 * s + 4 * s
        else:
            bob = math.sin(self.t * 0.11) * 1.3 * s
        y = cy + bob
        f = self.facing
        self.sqx = 1 + self.squash * 0.014
        self.sqy = 1 - self.squash * 0.02
        self.wig = math.sin(self.t * 1.3) * 5 * s \
            if self.state == "wiggle" else 0
        self.mouth_open = self.state in ("pounce", "pull") or \
            (self.state == "chase" and self.dist_to_mouse()[0] < 120)
        self.hop = 0
        if self.state == "pounce":
            self.hop = (9 - self.timer) * 3

        if self.stage == 0:
            self.draw_dragon(c, cx, y, s, f, baby=True)
        elif self.stage == 1:
            self.draw_dragon(c, cx, y, s, f, baby=False)
        else:
            self.draw_cat(c, cx, y, s, f)

        if self.state == "play" and self.ball:
            b = self.ball
            bx, by = cx + (b["x"] - self.x), cy + (b["y"] - self.y)
            c.create_oval(bx - 10, by - 10, bx + 10, by + 10,
                          fill="#FF8FA3", outline="")
            c.create_arc(bx - 10, by - 10, bx + 10, by + 10,
                         start=30, extent=120, style="arc", outline="#D65A73")
            c.create_arc(bx - 10, by - 10, bx + 10, by + 10,
                         start=200, extent=120, style="arc", outline="#D65A73")
        self.draw_bubble(c, cx)
        self.draw_fx(c, cx, y)

    def draw_bubble(self, c, cx):
        if self.t >= self.say_until or not self.say_text:
            return
        txt = self.say_text if len(self.say_text) <= 12 \
            else self.say_text[:12]
        wpx = 13 * len(txt) + 20
        x1 = max(4, cx - wpx // 2)
        x2 = min(W - 4, x1 + wpx)
        c.create_polygon(cx - 5, 34, cx + 5, 34, cx, 44,
                         fill="white", outline="")
        c.create_oval(x1, 6, x2, 38, fill="white", outline="#CCCCCC")
        c.create_text((x1 + x2) // 2, 22, text=txt, fill="#555555",
                      font=("Microsoft YaHei", 9))

    def look_dir(self):
        if self.state == "look":
            return math.sin(self.t * 0.07) * 2.5, 0
        try:
            mx, my = get_mouse()
        except Exception:
            return 0, 0
        dx = max(-2, min(2, (mx - self.x) / 60))
        dy = max(-1.5, min(2, (my - self.y) / 90))
        return dx, dy

    def draw_dragon(self, c, cx, y, s, f, baby):
        head_r = (34 if baby else 38) * s
        body_r = (26 if baby else 32) * s
        color, belly, spine = "#FFD94A", "#FFF3C0", "#F5A623"
        c.create_oval(cx - 36 * s * f - 16 * s + self.wig, y + 6 * s,
                      cx - 36 * s * f + 16 * s + self.wig, y + 22 * s,
                      fill=color, outline="")
        hy = y - (40 if baby else 46) * s + self.hop * -1.2
        if self.state == "stretch":
            hy += 7 * s
        c.create_oval(cx - body_r * self.sqx, y - body_r * self.sqy + 8 * s,
                      cx + body_r * self.sqx,
                      y + body_r * self.sqy + 12 * s, fill=color, outline="")
        c.create_oval(cx - body_r * 0.6 * self.sqx, y - body_r * 0.4 + 10 * s,
                      cx + body_r * 0.6 * self.sqx, y + body_r + 10 * s,
                      fill=belly, outline="")
        step = math.sin(self.t * 0.5) * 4 * s if self.moving else 0
        c.create_oval(cx - 20 * s + self.wig, y + body_r + 4 * s + step,
                      cx - 2 * s + self.wig, y + body_r + 16 * s + step,
                      fill=color, outline="")
        c.create_oval(cx + 2 * s + self.wig, y + body_r + 4 * s - step,
                      cx + 20 * s + self.wig, y + body_r + 16 * s - step,
                      fill=color, outline="")
        if not baby:
            c.create_oval(cx - 6 * s, hy - head_r * 0.35, cx + 6 * s,
                          hy - head_r * 0.95, fill="#B4E33D", outline="")
            c.create_oval(cx - 6 * s + 16 * f * s, hy - head_r * 0.45,
                          cx + 6 * s + 16 * f * s, hy - head_r * 1.05,
                          fill="#B4E33D", outline="")
        else:
            c.create_oval(cx - 5 * s, hy - head_r * 0.4, cx + 5 * s,
                          hy - head_r * 0.85, fill="#B4E33D", outline="")
        c.create_oval(cx - head_r, hy - head_r * 0.75, cx + head_r,
                      hy + head_r * 0.75, fill=color, outline="")
        c.create_oval(cx - head_r * 0.55, hy - head_r * 0.1,
                      cx + head_r * 0.55, hy + head_r * 0.6,
                      fill=belly, outline="")
        lx, ly = self.look_dir()
        eyes_closed = self.state in ("sleep", "groom") or self.blink
        for k in (-1, 1):
            ey = hy - 8 * s
            px = cx + k * 16 * s
            if eyes_closed:
                c.create_line(px - 5 * s, ey, px + 5 * s, ey, width=2,
                              fill="#5B4A12")
            else:
                c.create_oval(px - 5 * s, ey - 6 * s, px + 5 * s, ey + 6 * s,
                              fill="white", outline="")
                c.create_oval(px - 2.4 * s + lx * 2, ey - 2.4 * s + ly * 2,
                              px + 2.4 * s + lx * 2, ey + 2.4 * s + ly * 2,
                              fill="#3A2E0A", outline="")
        if self.mouth_open:
            c.create_oval(cx - 9 * s, hy + 8 * s, cx + 9 * s, hy + 22 * s,
                          fill="#D9534F", outline="")
        else:
            c.create_line(cx - 7 * s, hy + 13 * s, cx + 7 * s, hy + 13 * s,
                          width=2, fill="#5B4A12")
        c.create_oval(cx + 22 * s - 4, hy + 4 * s, cx + 26 * s, hy + 10 * s,
                      fill="#FFB6B6", outline="")
        c.create_oval(cx - 26 * s, hy + 4 * s, cx - 22 * s + 4, hy + 10 * s,
                      fill="#FFB6B6", outline="")
        if self.state == "groom" and self.t % 60 < 32:
            c.create_oval(cx + 10 * s, hy + 6 * s, cx + 24 * s, hy + 18 * s,
                          fill=color, outline="")
        if self.state == "stretch":
            for k in (-1, 1):
                c.create_oval(cx + k * 10 * s - 8 * s, hy + 20 * s,
                              cx + k * 10 * s + 8 * s, hy + 32 * s,
                              fill=color, outline="")

    def draw_cat(self, c, cx, y, s, f):
        color, belly, patch = "#FFEFD8", "#FFFFFF", "#FFC98A"
        hy = y - 46 * s - self.hop * 1.1
        if self.state == "stretch":
            hy += 8 * s
        by = y - 14 * s
        tf = 0.5 if self.state in ("chase", "pounce", "pull", "play",
                                   "wiggle") else 0.15
        tail_w = math.sin(self.t * tf) * 12 * s
        c.create_line(cx + 26 * s + self.wig, by + 8 * s,
                      cx + 44 * s + self.wig, by - 6 * s + tail_w,
                      cx + 40 * s, hy + 6 * s,
                      width=int(8 * s), fill=patch,
                      capstyle="round", smooth=True)
        c.create_oval(cx - 26 * s * self.sqx, by - 16 * s * self.sqy,
                      cx + 26 * s * self.sqx, by + 22 * s * self.sqy,
                      fill=color, outline="")
        c.create_oval(cx - 15 * s * self.sqx, by - 2 * s,
                      cx + 15 * s * self.sqx, by + 20 * s,
                      fill=belly, outline="")
        for k in (-1, 1):
            c.create_arc(cx + k * 24 * s - 8 * s, by - 12 * s,
                         cx + k * 24 * s + 8 * s, by + 8 * s,
                         start=90 if k < 0 else 270, extent=55, style="arc",
                         outline=patch, width=int(3 * s))
        step = math.sin(self.t * 0.5) * 3 * s if self.moving else 0
        for k, off in ((-1, step), (1, -step)):
            c.create_oval(cx + k * 13 * s - 8 * s + self.wig,
                          by + 16 * s + off,
                          cx + k * 13 * s + 8 * s + self.wig,
                          by + 24 * s + off,
                          fill=belly, outline="")
        if self.state == "stretch":
            for k in (-1, 1):
                c.create_oval(cx + k * 22 * s - 8 * s, by + 12 * s,
                              cx + k * 22 * s + 8 * s, by + 22 * s,
                              fill=belly, outline="")
        for k in (-1, 1):
            bx = cx + k * 21 * s
            c.create_polygon(bx - 12 * s, hy - 10 * s,
                             bx + k * 4 * s, hy - 34 * s,
                             bx + 12 * s, hy - 12 * s,
                             fill=color, outline="")
            c.create_polygon(bx - 6 * s, hy - 14 * s,
                             bx + k * 3 * s, hy - 27 * s,
                             bx + 6 * s, hy - 15 * s,
                             fill="#FFB6C1", outline="")
        c.create_oval(cx - 32 * s, hy - 24 * s, cx + 32 * s, hy + 24 * s,
                      fill=color, outline="")
        for k in (-1, 0, 1):
            c.create_line(cx + k * 9 * s - 2 * s, hy - 23 * s + abs(k) * 3 * s,
                          cx + k * 9 * s + 2 * s, hy - 14 * s + abs(k) * 2 * s,
                          width=int(3 * s), fill=patch, capstyle="round")
        lx, ly = self.look_dir()
        eyes_closed = self.state in ("sleep", "groom") or self.blink
        for k in (-1, 1):
            px, ey = cx + k * 14 * s, hy - 2 * s
            if eyes_closed:
                c.create_arc(px - 6 * s, ey - 4 * s, px + 6 * s, ey + 6 * s,
                             start=200, extent=140, style="arc",
                             outline="#6B5B4A", width=2)
            else:
                c.create_oval(px - 6.5 * s, ey - 7.5 * s,
                              px + 6.5 * s, ey + 7.5 * s,
                              fill="#4A3B5C", outline="")
                c.create_oval(px - 3 * s + lx * 1.5, ey - 4 * s + ly * 1.5,
                              px + 0.5 * s + lx * 1.5, ey - 0.5 * s + ly * 1.5,
                              fill="white", outline="")
        c.create_polygon(cx - 3 * s, hy + 8 * s, cx + 3 * s, hy + 8 * s,
                         cx, hy + 12 * s, fill="#FF9EB5", outline="")
        if self.mouth_open:
            c.create_oval(cx - 7 * s, hy + 12 * s, cx + 7 * s, hy + 23 * s,
                          fill="#E8747C", outline="")
        else:
            c.create_arc(cx - 9 * s, hy + 9 * s, cx - 1 * s, hy + 16 * s,
                         start=200, extent=140, style="arc",
                         outline="#6B5B4A")
            c.create_arc(cx + 1 * s, hy + 9 * s, cx + 9 * s, hy + 16 * s,
                         start=200, extent=140, style="arc",
                         outline="#6B5B4A")
        for k in (-1, 1):
            for i in (-1, 1):
                c.create_line(cx + k * 22 * s, hy + 8 * s + i * 4 * s,
                              cx + k * 42 * s, hy + 4 * s + i * 8 * s,
                              fill="#D9C3A5")
        c.create_oval(cx + 20 * s, hy + 6 * s, cx + 28 * s, hy + 12 * s,
                      fill="#FFC1CC", outline="")
        c.create_oval(cx - 28 * s, hy + 6 * s, cx - 20 * s, hy + 12 * s,
                      fill="#FFC1CC", outline="")
        if self.mouth_open:
            paw = 14 * s * math.sin(self.t * 0.9)
            for k in (-1, 1):
                c.create_oval(cx + k * 18 * s - 7 * s, hy + 18 * s - paw,
                              cx + k * 18 * s + 7 * s, hy + 28 * s - paw,
                              fill=belly, outline="")
        if self.state == "groom" and self.t % 60 < 32:
            gp = abs(math.sin(self.t * 0.5)) * 4 * s
            c.create_oval(cx + 10 * s, hy + 8 * s - gp, cx + 22 * s,
                          hy + 18 * s - gp, fill=belly, outline="")
        if self.state == "play" and self.swipe and self.ball:
            dirx = 1 if self.ball["x"] >= self.x else -1
            ext = (8 - self.swipe) * 5 * s * dirx
            c.create_oval(cx + dirx * 26 * s + ext - 7 * s, by - 6 * s,
                          cx + dirx * 26 * s + ext + 7 * s, by + 8 * s,
                          fill=belly, outline="")

    def draw_fx(self, c, cx, cy):
        keep = []
        for e in self.fx:
            e["life"] -= 1
            if e["life"] <= 0:
                continue
            keep.append(e)
            a, b, life = e["life"], 40, e
            if life["type"] == "love":
                c.create_text(cx + e["x"] + math.sin(a * 0.3) * 8,
                              cy + e["y"] - (40 - a),
                              text="❤", fill="#FF6B81",
                              font=("Arial", int(12 + (40 - a) * 0.2)))
            elif life["type"] == "food":
                c.create_text(cx + e["x"], cy + e["y"] + (40 - a) * 0.8,
                              text="🐟", font=("Segoe UI Emoji", 16))
            elif life["type"] == "bite":
                c.create_text(cx + W * 0 + e["x"], cy + e["y"], text="💢",
                              font=("Segoe UI Emoji", 12))
            elif life["type"] == "flash":
                r = (45 - a) * 6
                c.create_oval(cx - r, cy - r - 30, cx + r, cy + r - 30,
                              outline="#FFE066", width=3)
        self.fx = keep
        if self.thinking:
            dots = "・" * (1 + (self.t // 20) % 3)
            c.create_text(cx + 60, cy - 120, text="?" + dots,
                          fill="#888888", font=("Microsoft YaHei", 11))
        if self.state == "sleep":
            c.create_text(cx + 40, cy - 110,
                          text="Z" * (1 + (self.t // 30) % 3),
                          fill="#9BB8E8", font=("Arial", 14, "bold"))


def main():
    if not single_instance():
        r = tk.Tk()
        r.withdraw()
        r.after(1, r.destroy)
        print("奶猫已经在跑啦，不要重复启动~")
        return
    pet = Pet()
    pet.root.title("奶猫桌宠")
    pet.root.mainloop()


if __name__ == "__main__":
    main()
