# -*- coding: utf-8 -*-
"""奶龙进化桌宠：从奶龙宝宝养大，最终进化成奶猫。
会间隔追鼠标，追到会咬着拉扯光标。右键打开菜单。"""

import bisect
import ctypes
import ctypes.wintypes
import json
import math
import os
import random
import re
import sys
import threading
import time
import tkinter as tk
import urllib.parse
import urllib.request

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
        self.lrc_off = {}
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
        self.win_down = False
        self.win_last = -999
        self.lbtn = False
        self.lbtn_last = -999
        self.bienao = False
        self.last_act = 0
        self.but = None
        self._last_line = {}
        self.jump_t = 0
        self._mci = ctypes.windll.winmm.mciSendStringW
        self.song = None
        self.song_file = None
        self.song_len = 0
        self.song_t0 = 0.0
        self.song_pos0 = 0
        self.lyric = []
        self._lrc_times = []
        self.lyric_i = -1
        self.cur_line = ""
        self.prev_line = ""
        self.prev_until = 0
        self.line_no = 0
        self.sing_pose = "mic"
        self.ctrl_win = None
        self._btn_pause = None
        self._lrc_pending = None
        self.lyric_win = None
        self._lyric_cv = None
        self.lrc_off_cur = 0
        self.lrc_tag_cur = 0
        self.click_job = None
        self.press_x = 0
        self.press_y = 0
        self.press_t = 0.0
        self._status_w = None
        self._status_vars = []
        self._evo_btn = None
        self._evo_said = set()
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
            self.lrc_off = {str(k): int(v) for k, v in
                            d.get("lrc_off", {}).items()}
        except Exception:
            pass

    def save(self):
        try:
            with open(self.path(), "w", encoding="utf-8") as f:
                json.dump({"stage": self.stage, "progress": self.progress,
                           "total_secs": self.total_secs,
                           "hunger": self.hunger, "happy": self.happy,
                           "money": self.money, "thirst": self.thirst,
                           "stats": self.stats,
                           "lrc_off": self.lrc_off},
                          f, ensure_ascii=False)
        except Exception:
            pass

    # ---------- interaction ----------
    def say(self, text, dur=180):
        self.mood = text
        self.say_text = text
        self.say_until = self.t + dur

    # ---------- 台词系统：每种情境一个专属语料池 ----------
    LINES = {
        # 被摸 / 亲昵
        "pat_cat": ("喵～好舒服呀", "呼噜呼噜…", "蹭蹭你的手", "再摸一会会儿也行哦"),
        "pat_dragon": ("嗷呜～", "嘿嘿，痒痒的", "别停呀，继续摸", "尾巴都翘起来了"),
        "pat_happy": ("被撸得好开心", "就是这里，多来点", "舒服到想打呼噜", "眼睛眯成一条缝啦"),
        "pat_love": ("最喜欢你啦！", "最最最喜欢清江鱼了！", "心都化啦～", "想一直黏着你"),
        # 被打扰
        "wake_up": ("哎呀，被吵醒了", "嗯…干嘛把我叫醒", "睡得正香呢…"),
        "poke_angry": ("别戳了！生气啦！", "戳戳戳，戳不停是吧！", "再戳我可要咬人了！"),
        "shake": ("别晃我！要吐了！", "停下停下，头都晕了！", "我又不是拨浪鼓…"),
        "dizzy_land": ("头好晕…转圈圈", "被晃成浆糊了…", "放我下来…呕"),
        # 菜单指令的回应（日常口吻）
        "remind_on": ("好嘞，到时候我会提醒你喝水", "知道啦，我会盯着你喝水的"),
        "remind_off": ("好吧，那就不提醒啦", "收到，这次听你的"),
        "pull_off": ("好嘛，那我乖乖不拽鼠标", "知道啦，忍住不去咬鼠标"),
        "pull_on": ("嘿嘿，准备好咬鼠标啦", "那我可就不客气了哦"),
        "need_awake": ("先把我叫醒啦", "睡着了什么都做不了…", "Zzz…要先醒来才能办这事"),
        "laser_on": ("红点逗猫棒！点一下桌面试试", "看到红点我就控制不住自己！", "点一下桌面，把红点放出来！"),
        "laser_off": ("不玩红点了", "红点收起来啦，有点舍不得", "好吧，红点下次再见"),
        # 追鼠标 / 红点
        "lock_target": ("锁定目标！", "蹲下，扭扭，起跳！", "蓄力中…扑！"),
        "chase_start": ("盯上你的鼠标了！", "你的鼠标看起来好好吃", "目标：鼠标！"),
        "chase_start_laser": ("盯上红点了！", "红点跑不掉的！", "眼睛锁定红点"),
        "bite": ("啊呜！咬住！", "吃我一口！", "哈！抓到啦"),
        "grab": ("抓住啦！", "双手拿下！", "这下跑不掉了嘿嘿"),
        "drag_start": ("把你鼠标拖走！", "跟我走吧你～", "搬家搬家，挪挪鼠标"),
        "drag_ok": ("拖好啦，下次别乱动鼠标～", "放这里比较好看", "搬完了，风景不错"),
        "drag_fail": ("拖不动…你力气太大", "纹丝不动…可恶", "怎么这么沉！"),
        "chase_fail": ("没追上，好累", "追累了，休息一下", "今天状态不好，下次一定"),
        "laser_dot": ("红点！！", "红点出现了！！", "在那在那！红点！"),
        "laser_catch": ("拍到红点啦！", "扑到了！红点被我按住了！", "红点输给了本猫，嘿嘿"),
        # 玩耍 / 小游戏
        "ball_see": ("毛线球！！", "是毛线球！！眼睛发光", "球球！我的最爱！"),
        "ball_hit": ("拍！毛线球！", "左一拍右一拍！", "球球别跑！"),
        "ball_end": ("玩毛线球好累好开心", "球都累了，我也是", "下次再大战三百回合"),
        "sleep_deaf": ("Zzz…叫不应，在装睡", "呼…呼…（假装没听见）", "Zzz…（耳朵动了动，身体没动）"),
        "rps_tie": ("平局！都出{op}，默契～", "咦，出一样的！", "心有灵犀呀，都是{op}"),
        "rps_win": ("我出{op}，我赢啦！哈哈", "赢啦！{op}万岁！", "猜拳之王正是在下！"),
        "rps_lose": ("你赢了…我再练练！", "不服不服，再来一局！", "这次是让你赢的…才怪"),
        "come_go": ("来啦来啦！", "来啦～找我有事吗", "这就来这就来"),
        "come_arrive": ("到啦！要我干嘛～", "到！有什么吩咐", "我到了，说吧说吧"),
        "come_fail": ("追不上你，哼", "你走太快了啦", "腿短，追丢了…"),
        "flip_no": ("睡着翻不动…", "睡着翻会闪到腰的", "叫醒我再翻嘛"),
        "flip_go": ("看我的！", "表演一个！", "看好咯～"),
        "flip_done": ("怎么样，厉害吧！", "完美落地！", "帅吧？快夸我两句"),
        # 商店 / 吃喝
        "no_money": ("金币不够…去打工赚点吧", "钱包空空…等我打份工先", "买不起…我去搬砖赚钱！"),
        "eat": ("{name}！好好吃！", "呜哇，是{name}！", "{name}一口闷！", "吃到{name}就是幸福猫"),
        "drink": ("咕嘟咕嘟…{name}真解渴", "哈～好喝，{name}！", "{name}下肚，浑身清爽！"),
        # 学习 / 打工
        "lvup": ("{stat}升到 Lv.{new}！解锁更多工作！", "{stat}升级啦！离好工作更近了", "{stat} Lv.{new}！我变强了"),
        "stat_use": ("用了{name}，{stat}见长", "{name}果然有用，{stat}涨啦", "感觉{stat}提升了一点"),
        "sleep_busy": ("Zzz…睡着干不了活", "睡着呢…梦里也在搬砖", "想让我干活得先叫醒我"),
        "busy": ("手上这事还没做完！", "等一下嘛，先忙完这个", "马上就好，别急"),
        "weak": ("饿渴得没力气…先喂点吃的", "肚子咕咕叫了…来点吃的嘛", "又饿又渴，使不上劲…"),
        "study_start": ("开始修炼{stat}！", "认真读书，{stat}冲冲冲", "今天也要好好学习"),
        "study_mid": ("认真中…", "知识就是清江鱼！", "看懂了，大概…", "学霸猫养成中"),
        "study_done": ("学到了学到了！{study} +{gain:.1f}", "合上书，{study}涨啦 +{gain:.1f}", "{study} +{gain:.1f}（Lv.{new}）"),
        "job_locked": ("还没解锁…先去练{stat}！", "{stat}够格才能干这个呀", "{stat}还不够，报不了名"),
        "job_start": ("上班去：{job}！", "打工人，打工猫！", "为了罐罐，出发"),
        "job_mid": ("搬砖中…", "努力赚钱！", "认真打工，拒绝摸鱼", "带薪喘气中…"),
        "job_done": ("上班赚到了 {pay} 金币！🪙", "发工资啦！{pay} 金币！", "{pay} 金币到手，晚上加个餐"),
        # 生理 / 状态
        "hungry": ("好饿…商店买条清江鱼吧", "肚子空空的…有鱼吗", "再不吃我就要饿扁了"),
        "thirsty": ("好渴…想喝快乐水！", "嘴巴干干，想找水水", "有水吗？快乐水最好"),
        "water_remind": ("主人，喝口水休息一下吧！", "盯了你这么久，该喝水啦", "工作这么久，喝口水嘛"),
        "early_sleepy": ("好困…先睡了", "眼皮打架了…晚安", "清晨的猫只想睡觉"),
        "evo_soon": ("感觉快了…再喂我一点吧", "身体里有股暖流…", "离进化又近了一步！"),
        "evo_ready": ("进化条件达成啦！打开状态面板点「进化」按钮～",
                      "我…我要进化了！快去状态面板按进化按钮！",
                      "感觉充满了力量！点状态面板的进化按钮试试！"),
        "evo_done": ("进化成{name}！", "睁开眼睛，世界都不一样了", "全新形态——{name}！"),
        # 自娱自乐
        "tail": ("追尾巴！嘿嘿", "今天非要抓住这条尾巴不可", "尾巴别跑！"),
        "tail_end": ("追尾巴真好玩", "尾巴居然挑衅我", "抓到尾巴了…才怪"),
        "butterfly": ("哪来的蝴蝶！？", "有蝴蝶！我要扑！", "它居然在我头顶上飞！"),
        "butterfly_end": ("蝴蝶飞走啦～下次再玩", "飞走了…算你跑得快", "下次我一定扑得到"),
        "sing": ("清清嗓子～", "开演唱会啦！", "今晚，只唱一首"),
        "sing_end": ("唱完啦，感觉自己帅帅的", "今天嗓子状态不错", "可惜没有观众，唉"),
        "roll": ("我自己打个滚", "地上凉凉的，滚一滚", "先热个身，打个滚"),
        "roll_end": ("打滚真开心！", "滚完一身轻", "我就是滚圈小猫"),
        "mirror": ("镜子里的猫好帅", "这也太好看了吧（指镜子）", "跟镜子里的猫聊两句"),
        "mirror_end": ("镜子里的我最可爱", "他怎么跟我长得一模一样", "和镜子里的自己握手言和"),
        "solo_pounce": ("扑！", "差一点…没扑着", "你别跑呀"),
        "solo_dizzy": ("转得好晕…", "有点晕，扶我一下", "世界在转圈圈…"),
        # 打哈欠 / 躲猫猫 / 打喷嚏
        "yawn": ("哈～呜呜呜～", "睡不醒…根本睡不醒", "这空气太舒服了，忍不住打哈欠"),
        "peek": ("猜猜我在不在", "看不到我～看不到我～", "我是一只隐身猫"),
        "peek_end": ("Surprise！吓到没", "咦，我在这儿呢～", "被发现了，嘿嘿"),
        "sneez_pre": ("阿…阿…", "鼻子有点痒…", "感觉要有大事发生…"),
        "sneeze": ("哈啾！！", "哈——啾！！", "阿嚏！！把自己吓了一跳"),
        # 欢迎回家 / 讨食
        "greet": ("你回来啦！", "想死你了～", "你终于回来了！"),
        "beg": ("给口吃的嘛", "清江鱼…就一条", "肚子空空，爪爪合十"),
        # 踩奶 / 母鸡蹲 / 邀玩
        "knead": ("给你踩踩奶～", "左爪右爪，踩踩踩", "这个床床很软"),
        "loaf": ("四脚一缩，趴下", "变成一块猫面包", "安静地攒攒力气"),
        "playbow": ("一起来玩嘛！", "屁股翘高，准备扑～", "来追我呀！"),
        # 点歌台 / 唱歌
        "music_start": ("清清嗓子，麦霸上线🎤", "前奏一响，谁都拦不住我",
                        "好吧，这首我会唱！"),
        "music_none": ("歌单是空的…", "去 奶猫音乐盒 文件夹里放几首mp3吧",
                       "没歌我唱什么呀～"),
        "music_stop": ("咦，怎么断了", "好吧好吧，那我先不唱了",
                       "切歌？那我再挑一首"),
        "music_end": ("唱完啦，掌声在哪里👏", "呼～嗓子冒烟了",
                      "谢谢谢谢，我只是只爱唱歌的猫"),
        "sing_la": ("啦啦啦～♪", "喔～🎵 喔～🎵", "嗯嗯～♪～",
                    "♪ 嘟嘟嘟～", "跟着节奏摇尾巴～", "🎵 喵呜喵呜～"),
        "music_err": ("这歌放不出来呀…", "格式不对不对，我嗓子都等干了"),
    }

    def say_line(self, key, wait=180, **fmt):
        pool = self.LINES[key]
        last = self._last_line.get(key)
        picks = [p for p in pool if p != last] if len(pool) > 1 else list(pool)
        line = random.choice(picks) if len(picks) > 1 else picks[0]
        self._last_line[key] = line
        if fmt:
            line = line.format(**fmt)
        self.say(line, wait)

    def set_expr(self, e, dur=150):
        self.expr = e
        self.expr_until = self.t + dur

    def pat(self):
        self.happy = min(100.0, self.happy + 3)
        self.set_expr("happy")
        self.fx.append({"type": "love", "x": random.randint(-16, 16),
                        "y": -50, "life": 30})
        self.say_line("pat_cat" if self.stage == 2 else "pat_dragon")

    def note_user_act(self):
        gap = self.t - self.last_act
        self.last_act = self.t
        if gap > 2700 and self.state in ("rest", "pick", "wander",
                                         "groom", "stretch", "look",
                                         "yawn", "peek", "sneez",
                                         "knead", "loaf"):
            self.state = "greet"
            self.timer = 70
            self.set_expr("love", 220)
            self.say_line("greet", 220)
            self.jump_t = 16

    def touch(self):
        self.last_act = self.t

    def on_press(self, e):
        self.touch()
        if self.state == "sleep":
            self.state = "rest"
            self.say_line("wake_up")
            self.set_expr("confused", 140)
            return
        self.pokes = [x for x in self.pokes if self.t - x < 120]
        self.pokes.append(self.t)
        if len(self.pokes) >= 5:
            self.pokes = []
            self.happy = max(0.0, self.happy - 3)
            self.set_expr("angry", 260)
            self.say_line("poke_angry")
            if self.follow_on and not self.bienao:
                self.state = "chase"
                self.timer = 200
                return
        self.drag_dx, self.drag_dy = e.x, e.y
        self.press_x, self.press_y = e.x_root, e.y_root
        self.press_t = time.time()
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
                self.say_line("shake")
        self.x, self.y = nx, ny
        self.place_window()

    def on_release(self, e):
        if self.state == "chase":
            return
        if self.state == "drag" and \
                math.hypot(e.x_root - self.press_x,
                           e.y_root - self.press_y) < 10 and \
                time.time() - self.press_t < 0.6:
            if self.click_job is not None:
                self.root.after_cancel(self.click_job)
            self.click_job = self.root.after(400, self._click_status)
        if self.home_y - self.y > 150:
            self.dizzy_pending = True
        self.state = "fall"

    def _click_status(self):
        self.click_job = None
        self.show_status()

    def on_double(self, e):
        self.touch()
        if self.click_job is not None:
            self.root.after_cancel(self.click_job)
            self.click_job = None
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
            self.say_line("pat_love")
            self.jump_t = 16
            if self.happy > 85 and self.state in ("rest", "pick"):
                self.state = "knead"
                self.timer = 100
                self.say_line("knead", 200)
        else:
            self.set_expr("happy")
            self.say_line("pat_happy")

    def toggle_remind(self):
        self.remind_on = not self.remind_on
        self.remind_next = time.time() + 3600
        self.say_line("remind_on" if self.remind_on else "remind_off")

    def status_lines(self):
        names = {0: "奶龙宝宝", 1: "少年奶龙", 2: "奶猫"}
        def bar(v):
            n = max(0, min(10, int(round(v / 10))))
            return "▓" * n + "░" * (10 - n)
        secs = int(self.total_secs)
        need = "MAX" if self.stage >= 2 else \
            f"{self.progress:.1f}/{self.evo_needs[self.stage]}"
        out = [f"形态：{names[self.stage]}",
               f"金币：{self.money} 🪙",
               f"饱腹：{bar(100 - self.hunger)}",
               f"水分：{bar(100 - self.thirst)}",
               f"心情：{bar(self.happy)}",
               f"智力 Lv.{int(self.stats['智力'])}"
               f"　魅力 Lv.{int(self.stats['魅力'])}"
               f"　力量 Lv.{int(self.stats['力量'])}",
               f"进化进度：{need}",
               f"累计在线：{secs // 3600}小时{secs % 3600 // 60}分"]
        if self.song:
            out.append(f"正在唱：《{self.song[:14]}》")
        return out

    def refresh_status(self):
        if self._status_w is None:
            return
        try:
            if not self._status_w.winfo_exists():
                self._status_w = None
                self._evo_btn = None
                return
            for var, s in zip(self._status_vars, self.status_lines()):
                var.set(s)
            if self._evo_btn is not None:
                self.sync_evo_btn()
        except tk.TclError:
            self._status_w = None
            self._evo_btn = None

    def sync_evo_btn(self):
        names = {0: "奶龙宝宝", 1: "少年奶龙", 2: "奶猫"}
        if self.stage >= 2:
            text, st = "已是最终形态 🐱", "disabled"
        elif self.can_evolve():
            text = ("✨ 进化！（%s → %s）" %
                    (names[self.stage], names[self.stage + 1]))
            st = "normal"
        else:
            left = max(0.0, self.evo_needs[self.stage] - self.progress)
            text, st = "进化条件未满足（还差 %.0f 进度）" % left, "disabled"
        self._evo_btn.config(text=text, state=st)

    def show_status(self):
        if self._status_w is not None:
            try:
                if self._status_w.winfo_exists():
                    self._status_w.destroy()
                    self._status_w = None
                    return
            except tk.TclError:
                pass
        w = tk.Toplevel(self.root)
        self._status_w = w
        w.title("奶猫状态面板")
        w.attributes("-topmost", True)
        self._status_vars = []
        for s in self.status_lines():
            var = tk.StringVar(value=s)
            tk.Label(w, textvariable=var, font=("Microsoft YaHei", 10),
                     padx=16, pady=4, anchor="w").pack(fill="x")
            self._status_vars.append(var)
        btn = tk.Button(w, font=("Microsoft YaHei", 10, "bold"),
                        bg="#FFD98A", fg="#5A4632", relief="flat",
                        padx=12, pady=3, cursor="hand2",
                        command=self.user_evolve)
        btn.pack(pady=(2, 8))
        self._evo_btn = btn
        self.sync_evo_btn()
        w.resizable(False, False)
        # 点面板空白处最小化，但点进化按钮不触发最小化
        w.bind("<Button-1>",
               lambda e: None if e.widget is btn else w.iconify())

    def on_menu(self, e):
        self.touch()
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
        sm = tk.Menu(m, tearoff=0)
        songs = self.list_songs()
        for fn in songs:
            disp = os.path.splitext(fn)[0].replace(" - APLMate.com", "")
            sm.add_command(label="🎵 " + disp[:24],
                           command=lambda f=fn: self.start_music(f))
        if songs:
            sm.add_separator()
            if self.song:
                sm.add_command(label="⏹ 停止（正在唱：" + self.song[:10] + "）",
                               command=self.stop_music)
        else:
            sm.add_command(label="（歌单是空的）", state="disabled")
        sm.add_command(label="📂 打开歌单文件夹（把mp3放进去）",
                       command=self.open_music_dir)
        m.add_cascade(label="点歌台 🎤", menu=sm)
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
        m.add_command(label=("别闹中：点我恢复" if self.bienao else "别闹（不追鼠标）"),
                      command=self.toggle_bienao)
        m.add_command(label=("唤醒" if self.state == "sleep" else "睡觉"),
                      command=self.toggle_sleep)
        m.add_command(label="放大一点", command=lambda: self.set_scale(1.2))
        m.add_command(label="缩小一点", command=lambda: self.set_scale(0.83))
        m.add_command(label="保存到文件", command=self.save)
        m.add_command(label="退出", command=self.quit_app)
        m.tk_popup(e.x_root, e.y_root)

    def quit_app(self):
        self.stop_music(quiet=True)
        self.hide_lyric_win()
        self.root.destroy()

    def toggle_pull(self):
        self.pull_on = not self.pull_on
        self.say_line("pull_off" if not self.pull_on else "pull_on")

    def toggle_follow(self):
        self.follow_on = not self.follow_on
        if not self.follow_on and self.state == "chase":
            self.state = "rest"

    def toggle_bienao(self):
        self.bienao = not self.bienao
        if self.bienao:
            self.say("好吧，清江鱼不和我玩，那我自己玩", 300)
            self.set_expr("sad", 240)
            if self.state in ("wiggle", "chase"):
                self.state = "rest"
                self.timer = random.randint(40, 90)
        else:
            self.say("太好了，清江鱼愿意和我玩了", 300)
            self.set_expr("love", 240)

    def toggle_sleep(self):
        if self.state != "sleep":
            self.stop_music(quiet=True)
        self.state = "rest" if self.state == "sleep" else "sleep"

    def set_scale(self, k):
        self.scale = max(0.6, min(1.8, self.scale * k))

    # ---------- music box ----------
    def music_dir(self):
        return os.path.join(os.path.dirname(self.path()), "奶猫音乐盒")

    def mci(self, cmd):
        buf = ctypes.create_unicode_buffer(256)
        err = self._mci(cmd, buf, 255, None)
        if err:
            return ""
        return buf.value

    def mci_open(self, cmd):
        return self._mci(cmd, None, 0, None) == 0

    def list_songs(self):
        try:
            d = self.music_dir()
            os.makedirs(d, exist_ok=True)
            return sorted(f for f in os.listdir(d)
                          if f.lower().endswith((".mp3", ".wav")))
        except OSError:
            return []

    def open_music_dir(self):
        d = self.music_dir()
        os.makedirs(d, exist_ok=True)
        try:
            os.startfile(d)
        except OSError:
            self.say("这个文件夹打不开…")

    def load_lrc(self, stem):
        p = os.path.join(self.music_dir(), stem + ".lrc")
        out = []
        off = 0
        try:
            with open(p, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    m = re.match(r"\[offset:\s*(-?\d+)\]", line, re.I)
                    if m:
                        off = int(m.group(1))
                        continue
                    for m in re.finditer(r"\[(\d+):(\d+)[.:](\d+)\](.*)",
                                         line):
                        ms = (int(m.group(1)) * 60 + int(m.group(2))) * 1000 \
                            + int(m.group(3)) * 10
                        txt = m.group(4).strip()
                        if txt:
                            out.append((ms, txt))
        except OSError:
            return []
        out.sort()
        return out

    def lrc_tag_offset(self, stem):
        p = os.path.join(self.music_dir(), stem + ".lrc")
        try:
            with open(p, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    m = re.match(r"\[offset:\s*(-?\d+)\]", line.strip(), re.I)
                    if m:
                        return int(m.group(1))
        except OSError:
            pass
        return 0

    @staticmethod
    def _lrc_norm(s):
        return re.sub(r"[\s\-_()\[\]]", "", s.lower())

    LRC_ALIAS = {"陶喆": ("david tao",),
                 "孙燕姿": ("stefanie sun", "yanzi sun"),
                 "张惠妹": ("a-mei", "amei"),
                 "许嵩": ("vae",),
                 "李玖哲": ("eric li",),
                 "吕彦良": ("matt lv", "matt lu")}

    def _lrc_get_json(self, url):
        req = urllib.request.Request(
            url, headers={"User-Agent": "naichat-pet/1.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8"))

    def _lrc_fetch_text(self, title, artist):
        q = urllib.parse.urlencode({"q": title})
        try:
            rows = self._lrc_get_json("https://lrclib.net/api/search?" + q)
        except Exception:
            return None
        if not rows:
            return None
        tn, ar = self._lrc_norm(title), self._lrc_norm(artist)
        cand = [r for r in rows
                if tn in self._lrc_norm(r.get("trackName", "")) or
                self._lrc_norm(r.get("trackName", "")) in tn] or rows

        def hit(r):
            a = self._lrc_norm(r.get("artistName", ""))
            if not a:
                return False
            names = [ar] + [self._lrc_norm(x)
                            for x in self.LRC_ALIAS.get(artist, ())]
            return any(n and (n in a or a in n) for n in names)

        def pick(pool):
            exact = [r for r in pool if hit(r)]
            if not exact:
                if len(pool) > 3:
                    return None
                pool = pool
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

    def fetch_lrc_async(self, stem, fname):
        parts = [p.strip() for p in stem.split(" - ")]
        title = parts[0]
        artist = parts[1] if len(parts) > 1 else ""
        if not title:
            return

        def work():
            txt = None
            try:
                txt = self._lrc_fetch_text(title, artist)
            except Exception:
                txt = None
            if not txt or self.song_file != fname:
                return
            try:
                with open(os.path.join(self.music_dir(), stem + ".lrc"),
                          "w", encoding="utf-8") as f:
                    f.write(txt + "\n")
            except OSError:
                return
            lyr = self.load_lrc(stem)
            if not lyr or self.song_file != fname:
                return
            self._lrc_pending = (lyr, fname)

        threading.Thread(target=work, daemon=True).start()

    def apply_fetched(self, lyr, fname):
        if self.song_file != fname:
            return
        pos = self.song_pos0 + int((time.time() - self.song_t0) * 1000) \
            + self.lrc_off_cur
        self.set_lyric(lyr)
        self.lyric_i = bisect.bisect_right(self._lrc_times, pos) - 1
        if self.lyric_i >= 0:
            self.cur_line = self.lyric[self.lyric_i][1]
        self.say("歌词找到啦～♪", 150)


    def strip_id3(self, src, dst):
        with open(src, "rb") as f:
            d = f.read()
        i = 0
        if d[:3] == b"ID3":
            sz = ((d[6] & 0x7f) << 21) | ((d[7] & 0x7f) << 14) | \
                ((d[8] & 0x7f) << 7) | (d[9] & 0x7f)
            i = 10 + sz
            while i < len(d) - 4 and not (d[i] == 0xFF and
                                          (d[i + 1] & 0xE0) == 0xE0):
                i += 1
        with open(dst, "wb") as f:
            f.write(b"ID3\x03\x00\x00\x00\x00\x00\x00" + d[i:])

    def set_lyric(self, lyr):
        self.lyric = lyr
        self._lrc_times = [ms for ms, _ in lyr]

    def start_music(self, fname):
        if self.state == "sleep":
            self.state = "rest"
        self.stop_music(quiet=True)
        path = os.path.join(self.music_dir(), fname)
        cached = os.path.join(self.music_dir(), "_cache", fname)
        typ = " type mpegvideo" if fname.lower().endswith(".mp3") else ""
        if os.path.exists(cached):
            path = cached
        if not self.mci_open(f'open "{path}"{typ} alias petmus'):
            if not os.path.exists(cached):
                try:
                    os.makedirs(os.path.dirname(cached), exist_ok=True)
                    self.strip_id3(path, cached)
                    path = cached
                except OSError:
                    pass
            if not self.mci_open(f'open "{path}"{typ} alias petmus'):
                self.say_line("music_err", 160)
                return
        self.mci("play petmus")
        try:
            self.song_len = int(self.mci("status petmus length") or 0)
        except ValueError:
            self.song_len = 0
        self.mci("play petmus from 0")
        self.mci("setaudio petmus volume to 600")
        stem = os.path.splitext(fname)[0]
        self.song = stem.replace(" - APLMate.com", "")
        self.song_file = fname
        self.song_t0 = time.time()
        self.song_pos0 = 0
        self.lrc_off_cur = self.lrc_off.get(stem, 0) + \
            self.lrc_tag_offset(stem)
        self.lrc_tag_cur = self.lrc_tag_offset(stem)
        self.set_lyric(self.load_lrc(stem))
        if not self.lyric:
            self.fetch_lrc_async(stem, fname)
        self.lyric_i = -1
        self.cur_line = ""
        self.prev_line = ""
        self.line_no = 0
        self.sing_pose = random.choice(("mic", "both", "lean", "hop"))
        self.state = "music"
        self.set_expr(random.choice(("happy", "star", "love")), 240)
        self.say_line("music_start", 160)
        self.ensure_ctrl_win()
        self.place_ctrl()
        self.ensure_lyric_win()
        self.place_lyric()
        self.fx.append({"type": "note", "x": random.randint(-20, 20),
                        "y": -80, "life": 50})

    def stop_music(self, quiet=False):
        if self.song is None:
            return
        self.mci("stop petmus")
        self.mci("close petmus")
        self.song = None
        self.song_file = None
        self.set_lyric([])
        self.lyric_i = -1
        self.cur_line = ""
        self.prev_line = ""
        self._lrc_pending = None
        self.hide_ctrl_win()
        self.hide_lyric_win()
        if self.state == "music":
            self.state = "rest"
            self.timer = random.randint(40, 90)
        if not quiet:
            self.say_line("music_stop", 160)

    def ensure_ctrl_win(self):
        if self.ctrl_win is not None:
            try:
                if self.ctrl_win.winfo_exists():
                    self.ctrl_win.deiconify()
                    self._btn_pause.config(text="⏸")
                    return
            except tk.TclError:
                pass
        w = tk.Toplevel(self.root)
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        w.configure(bg="#F2E3C6")
        bs = dict(relief="flat", bg="#FFE9B8", activebackground="#FFD98A",
                  font=("Microsoft YaHei", 10), width=3, bd=0)
        tk.Button(w, text="−½", command=lambda: self.adjust_lrc_off(-500),
                  **bs).pack(side="left", padx=3, pady=3)
        tk.Button(w, text="＋½", command=lambda: self.adjust_lrc_off(500),
                  **bs).pack(side="left", padx=3, pady=3)
        self._btn_pause = tk.Button(w, text="⏸", command=self.toggle_pause,
                                    **bs)
        self._btn_pause.pack(side="left", padx=3, pady=3)
        tk.Button(w, text="⏭", command=self.next_song, **bs) \
            .pack(side="left", padx=3, pady=3)
        tk.Button(w, text="⏹", command=self.stop_music, **bs) \
            .pack(side="left", padx=3, pady=3)
        self.ctrl_win = w

    def hide_ctrl_win(self):
        if self.ctrl_win is not None:
            try:
                self.ctrl_win.withdraw()
            except tk.TclError:
                pass

    LRCW, LRCH = 360, 74

    def ensure_lyric_win(self):
        if self.lyric_win is not None:
            try:
                if self.lyric_win.winfo_exists():
                    self.lyric_win.deiconify()
                    return
            except tk.TclError:
                pass
        w = tk.Toplevel(self.root)
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        w.wm_attributes("-transparentcolor", COLORKEY)
        cv = tk.Canvas(w, width=self.LRCW, height=self.LRCH, bg=COLORKEY,
                       highlightthickness=0)
        cv.pack()
        self.lyric_win = w
        self._lyric_cv = cv

    def hide_lyric_win(self):
        if self.lyric_win is not None:
            try:
                self.lyric_win.withdraw()
            except tk.TclError:
                pass

    def place_lyric(self):
        try:
            if self.lyric_win is None or not self.lyric_win.winfo_viewable():
                return
        except tk.TclError:
            return
        px = int(max(self.L + self.LRCW // 2,
                     min(self.R - self.LRCW // 2, self.x)))
        py = int(self.y - H - 6)
        if py < self.T + 4:
            py = self.T + 4
        self.lyric_win.geometry("+%d+%d" % (px - self.LRCW // 2, py))

    def draw_lyric_win(self):
        c = self._lyric_cv
        if c is None or self.song is None:
            return
        c.delete("all")
        W2, H2 = self.LRCW, self.LRCH
        c.create_rectangle(6, 6, W2 - 6, H2 - 6, fill="#2B2440",
                           outline="#4C4270", width=1)
        c.create_line(6, 8, 20, 8, fill="#FFD98A")
        c.create_line(6, 8, 6, 22, fill="#FFD98A")
        c.create_line(W2 - 6, H2 - 8, W2 - 20, H2 - 8, fill="#FFD98A")
        c.create_line(W2 - 6, H2 - 8, W2 - 6, H2 - 22, fill="#FFD98A")
        if not self.cur_line:
            return
        cur = self.cur_line
        parts = [cur[:16], cur[16:32]] if len(cur) > 16 else [cur]
        col = self.LRC_COLORS[self.line_no % len(self.LRC_COLORS)]
        top = H2 // 2 + (0 if len(parts) == 1 else -8)
        if self.prev_line and self.t < self.prev_until:
            c.create_text(W2 // 2, top - 22, text=self.prev_line[:16],
                          fill="#6E6390", font=("Microsoft YaHei", 8))
        for i, seg in enumerate(parts):
            yy = top + i * 17
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                c.create_text(W2 // 2 + dx, yy + dy, text=seg, fill="white",
                              font=("Microsoft YaHei", 11, "bold"))
            c.create_text(W2 // 2, yy, text=seg, fill=col,
                          font=("Microsoft YaHei", 11, "bold"))
        w0 = 13 * len(parts[0]) + 4
        c.create_text(W2 // 2 - w0 // 2 - 11, top, text="♪", fill=col,
                      font=("Arial", 9))
        c.create_text(W2 // 2 + w0 // 2 + 11, top, text="♪", fill=col,
                      font=("Arial", 9))
        if self.lrc_off_cur:
            c.create_text(W2 - 14, 14, anchor="e",
                          text="%+.1fs" % (self.lrc_off_cur / 1000.0),
                          fill="#FFD98A", font=("Microsoft YaHei", 7))

    def adjust_lrc_off(self, delta):
        if self.song_file is None:
            return
        stem = os.path.splitext(self.song_file)[0]
        self.lrc_off_cur = max(-15000, min(15000,
                                           self.lrc_off_cur + delta))
        self.lrc_off[stem] = self.lrc_off_cur - self.lrc_tag_cur
        self.lyric_i = -2
        self.save()
        self.say("歌词校准 %+.1f 秒" % (self.lrc_off_cur / 1000.0), 120)

    def place_ctrl(self):
        try:
            if self.ctrl_win is None or not self.ctrl_win.winfo_viewable():
                return
        except tk.TclError:
            return
        px = int(max(self.L + 80, min(self.R - 80, self.x)) - 82)
        self.ctrl_win.geometry("+%d+%d" % (px, int(self.home_y) - 4))

    def set_line(self, txt):
        txt = txt.strip()
        if not txt or txt == self.cur_line:
            return
        self.prev_line = self.cur_line
        self.prev_until = self.t + 55
        self.cur_line = txt
        self.line_no += 1

    def toggle_pause(self):
        if self.song is None:
            return
        mode = self.mci("status petmus mode")
        if mode == "playing":
            self.song_pos0 += int((time.time() - self.song_t0) * 1000)
            self.mci("pause petmus")
            self._btn_pause.config(text="▶")
        elif mode == "paused":
            self.song_t0 = time.time()
            self.mci("play petmus")
            self._btn_pause.config(text="⏸")

    def next_song(self):
        songs = self.list_songs()
        if not songs:
            self.say_line("music_none", 200)
            return
        try:
            i = songs.index(self.song_file)
        except (ValueError, TypeError):
            i = -1
        self.start_music(songs[(i + 1) % len(songs)])

    def music_tick(self):
        if self.song is None:
            return
        if self._lrc_pending:
            lyr, fname = self._lrc_pending
            self._lrc_pending = None
            if fname == self.song_file:
                self.apply_fetched(lyr, fname)
            return
        if self.t % 16:
            return
        mode = self.mci("status petmus mode")
        if mode == "paused":
            return
        if mode != "playing":
            self.mci("close petmus")
            self.song = None
            self.song_file = None
            self.set_lyric([])
            self.lyric_i = -1
            self.cur_line = ""
            self.prev_line = ""
            self.hide_ctrl_win()
            self.hide_lyric_win()
            if self.state == "music":
                self.state = "rest"
                self.timer = random.randint(40, 90)
            self.happy = min(100.0, self.happy + 3)
            self.progress += 0.05
            self.say_line("music_end", 220)
            self.fx.append({"type": "star", "x": 0, "y": -90,
                            "life": 40})
            return
        try:
            pos = self.song_pos0 + int((time.time() - self.song_t0) * 1000) \
                + self.lrc_off_cur
        except (TypeError, ValueError):
            pos = self.lrc_off_cur
        if self.lyric:
            i = bisect.bisect_right(self._lrc_times, pos) - 1 \
                if self._lrc_times else -1
            if i != self.lyric_i:
                self.lyric_i = i
                if i >= 0:
                    self.set_line(self.lyric[i][1])
        elif self.t % 160 == 0:
            self.set_line(random.choice(Pet.LINES["sing_la"]))
        if self.state in ("rest", "pick"):
            self.state = "music"
        if self.state == "music":
            if self.t % 44 == 0:
                self.fx.append({"type": "note",
                                "x": random.randint(-26, 26),
                                "y": -76, "life": 50})
            if self.t % 300 == 0:
                self.set_expr(random.choice(("happy", "star", "love")),
                              260)
            if self.sing_pose == "hop" and self.t % 60 == 0:
                self.jump_t = 16

    # ---------- laser teaser ----------
    def toggle_laser(self):
        if self.state == "sleep":
            self.say_line("need_awake")
            return
        self.laser_on = not self.laser_on
        if self.laser_on:
            self.say_line("laser_on", 260)
            if self.state in ("rest", "pick", "wander", "groom",
                              "stretch", "look", "loaf"):
                self.state = "playbow"
                self.timer = 55
                self.say_line("playbow", 160)
        else:
            self.kill_laser()
            self.say_line("laser_off")

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
            self.say_line("laser_dot", 90)
            self.set_expr("star", 120)

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
            self.say_line("no_money", 220)
            self.set_expr("sad", 200)
            return False
        self.money -= cost
        if kind == "full":
            self.hunger = max(0.0, self.hunger - val)
            self.say_line("eat", name=name)
            self.set_expr("yum", 150)
        elif kind == "water":
            self.thirst = max(0.0, self.thirst - val)
            self.say_line("drink", name=name)
            self.set_expr("yum", 150)
        else:
            old = int(self.stats[stat])
            self.stats[stat] += val
            new = int(self.stats[stat])
            if new > old:
                self.say_line("lvup", 260, stat=stat, new=new)
                self.fx.append({"type": "flash", "x": 0, "y": -20,
                                "life": 45})
            else:
                self.say_line("stat_use", name=name, stat=stat)
        self.happy = min(100.0, self.happy + hp)
        self.progress += 0.1
        self.fx.append({"type": "food", "x": 0, "y": -50, "life": 40})
        if kind not in ("full", "water"):
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
            self.say_line("sleep_busy")
            return False
        if self.state in ("work", "study"):
            self.say_line("busy")
            return False
        if self.hunger > 80 or self.thirst > 80:
            self.say_line("weak")
            self.set_expr("sad", 200)
            return False
        return True

    def start_study(self, stat):
        if not self._can_act():
            return
        self.state = "study"
        self.study = stat
        self.timer = 270
        self.say_line("study_start", stat=stat)

    def study_tick(self):
        self.timer -= 1
        if self.timer % 60 == 30:
            self.say_line("study_mid", 80)
        if self.timer <= 0:
            gain = random.uniform(0.7, 1.0)
            old = int(self.stats[self.study])
            self.stats[self.study] += gain
            new = int(self.stats[self.study])
            self.hunger = min(100.0, self.hunger + 4)
            self.thirst = min(100.0, self.thirst + 5)
            self.progress += 0.2
            if new > old:
                self.say_line("lvup", 260, stat=self.study, new=new)
                self.fx.append({"type": "flash", "x": 0, "y": -20,
                                "life": 45})
                self.set_expr("surprised", 160)
            else:
                self.say_line("study_done", 220, study=self.study,
                              gain=gain, new=new)
                self.set_expr("happy", 160)
            self.study = None
            self.state = "rest"
            self.timer = 60

    def start_work(self, job):
        if not self._can_act():
            return
        if job[2] and int(self.stats[job[2]]) < job[3]:
            self.say_line("job_locked", 220, stat=job[2])
            self.set_expr("sad", 180)
            return
        self.state = "work"
        self.job = job
        self.timer = job[5]
        self.say_line("job_start", job=job[0])

    def work_tick(self):
        self.timer -= 1
        if self.timer % 90 == 45:
            self.say_line("job_mid", 80)
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
            self.say_line("job_done", 240, pay=pay)
            self.fx.append({"type": "coin", "x": 0, "y": -60, "life": 40})

    def start_play(self):
        if self.state == "sleep":
            return
        self.state = "play"
        self.timer = 360
        bx = self.x + random.choice((-1, 1)) * random.randint(60, 100)
        self.ball = {"x": bx, "y": self.home_y - 60,
                     "vx": random.uniform(-5, 5), "vy": -4}
        self.say_line("ball_see")
        self.set_expr("star", 160)

    # ---------- mini games ----------
    def play_rps(self):
        if self.state == "sleep":
            self.say_line("sleep_deaf")
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
                self.say_line("rps_tie", 240, op=ops[me])
                self.happy = min(100.0, self.happy + 1)
                self.set_expr("happy", 180)
            elif (me - bot) % 3 == 2:
                self.say_line("rps_win", 240, op=ops[bot])
                self.happy = min(100.0, self.happy + 4)
                self.progress += 0.2
                self.set_expr(random.choice(("smug", "laugh")), 240)
            else:
                self.say_line("rps_lose", 240)
                self.happy = max(0.0, self.happy - 1)
                self.set_expr(random.choice(("sad", "cry")), 240)

        for i, name in enumerate(ops):
            tk.Button(row, text=name, width=7,
                      font=("Microsoft YaHei", 11),
                      command=lambda i=i: throw(i)).pack(side="left",
                                                         padx=6)
        d.resizable(False, False)

    def call_here(self):
        if self.state == "sleep":
            self.say_line("sleep_deaf")
            return
        self.state = "come"
        self.timer = 360
        self.say_line("come_go")

    def do_flip(self):
        if self.state == "sleep":
            self.say_line("flip_no")
            return
        self.state = "flip"
        self.flip_t = 0
        self.flip_dir = self.facing
        self.say_line("flip_go")

    # ---------- solo play (自娱自乐) ----------
    SOLO = {"tail": 130, "butterfly": 320, "sing": 180,
            "roll": 200, "mirror": 150}

    def solo_start(self):
        act = random.choice(tuple(self.SOLO))
        dur = self.SOLO[act]
        self.state = act
        self.timer = dur
        self.say_line(act, 160)
        if act == "butterfly":
            self.but = {"ph": 0.0, "bx": self.x, "by": self.home_y - 90}
        if act == "roll":
            self.flip_t = 0
            self.flip_dir = self.facing
        if act == "mirror":
            self.set_expr("smug", dur)

    def _solo_end(self, key, hp, dizzy=0.0):
        self.state = "rest"
        self.timer = random.randint(40, 100)
        self.happy = min(100.0, self.happy + hp)
        self.progress += 0.05
        if dizzy and random.random() < dizzy:
            self.set_expr("dizzy", 200)
            self.say_line("solo_dizzy", 200)
        else:
            self.say_line(key + "_end", 180)

    def solo_tick(self):
        self.timer -= 1
        if self.state == "tail":
            if self.timer % 9 == 0:
                self.facing = -self.facing
                self.x += self.facing * 1.2
                self.clamp_pos()
                self.moving = True
            if self.timer <= 0:
                self._solo_end("tail", 1.5, dizzy=0.3)
        elif self.state == "sing":
            if self.timer % 14 == 0:
                self.fx.append({"type": "note",
                                "x": random.randint(12, 34),
                                "y": -70, "life": 50})
            if self.timer <= 0:
                self._solo_end("sing", 1.0)
        elif self.state == "mirror":
            if self.timer <= 0:
                self._solo_end("mirror", 1.0)
        elif self.state == "roll":
            self.flip_t += 1
            self.y = self.home_y - int(abs(math.sin(self.flip_t * 0.22)) * 38)
            self.x += self.flip_dir * 2.6
            if self.x <= self.L + 40 or self.x >= self.R - 40:
                self.flip_dir = -self.flip_dir
            self.clamp_pos()
            self.facing = self.flip_dir
            self.moving = True
            if self.t % 10 == 0:
                self.fx.append({"type": "dust",
                                "x": random.randint(-20, 20),
                                "y": -4, "life": 12})
            if self.timer <= 0:
                self.y = self.home_y
                self._solo_end("roll", 1.5)
        elif self.state == "butterfly":
            b = self.but
            b["ph"] += 0.12
            b["bx"] = self.x + math.sin(b["ph"] * 0.8) * 95
            b["by"] = (self.home_y - 75 -
                       abs(math.sin(b["ph"] * 1.7)) * 45)
            self.target = (b["bx"], self.home_y)
            self.moving = self.nudge(4.6)
            d = math.hypot(b["bx"] - self.x, b["by"] - (self.y - 40))
            if d < 55 and self.timer % 30 == 0:
                self.say_line("solo_pounce")
                self.fx.append({"type": "star", "x": 0, "y": -90,
                                "life": 20})
            if self.timer <= 0:
                self.but = None
                self._solo_end("butterfly", 2.0)

    def idle_act_start(self):
        self.state = random.choice(("groom", "stretch", "look",
                                    "yawn", "peek", "sneez",
                                    "knead", "loaf"))
        if self.state == "yawn":
            self.timer = 90
            self.set_expr("sleepy", 90)
            self.say_line("yawn", 200)
        elif self.state == "peek":
            self.timer = 150
            self.say_line("peek", 220)
        elif self.state == "sneez":
            self.timer = 55
            self.say_line("sneez_pre", 60)
        elif self.state == "knead":
            self.timer = 100
            self.set_expr("happy", 100)
            self.say_line("knead", 200)
        elif self.state == "loaf":
            self.timer = random.randint(150, 260)
            self.say_line("loaf", 180)
        else:
            self.timer = random.randint(90, 170)

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
            self.say_line("water_remind", 260)
            self.set_expr("surprised", 160)
        if self.laser_on:
            self.laser_tick()
        self.music_tick()
        if self.song and self.t % 6 == 0:
            self.place_ctrl()
            self.place_lyric()
            self.draw_lyric_win()
        win_down = bool(user32.GetAsyncKeyState(0x5B) & 0x8000) or \
            bool(user32.GetAsyncKeyState(0x5C) & 0x8000)
        if win_down and not self.win_down:
            self.note_user_act()
            if self.t - self.win_last > 90 and self.state != "sleep":
                self.win_last = self.t
                self.say("清江鱼累了吗？那休息吧", 240)
                self.set_expr("happy", 200)
        self.win_down = win_down
        lbtn = bool(user32.GetAsyncKeyState(0x01) & 0x8000)
        if lbtn and not self.lbtn:
            self.note_user_act()
            if self.t - self.lbtn_last > 150 and self.state != "sleep" \
                    and not self.laser_on:
                mx, my = get_mouse()
                on_pet = (self.x - W // 2 < mx < self.x + W // 2 and
                          self.y - H + 80 < my < self.y + H - 80)
                if not on_pet:
                    self.lbtn_last = self.t
                    self.say("清江鱼累了吗？那休息吧", 240)
                    self.set_expr("happy", 200)
        self.lbtn = lbtn
        if self.thinking and self.t > self.think_until:
            self.thinking = False
        if self.t % 90 == 0:
            self.blink = 6
        elif self.blink:
            self.blink -= 1
        if time.time() > self.save_next:
            self.save()
            self.save_next = time.time() + 20
        if self.t % 15 == 0 and self._status_w is not None:
            self.refresh_status()
        if self.squash:
            self.squash *= 0.86
            if self.squash < 0.3:
                self.squash = 0
        if self.jump_t:
            self.jump_t -= 1

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
                    self.say_line("dizzy_land", 220)
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
                self.say_line("early_sleepy", 240)
                self.state = "sleep"
            else:
                roll = random.random()
                idle_long = self.t - self.last_act > 2700
                if idle_long and roll < 0.5:
                    self.solo_start()
                elif self.follow_on and roll < 0.55 and \
                        not self.laser_on and not self.bienao:
                    self.state = "wiggle"
                    self.timer = 22
                    self.say_line("lock_target", 90)
                elif roll < 0.75:
                    self.target = (random.randint(self.L + 60, self.R - 60),
                                   self.home_y)
                    self.state = "wander"
                else:
                    self.idle_act_start()
        elif self.state in ("groom", "stretch", "look", "yawn",
                           "knead", "loaf", "playbow"):
            self.timer -= 1
            if self.timer <= 0:
                self.state = "rest"
                self.timer = random.randint(40, 120)
        elif self.state == "peek":
            self.timer -= 1
            if self.timer == 80:
                self.state = "rest"
                self.timer = 40
                self.say_line("peek_end", 160)
                self.set_expr("happy", 180)
                self.jump_t = 16
                self.happy = min(100.0, self.happy + 1)
                self.progress += 0.05
        elif self.state == "sneez":
            self.timer -= 1
            if self.timer == 15:
                self.say_line("sneeze", 120)
                self.set_expr("surprised", 60)
                self.jump_t = 10
                self.fx.append({"type": "dust", "x": -22, "y": -30,
                                "life": 12})
            if self.timer <= 0:
                self.state = "rest"
                self.timer = random.randint(40, 100)
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
                self.say_line("chase_fail")
                self.set_expr(random.choice(("sad", "sweat")), 160)
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
                    self.say_line("laser_catch")
                    self.kill_laser()
                else:
                    self.state = "bite"
                    self.timer = 30
                    self.say_line("bite")
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
                self.say_line("grab")
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
        elif self.state in ("tail", "butterfly", "sing", "roll", "mirror"):
            self.solo_tick()
        elif self.state == "greet":
            self.timer -= 1
            if self.timer <= 0:
                self.state = "rest"
                self.timer = 30
        elif self.state == "beg":
            self.timer -= 1
            if self.timer <= 0:
                self.state = "rest"
                self.timer = random.randint(40, 90)

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
        self.say_line("drag_start")

    def drag_tick(self):
        self.timer -= 1
        dx = self.drag_to[0] - self.x
        if abs(dx) < 12 or self.timer <= 0:
            self.state = "rest"
            self.timer = random.randint(60, 140)
            self.set_expr("smug", 220)
            self.say_line("drag_ok")
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
                self.set_expr(random.choice(("angry", "sweat", "sweat")),
                              200)
                self.say_line("drag_fail")
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
                self.say_line("ball_hit")
        if self.swipe:
            self.swipe -= 1
        if self.timer <= 0:
            self.state = "rest"
            self.timer = 80
            self.ball = None
            self.say_line("ball_end")

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
            self.say_line("come_arrive")
        elif self.timer <= 0:
            self.state = "rest"
            self.timer = 60
            self.say_line("come_fail")

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
            self.say_line("flip_done")
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
            self.say_line("chase_start_laser")
        else:
            self.say_line("chase_start")

    def evo_check(self):
        pass

    def can_evolve(self):
        if self.stage >= 2:
            return False
        need_time = self.total_secs >= self.evo_times[self.stage]
        need_feed = self.progress >= self.evo_needs[self.stage]
        return (need_time and need_feed) or \
            self.progress >= self.evo_needs[self.stage] * 2

    def evo_partial(self):
        if self.stage >= 2:
            return False
        return (self.progress >= self.evo_needs[self.stage] or
                self.total_secs >= self.evo_times[self.stage])

    def user_evolve(self):
        if not self.can_evolve():
            self.say("还没到进化的时机…再陪陪我吧", 150)
            return
        self.stage += 1
        self.fx.append({"type": "flash", "x": 0, "y": -20, "life": 45})
        names = ["", "少年奶龙", "奶猫"]
        self.say_line("evo_done", 300, name=names[self.stage])
        self._evo_said.discard("soon%d" % (self.stage - 1))
        self._evo_said.discard("ready%d" % (self.stage - 1))
        self.refresh_status()
        self.save()

    def update_mood(self):
        if self.state in ("bite", "pounce", "grab", "dragmouse", "play",
                          "work", "study", "greet", "beg", "music"):
            return
        if self.hunger > 75 and self.t > self.say_until:
            self.say_line("hungry", 240)
            if self.state == "rest" and self.stage == 2:
                self.state = "beg"
                self.timer = 90
        elif self.thirst > 75 and self.t > self.say_until:
            self.say_line("thirsty", 240)
        elif self.total_secs > 100 and self.can_evolve():
            key = "ready%d" % self.stage
            if key not in self._evo_said and self.t > self.say_until:
                self._evo_said.add(key)
                self.say_line("evo_ready", 300)
        elif self.total_secs > 100 and self.evo_partial():
            key = "soon%d" % self.stage
            if key not in self._evo_said and self.t > self.say_until:
                self._evo_said.add(key)
                self.say_line("evo_soon", 300)

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
        if self.state == "loaf":
            self.sqx *= 1.1
            self.sqy *= 0.88
        self.wig = math.sin(self.t * 1.3) * 5 * s \
            if self.state == "wiggle" else 0
        if self.state == "music" and self.sing_pose == "lean":
            self.wig = math.sin(self.t * 0.07) * 7 * s
        self.mouth_open = self.state == "pounce" or \
            (self.state == "bite" and self.timer % 12 >= 6) or \
            (self.state == "chase" and self.dist_to_mouse()[0] < 120) or \
            (self.state == "music" and self.t % 32 < 18)
        self.hop = 0
        if self.state == "pounce":
            self.hop = (9 - self.timer) * 3
        elif self.state == "bite":
            self.hop = 2 if self.timer % 12 < 6 else 0
        if self.jump_t:
            self.hop = max(self.hop, int(math.sin(
                self.jump_t / 16.0 * math.pi) * 14))
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

        if self.state == "greet":
            wave = math.sin(self.t * 0.5) * 7 * s
            paw_c = "#FFFFFF" if self.stage == 2 else "#FFF3C0"
            hy = y - 46 * s
            gx, gy = cx + 30 * s + wave * 0.4, hy - 26 * s
            c.create_oval(gx - 7 * s, gy - 4 * s, gx + 7 * s, gy + 12 * s,
                          fill=paw_c, outline="#D9C3A5")
            for i in (-1, 0, 1):
                c.create_oval(gx + i * 4.5 * s - 1.6 * s, gy - 8 * s,
                              gx + i * 4.5 * s + 1.6 * s, gy - 2 * s,
                              fill="#FFB6C1", outline="")
        if self.state == "knead":
            paw_c = "#FFFFFF" if self.stage == 2 else "#FFF3C0"
            for k in (-1, 1):
                ph = math.sin(self.t * 0.5 + (0 if k < 0 else math.pi))
                ph = ph * 4 * s
                kx, ky = cx + k * 10 * s, y - 20 * s + ph
                c.create_oval(kx - 6 * s, ky - 6 * s, kx + 6 * s, ky + 6 * s,
                              fill=paw_c, outline="#D9C3A5")
                for i in (-1, 0, 1):
                    c.create_oval(kx + i * 3.6 * s - 1.3 * s, ky - 5.5 * s,
                                  kx + i * 3.6 * s + 1.3 * s, ky - 2.5 * s,
                                  fill="#FFB6C1", outline="")
        if self.state == "beg":
            bp = math.sin(self.t * 0.3) * 2 * s
            paw_c = "#FFFFFF" if self.stage == 2 else "#FFF3C0"
            for k in (-1, 1):
                kx, ky = cx + k * 8 * s, y - 24 * s + bp
                c.create_oval(kx - 7 * s, ky - 8 * s, kx + 7 * s, ky + 8 * s,
                              fill=paw_c, outline="#D9C3A5")
                for i in (-1, 0, 1):
                    c.create_oval(kx + i * 4 * s - 1.3 * s, ky - 7 * s,
                                  kx + i * 4 * s + 1.3 * s, ky - 3.5 * s,
                                  fill="#FFB6C1", outline="")
        if self.state == "peek" and self.timer > 80:
            paw_c = "#FFFFFF" if self.stage == 2 else "#FFF3C0"
            hy = y - 44 * s
            wob = math.sin(self.t * 0.25) * 2 * s
            for k in (-1, 1):
                px = cx + k * 14 * s
                py = hy + wob
                c.create_oval(px - 10 * s, py - 9 * s, px + 10 * s,
                              py + 9 * s, fill=paw_c, outline="#D9C3A5")
                for i in (-1, 0, 1):
                    c.create_oval(px + i * 5 * s - 1.6 * s, py - 7 * s,
                                  px + i * 5 * s + 1.6 * s, py - 3 * s,
                                  fill="#FFB6C1", outline="")

        if self.state == "music":
            paw_c = "#FFFFFF" if self.stage == 2 else "#FFF3C0"
            hy = y - 46 * s
            pose = self.sing_pose
            if pose == "mic":
                mx, my = cx + 12 * s, hy + 14 * s
                c.create_line(mx - 5 * s, my + 13 * s, mx + 2 * s,
                              my + 4 * s, width=max(2, int(4 * s)),
                              fill="#8A8A8A")
                c.create_oval(mx, my - 3 * s, mx + 11 * s, my + 8 * s,
                              fill="#4A4A55", outline="")
                c.create_oval(mx + 1 * s, hy + 9 * s, mx + 12 * s,
                              hy + 19 * s, fill=paw_c, outline="#D9C3A5")
                c.create_line(cx - 22 * s, hy + 16 * s, cx - 38 * s,
                              hy + 6 * s, width=max(2, int(6 * s)),
                              fill=paw_c)
            elif pose == "both":
                sw = math.sin(self.t * 0.18) * 4 * s
                for k in (-1, 1):
                    px = cx + k * 27 * s
                    py = hy - 4 * s + sw * k
                    c.create_oval(px - 7 * s, py - 4 * s, px + 7 * s,
                                  py + 10 * s, fill=paw_c,
                                  outline="#D9C3A5")
                    for i in (-1, 0, 1):
                        c.create_oval(px + i * 4 * s - 1.3 * s, py - 8 * s,
                                      px + i * 4 * s + 1.3 * s, py - 4 * s,
                                      fill="#FFB6C1", outline="")
            elif pose == "lean":
                c.create_oval(cx - 12 * s, y - 16 * s, cx - 2 * s,
                              y - 6 * s, fill=paw_c, outline="#D9C3A5")
                c.create_line(cx + 20 * s, hy + 18 * s, cx + 38 * s,
                              hy + 30 * s, width=max(2, int(6 * s)),
                              fill=paw_c)
            elif pose == "hop":
                for k in (-1, 1):
                    px = cx + k * 22 * s
                    py = hy - 16 * s
                    c.create_line(cx + k * 12 * s, hy + 16 * s, px, py,
                                  width=max(2, int(5 * s)), fill=paw_c)
                    c.create_oval(px - 5 * s, py - 5 * s, px + 5 * s,
                                  py + 5 * s, fill=paw_c,
                                  outline="#D9C3A5")
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

        if self.state == "butterfly" and self.but:
            b = self.but
            bx = cx + (b["bx"] - self.x)
            by = cy + (b["by"] - self.y)
            if 8 < bx < W - 8 and 8 < by < H - 8:
                flap = 1 + math.sin(b["ph"] * 6) * 0.25
                c.create_text(bx, by, text="🦋",
                              font=("Segoe UI Emoji", int(16 * flap)))
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

    LRC_COLORS = ("#D65A73", "#B4690E", "#5B8DB8", "#6B8E4E", "#8A6BB3")

    def draw_bubble(self, c, cx):
        if self.t >= self.say_until or not self.say_text:
            return
        txt = self.say_text
        lines = [txt] if len(txt) <= 16 else [txt[:16], txt[16:32]]
        wpx = 13 * max(len(t) for t in lines) + 20
        x1 = max(4, cx - wpx // 2)
        x2 = min(W - 4, x1 + wpx)
        c.create_polygon(cx - 5, 34, cx + 5, 34, cx, 44,
                         fill="white", outline="")
        c.create_oval(x1, 6 if len(lines) == 1 else 0, x2, 40,
                      fill="white", outline="#CCCCCC")
        if len(lines) == 1:
            c.create_text((x1 + x2) // 2, 22, text=lines[0],
                          fill="#555555", font=("Microsoft YaHei", 9))
        else:
            c.create_text((x1 + x2) // 2, 12, text=lines[0],
                          fill="#555555", font=("Microsoft YaHei", 9))
            c.create_text((x1 + x2) // 2, 30, text=lines[1],
                          fill="#555555", font=("Microsoft YaHei", 9))

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
        if e == "star":
            r = 6.2 * s
            c.create_oval(px - r * 0.85, ey - r, px + r * 0.85, ey + r,
                          fill="#3A2E0A", outline="")
            c.create_text(px, ey, text="✦", fill="#FFE066",
                          font=("Arial", int(9 * s)))
            return True
        if e == "laugh":
            c.create_arc(px - 6 * s, ey - 7 * s, px + 6 * s, ey + 5 * s,
                         start=20, extent=140, style="arc",
                         outline=line_c, width=2)
            if k > 0:
                c.create_oval(px + 7 * s, ey - 2 * s, px + 11 * s,
                              ey + 4 * s, fill="#9BD8F5", outline="")
            return True
        if e == "cry":
            c.create_arc(px - 6 * s, ey - 6 * s, px + 6 * s, ey + 6 * s,
                         start=200, extent=140, style="arc",
                         outline=line_c, width=2)
            drop = (self.t % 40) * 0.45 * s
            c.create_oval(px + 4 * s, ey + 5 * s + drop, px + 9 * s,
                          ey + 13 * s + drop, fill="#9BD8F5", outline="")
            return True
        if e == "confused":
            r = 5.5 * s if k < 0 else 3 * s
            c.create_oval(px - r, ey - r, px + r, ey + r,
                          fill=line_c, outline="")
            return True
        if e in ("happy", "yum"):
            c.create_arc(px - 6 * s, ey - 7 * s, px + 6 * s, ey + 5 * s,
                         start=20, extent=140, style="arc",
                         outline=line_c, width=2)
            return True
        if e == "shy":
            c.create_arc(px - 6 * s, ey - 5 * s, px + 6 * s, ey + 7 * s,
                         start=200, extent=140, style="arc",
                         outline=line_c, width=2)
            return True
        if e == "sweat":
            if k > 0:
                c.create_oval(px + 6 * s, ey - 16 * s, px + 12 * s,
                              ey - 8 * s, fill="#9BD8F5", outline="")
            return False
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
        if e == "laugh":
            c.create_oval(cx - 8 * s, my - 4 * s, cx + 8 * s, my + 9 * s,
                          fill="#E8747C", outline="")
            c.create_oval(cx - 4 * s, my + 3 * s, cx + 4 * s, my + 9 * s,
                          fill="#FF9EB5", outline="")
            return True
        if e == "cry":
            c.create_oval(cx - 4 * s, my, cx + 4 * s, my + 8 * s,
                          fill="#D9534F", outline="")
            return True
        if e == "confused":
            c.create_line(cx - 2 * s, my + 2 * s, cx + 6 * s,
                          my + 1 * s, width=2, fill=line_c)
            return True
        if e == "yum":
            c.create_oval(cx - 6 * s, my - 3 * s, cx + 6 * s, my + 7 * s,
                          fill="#E8747C", outline="")
            c.create_oval(cx - 1 * s, my + 2 * s, cx + 5 * s, my + 9 * s,
                          fill="#FF9EB5", outline="")
            return True
        if e == "shy":
            c.create_arc(cx - 4 * s, my - 1 * s, cx, my + 4 * s,
                         start=180, extent=160, style="arc",
                         outline=line_c)
            c.create_arc(cx, my - 1 * s, cx + 4 * s, my + 4 * s,
                         start=180, extent=160, style="arc",
                         outline=line_c)
            return True
        if e == "sweat":
            c.create_line(cx - 6 * s, my + 2 * s, cx - 2 * s, my - 1 * s,
                          cx + 2 * s, my + 3 * s, cx + 6 * s, my,
                          width=2, fill=line_c)
            return True
        if self.state == "yawn":
            c.create_oval(cx - 7 * s, my - 8 * s, cx + 7 * s, my + 6 * s,
                          fill="#D9534F", outline="")
            c.create_oval(cx - 3 * s, my + 1 * s, cx + 3 * s, my + 6 * s,
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
        elif self.state == "playbow":
            hy += 10 * s
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
        elif self.state == "playbow":
            hy += 9 * s
        by = y - 14 * s
        tf = 0.5 if self.state in ("chase", "pounce", "pull", "play",
                                   "wiggle", "playbow") else 0.15
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
        if self.mouth_open and self.state != "music":
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
            elif life["type"] == "note":
                c.create_text(cx + e["x"] + math.sin(a * 0.2) * 6,
                              cy + e["y"] - (50 - a) * 0.9,
                              text="♪", fill="#7B8FBF",
                              font=("Arial", 14))
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
            if self.t % 240 < 110:
                dz = abs(math.sin(self.t * 0.08)) * 3
                c.create_oval(cx + 8, cy - 30 + dz,
                              cx + 14, cy - 22 + dz,
                              fill="#9BD8F5", outline="")


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
