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
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000

# 商品：名称, 图标, 价格, 效果类型, 数值, 心情, 属性名
SHOP = [
    ("清江鱼", "🐟", 20, "full", 40, 6, None),
    ("小鱼干", "🍤", 8, "full", 15, 2, None),
    ("奶油蛋糕", "🍰", 30, "full", 25, 8, None),
    ("红烧泡面", "🍜", 12, "full", 22, 4, None),
    ("矿泉水", "💧", 5, "water", 30, 0, None),
    ("珍珠奶茶", "🧋", 15, "water", 28, 6, None),
    ("冰美式咖啡", "☕", 18, "water", 22, 2, None),
    ("快乐水", "🥤", 12, "water", 24, 8, None),
    ("《十万个为什么》", "📖", 30, "stat", 1.0, 2, "智力"),
    ("限量口红", "💄", 30, "stat", 1.0, 2, "魅力"),
    ("小哑铃", "🏋️", 30, "stat", 1.0, 2, "力量"),
]

# 工作：名称, 图标, 要求属性, 要求等级, 工资, 工时(tick)
JOBS = [
    ("发传单", "📄", None, 0, 15, 240),
    ("洗碗工", "🧽", None, 0, 18, 260),
    ("摆摊烤肠", "🌭", None, 0, 22, 280),
    ("家教", "📚", "智力", 3, 45, 300),
    ("搬运工", "📦", "力量", 3, 45, 300),
    ("驻唱歌手", "🎤", "魅力", 5, 65, 320),
    ("健身教练", "🏋️", "力量", 6, 80, 340),
    ("程序员", "💻", "智力", 7, 110, 380),
    ("带货主播", "📱", "魅力", 8, 120, 380),
]


class Pet:
    def __init__(self):
        self.stage = 0
        self.progress = 0.0
        self.total_secs = 0.0
        self.hunger = 0.0
        self.money = 50
        self.thirst = 0.0
        self.stats = {"智力": 0.0, "魅力": 0.0, "力量": 0.0}
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
        self.blink = 0
        self.thinking = False
        self.think_until = 0
        self.fx = []
        self.say_text = ""
        self.say_until = 0
        self.squash = 0
        self.swipe = 0
        self.ball = None
        self.drag_to = (0, 0)
        self.slip = 0
        self.grab_pt = None
        self.happy = 60.0
        self.pet_count = 0
        self.pet_last = 0
        self.expr = "normal"
        self.expr_until = 0
        self._expr = "normal"
        self.shake = 0
        self.dizzy_pending = False
        self.remind_on = True
        self.remind_next = time.time() + 3600
        self.drag_dx = 0
        self.drag_dy = 0
        self.save_next = time.time() + 20
        self.laser_on = False
        self.laser = None
        self.laser_win = None
        self.laser_cv = None
        self.laser_target = False
        self.btn_down = False
        self.pokes = []
        self.flip_t = 0
        self.flip_dir = 1
        self.job = None
        self.study = None
        self._shop = None
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
            self.happy = d.get("happy", 60.0)
            self.money = d.get("money", 50)
            self.thirst = d.get("thirst", 0.0)
            st = d.get("stats", {})
            for kk in self.stats:
                self.stats[kk] = st.get(kk, 0.0)
        except Exception:
            pass

    def save(self):
        try:
            with open(self.path(), "w", encoding="utf-8") as f:
                json.dump({"stage": self.stage, "progress": self.progress,
                           "total_secs": self.total_secs,
                           "hunger": self.hunger, "happy": self.happy,
                           "money": self.money, "thirst": self.thirst,
                           "stats": self.stats},
                          f, ensure_ascii=False)
        except Exception:
            pass

    # ---------- interaction ----------
    def say(self, text, dur=180):
        self.mood = text
        self.say_text = text
        self.say_until = self.t + dur

    def set_expr(self, e, dur=150):
        self.expr = e
        self.expr_until = self.t + dur

    def pat(self):
        self.happy = min(100.0, self.happy + 3)
        self.set_expr("happy")
        self.fx.append({"type": "love", "x": random.randint(-16, 16),
                        "y": -50, "life": 30})
        self.say("喵～好舒服" if self.stage == 2 else "嗷呜～")

    def on_press(self, e):
        if self.state == "sleep":
            self.state = "rest"
            self.say("被吵醒啦")
            return
        self.pokes = [x for x in self.pokes if self.t - x < 120]
        self.pokes.append(self.t)
        if len(self.pokes) >= 5:
            self.pokes = []
            self.happy = max(0.0, self.happy - 3)
            self.set_expr("angry", 260)
            self.say("别戳了！生气啦！")
            if self.follow_on:
                self.state = "chase"
                self.timer = 200
                return
        self.drag_dx, self.drag_dy = e.x, e.y
        self.state = "drag"

    def on_drag(self, e):
        nx = self.root.winfo_x() + e.x - W // 2
        ny = self.root.winfo_y() + e.y - H + 80
        if abs(nx - self.x) + abs(ny - self.y) > 45:
            self.shake += 1
            if self.shake > 4:
                self.shake = 0
                self.dizzy_pending = True
                self.happy = max(0.0, self.happy - 4)
                self.set_expr("angry", 120)
                self.say("别晃我！要吐了！")
        self.x, self.y = nx, ny
        self.place_window()

    def on_release(self, e):
        if self.state == "chase":
            return
        if self.home_y - self.y > 150:
            self.dizzy_pending = True
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
        self.pet_count = self.pet_count + 1 \
            if self.t - self.pet_last < 90 else 1
        self.pet_last = self.t
        self.happy = min(100.0, self.happy + 3)
        if self.pet_count >= 3:
            self.set_expr("love", 240)
            self.say("最喜欢你啦！")
        else:
            self.set_expr("happy")
            self.say("被撸得好开心")

    def toggle_remind(self):
        self.remind_on = not self.remind_on
        self.remind_next = time.time() + 3600
        self.say("会提醒你喝水" if self.remind_on else "好吧不提醒了")

    def show_status(self):
        names = {0: "奶龙宝宝", 1: "少年奶龙", 2: "奶猫"}
        def bar(v):
            n = max(0, min(10, int(round(v / 10))))
            return "▓" * n + "░" * (10 - n)
        secs = int(self.total_secs)
        need = "MAX" if self.stage >= 2 else \
            f"{self.progress:.1f}/{self.evo_needs[self.stage]}"
        lines = [f"形态：{names[self.stage]}",
                 f"金币：{self.money} 🪙",
                 f"饱腹：{bar(100 - self.hunger)}",
                 f"水分：{bar(100 - self.thirst)}",
                 f"心情：{bar(self.happy)}",
                 f"智力 Lv.{int(self.stats['智力'])}"
                 f"　魅力 Lv.{int(self.stats['魅力'])}"
                 f"　力量 Lv.{int(self.stats['力量'])}",
                 f"进化进度：{need}",
                 f"累计在线：{secs // 3600}小时{secs % 3600 // 60}分"]
        w = tk.Toplevel(self.root)
        w.title("奶猫状态面板")
        w.attributes("-topmost", True)
        for s in lines:
            tk.Label(w, text=s, font=("Microsoft YaHei", 10),
                     padx=16, pady=4, anchor="w").pack(fill="x")
        w.resizable(False, False)

    def on_menu(self, e):
        m = tk.Menu(self.root, tearoff=0)
        m.add_command(label="喂清江鱼（20金）", command=self.feed)
        m.add_command(label="商店购物", command=self.open_shop)
        lm = tk.Menu(m, tearoff=0)
        lm.add_command(label="读书（智力+）",
                       command=lambda: self.start_study("智力"))
        lm.add_command(label="唱歌（魅力+）",
                       command=lambda: self.start_study("魅力"))
        lm.add_command(label="健身（力量+）",
                       command=lambda: self.start_study("力量"))
        m.add_cascade(label="学习成长", menu=lm)
        jm = tk.Menu(m, tearoff=0)
        for jb in JOBS:
            nm, icon, stat, req, pay, dur = jb
            if stat:
                label = "%s%s %d金 · 需%sLv.%d" % (icon, nm, pay, stat, req)
                ok = int(self.stats[stat]) >= req
            else:
                label = "%s%s %d金" % (icon, nm, pay)
                ok = True
            jm.add_command(label=label,
                           state=("normal" if ok else "disabled"),
                           command=lambda j=jb: self.start_work(j))
        m.add_cascade(label="打工赚钱", menu=jm)
        m.add_command(label="摸摸头", command=self.pat)
        m.add_command(label="玩毛线球", command=self.start_play)
        m.add_command(label=("激光逗猫棒：开" if self.laser_on
                             else "激光逗猫棒"),
                      command=self.toggle_laser)
        m.add_command(label="猜拳", command=self.play_rps)
        m.add_command(label="过来", command=self.call_here)
        m.add_command(label="翻跟头", command=self.do_flip)
        m.add_command(label=("喝水提醒：开" if self.remind_on
                             else "喝水提醒：关"),
                      command=self.toggle_remind)
        m.add_command(label="查看状态", command=self.show_status)
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

    # ---------- laser teaser ----------
    def toggle_laser(self):
        if self.state == "sleep":
            self.say("先把我叫醒啦")
            return
        self.laser_on = not self.laser_on
        if self.laser_on:
            self.say("红点逗猫棒！点一下桌面试试", 260)
        else:
            self.kill_laser()
            self.say("不玩红点了")

    def ensure_laser_win(self):
        if self.laser_win is not None:
            return
        w = tk.Toplevel(self.root)
        w.overrideredirect(True)
        w.attributes("-transparentcolor", COLORKEY)
        w.attributes("-topmost", True)
        cv = tk.Canvas(w, width=36, height=36, bg=COLORKEY,
                       highlightthickness=0)
        cv.pack()
        cv.create_oval(13, 13, 23, 23, fill="#FF2A2A", outline="")
        cv.create_oval(8, 8, 28, 28, outline="#FF7B6B")
        cv.create_oval(4, 4, 32, 32, outline="#FFB3A6")
        self.laser_win, self.laser_cv = w, cv
        w.update_idletasks()
        h = user32.GetParent(w.winfo_id()) or w.winfo_id()
        user32.SetWindowLongW(h, GWL_EXSTYLE,
                              user32.GetWindowLongW(h, GWL_EXSTYLE)
                              | WS_EX_TOOLWINDOW | WS_EX_TRANSPARENT
                              | WS_EX_LAYERED)
        user32.SetWindowPos(h, -1, 0, 0, 0, 0, 1 | 2 | 0x10)

    def spawn_laser(self, x, y):
        if self.state == "sleep":
            return
        self.ensure_laser_win()
        self.laser = {"x": x, "y": y, "life": 300}
        self.laser_win.deiconify()
        if self.state in ("rest", "wander", "groom", "stretch", "look"):
            self.state = "wiggle"
            self.timer = 8
            self.say("红点！！", 90)

    def kill_laser(self):
        self.laser = None
        if self.laser_win is not None:
            self.laser_win.withdraw()

    def laser_tick(self):
        down = bool(user32.GetAsyncKeyState(0x01) & 0x8000)
        if down and not self.btn_down:
            mx, my = get_mouse()
            in_pet = (self.x - W // 2 < mx < self.x + W // 2 and
                      self.y - H + 80 < my < self.y + H - 80)
            if not in_pet:
                self.spawn_laser(mx, my)
        self.btn_down = down
        if self.laser:
            self.laser["x"] += random.uniform(-2.5, 2.5)
            self.laser["y"] += random.uniform(-2.5, 2.5)
            self.laser["x"] = max(self.L + 20, min(self.R - 20,
                                                    self.laser["x"]))
            self.laser["y"] = max(self.T + 20, min(self.B - 20,
                                                    self.laser["y"]))
            self.laser["life"] -= 1
            self.laser_win.geometry("+%d+%d" % (int(self.laser["x"]) - 18,
                                                int(self.laser["y"]) - 18))
            if self.laser["life"] <= 0:
                self.kill_laser()

    def feed(self):
        self.buy(SHOP[0])

    # ---------- shop ----------
    def buy(self, item):
        name, icon, cost, kind, val, hp, stat = item
        if self.money < cost:
            self.say("金币不够…去打工赚点吧", 220)
            self.set_expr("sad", 200)
            return False
        self.money -= cost
        if kind == "full":
            self.hunger = max(0.0, self.hunger - val)
            self.say(f"{name}！好好吃！")
        elif kind == "water":
            self.thirst = max(0.0, self.thirst - val)
            self.say(f"咕嘟咕嘟…{name}真解渴")
        else:
            old = int(self.stats[stat])
            self.stats[stat] += val
            new = int(self.stats[stat])
            if new > old:
                self.say(f"{stat}升到 Lv.{new}！解锁更多工作！", 260)
                self.fx.append({"type": "flash", "x": 0, "y": -20,
                                "life": 45})
            else:
                self.say(f"用了{name}，{stat}见长")
        self.happy = min(100.0, self.happy + hp)
        self.progress += 0.1
        self.fx.append({"type": "food", "x": 0, "y": -50, "life": 40})
        self.set_expr("love" if self.happy > 90 else "happy", 200)
        if self.state in ("idle", "rest", "wander"):
            self.state = "rest"
            self.timer = 40
        return True

    def open_shop(self):
        if self._shop is not None:
            try:
                if self._shop.winfo_exists():
                    self._shop.lift()
                    return
            except tk.TclError:
                pass
        w = tk.Toplevel(self.root)
        self._shop = w
        w.title("奶猫小卖部")
        w.attributes("-topmost", True)
        tk.Label(w, text="买了就地吃掉～",
                 font=("Microsoft YaHei", 9), fg="#888").pack(
                     anchor="w", padx=12, pady=(8, 0))
        top = tk.Label(w, font=("Microsoft YaHei", 11, "bold"), anchor="w")
        top.pack(fill="x", padx=12, pady=(2, 6))
        btns = []

        def refresh():
            top.config(text="💰 金币：%d" % self.money)
            for b, it in btns:
                b.config(state=("normal" if self.money >= it[2]
                                else "disabled"))

        for it in SHOP:
            row = tk.Frame(w)
            row.pack(fill="x", padx=10, pady=1)
            if it[3] == "stat":
                tip = "%s %s　%d金　%s+1级" % (it[1], it[0], it[2], it[6])
            else:
                k = "饱腹" if it[3] == "full" else "水分"
                tip = "%s %s　%d金　%s+%d" % (it[1], it[0], it[2], k, it[4])
            tk.Label(row, text=tip, width=26, anchor="w",
                     font=("Microsoft YaHei", 10)).pack(side="left")
            b = tk.Button(row, text="买", width=4,
                          command=lambda i=it: (self.buy(i), refresh()))
            b.pack(side="right")
            btns.append((b, it))
        refresh()
        w.resizable(False, False)

    # ---------- study & work ----------
    def _can_act(self):
        if self.state == "sleep":
            self.say("Zzz…睡着干不了活")
            return False
        if self.state in ("work", "study"):
            self.say("手上这事还没做完！")
            return False
        if self.hunger > 80 or self.thirst > 80:
            self.say("饿渴得没力气…先喂点吃的")
            self.set_expr("sad", 200)
            return False
        return True

    def start_study(self, stat):
        if not self._can_act():
            return
        self.state = "study"
        self.study = stat
        self.timer = 270
        self.say(f"开始修炼{stat}！")

    def study_tick(self):
        self.timer -= 1
        if self.timer % 60 == 30:
            self.say(random.choice(("认真中…", "知识就是清江鱼！",
                                    "学到了学到了")), 80)
        if self.timer <= 0:
            gain = random.uniform(0.7, 1.0)
            old = int(self.stats[self.study])
            self.stats[self.study] += gain
            new = int(self.stats[self.study])
            self.hunger = min(100.0, self.hunger + 4)
            self.thirst = min(100.0, self.thirst + 5)
            self.progress += 0.2
            if new > old:
                self.say(f"{self.study}升到 Lv.{new}！解锁更多工作！", 260)
                self.fx.append({"type": "flash", "x": 0, "y": -20,
                                "life": 45})
                self.set_expr("surprised", 160)
            else:
                self.say(f"{self.study} +{gain:.1f}（Lv.{new}）", 220)
                self.set_expr("happy", 160)
            self.study = None
            self.state = "rest"
            self.timer = 60

    def start_work(self, job):
        if not self._can_act():
            return
        if job[2] and int(self.stats[job[2]]) < job[3]:
            self.say("还没解锁…先去练%s！" % job[2], 220)
            self.set_expr("sad", 180)
            return
        self.state = "work"
        self.job = job
        self.timer = job[5]
        self.say(f"上班去：{job[0]}！")

    def work_tick(self):
        self.timer -= 1
        if self.timer % 90 == 45:
            self.say(random.choice(("搬砖中…", "努力赚钱！",
                                    "为了清江鱼！")), 80)
        if self.timer <= 0:
            name, icon, stat, req, pay, dur = self.job
            if stat:
                pay += max(0, int((self.stats[stat] - req) // 2))
            self.money += pay
            self.hunger = min(100.0, self.hunger + 8)
            self.thirst = min(100.0, self.thirst + 10)
            self.happy = max(0.0, self.happy - 2)
            self.progress += 0.3
            self.job = None
            self.state = "rest"
            self.timer = 80
            self.set_expr("happy", 180)
            self.say(f"上班赚到了 {pay} 金币！🪙", 240)
            self.fx.append({"type": "coin", "x": 0, "y": -60, "life": 40})

    def start_play(self):
        if self.state == "sleep":
            return
        self.state = "play"
        self.timer = 360
        bx = self.x + random.choice((-1, 1)) * random.randint(60, 100)
        self.ball = {"x": bx, "y": self.home_y - 60,
                     "vx": random.uniform(-5, 5), "vy": -4}
        self.say("毛线球！！")

    # ---------- mini games ----------
    def play_rps(self):
        if self.state == "sleep":
            self.say("Zzz…叫不应，在装睡")
            return
        d = tk.Toplevel(self.root)
        d.title("和我猜拳")
        d.attributes("-topmost", True)
        tk.Label(d, text="我数到三，出拳！",
                 font=("Microsoft YaHei", 12)).pack(pady=(12, 4))
        row = tk.Frame(d)
        row.pack(pady=8)
        ops = ("石头", "剪刀", "布")

        def throw(me):
            d.destroy()
            bot = random.randrange(3)
            if me == bot:
                self.say("平局！都出%s，默契～" % ops[me], 240)
                self.happy = min(100.0, self.happy + 1)
                self.set_expr("happy", 180)
            elif (me - bot) % 3 == 2:
                self.say("我出%s，我赢啦！哈哈" % ops[bot], 240)
                self.happy = min(100.0, self.happy + 4)
                self.progress += 0.2
                self.set_expr("smug", 240)
            else:
                self.say("你赢了…我再练练！", 240)
                self.happy = max(0.0, self.happy - 1)
                self.set_expr("sad", 240)

        for i, name in enumerate(ops):
            tk.Button(row, text=name, width=7,
                      font=("Microsoft YaHei", 11),
                      command=lambda i=i: throw(i)).pack(side="left",
                                                         padx=6)
        d.resizable(False, False)

    def call_here(self):
        if self.state == "sleep":
            self.say("Zzz…叫不应，在装睡")
            return
        self.state = "come"
        self.timer = 360
        self.say("来啦来啦！")

    def do_flip(self):
        if self.state == "sleep":
            self.say("睡着翻不动…")
            return
        self.state = "flip"
        self.flip_t = 0
        self.flip_dir = self.facing
        self.say("看我的！")

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
            self.thirst = min(100, self.thirst + 0.2)
            self.happy = max(0.0, self.happy - 0.04)
        if self.remind_on and time.time() > self.remind_next:
            self.remind_next += 3600
            self.say("主人，喝口水休息一下吧！", 260)
            self.set_expr("surprised", 160)
        if self.laser_on:
            self.laser_tick()
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
                if self.dizzy_pending:
                    self.dizzy_pending = False
                    self.set_expr("dizzy", 220)
                    self.say("头好晕…转圈圈", 220)
                    self.fx.append({"type": "star", "x": 0, "y": -90,
                                    "life": 60})
                else:
                    self.shake = 0
        elif self.state == "rest":
            self.timer -= 1
            if self.timer <= 0:
                self.state = "pick"
                self.timer = 1
        elif self.state == "pick":
            if time.localtime().tm_hour < 7 and random.random() < 0.6:
                self.set_expr("sleepy", 600)
                self.say("好困…先睡了", 240)
                self.state = "sleep"
            else:
                roll = random.random()
                if self.follow_on and roll < 0.55 and not self.laser_on:
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
            if self.laser_on and self.laser:
                self.laser_target = True
                lx, ly = self.laser["x"], self.laser["y"]
                d = math.hypot(lx - self.x, ly - self.y)
                self.target = (lx, min(ly, self.home_y))
            else:
                self.laser_target = False
                d, mx, my = self.dist_to_mouse()
                self.target = (mx, min(my, self.home_y))
            sp = 6.5 if self.stage == 2 else (5.5 if self.stage == 1 else 4.5)
            self.moving = self.nudge(sp)
            self.timer -= 1
            if d < 46 and (self.laser_target or self.pull_on):
                self.state = "pounce"
                self.timer = 9
            elif d < 40 or self.timer <= 0 or \
                    (d > 600 and not self.laser_target):
                self.state = "rest"
                self.timer = random.randint(30, 90)
                self.say("没追上，好累")
        elif self.state == "pounce":
            self.timer -= 1
            if self.timer <= 0:
                if self.laser_target and self.laser:
                    self.state = "rest"
                    self.timer = random.randint(40, 80)
                    self.happy = min(100.0, self.happy + 2)
                    self.progress += 0.1
                    self.set_expr("happy", 160)
                    self.fx.append({"type": "star", "x": 0, "y": -90,
                                    "life": 40})
                    self.say("拍到红点啦！")
                    self.kill_laser()
                else:
                    self.state = "bite"
                    self.timer = 30
                    self.say("啊呜！咬住！")
        elif self.state == "bite":
            self.timer -= 1
            self.hold_cursor(self.x + self.facing * 10, self.y - 30, 42)
            if self.timer % 12 == 6:
                mx, my = get_mouse()
                set_mouse(mx + random.randint(-5, 5),
                          my + random.randint(-5, 5))
                self.fx.append({"type": "bite", "x": random.randint(-14, 14),
                                "y": -34, "life": 14})
            if self.timer <= 0:
                self.state = "grab"
                self.timer = 16
                self.say("抓住啦！")
        elif self.state == "grab":
            self.timer -= 1
            self.hold_cursor(self.x + self.facing * 20, self.y - 26, 30)
            if self.timer <= 0:
                self.start_drag()
        elif self.state == "dragmouse":
            self.drag_tick()
        elif self.state == "come":
            self.come_tick()
        elif self.state == "flip":
            self.flip_tick()
        elif self.state == "study":
            self.study_tick()
        elif self.state == "work":
            self.work_tick()

        self.update_mood()
        self.place_window()
        self.draw()
        self.root.after(FPS_MS, self.tick)

    def hold_cursor(self, hx, hy, radius, snap=0.6):
        mx, my = get_mouse()
        if math.hypot(hx - mx, hy - my) > radius:
            set_mouse(mx + (hx - mx) * snap, my + (hy - my) * snap)

    def start_drag(self):
        self.state = "dragmouse"
        self.timer = 150
        tx = self.x + random.choice((-1, 1)) * random.randint(140, 320)
        self.drag_to = (max(self.L + 60, min(self.R - 60, tx)), self.home_y)
        self.say("把你鼠标拖走！")

    def drag_tick(self):
        self.timer -= 1
        dx = self.drag_to[0] - self.x
        if abs(dx) < 12 or self.timer <= 0:
            self.state = "rest"
            self.timer = random.randint(60, 140)
            self.set_expr("smug", 220)
            self.say("拖好啦，下次别乱动鼠标～")
            self.evo_check()
            return
        self.facing = 1 if dx > 0 else -1
        self.x += self.facing * 4.2
        self.y = min(self.y + 1.5, self.home_y)
        self.clamp_pos()
        self.moving = True
        mx, my = get_mouse()
        gx = self.x + self.facing * 26
        gy = self.y - 26
        d = math.hypot(gx - mx, gy - my)
        if d > 340:
            self.slip += 1
            if self.slip > 30:
                self.state = "rest"
                self.timer = 60
                self.set_expr("angry", 200)
                self.say("拖不动…你力气太大")
                return
        else:
            self.slip = 0
        pull = min(0.8, 0.4 + d / 600)
        set_mouse(max(self.L, min(self.R, mx + (gx - mx) * pull)),
                  max(self.T, min(self.B, my + (gy - my) * pull)))
        if self.t % 14 == 0:
            self.fx.append({"type": "bite", "x": random.randint(-10, 10),
                            "y": -30, "life": 12})

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

    def come_tick(self):
        self.timer -= 1
        mx, my = get_mouse()
        self.target = (mx, self.home_y)
        self.moving = self.nudge(4.8)
        if abs(mx - self.x) < 40:
            self.state = "rest"
            self.timer = 30
            self.happy = min(100.0, self.happy + 1)
            self.set_expr("happy", 150)
            self.say("到啦！要我干嘛～")
        elif self.timer <= 0:
            self.state = "rest"
            self.timer = 60
            self.say("追不上你，哼")

    def flip_tick(self):
        self.flip_t += 1
        ph = self.flip_t / 36.0
        if ph >= 1.0:
            self.state = "rest"
            self.timer = 40
            self.y = self.home_y
            self.happy = min(100.0, self.happy + 2)
            self.progress += 0.1
            self.set_expr("smug", 220)
            self.say("怎么样，厉害吧！")
            self.fx.append({"type": "star", "x": 0, "y": -90, "life": 45})
        else:
            self.y = self.home_y - int(math.sin(ph * math.pi) * 80)
            self.x += self.flip_dir * 4.5
            self.clamp_pos()
            self.facing = self.flip_dir if ph < 0.5 else -self.flip_dir
            self.moving = True
            if self.flip_t % 8 == 0:
                self.fx.append({"type": "dust",
                                "x": random.randint(-24, 24),
                                "y": -4, "life": 12})

    def start_chase(self):
        if self.stage >= 2 and random.random() < 0.5:
            self.thinking = True
            self.think_until = self.t + random.randint(50, 110)
        self.state = "chase"
        self.timer = random.randint(160, 260)
        if self.laser_on and self.laser:
            self.say("盯上红点了！")
        else:
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
        if self.state in ("bite", "pounce", "grab", "dragmouse", "play",
                          "work", "study"):
            return
        if self.hunger > 75 and self.t > self.say_until:
            self.say("好饿…商店买条清江鱼吧", 240)
        elif self.thirst > 75 and self.t > self.say_until:
            self.say("好渴…想喝快乐水！", 240)
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
        if self.t < self.expr_until:
            self._expr = self.expr
        elif self.state == "sleep":
            self._expr = "sleepy"
        elif self.hunger > 75 or self.thirst > 75 or self.happy < 25:
            self._expr = "sad"
        else:
            self._expr = "normal"
        self.sqx = 1 + self.squash * 0.014
        self.sqy = 1 - self.squash * 0.02
        self.wig = math.sin(self.t * 1.3) * 5 * s \
            if self.state == "wiggle" else 0
        self.mouth_open = self.state == "pounce" or \
            (self.state == "bite" and self.timer % 12 >= 6) or \
            (self.state == "chase" and self.dist_to_mouse()[0] < 120)
        self.hop = 0
        if self.state == "pounce":
            self.hop = (9 - self.timer) * 3
        elif self.state == "bite":
            self.hop = 2 if self.timer % 12 < 6 else 0
        self.grab_pt = None
        if self.state in ("grab", "dragmouse"):
            mx, my = get_mouse()
            gx = max(12, min(W - 12, cx + (mx - self.x)))
            gy = max(50, min(H - 12, cy + (my - self.y)))
            self.grab_pt = (gx, gy)

        if self.stage == 0:
            self.draw_dragon(c, cx, y, s, f, baby=True)
        elif self.stage == 1:
            self.draw_dragon(c, cx, y, s, f, baby=False)
        else:
            self.draw_cat(c, cx, y, s, f)

        if self.state == "study":
            c.create_text(cx - 38 * s, y - 58 * s, text="📖",
                          font=("Segoe UI Emoji", int(15 * s)))
        elif self.state == "work" and self.job:
            c.create_text(cx - 38 * s, y - 58 * s, text=self.job[1],
                          font=("Segoe UI Emoji", int(15 * s)))
            fr = max(0.0, min(1.0, 1 - self.timer / float(self.job[5])))
            c.create_rectangle(cx - 26, y - 88, cx + 26, y - 82,
                               fill="#FFFFFF", outline="#AAAAAA")
            c.create_rectangle(cx - 26, y - 88, cx - 26 + int(52 * fr),
                               y - 82, fill="#FFC94A", outline="")

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

    def expr_eyes(self, c, px, ey, s, line_c, k=0):
        e = self._expr
        if e == "love":
            c.create_text(px, ey, text="❤", fill="#FF6B81",
                          font=("Arial", int(10 * s)))
            return True
        if e == "happy":
            c.create_arc(px - 6 * s, ey - 7 * s, px + 6 * s, ey + 5 * s,
                         start=20, extent=140, style="arc",
                         outline=line_c, width=2)
            return True
        if e in ("angry", "dizzy"):
            r = 5.5 * s if e == "angry" else 4 * s
            c.create_line(px - r, ey - r * 0.8, px + r, ey + r * 0.8,
                          width=2, fill=line_c)
            c.create_line(px - r, ey + r * 0.8, px + r, ey - r * 0.8,
                          width=2, fill=line_c)
            return True
        if e == "smug" and k < 0:
            c.create_line(px - 5.5 * s, ey + 1 * s, px + 5.5 * s, ey + 1 * s,
                          width=2, fill=line_c)
            return True
        return False

    def expr_mouth(self, c, cx, my, s, line_c):
        e = self._expr
        if e == "sad":
            c.create_arc(cx - 7 * s, my, cx + 7 * s, my + 10 * s,
                         start=20, extent=140, style="arc", outline=line_c)
            return True
        if e == "smug":
            c.create_arc(cx - 1 * s, my - 4 * s, cx + 9 * s, my + 4 * s,
                         start=180, extent=110, style="arc", outline=line_c)
            return True
        if e == "happy":
            c.create_oval(cx - 6 * s, my - 2 * s, cx + 6 * s, my + 8 * s,
                          fill="#E8747C", outline="")
            c.create_oval(cx - 3 * s, my + 2 * s, cx + 3 * s, my + 8 * s,
                          fill="#FF9EB5", outline="")
            return True
        return False

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
            if self.state == "dragmouse" or self._expr == "angry":
                c.create_line(px - 5 * s, ey - 4 * s, px + 5 * s, ey + 4 * s,
                              width=2, fill="#5B4A12")
                c.create_line(px - 5 * s, ey + 4 * s, px + 5 * s, ey - 4 * s,
                              width=2, fill="#5B4A12")
                bx = 7 * s
                c.create_line(px - bx, ey - 12 * s + (k * 2 * s * -f),
                              px + bx, ey - 9 * s + (k * 2 * s * f),
                              width=2, fill="#5B4A12")
            elif self.expr_eyes(c, px, ey, s, "#5B4A12", k):
                pass
            elif eyes_closed or self._expr == "sleepy":
                c.create_line(px - 5 * s, ey, px + 5 * s, ey, width=2,
                              fill="#5B4A12")
            else:
                big = 1.35 if self._expr == "surprised" else 1.0
                pr = 2.4 * s * (0.7 if self._expr == "surprised" else 1.0)
                dy = 2 * s if self._expr == "sad" else 0
                c.create_oval(px - 5 * s * big, ey - 6 * s * big,
                              px + 5 * s * big, ey + 6 * s * big,
                              fill="white", outline="")
                c.create_oval(px - pr + lx * 2, ey - pr + ly * 2 + dy,
                              px + pr + lx * 2, ey + pr + ly * 2 + dy,
                              fill="#3A2E0A", outline="")
        if self.mouth_open:
            c.create_oval(cx - 9 * s, hy + 8 * s, cx + 9 * s, hy + 22 * s,
                          fill="#D9534F", outline="")
        elif not self.expr_mouth(c, cx, hy + 10 * s, s, "#5B4A12"):
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
        if self.grab_pt:
            gx, gy = self.grab_pt
            for k in (-1, 1):
                wob = math.sin(self.t * 0.9 + (0 if k < 0 else 1.4)) * 3 * s
                px = (cx + gx) / 2 + k * 5 * s
                py = (hy + 14 * s + gy) / 2 + wob
                c.create_oval(px - 6 * s, py - 5 * s, px + 6 * s, py + 5 * s,
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
            if self.state == "dragmouse" or self._expr == "angry":
                c.create_line(px - 5.5 * s, ey - 4.5 * s,
                              px + 5.5 * s, ey + 4.5 * s,
                              width=2, fill="#6B5B4A")
                c.create_line(px - 5.5 * s, ey + 4.5 * s,
                              px + 5.5 * s, ey - 4.5 * s,
                              width=2, fill="#6B5B4A")
                c.create_line(px - 7 * s, ey - 12 * s - k * 2 * s,
                              px + 7 * s, ey - 9 * s + k * 2 * s,
                              width=2, fill="#6B5B4A")
            elif self.expr_eyes(c, px, ey, s, "#6B5B4A", k):
                pass
            elif eyes_closed or self._expr == "sleepy":
                c.create_arc(px - 6 * s, ey - 4 * s, px + 6 * s, ey + 6 * s,
                             start=200, extent=140, style="arc",
                             outline="#6B5B4A", width=2)
            else:
                big = 1.25 if self._expr == "surprised" else 1.0
                dy = 2 * s if self._expr == "sad" else 0
                c.create_oval(px - 6.5 * s * big, ey - 7.5 * s * big,
                              px + 6.5 * s * big, ey + 7.5 * s * big,
                              fill="#4A3B5C", outline="")
                c.create_oval(px - 3 * s + lx * 1.5,
                              ey - 4 * s + ly * 1.5 + dy,
                              px + 0.5 * s + lx * 1.5,
                              ey - 0.5 * s + ly * 1.5 + dy,
                              fill="white", outline="")
        c.create_polygon(cx - 3 * s, hy + 8 * s, cx + 3 * s, hy + 8 * s,
                         cx, hy + 12 * s, fill="#FF9EB5", outline="")
        if self.mouth_open:
            c.create_oval(cx - 7 * s, hy + 12 * s, cx + 7 * s, hy + 23 * s,
                          fill="#E8747C", outline="")
        elif not self.expr_mouth(c, cx, hy + 14 * s, s, "#6B5B4A"):
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
        if self.grab_pt:
            gx, gy = self.grab_pt
            for k in (-1, 1):
                wob = math.sin(self.t * 0.9 + (0 if k < 0 else 1.4)) * 3 * s
                px = (cx + gx) / 2 + k * 6 * s
                py = (hy + 20 * s + gy) / 2 + wob
                c.create_oval(px - 7 * s, py - 5.5 * s, px + 7 * s,
                              py + 5.5 * s, fill=belly, outline="")
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
            elif life["type"] == "coin":
                c.create_text(cx + e["x"] + math.sin(a * 0.4) * 6,
                              cy + e["y"] - (40 - a),
                              text="🪙", font=("Segoe UI Emoji", 15))
            elif life["type"] == "dust":
                r = 2 + (12 - a) * 0.4
                c.create_oval(cx + e["x"] - r, cy + e["y"] - r * 0.6,
                              cx + e["x"] + r, cy + e["y"] + r * 0.6,
                              fill="#E4D8C2", outline="")
            elif life["type"] == "star":
                ang = a * 0.25
                c.create_text(cx + math.cos(ang) * 34,
                              cy + e["y"] + math.sin(ang) * 8,
                              text="✦", fill="#FFD94A",
                              font=("Arial", 12))
                c.create_text(cx - math.cos(ang) * 34,
                              cy + e["y"] - math.sin(ang) * 8,
                              text="✦", fill="#FFD94A",
                              font=("Arial", 10))
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
