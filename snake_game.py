"""
Snake - Pro Edition
===================
A feature-rich Snake game built with pygame.

GAMEPLAY
    * 3 game modes: Classic, Time Attack (90s + 3s per food), Zen (no walls/obstacles)
    * 3 difficulties, 3 grid sizes, optional wrap-around edges
    * Power-ups: Shield, Slow-Mo, 2x Score, Shrink
    * Combo multiplier (eat quickly, up to x5), golden bonus food that expires
    * Levels with growing obstacles, speed ramp, 3-2-1 countdown before play

REAL-WORLD APP FEATURES
    * Mouse-clickable menus + keyboard + gamepad support
    * Settings screen (sound, volume, theme, grid size, wrap, fullscreen ...)
    * 4 colour themes
    * Top-10 leaderboard with name entry, lifetime stats, 10 achievements
    * Settings / scores / stats saved in your user-data folder (works from an .exe)
    * Fullscreen (F / F11) + freely resizable window, UI scales to any resolution
    * Auto-pause when the window loses focus, mute key (M), screenshots (F12)
    * Input buffering so quick turns are never dropped
    * Crash log written to the data folder if something goes wrong

CONTROLS
    Arrows / WASD ... steer / navigate menus      ENTER / SPACE ... select
    P or ESC ........ pause / back                F or F11 ........ fullscreen
    M ............... mute                        F12 ............. screenshot
    Mouse: hover + click menu items (right-click = change option backwards)

Run:
    pip install pygame
    python snake_game.py
"""

import array
import copy
import datetime
import json
import math
import os
import random
import sys
import time
import traceback

import pygame

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
APP_NAME = "SnakeGame"
VERSION = "3.0"

DEFAULT_WINDOW = (960, 720)
BASE_HEADER = 84
RENDER_FPS = 60

FPS_MAX = 24            # fastest snake speed (moves per second)
FPS_STEP_EVERY = 6      # speed +1 every N foods
LEVEL_UP_EVERY = 8      # foods per level
COMBO_WINDOW = 3.0      # seconds to chain the next food
COMBO_MAX = 5
SLOW_FACTOR = 1.6       # slow-mo makes each step 1.6x longer
SLOW_SECONDS = 8.0
DOUBLE_SECONDS = 10.0
POWERUP_TTL = 10.0
SPECIAL_FOOD_TTL = 7.0
TIME_ATTACK_SECONDS = 90.0
TIME_ATTACK_BONUS = 3.0
LEADERBOARD_SIZE = 10
START_COUNTDOWN = 3.0
RESUME_COUNTDOWN = 2.0

UP, DOWN, LEFT, RIGHT = (0, -1), (0, 1), (-1, 0), (1, 0)

DIFFICULTIES = [
    {"name": "Easy", "fps": 7, "obstacles": 0, "powerup": 0.40},
    {"name": "Medium", "fps": 10, "obstacles": 5, "powerup": 0.30},
    {"name": "Hard", "fps": 13, "obstacles": 10, "powerup": 0.22},
]

MODES = [
    ("Classic", "Grow, level up and dodge obstacles. Walls are deadly."),
    ("Time Attack", "90 seconds on the clock. Every food adds 3 seconds."),
    ("Zen", "No walls, no obstacles, no speed-up. Just relax."),
]

GRID_SIZES = {"Small": (20, 15), "Medium": (30, 22), "Large": (40, 28)}

POWERUPS = {
    "shield": {"name": "Shield", "letter": "S", "color": (70, 150, 255),
               "desc": "Survive one crash"},
    "slow": {"name": "Slow-Mo", "letter": "T", "color": (150, 110, 255),
             "desc": "Slows the snake for 8s"},
    "double": {"name": "2x Score", "letter": "2", "color": (255, 170, 40),
               "desc": "Double points for 10s"},
    "shrink": {"name": "Shrink", "letter": "-", "color": (255, 110, 200),
               "desc": "Removes 3 tail segments"},
}

THEMES = {
    "Classic": dict(
        bg1=(15, 15, 20), bg2=(26, 26, 34), menu_bg=(11, 12, 16), header=(20, 20, 28),
        panel=(24, 24, 34), text=(240, 240, 240), dim=(130, 130, 146), accent=(245, 205, 45),
        head=(0, 225, 115), body_a=(0, 190, 90), body_b=(0, 115, 58), food=(225, 65, 65),
        bonus=(245, 205, 45), obstacle=(92, 104, 132), obstacle_edge=(52, 58, 78),
        safe=(0, 205, 165), danger=(225, 75, 75)),
    "Neon": dict(
        bg1=(10, 7, 26), bg2=(18, 12, 42), menu_bg=(8, 5, 20), header=(14, 9, 34),
        panel=(22, 14, 48), text=(236, 236, 255), dim=(140, 128, 184), accent=(255, 70, 175),
        head=(0, 255, 230), body_a=(0, 215, 255), body_b=(150, 70, 255), food=(255, 70, 175),
        bonus=(255, 240, 70), obstacle=(96, 66, 170), obstacle_edge=(54, 34, 104),
        safe=(0, 255, 230), danger=(255, 70, 100)),
    "Retro": dict(
        bg1=(155, 188, 15), bg2=(143, 176, 15), menu_bg=(155, 188, 15), header=(120, 150, 12),
        panel=(139, 172, 15), text=(15, 56, 15), dim=(62, 98, 38), accent=(15, 56, 15),
        head=(15, 56, 15), body_a=(35, 86, 35), body_b=(48, 98, 48), food=(140, 40, 30),
        bonus=(205, 150, 15), obstacle=(70, 110, 45), obstacle_edge=(15, 56, 15),
        safe=(15, 56, 15), danger=(140, 40, 30)),
    "Desert": dict(
        bg1=(46, 34, 26), bg2=(58, 44, 34), menu_bg=(34, 25, 19), header=(34, 25, 19),
        panel=(38, 28, 22), text=(250, 240, 225), dim=(166, 144, 122), accent=(255, 190, 60),
        head=(255, 190, 60), body_a=(230, 150, 50), body_b=(170, 90, 40), food=(220, 70, 60),
        bonus=(110, 230, 200), obstacle=(120, 98, 76), obstacle_edge=(72, 56, 42),
        safe=(110, 230, 200), danger=(230, 80, 70)),
}
THEME_NAMES = list(THEMES.keys())

DEFAULT_SETTINGS = {
    "sound": True, "volume": 0.6, "theme": "Classic", "difficulty": 1, "mode": 0,
    "grid": "Medium", "wrap": False, "checker": True, "fullscreen": False,
    "player_name": "PLAYER",
}

DEFAULT_STATS = {
    "games": 0, "food": 0, "playtime": 0.0, "best_length": 0, "best_combo": 0,
    "powerups": 0, "total_score": 0, "best_level": 1, "achievements": [],
}

ACHIEVEMENTS = [
    ("first_bite", "First Bite", "Eat your first food", lambda g: g.stats["food"] >= 1),
    ("century", "Century", "Score 100 points in one game", lambda g: g.score >= 100),
    ("high_roller", "High Roller", "Score 500 points in one game", lambda g: g.score >= 500),
    ("long_boy", "Long Boy", "Reach a length of 20", lambda g: len(g.snake.body) >= 20),
    ("veteran", "Veteran", "Reach level 5", lambda g: g.level >= 5),
    ("combo_master", "Combo Master", "Hit a x5 combo", lambda g: g.combo >= COMBO_MAX),
    ("power_player", "Power Player", "Collect 10 power-ups", lambda g: g.stats["powerups"] >= 10),
    ("survivor", "Survivor", "Survive 2 minutes in one game", lambda g: g.session_time >= 120),
    ("close_call", "Close Call", "Survive a crash with a Shield", lambda g: g.shield_saves >= 1),
    ("regular", "Regular", "Play 10 games", lambda g: g.stats["games"] >= 10),
]

KEY_ACTIONS = {
    pygame.K_UP: "up", pygame.K_w: "up",
    pygame.K_DOWN: "down", pygame.K_s: "down",
    pygame.K_LEFT: "left", pygame.K_a: "left",
    pygame.K_RIGHT: "right", pygame.K_d: "right",
    pygame.K_RETURN: "select", pygame.K_KP_ENTER: "select", pygame.K_SPACE: "select",
    pygame.K_p: "pause", pygame.K_ESCAPE: "back",
}
DIR_ACTIONS = {"up": UP, "down": DOWN, "left": LEFT, "right": RIGHT}

BACKDROP_STATES = ("main", "settings", "leaderboard", "stats", "help")
FONT_NAMES = "consolas,menlo,dejavusansmono,couriernew,monospace"


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def lerp_color(a, b, t):
    t = clamp(t, 0.0, 1.0)
    return (int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


def fmt_time(seconds):
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m:02d}m {s:02d}s"
    if m:
        return f"{m}m {s:02d}s"
    return f"{s}s"


def get_data_dir():
    """Per-user writable folder (works when the game is packaged as an .exe)."""
    home = os.path.expanduser("~")
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or home
    elif sys.platform == "darwin":
        base = os.path.join(home, "Library", "Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.join(home, ".local", "share")
    path = os.path.join(base, APP_NAME)
    try:
        os.makedirs(path, exist_ok=True)
        return path
    except OSError:
        return os.getcwd()


class Storage:
    """Tiny JSON persistence layer with atomic writes and corruption tolerance."""

    def __init__(self):
        self.dir = get_data_dir()

    def path(self, name):
        return os.path.join(self.dir, name)

    def load(self, name, default):
        try:
            with open(self.path(name), "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(default, dict) and isinstance(data, dict):
                merged = copy.deepcopy(default)
                merged.update(data)
                return merged
            if isinstance(default, list) and isinstance(data, list):
                return data
        except (OSError, ValueError):
            pass
        return copy.deepcopy(default)

    def save(self, name, data):
        tmp = self.path(name + ".tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, self.path(name))
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Sound - synthesised at start-up, so no asset files are needed
# ---------------------------------------------------------------------------
class SoundBank:
    def __init__(self, enabled=True, volume=0.6):
        self.enabled = enabled
        self.volume = volume
        self.sounds = {}
        self.ok = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(44100, -16, 1, 512)
            self.rate, fmt, self.channels = pygame.mixer.get_init()
            if fmt != -16:
                raise RuntimeError("unsupported sample format")
            self._build()
            self.ok = True
            self.set_volume(volume)
        except Exception:
            self.ok = False

    # --- synthesis -------------------------------------------------------
    def _env(self, i, n):
        attack = min(1.0, i / (0.004 * self.rate))
        return attack * (1.0 - i / n) ** 1.3

    def _wave(self, f0, ms, shape="sine", f1=None, vol=1.0):
        n = max(1, int(self.rate * ms / 1000.0))
        f1 = f0 if f1 is None else f1
        out, phase = [], 0.0
        for i in range(n):
            f = f0 + (f1 - f0) * (i / n)
            phase += 2.0 * math.pi * f / self.rate
            s = math.sin(phase)
            if shape == "square":
                s = 1.0 if s >= 0 else -1.0
            elif shape == "tri":
                s = (2.0 / math.pi) * math.asin(s)
            out.append(s * self._env(i, n) * vol)
        return out

    def _noise(self, ms, vol=1.0):
        n = max(1, int(self.rate * ms / 1000.0))
        return [(random.random() * 2 - 1) * self._env(i, n) * vol for i in range(n)]

    @staticmethod
    def _mix(a, b):
        length = max(len(a), len(b))
        a = a + [0.0] * (length - len(a))
        b = b + [0.0] * (length - len(b))
        return [(x + y) * 0.6 for x, y in zip(a, b)]

    def _make(self, samples):
        buf = array.array("h")
        for s in samples:
            v = int(clamp(s, -1.0, 1.0) * 32767 * 0.8)
            for _ in range(self.channels):
                buf.append(v)
        return pygame.mixer.Sound(buffer=buf.tobytes())

    def _build(self):
        fanfare = []
        for f in (523, 659, 784, 1047):
            fanfare += self._wave(f, 85, "tri")
        chime = []
        for f in (784, 988, 1175):
            chime += self._wave(f, 100, "sine")
        self.sounds = {
            "eat": self._make(self._wave(520, 70, "tri", 780, 0.9)),
            "bonus": self._make(self._wave(700, 60, "tri") + self._wave(1050, 110, "tri")),
            "crash": self._make(self._mix(self._noise(260, 0.9),
                                          self._wave(190, 300, "square", 50, 0.8))),
            "level": self._make(fanfare),
            "power": self._make(self._wave(380, 180, "sine", 980, 0.9)),
            "shield_break": self._make(self._mix(self._noise(140, 0.8),
                                                 self._wave(900, 170, "sine", 280, 0.9))),
            "click": self._make(self._wave(880, 28, "square", None, 0.35)),
            "achieve": self._make(chime),
        }

    # --- playback --------------------------------------------------------
    def set_volume(self, volume):
        self.volume = volume
        for snd in self.sounds.values():
            snd.set_volume(volume)

    def play(self, name):
        if self.enabled and self.ok:
            snd = self.sounds.get(name)
            if snd:
                snd.play()


# ---------------------------------------------------------------------------
# Game entities
# ---------------------------------------------------------------------------
class Snake:
    def __init__(self, gw, gh):
        self.gw, self.gh = gw, gh
        cx, cy = gw // 2, gh // 2
        self.body = [(cx, cy), (cx - 1, cy), (cx - 2, cy)]
        self.direction = RIGHT
        self.queue = []          # buffered turns (max 2) so fast key taps aren't lost
        self.grow_pending = 0

    def turn(self, d):
        last = self.queue[-1] if self.queue else self.direction
        if d == last or (d[0] + last[0], d[1] + last[1]) == (0, 0):
            return
        if len(self.queue) < 2:
            self.queue.append(d)

    def move(self, wrap):
        if self.queue:
            self.direction = self.queue.pop(0)
        hx, hy = self.body[0]
        nx, ny = hx + self.direction[0], hy + self.direction[1]
        if wrap:
            nx %= self.gw
            ny %= self.gh
        self.body.insert(0, (nx, ny))
        if self.grow_pending > 0:
            self.grow_pending -= 1
        else:
            self.body.pop()

    def grow(self, amount=1):
        self.grow_pending += amount

    @property
    def head(self):
        return self.body[0]


class Food:
    def __init__(self, pos, special=False):
        self.pos = pos
        self.special = special
        self.ttl = SPECIAL_FOOD_TTL if special else None


class PowerUp:
    def __init__(self, kind, pos):
        self.kind = kind
        self.pos = pos
        self.ttl = POWERUP_TTL


class Particle:
    def __init__(self, x, y, color, speed=170):
        ang = random.uniform(0, math.tau)
        sp = random.uniform(0.3, 1.0) * speed
        self.x, self.y = x, y
        self.vx, self.vy = math.cos(ang) * sp, math.sin(ang) * sp - 40
        self.life = random.uniform(0.35, 0.7)
        self.age = 0.0
        self.color = color
        self.size = random.uniform(2.0, 4.5)

    def update(self, dt):
        self.age += dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 380 * dt

    @property
    def alive(self):
        return self.age < self.life

    @property
    def ratio(self):
        return max(0.0, 1.0 - self.age / self.life)


class Popup:
    """Floating '+30 x3' style text."""

    def __init__(self, text, x, y, color, life=1.0):
        self.text, self.x, self.y, self.color = text, x, y, color
        self.life, self.age = life, 0.0

    @property
    def alive(self):
        return self.age < self.life


class DemoSnake:
    """A tiny AI snake that wanders behind the menus (attract mode)."""

    def __init__(self):
        self.gw, self.gh = 32, 20
        self.timer = 0.0
        self.reset()

    def reset(self):
        self.snake = Snake(self.gw, self.gh)
        self.place_food()

    def place_food(self):
        free = [(x, y) for x in range(self.gw) for y in range(self.gh)
                if (x, y) not in self.snake.body]
        self.food = random.choice(free)

    def steer(self):
        s = self.snake
        hx, hy = s.head
        fx, fy = self.food
        options = []
        for d in (UP, DOWN, LEFT, RIGHT):
            if (d[0] + s.direction[0], d[1] + s.direction[1]) == (0, 0):
                continue
            nx, ny = hx + d[0], hy + d[1]
            if not (0 <= nx < self.gw and 0 <= ny < self.gh):
                continue
            if (nx, ny) in s.body[:-1]:
                continue
            options.append((abs(nx - fx) + abs(ny - fy), d))
        if options:
            options.sort(key=lambda o: o[0])
            s.queue = []
            s.direction = options[0][1]

    def update(self, dt):
        self.timer += dt
        if self.timer < 0.085:
            return
        self.timer = 0.0
        self.steer()
        self.snake.move(False)
        hx, hy = self.snake.head
        if (not (0 <= hx < self.gw and 0 <= hy < self.gh)
                or self.snake.head in self.snake.body[1:]):
            self.reset()
            return
        if self.snake.head == self.food:
            self.snake.grow(1)
            self.place_food()

    def draw(self, surf, theme, w, h):
        bg = theme["menu_bg"]
        cell = max(math.ceil(w / self.gw), math.ceil(h / self.gh))
        ox, oy = (w - cell * self.gw) // 2, (h - cell * self.gh) // 2
        body_c = lerp_color(bg, theme["body_a"], 0.20)
        head_c = lerp_color(bg, theme["head"], 0.32)
        food_c = lerp_color(bg, theme["food"], 0.35)
        pad = max(1, cell // 10)
        for i, (x, y) in enumerate(self.snake.body):
            r = pygame.Rect(ox + x * cell + pad, oy + y * cell + pad, cell - pad * 2, cell - pad * 2)
            pygame.draw.rect(surf, head_c if i == 0 else body_c, r, border_radius=cell // 4)
        fx, fy = self.food
        pygame.draw.circle(surf, food_c, (ox + fx * cell + cell // 2, oy + fy * cell + cell // 2), cell // 3)


# ---------------------------------------------------------------------------
# Menu plumbing
# ---------------------------------------------------------------------------
class MenuItem:
    def __init__(self, label, select=None, change=None):
        self.label = label
        self.select = select    # called on ENTER / click
        self.change = change    # called with +1 / -1 on LEFT / RIGHT

    def text(self):
        return self.label() if callable(self.label) else self.label


class Menu:
    def __init__(self, items):
        self.items = items
        self.index = 0
        self.rects = []


# ---------------------------------------------------------------------------
# The game
# ---------------------------------------------------------------------------
class Game:
    def __init__(self):
        pygame.init()
        self.storage = Storage()
        self.settings = self._load_settings()
        self.scores = [e for e in self.storage.load("scores.json", [])
                       if isinstance(e, dict) and isinstance(e.get("score"), int)]
        self.stats = self.storage.load("stats.json", DEFAULT_STATS)

        pygame.display.set_caption("Snake")
        try:
            pygame.display.set_icon(self._make_icon())
        except pygame.error:
            pass
        self.is_fullscreen = False
        self.windowed_size = DEFAULT_WINDOW
        self.screen = pygame.display.set_mode(DEFAULT_WINDOW, pygame.RESIZABLE)
        self.clock = pygame.time.Clock()

        self.sound = SoundBank(self.settings["sound"], self.settings["volume"])
        self.theme = THEMES[self.settings["theme"]]
        self.fonts = {}
        self.ui_scale = 1.0
        self.header_h = BASE_HEADER
        self.cell = 20
        self.ox = self.oy = self.dox = self.doy = 0
        self.gw, self.gh = GRID_SIZES[self.settings["grid"]]
        self._layout_size = None
        self._layout_grid = None
        self.board_cache = None
        self._dim_cache = None

        self.joysticks = []
        self.axis_state = {}
        self._init_joysticks()

        self.toasts, self.popups, self.particles = [], [], []
        self.ui_time = 0.0
        self.shake = 0.0

        self.state = "main"
        self.return_state = "main"
        self.confirm_reset = False
        self.name_buffer = ""
        self.name_fresh = True
        self.last_entry = None
        self.demo = DemoSnake()

        self.snake = Snake(self.gw, self.gh)
        self._reset_runtime()
        self._build_menus()
        self.sync_display(force=True)
        if self.settings["fullscreen"]:
            self.set_fullscreen(True)

    # ------------------------------------------------------------------
    # Settings / persistence
    # ------------------------------------------------------------------
    def _load_settings(self):
        s = self.storage.load("settings.json", DEFAULT_SETTINGS)

        def as_int(v, default, lo, hi):
            try:
                return clamp(int(v), lo, hi)
            except (TypeError, ValueError):
                return default

        s["difficulty"] = as_int(s["difficulty"], 1, 0, len(DIFFICULTIES) - 1)
        s["mode"] = as_int(s["mode"], 0, 0, len(MODES) - 1)
        try:
            s["volume"] = clamp(float(s["volume"]), 0.0, 1.0)
        except (TypeError, ValueError):
            s["volume"] = 0.6
        if s["theme"] not in THEMES:
            s["theme"] = "Classic"
        if s["grid"] not in GRID_SIZES:
            s["grid"] = "Medium"
        for key in ("sound", "wrap", "checker", "fullscreen"):
            s[key] = bool(s[key])
        s["player_name"] = (str(s["player_name"]).strip().upper()[:10]) or "PLAYER"
        return s

    def save_settings(self):
        self.storage.save("settings.json", self.settings)

    def save_all(self):
        self.save_settings()
        self.storage.save("stats.json", self.stats)
        self.storage.save("scores.json", self.scores)

    def best_score(self):
        return max((e["score"] for e in self.scores), default=0)

    @staticmethod
    def _make_icon():
        s = pygame.Surface((32, 32), pygame.SRCALPHA)
        pygame.draw.rect(s, (20, 24, 30), (0, 0, 32, 32), border_radius=7)
        pygame.draw.lines(s, (0, 210, 100), False, [(6, 25), (6, 15), (17, 15), (17, 8), (25, 8)], 5)
        pygame.draw.circle(s, (255, 255, 255), (25, 8), 3)
        pygame.draw.circle(s, (225, 65, 65), (24, 24), 3)
        return s

    def _init_joysticks(self):
        self.joysticks = []
        try:
            for i in range(pygame.joystick.get_count()):
                self.joysticks.append(pygame.joystick.Joystick(i))
        except pygame.error:
            pass

    # ------------------------------------------------------------------
    # Display / layout
    # ------------------------------------------------------------------
    def font(self, size, bold=True):
        key = (size, bold)
        f = self.fonts.get(key)
        if f is None:
            f = pygame.font.SysFont(FONT_NAMES, max(8, int(size * self.ui_scale)), bold=bold)
            self.fonts[key] = f
        return f

    def text(self, s, size, color, pos, anchor="topleft", shadow=False, alpha=None, bold=True):
        font = self.font(size, bold)
        surf = font.render(str(s), True, color)
        rect = surf.get_rect()
        setattr(rect, anchor, (int(pos[0]), int(pos[1])))
        if shadow:
            off = max(1, int(2 * self.ui_scale))
            sh = font.render(str(s), True, (0, 0, 0))
            if alpha is not None:
                sh.set_alpha(alpha)
            self.screen.blit(sh, rect.move(off, off))
        if alpha is not None:
            surf.set_alpha(alpha)
        self.screen.blit(surf, rect)
        return rect

    def draw_panel(self, rect, alpha=238, radius=16):
        T = self.theme
        surf = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(surf, (*T["panel"], alpha), surf.get_rect(), border_radius=radius)
        pygame.draw.rect(surf, (*T["accent"], 255), surf.get_rect(), width=2, border_radius=radius)
        self.screen.blit(surf, rect.topleft)

    def dim(self, alpha=150):
        size = self.screen.get_size()
        if not self._dim_cache or self._dim_cache[0] != (size, alpha):
            surf = pygame.Surface(size, pygame.SRCALPHA)
            surf.fill((0, 0, 0, alpha))
            self._dim_cache = ((size, alpha), surf)
        self.screen.blit(self._dim_cache[1], (0, 0))

    def set_fullscreen(self, on):
        try:
            if on:
                self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            else:
                self.screen = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
            self.is_fullscreen = on
        except pygame.error:
            self.screen = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
            self.is_fullscreen = False
        self.settings["fullscreen"] = self.is_fullscreen
        self.sync_display(force=True)

    def toggle_fullscreen(self):
        self.set_fullscreen(not self.is_fullscreen)
        self.save_settings()

    def sync_display(self, force=False):
        surf = pygame.display.get_surface()
        if surf is None:
            return
        self.screen = surf
        size = surf.get_size()
        if not self.is_fullscreen:
            self.windowed_size = size
        if force or size != self._layout_size or self._layout_grid != (self.gw, self.gh):
            self.recompute_layout()

    def recompute_layout(self):
        w, h = self.screen.get_size()
        w, h = max(w, 1), max(h, 1)
        self.ui_scale = clamp(min(w / DEFAULT_WINDOW[0], h / DEFAULT_WINDOW[1]), 0.5, 2.2)
        self.fonts.clear()
        self.header_h = int(BASE_HEADER * self.ui_scale)
        self.cell = max(6, min(w // self.gw, (h - self.header_h) // self.gh))
        pw, ph = self.cell * self.gw, self.cell * self.gh
        self.ox = (w - pw) // 2
        self.oy = self.header_h + max(0, (h - self.header_h - ph) // 2)
        self._layout_size = (w, h)
        self._layout_grid = (self.gw, self.gh)
        self.board_cache = None

    def get_board(self):
        key = (self.cell, self.gw, self.gh, self.settings["theme"], self.settings["checker"])
        if self.board_cache and self.board_cache[0] == key:
            return self.board_cache[1]
        T = self.theme
        surf = pygame.Surface((self.cell * self.gw, self.cell * self.gh))
        surf.fill(T["bg1"])
        if self.settings["checker"]:
            for x in range(self.gw):
                for y in range(self.gh):
                    if (x + y) % 2:
                        surf.fill(T["bg2"], (x * self.cell, y * self.cell, self.cell, self.cell))
        self.board_cache = (key, surf)
        return surf

    def cell_rect(self, x, y):
        return pygame.Rect(self.dox + x * self.cell, self.doy + y * self.cell, self.cell, self.cell)

    def cell_center(self, pos):
        return (self.ox + (pos[0] + 0.5) * self.cell, self.oy + (pos[1] + 0.5) * self.cell)

    # ------------------------------------------------------------------
    # Menus
    # ------------------------------------------------------------------
    def _build_menus(self):
        S = self.settings
        onoff = lambda v: "On" if v else "Off"
        self.menus = {
            "main": Menu([
                MenuItem("Play", select=self.new_game),
                MenuItem(lambda: f"Mode: < {MODES[S['mode']][0]} >",
                         change=lambda d: self.cycle_index("mode", len(MODES), d)),
                MenuItem(lambda: f"Difficulty: < {DIFFICULTIES[S['difficulty']]['name']} >",
                         change=lambda d: self.cycle_index("difficulty", len(DIFFICULTIES), d)),
                MenuItem("Settings", select=lambda: self.open_sub("settings")),
                MenuItem("Leaderboard", select=lambda: self.open_sub("leaderboard")),
                MenuItem("Stats & Achievements", select=lambda: self.open_sub("stats")),
                MenuItem("How to Play", select=lambda: self.open_sub("help")),
                MenuItem("Quit", select=self.quit),
            ]),
            "settings": Menu([
                MenuItem(lambda: f"Sound: < {onoff(S['sound'])} >",
                         change=lambda d: self.toggle_setting("sound")),
                MenuItem(lambda: f"Volume: < {int(round(S['volume'] * 100))}% >",
                         change=self.change_volume),
                MenuItem(lambda: f"Theme: < {S['theme']} >",
                         change=lambda d: self.cycle_choice("theme", THEME_NAMES, d)),
                MenuItem(lambda: f"Grid Size: < {S['grid']} >",
                         change=lambda d: self.cycle_choice("grid", list(GRID_SIZES), d)),
                MenuItem(lambda: f"Wrap Edges: < {onoff(S['wrap'])} >",
                         change=lambda d: self.toggle_setting("wrap")),
                MenuItem(lambda: f"Checkerboard: < {onoff(S['checker'])} >",
                         change=lambda d: self.toggle_setting("checker")),
                MenuItem(lambda: f"Fullscreen: < {onoff(self.is_fullscreen)} >",
                         change=lambda d: self.toggle_fullscreen()),
                MenuItem(lambda: "CONFIRM: erase scores & stats?" if self.confirm_reset
                         else "Reset Scores & Stats", select=self.reset_data),
                MenuItem("Back", select=self.close_sub),
            ]),
            "pause": Menu([
                MenuItem("Resume", select=self.resume),
                MenuItem("Restart", select=self.new_game),
                MenuItem("Settings", select=lambda: self.open_sub("settings")),
                MenuItem("Main Menu", select=self.to_main),
            ]),
            "game_over": Menu([
                MenuItem("Play Again", select=self.new_game),
                MenuItem("Leaderboard", select=lambda: self.open_sub("leaderboard")),
                MenuItem("Main Menu", select=self.to_main),
            ]),
        }

    def active_menu(self):
        return {"main": self.menus["main"], "settings": self.menus["settings"],
                "paused": self.menus["pause"], "game_over": self.menus["game_over"]}.get(self.state)

    def on_setting_changed(self):
        self.theme = THEMES[self.settings["theme"]]
        self.sound.enabled = self.settings["sound"]
        self.sound.set_volume(self.settings["volume"])
        self.save_settings()
        self.sound.play("click")

    def cycle_index(self, key, count, d):
        self.settings[key] = (self.settings[key] + d) % count
        self.on_setting_changed()

    def cycle_choice(self, key, options, d):
        i = options.index(self.settings[key])
        self.settings[key] = options[(i + d) % len(options)]
        self.on_setting_changed()

    def toggle_setting(self, key):
        self.settings[key] = not self.settings[key]
        self.on_setting_changed()

    def change_volume(self, d):
        self.settings["volume"] = clamp(round(self.settings["volume"] + 0.1 * d, 1), 0.0, 1.0)
        self.on_setting_changed()

    def reset_data(self):
        if not self.confirm_reset:
            self.confirm_reset = True
            self.toast("Select again to confirm the reset", self.theme["danger"])
            return
        self.scores = []
        self.stats = copy.deepcopy(DEFAULT_STATS)
        self.last_entry = None
        self.confirm_reset = False
        self.save_all()
        self.toast("Scores and stats cleared", self.theme["safe"])

    def open_sub(self, state):
        self.return_state = self.state
        self.state = state
        self.confirm_reset = False

    def close_sub(self):
        self.confirm_reset = False
        self.state = self.return_state if self.return_state != self.state else "main"

    def to_main(self):
        self.state = "main"

    # ------------------------------------------------------------------
    # Game state
    # ------------------------------------------------------------------
    def _reset_runtime(self):
        self.zen = self.time_attack = False
        self.wrap = False
        self.mode_name = MODES[self.settings["mode"]][0]
        self.diff = DIFFICULTIES[self.settings["difficulty"]]
        self.fps = self.diff["fps"]
        self.score = 0
        self.level = 1
        self.eaten = 0
        self.combo = 0
        self.combo_timer = 0.0
        self.effects = {"slow": 0.0, "double": 0.0}
        self.shield = False
        self.shield_saves = 0
        self.session_time = 0.0
        self.time_left = TIME_ATTACK_SECONDS
        self.accum = 0.0
        self.countdown = 0.0
        self.obstacles = []
        self.food = None
        self.powerup = None
        self.end_reason = ""
        self.new_best = False
        self.best_before = 0

    def new_game(self):
        self._reset_runtime()
        self.zen = self.mode_name == "Zen"
        self.time_attack = self.mode_name == "Time Attack"
        self.wrap = self.settings["wrap"] or self.zen
        self.gw, self.gh = GRID_SIZES[self.settings["grid"]]
        self.snake = Snake(self.gw, self.gh)
        self.particles.clear()
        self.popups.clear()
        self.last_entry = None
        self.best_before = self.best_score()
        self.countdown = START_COUNTDOWN
        count = 0 if self.zen else self.diff["obstacles"]
        for _ in range(count):
            cell = self.random_free_cell(min_head_dist=6)
            if cell:
                self.obstacles.append(cell)
        self.food = self.spawn_food()
        self.state = "playing"
        self.sync_display(force=True)

    def pause(self):
        if self.state == "playing":
            self.state = "paused"
            self.menus["pause"].index = 0

    def resume(self):
        if self.state == "paused":
            self.state = "playing"
            self.countdown = max(self.countdown, RESUME_COUNTDOWN)
            self.accum = 0.0

    def random_free_cell(self, min_head_dist=0):
        occupied = set(self.snake.body) | set(self.obstacles)
        if self.food:
            occupied.add(self.food.pos)
        if self.powerup:
            occupied.add(self.powerup.pos)
        hx, hy = self.snake.head
        cells = [(x, y) for x in range(self.gw) for y in range(self.gh)
                 if (x, y) not in occupied and abs(x - hx) + abs(y - hy) >= min_head_dist]
        return random.choice(cells) if cells else None

    def spawn_food(self, force_normal=False):
        cell = self.random_free_cell()
        if cell is None:
            return None
        return Food(cell, special=(not force_normal and random.random() < 0.15))

    def maybe_spawn_powerup(self):
        if self.powerup is not None or random.random() > self.diff["powerup"]:
            return
        cell = self.random_free_cell(min_head_dist=3)
        if cell:
            kind = random.choices(list(POWERUPS), weights=[28, 28, 28, 16])[0]
            self.powerup = PowerUp(kind, cell)

    # ------------------------------------------------------------------
    # Effects / feedback helpers
    # ------------------------------------------------------------------
    def toast(self, text, color=None, sound=None):
        self.toasts.append({"text": text, "color": color or self.theme["accent"],
                            "age": 0.0, "life": 3.0})
        if sound:
            self.sound.play(sound)

    def add_popup(self, text, cell, color):
        x, y = self.cell_center(cell)
        self.popups.append(Popup(text, x, y, color))

    def burst(self, cell, color, count=14):
        x, y = self.cell_center(cell)
        for _ in range(count):
            self.particles.append(Particle(x, y, color))

    def check_achievements(self):
        unlocked = self.stats["achievements"]
        for aid, name, _desc, cond in ACHIEVEMENTS:
            if aid not in unlocked and cond(self):
                unlocked.append(aid)
                self.toast(f"Achievement: {name}", self.theme["safe"], "achieve")
                self.storage.save("stats.json", self.stats)

    # ------------------------------------------------------------------
    # Leaderboard
    # ------------------------------------------------------------------
    def qualifies(self, score):
        if score <= 0:
            return False
        if len(self.scores) < LEADERBOARD_SIZE:
            return True
        return score > min(e["score"] for e in self.scores)

    def add_score(self, name):
        entry = {"name": name, "score": self.score, "mode": self.mode_name,
                 "difficulty": self.diff["name"], "level": self.level,
                 "date": datetime.date.today().isoformat()}
        self.scores.append(entry)
        self.scores.sort(key=lambda e: e["score"], reverse=True)
        del self.scores[LEADERBOARD_SIZE:]
        self.last_entry = entry
        self.storage.save("scores.json", self.scores)

    def commit_name(self):
        name = self.name_buffer.strip().upper() or "PLAYER"
        self.settings["player_name"] = name
        self.save_settings()
        self.add_score(name)
        self.state = "game_over"
        self.menus["game_over"].index = 0

    # ------------------------------------------------------------------
    # Core rules
    # ------------------------------------------------------------------
    def end_game(self, reason):
        if self.state != "playing":
            return
        self.end_reason = reason
        if reason == "win":
            self.sound.play("level")
        else:
            self.sound.play("crash")
        if reason in ("wall", "self", "obstacle"):
            self.shake = 0.4
        st = self.stats
        st["games"] += 1
        st["playtime"] += self.session_time
        st["total_score"] += self.score
        st["best_length"] = max(st["best_length"], len(self.snake.body))
        st["best_level"] = max(st["best_level"], self.level)
        self.new_best = self.score > self.best_before and self.score > 0
        self.check_achievements()
        self.storage.save("stats.json", st)
        if self.qualifies(self.score):
            self.name_buffer = self.settings["player_name"]
            self.name_fresh = True
            self.state = "name_entry"
        else:
            self.state = "game_over"
            self.menus["game_over"].index = 0

    def tick(self):
        s = self.snake
        s.move(self.wrap)
        hx, hy = s.head
        crash = None
        if not self.wrap and not (0 <= hx < self.gw and 0 <= hy < self.gh):
            crash = "wall"
        elif s.head in s.body[1:]:
            crash = "self"
        elif s.head in self.obstacles:
            crash = "obstacle"

        if crash:
            if not self.shield:
                self.end_game(crash)
                return
            # Shield absorbs the crash
            self.shield = False
            self.shield_saves += 1
            self.sound.play("shield_break")
            self.shake = 0.15
            if crash == "wall":
                s.body[0] = (hx % self.gw, hy % self.gh)
                if s.head in s.body[1:]:
                    self.end_game("self")
                    return
                if s.head in self.obstacles:
                    self.end_game("obstacle")
                    return
            elif crash == "obstacle":
                self.obstacles.remove(s.head)
            else:
                k = s.body.index(s.head, 1)
                del s.body[max(k, 1):]
            self.burst(s.head, POWERUPS["shield"]["color"], 22)
            self.toast("Shield saved you!", POWERUPS["shield"]["color"])

        if self.food and s.head == self.food.pos:
            self.eat_food()
        if self.state != "playing":
            return
        if self.powerup and s.head == self.powerup.pos:
            self.collect_powerup()

    def eat_food(self):
        T = self.theme
        f = self.food
        base = 30 if f.special else 10
        if self.combo_timer > 0 and self.combo > 0:
            self.combo = min(COMBO_MAX, self.combo + 1)
        else:
            self.combo = 1
        self.combo_timer = COMBO_WINDOW
        mult = self.combo * (2 if self.effects["double"] > 0 else 1)
        points = base * mult
        self.score += points
        self.snake.grow(2 if f.special else 1)
        self.eaten += 1
        self.stats["food"] += 1
        self.stats["best_combo"] = max(self.stats["best_combo"], self.combo)

        label = f"+{points}" + (f"  x{self.combo}" if self.combo >= 2 else "")
        color = T["bonus"] if f.special else T["text"]
        self.add_popup(label, f.pos, color)
        self.burst(f.pos, T["bonus"] if f.special else T["food"], 16)
        self.sound.play("bonus" if f.special else "eat")

        if self.time_attack:
            self.time_left = min(self.time_left + TIME_ATTACK_BONUS, TIME_ATTACK_SECONDS * 2)

        self.food = self.spawn_food()
        if self.food is None:
            self.end_game("win")
            return

        if not self.zen and self.eaten % FPS_STEP_EVERY == 0 and self.fps < FPS_MAX:
            self.fps += 1

        new_level = self.eaten // LEVEL_UP_EVERY + 1
        if new_level > self.level:
            self.level = new_level
            self.stats["best_level"] = max(self.stats["best_level"], self.level)
            self.toast(f"Level {self.level}!", T["accent"], "level")
            if not self.zen:
                cell = self.random_free_cell(min_head_dist=5)
                if cell:
                    self.obstacles.append(cell)
        self.maybe_spawn_powerup()

    def collect_powerup(self):
        p = self.powerup
        self.powerup = None
        info = POWERUPS[p.kind]
        self.stats["powerups"] += 1
        if p.kind == "shield":
            self.shield = True
        elif p.kind == "slow":
            self.effects["slow"] = SLOW_SECONDS
        elif p.kind == "double":
            self.effects["double"] = DOUBLE_SECONDS
        elif p.kind == "shrink":
            n = max(0, min(3, len(self.snake.body) - 3))
            if n:
                del self.snake.body[-n:]
            self.snake.grow_pending = 0
        self.sound.play("power")
        self.add_popup(info["name"], p.pos, info["color"])
        self.burst(p.pos, info["color"], 18)

    # ------------------------------------------------------------------
    # Per-frame update
    # ------------------------------------------------------------------
    def update(self, dt):
        self.ui_time += dt
        for t in self.toasts:
            t["age"] += dt
        self.toasts = [t for t in self.toasts if t["age"] < t["life"]]
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.alive]
        for p in self.popups:
            p.age += dt
        self.popups = [p for p in self.popups if p.alive]
        if self.shake > 0:
            self.shake = max(0.0, self.shake - dt)

        if self.state == "playing":
            self.update_playing(dt)
        elif self.state in BACKDROP_STATES:
            self.demo.update(dt)

    def update_playing(self, dt):
        if self.countdown > 0:
            self.countdown = max(0.0, self.countdown - dt)
            return
        self.session_time += dt

        if self.combo_timer > 0:
            self.combo_timer -= dt
            if self.combo_timer <= 0:
                self.combo = 0
        for k in self.effects:
            if self.effects[k] > 0:
                self.effects[k] = max(0.0, self.effects[k] - dt)
        if self.powerup:
            self.powerup.ttl -= dt
            if self.powerup.ttl <= 0:
                self.powerup = None
        if self.food and self.food.ttl is not None:
            self.food.ttl -= dt
            if self.food.ttl <= 0:
                self.food = self.spawn_food(force_normal=True)
                if self.food is None:
                    self.end_game("win")
                    return
        if self.time_attack:
            self.time_left -= dt
            if self.time_left <= 0:
                self.time_left = 0.0
                self.end_game("time")
                return

        interval = 1.0 / self.fps
        if self.effects["slow"] > 0:
            interval *= SLOW_FACTOR
        self.accum += dt
        steps = 0
        while self.accum >= interval and self.state == "playing":
            self.accum -= interval
            self.tick()
            steps += 1
            if steps >= 4:
                self.accum = 0.0
                break
        if self.state == "playing":
            self.check_achievements()

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------
    def handle_events(self):
        focus_lost = getattr(pygame, "WINDOWFOCUSLOST", None)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit()
            elif event.type == pygame.KEYDOWN:
                self.on_key(event)
            elif event.type == pygame.MOUSEMOTION:
                self.on_mouse_motion(event.pos)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self.on_mouse_click(event)
            elif event.type == pygame.JOYHATMOTION:
                x, y = event.value
                if x:
                    self.do_action("right" if x > 0 else "left")
                if y:
                    self.do_action("up" if y > 0 else "down")
            elif event.type == pygame.JOYAXISMOTION:
                self.on_joy_axis(event)
            elif event.type == pygame.JOYBUTTONDOWN:
                action = {0: "select", 1: "back", 7: "pause", 9: "pause"}.get(event.button)
                if action:
                    self.do_action(action)
            elif event.type in (getattr(pygame, "JOYDEVICEADDED", -1),
                                getattr(pygame, "JOYDEVICEREMOVED", -1)):
                self._init_joysticks()
            elif focus_lost is not None and event.type == focus_lost:
                self.pause()    # auto-pause when the window loses focus

    def on_joy_axis(self, event):
        if event.axis not in (0, 1):
            return
        key = (getattr(event, "instance_id", 0), event.axis)
        cur = 0 if abs(event.value) < 0.6 else (1 if event.value > 0 else -1)
        prev = self.axis_state.get(key, 0)
        self.axis_state[key] = cur
        if cur and cur != prev:
            if event.axis == 0:
                self.do_action("right" if cur > 0 else "left")
            else:
                self.do_action("down" if cur > 0 else "up")

    def on_key(self, event):
        key = event.key
        if key == pygame.K_F11 or (key == pygame.K_f and self.state != "name_entry"):
            self.toggle_fullscreen()
            return
        if key == pygame.K_F12:
            self.screenshot()
            return
        if self.state == "name_entry":
            self.name_key(event)
            return
        if key == pygame.K_m:
            self.toggle_setting("sound")
            self.toast("Sound " + ("on" if self.settings["sound"] else "off"))
            return
        if self.state in ("leaderboard", "stats", "help"):
            self.close_sub()        # any key closes the info screens
            return
        action = KEY_ACTIONS.get(key)
        if action:
            self.do_action(action)

    def name_key(self, event):
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
            self.commit_name()
        elif event.key == pygame.K_BACKSPACE:
            self.name_buffer = "" if self.name_fresh else self.name_buffer[:-1]
            self.name_fresh = False
        else:
            ch = event.unicode
            if ch and ch.isprintable() and (ch.isalnum() or ch in " _-."):
                if self.name_fresh:
                    self.name_buffer, self.name_fresh = "", False
                if len(self.name_buffer) < 10:
                    self.name_buffer += ch.upper()

    def do_action(self, action):
        st = self.state
        if st == "playing":
            if action in DIR_ACTIONS:
                self.snake.turn(DIR_ACTIONS[action])
            elif action in ("pause", "back"):
                self.pause()
        elif st == "paused":
            if action in ("pause", "back"):
                self.resume()
            else:
                self.menu_action(self.menus["pause"], action)
        elif st in ("main", "settings", "game_over"):
            if action == "back":
                if st == "main":
                    self.quit()
                elif st == "settings":
                    self.close_sub()
                else:
                    self.to_main()
            else:
                self.menu_action(self.menus[st], action)
        elif st in ("leaderboard", "stats", "help"):
            if action in ("back", "select", "pause"):
                self.close_sub()

    def menu_action(self, menu, action):
        item = menu.items[menu.index]
        if action in ("up", "down"):
            menu.index = (menu.index + (-1 if action == "up" else 1)) % len(menu.items)
            self.confirm_reset = False
            self.sound.play("click")
        elif action in ("left", "right") and item.change:
            item.change(-1 if action == "left" else 1)
        elif action == "select":
            if item.select:
                self.sound.play("click")
                item.select()
            elif item.change:
                item.change(1)

    def on_mouse_motion(self, pos):
        menu = self.active_menu()
        if not menu:
            return
        for i, r in enumerate(menu.rects):
            if r.collidepoint(pos):
                if i != menu.index:
                    menu.index = i
                    self.confirm_reset = False
                    self.sound.play("click")
                break

    def on_mouse_click(self, event):
        if event.button not in (1, 3):
            return
        menu = self.active_menu()
        if menu:
            for i, r in enumerate(menu.rects):
                if r.collidepoint(event.pos):
                    menu.index = i
                    item = menu.items[i]
                    if event.button == 3 and item.change:
                        item.change(-1)
                    elif item.select:
                        self.sound.play("click")
                        item.select()
                    elif item.change:
                        item.change(1)
                    return
        elif self.state in ("leaderboard", "stats", "help") and event.button == 1:
            self.close_sub()

    def screenshot(self):
        try:
            folder = os.path.join(self.storage.dir, "screenshots")
            os.makedirs(folder, exist_ok=True)
            path = os.path.join(folder, time.strftime("snake_%Y%m%d_%H%M%S.png"))
            pygame.image.save(self.screen, path)
            self.toast("Screenshot saved", self.theme["safe"])
        except (OSError, pygame.error):
            self.toast("Could not save screenshot", self.theme["danger"])

    # ------------------------------------------------------------------
    # Drawing - shared pieces
    # ------------------------------------------------------------------
    def draw_backdrop(self):
        w, h = self.screen.get_size()
        self.screen.fill(self.theme["menu_bg"])
        self.demo.draw(self.screen, self.theme, w, h)

    def draw_menu(self, menu, cx, top, step, width, size=26):
        T, s = self.theme, self.ui_scale
        menu.rects = []
        for i, item in enumerate(menu.items):
            rect = pygame.Rect(0, 0, width, max(10, int(step * 0.88)))
            rect.center = (cx, top + i * step + step // 2)
            sel = i == menu.index
            if sel:
                hl = pygame.Surface(rect.size, pygame.SRCALPHA)
                pygame.draw.rect(hl, (*T["accent"], 46), hl.get_rect(), border_radius=10)
                pygame.draw.rect(hl, (*T["accent"], 255), hl.get_rect(), width=2, border_radius=10)
                self.screen.blit(hl, rect.topleft)
                t = int(9 * s)
                pygame.draw.polygon(self.screen, T["accent"], [
                    (rect.left + t, rect.centery - t), (rect.left + t, rect.centery + t),
                    (rect.left + t * 2, rect.centery)])
            self.text(item.text(), size, T["accent"] if sel else T["text"], rect.center, "center")
            menu.rects.append(rect)

    def draw_toasts(self):
        T, s = self.theme, self.ui_scale
        w, h = self.screen.get_size()
        # In-game: stack downward under the header. In menus: stack upward from the
        # bottom edge so a toast never covers a screen title.
        in_game = self.state not in BACKDROP_STATES
        y = (self.header_h + 10 * s) if in_game else (h - 14 * s)
        for t in self.toasts[-3:] if in_game else self.toasts[-1:]:
            a = clamp(min(t["age"] / 0.2, (t["life"] - t["age"]) / 0.4), 0.0, 1.0)
            surf = self.font(20).render(t["text"], True, T["text"])
            pad = int(14 * s)
            r = pygame.Rect(0, 0, surf.get_width() + pad * 2, surf.get_height() + int(pad * 0.8))
            if in_game:
                r.midtop = (w // 2, int(y))
            else:
                r.midbottom = (w // 2, int(y))
            box = pygame.Surface(r.size, pygame.SRCALPHA)
            pygame.draw.rect(box, (*T["panel"], int(240 * a)), box.get_rect(), border_radius=10)
            pygame.draw.rect(box, (*t["color"], int(255 * a)), box.get_rect(), width=2, border_radius=10)
            self.screen.blit(box, r.topleft)
            surf.set_alpha(int(255 * a))
            self.screen.blit(surf, surf.get_rect(center=r.center))
            y += (r.height + 8 * s) if in_game else -(r.height + 8 * s)

    # ------------------------------------------------------------------
    # Drawing - game scene
    # ------------------------------------------------------------------
    def draw_game(self):
        T, s = self.theme, self.ui_scale
        self.screen.fill(T["bg1"])
        mag = int(10 * s * (self.shake / 0.4)) if self.shake > 0 else 0
        sx = random.randint(-mag, mag) if mag else 0
        sy = random.randint(-mag, mag) if mag else 0
        self.dox, self.doy = self.ox + sx, self.oy + sy
        pw, ph = self.cell * self.gw, self.cell * self.gh
        self.screen.blit(self.get_board(), (self.dox, self.doy))
        if self.effects["slow"] > 0:
            tint = pygame.Surface((pw, ph), pygame.SRCALPHA)
            tint.fill((*POWERUPS["slow"]["color"], 30))
            self.screen.blit(tint, (self.dox, self.doy))

        self.draw_obstacles()
        self.draw_powerup()
        self.draw_food()
        self.draw_snake()
        self.draw_particles()
        self.draw_popups()

        border = T["safe"] if self.wrap else T["danger"]
        pygame.draw.rect(self.screen, border, (self.dox - 3, self.doy - 3, pw + 6, ph + 6),
                         3, border_radius=4)
        self.draw_header()
        self.draw_chips()
        if self.state == "playing" and self.countdown > 0:
            self.draw_countdown()

    def draw_obstacles(self):
        T, c = self.theme, self.cell
        pad = max(1, c // 14)
        for (x, y) in self.obstacles:
            r = self.cell_rect(x, y).inflate(-pad * 2, -pad * 2)
            pygame.draw.rect(self.screen, T["obstacle"], r, border_radius=max(2, c // 6))
            pygame.draw.rect(self.screen, T["obstacle_edge"], r, width=max(1, c // 10),
                             border_radius=max(2, c // 6))
            inner = r.inflate(-c // 3, -c // 3)
            pygame.draw.rect(self.screen, lerp_color(T["obstacle"], T["obstacle_edge"], 0.5),
                             inner, border_radius=2)

    def draw_powerup(self):
        p = self.powerup
        if not p:
            return
        if p.ttl < 3.0 and int(self.ui_time * 6) % 2 == 0:
            return
        info = POWERUPS[p.kind]
        c = self.cell
        r = self.cell_rect(*p.pos).inflate(-max(2, c // 8), -max(2, c // 8))
        pygame.draw.rect(self.screen, info["color"], r, border_radius=max(3, c // 4))
        pygame.draw.rect(self.screen, (255, 255, 255), r, width=2, border_radius=max(3, c // 4))
        self.text(info["letter"], int(c * 0.72 / self.ui_scale), (20, 20, 20), r.center, "center")

    def draw_food(self):
        f = self.food
        if not f:
            return
        T, c = self.theme, self.cell
        r = self.cell_rect(*f.pos)
        pulse = 1.0 + 0.07 * math.sin(self.ui_time * 7)
        color = T["bonus"] if f.special else T["food"]
        rad = max(2, int(c * 0.38 * pulse))
        pygame.draw.circle(self.screen, color, r.center, rad)
        pygame.draw.circle(self.screen, lerp_color(color, (255, 255, 255), 0.55),
                           (r.centerx - rad // 3, r.centery - rad // 3), max(1, rad // 4))
        if f.special:
            blink = f.ttl is not None and f.ttl < 2.0 and int(self.ui_time * 8) % 2 == 0
            if not blink:
                pygame.draw.circle(self.screen, color, r.center, rad + max(3, c // 6), max(1, c // 12))

    def draw_snake(self):
        T, c = self.theme, self.cell
        body = self.snake.body
        n = len(body)
        pad = max(1, c // 14)
        radius = max(3, c // 4)
        hr = self.cell_rect(*body[0])
        if self.shield:
            r = int(c * (0.78 + 0.08 * math.sin(self.ui_time * 8)))
            col = POWERUPS["shield"]["color"]
            aura = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(aura, (*col, 70), (r, r), r)
            pygame.draw.circle(aura, (*col, 210), (r, r), r, 2)
            self.screen.blit(aura, (hr.centerx - r, hr.centery - r))
        for i in range(n - 1, -1, -1):
            r = self.cell_rect(*body[i]).inflate(-pad * 2, -pad * 2)
            color = T["head"] if i == 0 else lerp_color(T["body_a"], T["body_b"], (i - 1) / max(1, n - 2))
            pygame.draw.rect(self.screen, color, r, border_radius=radius)
        d = self.snake.direction
        px, py = -d[1], d[0]
        for sgn in (-1, 1):
            ex = hr.centerx + d[0] * c * 0.16 + px * sgn * c * 0.2
            ey = hr.centery + d[1] * c * 0.16 + py * sgn * c * 0.2
            pygame.draw.circle(self.screen, (255, 255, 255), (int(ex), int(ey)), max(2, int(c * 0.14)))
            pygame.draw.circle(self.screen, (10, 10, 10),
                               (int(ex + d[0] * c * 0.05), int(ey + d[1] * c * 0.05)), max(1, int(c * 0.07)))

    def draw_particles(self):
        for p in self.particles:
            rad = max(1, int(p.size * p.ratio))
            surf = pygame.Surface((rad * 2 + 2, rad * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*p.color, int(255 * p.ratio)), (rad + 1, rad + 1), rad)
            self.screen.blit(surf, (p.x - rad - 1, p.y - rad - 1))

    def draw_popups(self):
        for p in self.popups:
            k = p.age / p.life
            self.text(p.text, 22, p.color, (p.x, p.y - 46 * self.ui_scale * k), "center",
                      shadow=True, alpha=int(255 * (1 - k)))

    def draw_header(self):
        T, s = self.theme, self.ui_scale
        w = self.screen.get_width()
        pygame.draw.rect(self.screen, T["header"], (0, 0, w, self.header_h))
        # level progress bar along the bottom edge
        prog = (self.eaten % LEVEL_UP_EVERY) / LEVEL_UP_EVERY
        pygame.draw.rect(self.screen, T["bg2"], (0, self.header_h - 4, w, 4))
        pygame.draw.rect(self.screen, T["accent"], (0, self.header_h - 4, int(w * prog), 4))

        self.text(f"SCORE {self.score}", 30, T["text"], (16 * s, 8 * s))
        self.text(f"BEST {max(self.best_score(), self.score)}   LV {self.level}", 17, T["dim"],
                  (16 * s, 8 * s + 40 * s))

        cx = w // 2
        if self.time_attack:
            t = max(0.0, self.time_left)
            col = T["danger"] if t < 10 else T["text"]
            self.text(f"{int(t) // 60}:{int(t) % 60:02d}", 34, col, (cx, 6 * s), "midtop")
        else:
            self.text(self.mode_name.upper(), 26, T["text"], (cx, 10 * s), "midtop")
        self.text(f"LENGTH {len(self.snake.body)}", 17, T["dim"], (cx, 8 * s + 40 * s), "midtop")

        self.text(f"{self.diff['name'].upper()}  SPD {self.fps}", 17, T["dim"],
                  (w - 16 * s, 10 * s), "topright")
        self.text("WRAP" if self.wrap else "WALLS", 17, T["safe"] if self.wrap else T["danger"],
                  (w - 16 * s, 10 * s + 24 * s), "topright")
        if self.state == "paused":
            self.text("PAUSED", 20, T["accent"], (w - 16 * s, 10 * s + 48 * s), "topright")

    def draw_chips(self):
        T, s = self.theme, self.ui_scale
        chips = []
        if self.shield:
            chips.append(("SHIELD", POWERUPS["shield"]["color"]))
        if self.effects["slow"] > 0:
            chips.append((f"SLOW {self.effects['slow']:.1f}s", POWERUPS["slow"]["color"]))
        if self.effects["double"] > 0:
            chips.append((f"2X {self.effects['double']:.1f}s", POWERUPS["double"]["color"]))
        if self.combo >= 2 and self.combo_timer > 0:
            chips.append((f"COMBO x{self.combo}", T["accent"]))
        x = self.ox + 8 * s
        y = self.oy + self.cell * self.gh - 34 * s
        for label, color in chips:
            surf = self.font(16).render(label, True, (15, 15, 15))
            r = pygame.Rect(0, 0, surf.get_width() + 18 * s, surf.get_height() + 8 * s)
            r.topleft = (int(x), int(y))
            box = pygame.Surface(r.size, pygame.SRCALPHA)
            pygame.draw.rect(box, (*color, 225), box.get_rect(), border_radius=8)
            self.screen.blit(box, r.topleft)
            self.screen.blit(surf, surf.get_rect(center=r.center))
            x += r.width + 8 * s

    def draw_countdown(self):
        T, s = self.theme, self.ui_scale
        cx = self.ox + self.cell * self.gw // 2
        cy = self.oy + self.cell * self.gh // 2
        n = math.ceil(self.countdown)
        frac = self.countdown - (n - 1)
        self.text("GET READY", 30, T["accent"], (cx, cy - 90 * s), "center", shadow=True)
        self.text(str(n), int(120 * (0.85 + 0.15 * frac)), T["text"], (cx, cy), "center", shadow=True)
        self.text("Steer with Arrows / WASD", 18, T["dim"], (cx, cy + 90 * s), "center", shadow=True)

    # ------------------------------------------------------------------
    # Drawing - overlays and screens
    # ------------------------------------------------------------------
    def draw_pause(self):
        T, s = self.theme, self.ui_scale
        w, h = self.screen.get_size()
        self.dim(150)
        rect = pygame.Rect(0, 0, int(460 * s), int(380 * s))
        rect.center = (w // 2, h // 2)
        self.draw_panel(rect)
        self.text("PAUSED", 54, T["accent"], (rect.centerx, rect.top + 20 * s), "midtop", shadow=True)
        self.draw_menu(self.menus["pause"], rect.centerx, rect.top + int(110 * s), int(56 * s), int(360 * s))

    def draw_name_entry(self):
        T, s = self.theme, self.ui_scale
        w, h = self.screen.get_size()
        self.dim(170)
        rect = pygame.Rect(0, 0, int(580 * s), int(380 * s))
        rect.center = (w // 2, h // 2)
        self.draw_panel(rect)
        self.text("NEW HIGH SCORE!", 44, T["accent"], (rect.centerx, rect.top + 26 * s), "midtop", shadow=True)
        self.text(f"Score: {self.score}", 30, T["text"], (rect.centerx, rect.top + 96 * s), "midtop")
        self.text("Enter your name", 18, T["dim"], (rect.centerx, rect.top + 160 * s), "midtop")
        box = pygame.Rect(0, 0, int(360 * s), int(60 * s))
        box.center = (rect.centerx, rect.top + int(235 * s))
        pygame.draw.rect(self.screen, T["bg1"], box, border_radius=10)
        pygame.draw.rect(self.screen, T["accent"], box, width=2, border_radius=10)
        shown = self.name_buffer
        cursor = "_" if int(self.ui_time * 2) % 2 == 0 and not self.name_fresh else ""
        txt_rect = self.text(shown + cursor, 32, T["text"], box.center, "center")
        if self.name_fresh and shown:
            pygame.draw.rect(self.screen, T["accent"], txt_rect.inflate(10, 6), width=2, border_radius=4)
        self.text("ENTER to save    BACKSPACE to edit", 16, T["dim"],
                  (rect.centerx, rect.bottom - 40 * s), "midtop")

    def draw_game_over(self):
        T, s = self.theme, self.ui_scale
        w, h = self.screen.get_size()
        self.dim(170)
        rect = pygame.Rect(0, 0, int(560 * s), int(470 * s))
        rect.center = (w // 2, h // 2)
        self.draw_panel(rect)
        titles = {
            "wall": ("CRASHED!", "You hit the wall"),
            "self": ("CRASHED!", "You bit your own tail"),
            "obstacle": ("CRASHED!", "You hit an obstacle"),
            "time": ("TIME'S UP!", "The clock ran out"),
            "win": ("BOARD CLEARED!", "A perfect game"),
        }
        title, sub = titles.get(self.end_reason, ("GAME OVER", ""))
        good = self.end_reason in ("time", "win")
        cx = rect.centerx
        self.text(title, 48, T["safe"] if good else T["danger"], (cx, rect.top + 20 * s), "midtop", shadow=True)
        self.text(sub, 18, T["dim"], (cx, rect.top + 78 * s), "midtop")
        self.text(f"SCORE {self.score}", 40, T["text"], (cx, rect.top + 108 * s), "midtop")
        extra = f"Level {self.level}   Length {len(self.snake.body)}   Food {self.eaten}"
        self.text(extra, 18, T["dim"], (cx, rect.top + 160 * s), "midtop")
        if self.new_best and int(self.ui_time * 3) % 2 == 0:
            self.text("NEW BEST SCORE!", 22, T["accent"], (cx, rect.top + 190 * s), "midtop")
        elif self.last_entry is not None:
            rank = next((i + 1 for i, e in enumerate(self.scores) if e is self.last_entry), None)
            if rank:
                self.text(f"Leaderboard rank #{rank}", 20, T["accent"], (cx, rect.top + 190 * s), "midtop")
        self.draw_menu(self.menus["game_over"], cx, rect.top + int(235 * s), int(60 * s), int(380 * s))

    def draw_main(self):
        T, s = self.theme, self.ui_scale
        w, h = self.screen.get_size()
        self.draw_backdrop()
        self.text("SNAKE", 88, T["accent"], (w // 2, int(h * 0.04)), "midtop", shadow=True)
        self.text(f"PRO EDITION  v{VERSION}", 17, T["dim"], (w // 2, int(h * 0.04 + 96 * s)), "midtop")
        menu = self.menus["main"]
        top = int(h * 0.26)
        step = min(int(50 * s), int((h * 0.84 - top) / len(menu.items)))
        self.draw_menu(menu, w // 2, top, step, int(440 * s))
        self.text(MODES[self.settings["mode"]][1], 17, T["dim"], (w // 2, int(h * 0.865)), "midtop")
        self.text(f"Best score: {self.best_score()}", 20, T["text"], (w // 2, int(h * 0.905)), "midtop")
        self.text("Arrows/WASD + Enter, or use the mouse     F fullscreen     M mute", 15, T["dim"],
                  (w // 2, int(h * 0.95)), "midtop")

    def draw_settings(self):
        T, s = self.theme, self.ui_scale
        w, h = self.screen.get_size()
        self.draw_backdrop()
        rect = pygame.Rect(0, 0, int(640 * s), int(h * 0.82))
        rect.midtop = (w // 2, int(h * 0.05))
        self.draw_panel(rect)
        self.text("SETTINGS", 46, T["accent"], (rect.centerx, rect.top + 14 * s), "midtop", shadow=True)
        menu = self.menus["settings"]
        top = rect.top + int(76 * s)
        step = min(int(52 * s), int((rect.bottom - 14 * s - top) / len(menu.items)))
        self.draw_menu(menu, rect.centerx, top, step, rect.width - int(50 * s), size=24)
        self.text("LEFT / RIGHT to change   -   Grid size applies to the next game", 15, T["dim"],
                  (w // 2, rect.bottom + 12 * s), "midtop")

    def _sub_panel(self, title, title_size=46):
        T, s = self.theme, self.ui_scale
        w, h = self.screen.get_size()
        self.draw_backdrop()
        rect = pygame.Rect(0, 0, min(w - 30, int(900 * s)), int(h * 0.88))
        rect.midtop = (w // 2, int(h * 0.04))
        self.draw_panel(rect)
        self.text(title, title_size, T["accent"], (rect.centerx, rect.top + 14 * s), "midtop", shadow=True)
        self.text("Press any key or click to go back", 15, T["dim"],
                  (rect.centerx, rect.bottom - 26 * s), "midtop")
        return rect

    def draw_leaderboard(self):
        T, s = self.theme, self.ui_scale
        rect = self._sub_panel("LEADERBOARD")
        pw = rect.width
        cols = [("#", 0.04, "topleft"), ("NAME", 0.10, "topleft"), ("SCORE", 0.47, "topright"),
                ("MODE", 0.52, "topleft"), ("DIFF", 0.70, "topleft"), ("DATE", 0.84, "topleft")]
        y = rect.top + 84 * s
        for label, fx, anchor in cols:
            self.text(label, 15, T["dim"], (rect.left + fx * pw, y), anchor)
        row_h = (rect.height - 150 * s) / LEADERBOARD_SIZE
        y += 26 * s
        if not self.scores:
            self.text("No scores yet - go set one!", 24, T["text"], (rect.centerx, rect.centery), "center")
            return
        for i, e in enumerate(self.scores[:LEADERBOARD_SIZE]):
            ry = y + i * row_h
            if e is self.last_entry:
                hl = pygame.Surface((int(pw - 24 * s), int(row_h * 0.9)), pygame.SRCALPHA)
                pygame.draw.rect(hl, (*T["accent"], 55), hl.get_rect(), border_radius=8)
                self.screen.blit(hl, (rect.left + 12 * s, ry - 2 * s))
            color = T["accent"] if i == 0 else T["text"]
            vals = [str(i + 1), str(e.get("name", "?")), str(e["score"]), str(e.get("mode", "")),
                    str(e.get("difficulty", "")), str(e.get("date", ""))]
            for (label, fx, anchor), v in zip(cols, vals):
                self.text(v, 21, color if label in ("#", "NAME", "SCORE") else T["dim"],
                          (rect.left + fx * pw, ry), anchor)

    def draw_stats(self):
        T, s = self.theme, self.ui_scale
        rect = self._sub_panel("STATS & ACHIEVEMENTS", 40)
        pw, st = rect.width, self.stats
        lx = rect.left + 0.05 * pw
        y = rect.top + 84 * s
        line = 34 * s
        self.text("LIFETIME STATS", 20, T["accent"], (lx, y))
        y += line * 1.1
        rows = [("Games played", st["games"]), ("Food eaten", st["food"]),
                ("Total score", st["total_score"]), ("Best level", st["best_level"]),
                ("Longest snake", st["best_length"]), ("Best combo", f"x{st['best_combo']}"),
                ("Power-ups used", st["powerups"]), ("Time played", fmt_time(st["playtime"]))]
        for label, val in rows:
            self.text(label, 19, T["dim"], (lx, y))
            self.text(val, 19, T["text"], (lx + 0.40 * pw, y), "topright")
            y += line
        rx = rect.left + 0.52 * pw
        y = rect.top + 84 * s
        unlocked = st["achievements"]
        self.text(f"ACHIEVEMENTS  {len(unlocked)}/{len(ACHIEVEMENTS)}", 20, T["accent"], (rx, y))
        y += line * 1.1
        for aid, name, desc, _cond in ACHIEVEMENTS:
            got = aid in unlocked
            self.text(("[x] " if got else "[ ] ") + name, 19, T["safe"] if got else T["dim"], (rx, y))
            self.text(desc, 14, T["dim"], (rx + 30 * s, y + 21 * s), bold=False)
            y += 44 * s

    def draw_help(self):
        T, s = self.theme, self.ui_scale
        rect = self._sub_panel("HOW TO PLAY")
        x = rect.left + 44 * s
        y = rect.top + 84 * s
        lh = 27 * s
        self.text("CONTROLS", 20, T["accent"], (x, y))
        y += lh * 1.1
        for k, v in [("Arrows / WASD", "Steer the snake, navigate menus"),
                     ("P / ESC", "Pause (the game also pauses if you switch window)"),
                     ("F / F11", "Toggle fullscreen"),
                     ("M", "Mute / unmute"),
                     ("F12", "Save a screenshot"),
                     ("Gamepad", "D-pad or stick to steer, A select, Start pause")]:
            self.text(k, 17, T["text"], (x, y))
            self.text(v, 17, T["dim"], (x + 210 * s, y))
            y += lh
        y += lh * 0.5
        self.text("POWER-UPS  (they vanish after 10 seconds)", 20, T["accent"], (x, y))
        y += lh * 1.2
        for info in POWERUPS.values():
            box = pygame.Rect(int(x), int(y - 2 * s), int(24 * s), int(24 * s))
            pygame.draw.rect(self.screen, info["color"], box, border_radius=5)
            self.text(info["letter"], 17, (20, 20, 20), box.center, "center")
            self.text(info["name"], 17, T["text"], (x + 38 * s, y))
            self.text(info["desc"], 17, T["dim"], (x + 210 * s, y))
            y += lh * 1.1
        y += lh * 0.4
        self.text("TIPS", 20, T["accent"], (x, y))
        y += lh * 1.1
        for tip in ["Eat quickly in a row to build a combo (up to x5).",
                    "Golden food is worth 3x but disappears fast.",
                    "Time Attack: every food adds 3 seconds to the clock.",
                    "A Shield saves you once: it smashes obstacles and wraps walls."]:
            self.text("- " + tip, 16, T["dim"], (x, y))
            y += lh * 0.9

    def draw(self):
        st = self.state
        if st == "main":
            self.draw_main()
        elif st == "settings":
            self.draw_settings()
        elif st == "leaderboard":
            self.draw_leaderboard()
        elif st == "stats":
            self.draw_stats()
        elif st == "help":
            self.draw_help()
        else:
            self.draw_game()
            if st == "paused":
                self.draw_pause()
            elif st == "name_entry":
                self.draw_name_entry()
            elif st == "game_over":
                self.draw_game_over()
        self.draw_toasts()
        pygame.display.flip()

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def frame(self, dt):
        self.sync_display()
        self.handle_events()
        self.update(dt)
        self.draw()

    def run(self):
        while True:
            dt = min(self.clock.tick(RENDER_FPS) / 1000.0, 0.1)
            self.frame(dt)

    def quit(self):
        try:
            self.save_all()
        finally:
            pygame.quit()
            sys.exit()


def main():
    if sys.platform.startswith("win"):
        try:    # crisp rendering on high-DPI Windows displays
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
    try:
        Game().run()
    except SystemExit:
        raise
    except Exception:
        try:
            with open(os.path.join(get_data_dir(), "crash.log"), "a", encoding="utf-8") as f:
                f.write(f"\n--- {datetime.datetime.now().isoformat()} ---\n")
                f.write(traceback.format_exc())
        except OSError:
            pass
        raise


if __name__ == "__main__":
    main()
