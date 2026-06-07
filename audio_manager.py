# audio_manager.py — 陀螺特工 Beyblade Agent
# Centralised sound / music controller.
# All volume math is in linear amplitude (0.0‥1.0).
# "-20 ~ -30 dB" ≈ amplitude 0.10 ~ 0.03.  We use 0.07 (≈ -23 dB) for BG music.

import pygame
import os
from constants import MATERIAL_STEEL, MATERIAL_WOOD, MATERIAL_PLASTIC

# ── dB helpers ────────────────────────────────────────────────────────────────

def db_to_linear(db: float) -> float:
    """Convert dB to linear amplitude.  0 dB → 1.0,  -23 dB → ~0.07."""
    import math
    return 10 ** (db / 20)

# Volume constants
BG_MUSIC_VOLUME = {
    "title": 0.5081,
    1:       0.2234,
    2:       0.9264,
    3:       0.3540,
    4:       0.3983,
    5:       0.6551,
}   # ≈ 0.316  louder BGM
SFX_VOLUME        = 0.85                 # general SFX (one-shot)
PRESS_VOLUME      = 0.80                 # button press click
INTRO_SFX_VOLUME  = 0.75                 # level intro sting


class AudioManager:
    """
    Singleton-style audio manager.
    Usage:
        audio = AudioManager()
        audio.play_title_music()
        audio.play_sfx("press")
        audio.stop_music()
    """

    # Map logical names → file names inside the audio/ folder
    _SFX_FILES = {
        "final_screen":      "final_screen_sound.wav",
        "game_over":         "game_over_sound.wav",
        "get_reward":        "get_reward_sound.wav",
        "level_clear":       "level_clear _sound.wav",   # note the space in original filename
        "press":             "Press_to_start_sound.wav",
        "level_intro":       "shorten_level_intro_sound.wav",
        "hit":               "clash_trimmed.wav",   # 不鏽鋼/鈦合金
        "hit_wood":          "wood.wav",             # v0.8: 木頭材質
        "hit_plastic":       "plastic.wav",           # v0.8: L1 塑膠
    }

    _BG_FILES = {
        "title":    "State_title_bg_music.wav",
        1:          "level_one_bg_music.wav",
        2:          "level_two_bg_music.wav",
        3:          "level_three_bg_music.wav",
        4:        "level_four_bg_music.wav",
        5:          "level_five_bg_music.wav",
    }

    def __init__(self, audio_dir: str = None):
        # Locate the audio/ folder relative to this file
        if audio_dir is None:
            audio_dir = os.path.join(os.path.dirname(__file__), "audio")
        self._audio_dir = audio_dir

        # Initialise mixer if not already done
        if not pygame.get_init():
            pygame.init()
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            except Exception as e:
                print(f"[Audio] mixer init failed: {e}")
                self._ok = False
                return
        self._ok = True

        # Pre-load all SFX into Sound objects
        self._sfx: dict[str, pygame.mixer.Sound | None] = {}
        for key, fname in self._SFX_FILES.items():
            path = os.path.join(self._audio_dir, fname)
            if os.path.exists(path):
                try:
                    snd = pygame.mixer.Sound(path)
                    snd.set_volume(SFX_VOLUME)
                    self._sfx[key] = snd
                except Exception as e:
                    print(f"[Audio] failed to load SFX '{key}': {e}")
                    self._sfx[key] = None
            else:
                print(f"[Audio] SFX file not found: {path}")
                self._sfx[key] = None

        # Override volumes for specific SFX
        if self._sfx.get("press"):
            self._sfx["press"].set_volume(PRESS_VOLUME)
        if self._sfx.get("level_intro"):
            self._sfx["level_intro"].set_volume(INTRO_SFX_VOLUME)
        # 碰撞音效音量稍低，避免過於刺耳
        if self._sfx.get("hit"):
            self._sfx["hit"].set_volume(0.28)
        if self._sfx.get("hit_wood"):
            self._sfx["hit_wood"].set_volume(0.32)
        if self._sfx.get("hit_plastic"):
            self._sfx["hit_plastic"].set_volume(0.364)

        self._current_bg_key = None   # track what music is playing
        self._hit_cooldown   = 0.0    # v0.5: 碰撞音效冷卻（避免疊加）

        # Delayed SFX queue: list of (time_remaining, key) tuples
        self._delayed_sfx_queue: list[tuple[float, str]] = []

    def update(self, dt: float):
        """
        Call this every frame with delta time to process delayed SFX.
        dt should be in seconds (e.g., 0.016 for 60 FPS).
        """
        if not self._ok:
            return
        if self._hit_cooldown > 0:
            self._hit_cooldown -= dt

        # Update all delayed SFX timers
        new_queue = []
        for remaining_time, key in self._delayed_sfx_queue:
            remaining_time -= dt
            if remaining_time <= 0:
                # Time to play this SFX
                self.play_sfx(key)
            else:
                new_queue.append((remaining_time, key))
        self._delayed_sfx_queue = new_queue

    # ── Public API ────────────────────────────────────────────────────────────

    def play_title_music(self):
        """Loop the title screen background music."""
        self._start_bg("title")

    def play_level_music(self, level: int):
        """Loop the appropriate background music for *level*."""
        # Level 4 is skipped; fall back to level 3 track as a safety net
        key = level if level in self._BG_FILES else 3
        self._start_bg(key)

    def stop_music(self):
        """Immediately stop any playing background music."""
        if self._ok:
            pygame.mixer.music.stop()
            self._current_bg_key = None

    def fadeout_music(self, ms: int = 500):
        """Fade out the current background music over *ms* milliseconds."""
        if self._ok:
            pygame.mixer.music.fadeout(ms)
            self._current_bg_key = None

    def play_sfx(self, key: str, delay_ms: int = 0):
        """
        Play a one-shot sound effect by logical name.
        If delay_ms > 0, the sound will be played after that many milliseconds.
        """
        if not self._ok:
            return
        
        if delay_ms > 0:
            # Add to delayed queue
            delay_seconds = delay_ms / 1000.0
            self._delayed_sfx_queue.append((delay_seconds, key))
        else:
            # Play immediately
            snd = self._sfx.get(key)
            if snd:
                snd.play()
            else:
                print(f"[Audio] SFX not available: '{key}'")

    # Convenience wrappers so callers don't have to remember key names
    def play_press(self):          self.play_sfx("press")
    def play_level_intro(self):    self.play_sfx("level_intro")
    def play_level_clear(self):    self.play_sfx("level_clear", delay_ms=650)
    def play_game_over(self):      self.play_sfx("game_over")
    def play_get_reward(self):     self.play_sfx("get_reward", delay_ms=200)
    def play_final_screen(self):   self.play_sfx("final_screen")

    def play_hit_sfx(self, level=1, material=None):
        """
        播放碰撞音效。根據關卡和材質選擇合適的音效檔案。
        
        Args:
            level: 遊戲關卡 (1-5)
            material: 材質類型 (MATERIAL_STEEL, MATERIAL_WOOD, MATERIAL_PLASTIC 或 None)
                      如果為 None，根據 level 自動選擇：
                      - level=1 → MATERIAL_PLASTIC
                      - level>=2 → MATERIAL_STEEL
        
        Returns:
            True 如果成功播放，False 如果在冷卻期內
        
        Note:
            - 冷卻時間 0.18s，防止多個碰撞聲音疊加
            - MATERIAL_WOOD 用於特定敵人（如竹子）
        """
        if not self._ok or self._hit_cooldown > 0:
            return False
        
        # 若未指定材質，根據關卡自動判定
        if material is None:
            material = MATERIAL_PLASTIC if level == 1 else MATERIAL_STEEL
        
        # 選擇對應的音效 key
        if material == MATERIAL_PLASTIC:
            key = "hit_plastic"
        elif material == MATERIAL_WOOD:
            key = "hit_wood"
        else:  # MATERIAL_STEEL 或其他預設為 steel
            key = "hit"
        
        # 播放音效（如果不存在則嘗試 fallback 到 "hit"）
        snd = self._sfx.get(key) or self._sfx.get("hit")
        if snd:
            snd.play()
            self._hit_cooldown = 0.18
            return True
        return False

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _start_bg(self, key):
        if not self._ok:
            return
        if key == self._current_bg_key:
            return

        fname = self._BG_FILES.get(key)
        if not fname:
            return
        path = os.path.join(self._audio_dir, fname)
        if not os.path.exists(path):
            return

        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(BG_MUSIC_VOLUME.get(key, 0.5))
            pygame.mixer.music.play(-1)
            self._current_bg_key = key
        except Exception as e:
            print(f"[Audio] Failed to start BG music '{key}': {e}")
