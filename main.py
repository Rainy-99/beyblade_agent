#!/usr/bin/env python3
# main.py — 陀螺特工 Beyblade Agent
import pygame
import sys
import os
import math
import random

os.environ.setdefault('SDL_VIDEO_CENTERED', '1')

from colors import *
from constants import *
from player import Player
from particles import ParticleSystem, Afterimage, DamageNumberSystem
from spin_detector import SpinDetector
from hud import HUD
from scenes import draw_scene
from level_manager import LevelManager
from screens import (RewardScreen, TitleScreen, LevelIntroScreen,
                     GameOverScreen, FinalScreen, ClearAnim, PauseScreen, REWARDS)
from audio_manager import AudioManager


def load_fonts():
    """Load CJK-capable fonts across Windows / macOS / Linux."""

    # ── 1. Explicit file paths ─────────────────────────────────────────
    win_dir = os.environ.get('WINDIR', 'C:\\Windows')
    explicit_candidates = [
        # Windows built-in CJK fonts
        os.path.join(win_dir, 'Fonts', 'msjh.ttc'),
        os.path.join(win_dir, 'Fonts', 'msjhbd.ttc'),
        os.path.join(win_dir, 'Fonts', 'msyh.ttc'),
        os.path.join(win_dir, 'Fonts', 'msyhbd.ttc'),
        os.path.join(win_dir, 'Fonts', 'simsun.ttc'),
        os.path.join(win_dir, 'Fonts', 'mingliu.ttc'),
        # macOS
        '/System/Library/Fonts/PingFang.ttc',
        '/System/Library/Fonts/Hiragino Sans GB.ttc',
        # Linux
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/noto-cjk/NotoSansCJKtc-Regular.otf',
    ]

    def find_file_font(candidates):
        for f in candidates:
            if os.path.exists(f):
                return f
        return None

    # ── 2. SysFont names that include CJK glyphs ──────────────────────
    cjk_sysfonts = [
        'microsoftyahei', 'microsoftjhenghei', 'msjh', 'msyh',
        'pingfang', 'notosanscjk', 'simhei', 'simsun',
        'yugothic', 'meiryoui',
    ]

    def find_sys_font():
        available = [f.lower() for f in pygame.font.get_fonts()]
        for name in cjk_sysfonts:
            if name in available:
                return name
        return None

    file_font = find_file_font(explicit_candidates)
    sys_name  = find_sys_font() if not file_font else None

    def mf(size, bold=False):
        if file_font:
            try:
                return pygame.font.Font(file_font, size)
            except Exception:
                pass
        if sys_name:
            try:
                return pygame.font.SysFont(sys_name, size, bold=bold)
            except Exception:
                pass
        try:
            return pygame.font.SysFont('arial', size, bold=bold)
        except Exception:
            return pygame.font.Font(None, size)

    fonts = {
        'big':   mf(48, bold=True),
        'title': mf(32, bold=True),
        'card':  mf(20),
        'card_bold': mf(20, bold=True),    # 新增
        'sm':    mf(14),
        'sm_bold': mf(14, bold=True),      # 新增
        'damage': mf(24, bold=True),
        'damage_small': mf(20, bold=True),
    }

    if file_font:
        print(f"[Font] Using file: {os.path.basename(file_font)}")
    elif sys_name:
        print(f"[Font] Using SysFont: {sys_name}")
    else:
        print("[Font] Fallback: no CJK font found, Chinese text may not render")

    return fonts


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("陀螺特工 Beyblade Agent")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()

        self.fonts = load_fonts()
        self.state = STATE_TITLE
        self.current_level = 1
        self.player = Player()

        self.title_screen = TitleScreen(self.fonts)
        self.level_intro = None
        self.level_mgr = None
        self.reward_screen = None
        self.gameover_screen = None
        self.final_screen = None
        self.clear_anim = None
        self.pause_screen = None

        self.particles = ParticleSystem()
        self.afterimage = Afterimage()
        self.spin_detector = SpinDetector(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        self.hud = HUD(self.fonts)
        self.damage_numbers = DamageNumberSystem()

        # ── Auto-spin (測試用) ─────────────────────────────────────────
        self.auto_spin = False
        # 按鈕位置：右上角，fps 文字左側
        self._autospin_btn = pygame.Rect(SCREEN_WIDTH - 210, 2, 148, 22)

        # ── Audio ──────────────────────────────────────────────────────
        self.audio = AudioManager()
        self.audio.play_title_music()

    # ── Level control ─────────────────────────────────────────────────

    def start_level(self, level):
        self.current_level = level
        self.level_intro = LevelIntroScreen(level, self.fonts)
        self.state = STATE_LEVEL_INTRO
        # Play level intro sting; BG music starts when gameplay begins
        self.audio.stop_music()
        self.audio.play_level_intro()

    def enter_play(self):
        self.level_mgr = LevelManager(self.current_level, self.player, audio=self.audio)
        self.particles = ParticleSystem()
        self.state = STATE_PLAYING
        self.damage_numbers = DamageNumberSystem()
        self.audio.play_level_music(self.current_level)
        # v0.9 (1-A): arm first-hit demo for this level
        self.player._intro_hit_pending = True

    def level_clear(self):
        self.clear_anim = ClearAnim(self.fonts)
        self.particles.emit_clear(self.player.x, self.player.y)
        self.state = STATE_CLEAR_ANIM
        self.audio.fadeout_music(600)
        self.audio.play_level_clear()

    def show_reward(self):
        self.reward_screen = RewardScreen(self.current_level, self.fonts)
        self.state = STATE_REWARD

    def apply_reward(self, choice_id):
        p = self.player
        
        # 若 choice_id 為 None（玩家沒有選擇或超時），選擇第一個獎勵
        if choice_id is None:
            reward_list = REWARDS[self.current_level]
            if reward_list:
                choice_id = reward_list[0]['id']
        
        if choice_id in ('wood', 'steel', 'titan'):
            p.material = choice_id
        elif choice_id in ('scythe', 'staff', 'hammer'):
            p.weapon = choice_id
            if choice_id == 'scythe':
                p.weapon_attack_bonus = 5; p.weapon_reach = 16; p.weapon_count = 2
            elif choice_id == 'staff':
                p.weapon_attack_bonus = 2; p.weapon_reach = 28; p.weapon_count = 4
            elif choice_id == 'hammer':
                p.weapon_attack_bonus = 8; p.weapon_reach = 36; p.weapon_count = 1
                p.hammer_penalty = True
        elif choice_id in ('axis', 'gear_ring', 'dash_tape'):
            p.accessory = choice_id
            if choice_id == 'axis':
                p.rpm_max = int(RPM_MAX * 1.10)
        elif choice_id in ('chaos', 'shield', 'crown'):
            p.core = choice_id
        elif choice_id in ('recoil_dampener', 'shockwave', 'splinter_echo'):
            p.drive = choice_id

    def game_over(self):
        self.gameover_screen = GameOverScreen(self.fonts)
        self.state = STATE_GAMEOVER
        self.audio.fadeout_music(400)
        self.audio.play_game_over()

    def restart(self):
        self.player.rpm = RPM_INIT
        self.player.x = PLAY_LEFT + PLAY_W // 2
        self.player.y = PLAY_TOP + PLAY_H // 2
        self.player.vx = self.player.vy = 0
        self.player.stun_timer = 0
        self.player.invincible_timer = 0
        self.auto_spin = False          # 重新開始時重置自動旋轉
        self.audio.play_press()
        # 重新開始關卡，顯示level info介紹屏幕
        self.start_level(self.current_level)

    def go_to_menu(self):
        self.player = Player()
        self.current_level = 1
        self.title_screen = TitleScreen(self.fonts)
        self.state = STATE_TITLE
        self.auto_spin = False          # 回主選單時重置自動旋轉
        self.audio.play_press()
        self.audio.play_title_music()

    def next_level(self):
        nl = self.current_level + 1
        if nl > 5:
            self.final_screen = FinalScreen(self.player, self.fonts)
            self.state = STATE_FINAL
            self.audio.stop_music()
            self.audio.play_final_screen()
        else:
            self.player.rpm = min(self.player.rpm_max, self.player.rpm + 150)
            self.start_level(nl)

    def _draw_autospin_btn(self, surface):
        """右上角自動旋轉測試按鈕。開啟後持續亮起，重新開始才重置。"""
        btn = self._autospin_btn
        font = self.fonts['sm']

        if self.auto_spin:
            # 開啟狀態：綠底 + 白字 + 綠色外框光暈
            bg_color     = (30,  90,  30)
            border_color = SUCCESS_GREEN
            text_color   = SUCCESS_GREEN
            label        = "● AUTO-SPIN  ON"
        else:
            # 關閉狀態：暗底 + 灰字，提示可點擊
            bg_color     = (20, 24, 30)
            border_color = STEEL_MID
            text_color   = STEEL_LIGHT
            label        = "○ AUTO-SPIN OFF"

        # 背景
        pygame.draw.rect(surface, bg_color, btn, border_radius=4)
        # 外框
        pygame.draw.rect(surface, border_color, btn, 1, border_radius=4)

        # 開啟時加一圈外發光
        if self.auto_spin:
            glow = pygame.Surface((btn.width + 6, btn.height + 6), pygame.SRCALPHA)
            pygame.draw.rect(glow, (*SUCCESS_GREEN, 50),
                             (0, 0, btn.width + 6, btn.height + 6), border_radius=5)
            surface.blit(glow, (btn.x - 3, btn.y - 3))
            # 重新畫外框（避免被光暈蓋掉）
            pygame.draw.rect(surface, border_color, btn, 1, border_radius=4)

        # 文字置中
        txt = font.render(label, True, text_color)
        tx  = btn.x + (btn.width  - txt.get_width())  // 2
        ty  = btn.y + (btn.height - txt.get_height()) // 2
        surface.blit(txt, (tx, ty))

    # ── Main loop ─────────────────────────────────────────────────────

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)
            self._handle_events()
            self._update(dt)
            self._draw()
            pygame.display.flip()

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            # ── 自動旋轉按鈕（任何畫面皆可點擊，但只在 PLAYING 狀態有效）
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self._autospin_btn.collidepoint(event.pos):
                    self.auto_spin = not self.auto_spin
                    continue   # 不讓點擊事件繼續往下處理

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if self.state == STATE_PLAYING:
                    self.pause_screen = PauseScreen(self.fonts, self.player, self.current_level)
                    self.state = STATE_PAUSED
                    pygame.mixer.music.pause()
                    return
                elif self.state == STATE_PAUSED:
                    # ESC toggles pause (resume)
                    self.pause_screen.choice = 'resume'
                    self.pause_screen.done = True
                    return

            if self.state == STATE_TITLE:
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    self.audio.play_press()
                    self.start_level(1)

            elif self.state == STATE_LEVEL_INTRO:
                # 按任意鍵跳過關卡介紹動畫
                if event.type == pygame.KEYDOWN:
                    if self.level_intro and not self.level_intro.done:
                        self.level_intro.done = True

            elif self.state == STATE_REWARD:
                prev_done = self.reward_screen.done
                prev_selected = self.reward_screen.selected
                self.reward_screen.handle_event(event)
                # Play get_reward sound the moment a card is selected
                if self.reward_screen.selected >= 0 and prev_selected < 0:
                    self.audio.play_get_reward()

            elif self.state == STATE_PAUSED:
                prev_done = self.pause_screen.done
                self.pause_screen.handle_event(event)

            elif self.state == STATE_GAMEOVER:
                prev_done = self.gameover_screen.done
                self.gameover_screen.handle_event(event)
                # Press sound fires when the player picks an option
                if self.gameover_screen.done and not prev_done:
                    self.audio.play_press()

            elif self.state == STATE_FINAL:
                prev_done = self.final_screen.done
                self.final_screen.handle_event(event)
                if self.final_screen.done and not prev_done:
                    self.audio.play_press()

    def _update(self, dt):
        # Update audio system (for delayed SFX playback)
        self.audio.update(dt)
        
        if self.state == STATE_TITLE:
            self.title_screen.update(dt)

        elif self.state == STATE_LEVEL_INTRO:
            self.level_intro.update(dt)
            if self.level_intro.done:
                self.enter_play()

        elif self.state == STATE_PLAYING:
            keys = pygame.key.get_pressed()
            mx, my = pygame.mouse.get_pos()

            spins = self.spin_detector.update(dt, mx, my)
            if spins > 0:
                gain = self.player.rpm_spin_gain() * spins
                self.player.add_rpm(gain)

            # ── 自動旋轉：每幀模擬一個完整旋轉的 RPM 增益 ──────────
            if self.auto_spin:
                # rpm_spin_gain() 回傳每圈的增益，以 60fps 換算持續每幀增益
                # 等效每秒約補充 3 圈的 RPM（測試用，讓轉速維持在接近滿格）
                auto_gain = self.player.rpm_spin_gain() * 3.0 * dt
                self.player.add_rpm(auto_gain)

            self.player.update(dt, keys, self.particles)

            # v0.10: enforce bamboo walls immediately after player moves
            if self.level_mgr and self.current_level == 2:
                self.level_mgr._enforce_bamboo_walls()

            if self.player.is_dashing:
                self.afterimage.add(self.player.render_snapshot(),
                                    self.player.x, self.player.y)

            self.afterimage.update(dt)
            self.particles.update(dt)
            self.damage_numbers.update(dt)

            if self.player.rpm <= 0:
                self.game_over()
                return

            if self.level_mgr:
                self.level_mgr.update(dt, self.particles, self.damage_numbers)
                if self.level_mgr.cleared:
                    self.level_clear()

            # v0.12: safety clamp AFTER level update (bounce logic runs inside update)
            if self.level_mgr and self.current_level == 4:
                self.level_mgr._clamp_player_to_ring()

        elif self.state == STATE_PAUSED:
            self.pause_screen.update(dt)
            if self.pause_screen.done:
                if self.pause_screen.choice == 'resume':
                    self.audio.play_press()
                    pygame.mixer.music.unpause()
                    self.state = STATE_PLAYING
                elif self.pause_screen.choice == 'restart':
                    self.restart()
                elif self.pause_screen.choice == 'menu':
                    self.go_to_menu()

        elif self.state == STATE_CLEAR_ANIM:
            self.clear_anim.update(dt)
            if self.clear_anim.done:
                self.show_reward()

        elif self.state == STATE_REWARD:
            self.reward_screen.update(dt)
            if self.reward_screen.done:
                self.apply_reward(self.reward_screen.choice)
                self.next_level()

        elif self.state == STATE_GAMEOVER:
            self.gameover_screen.update(dt)
            if self.gameover_screen.done:
                if self.gameover_screen.choice == 'retry':
                    self.restart()
                else:
                    self.go_to_menu()

        elif self.state == STATE_FINAL:
            self.final_screen.update(dt)
            if self.final_screen.done:
                self.go_to_menu()

    def _draw(self):
        self.screen.fill(VOID_BLACK)

        if self.state == STATE_TITLE:
            self.title_screen.draw(self.screen)

        elif self.state == STATE_LEVEL_INTRO:
            self.level_intro.draw(self.screen)

        elif self.state in (STATE_PLAYING, STATE_CLEAR_ANIM):
            shrink = 0
            boss = self.level_mgr.get_boss() if self.level_mgr else None
            if boss:
                shrink = boss.get_arena_shrink()
            draw_scene(self.screen, self.current_level, shrink)

            self.afterimage.draw(self.screen)

            if self.level_mgr:
                self.level_mgr.draw(self.screen)

            self.particles.draw(self.screen)
            self.player.draw(self.screen)
            font_sm = self.fonts['damage_small'] 
            font_md = self.fonts['damage']
            self.damage_numbers.draw(self.screen, font_sm, font_md)

            exp = self.level_mgr.exp if self.level_mgr else 0
            # v0.9: build extra dict for HUD
            _extra = {}
            if self.level_mgr:
                lm = self.level_mgr
                # 7-A: L1 tutorial
                if self.current_level == 1:
                    _extra['tutorial_msg']   = getattr(lm, '_tutorial_msg', '')
                    _extra['tutorial_timer'] = getattr(lm, '_tutorial_timer', 0)
                # 3-E: boss skill name
                _extra['boss_skill']       = getattr(lm, '_boss_skill_label', '')
                _extra['boss_skill_timer'] = getattr(lm, '_boss_skill_timer', 0)

            self.hud.draw(self.screen, self.player, exp, EXP_TO_CLEAR,
                          self.current_level,
                          self.spin_detector.compass_sector,
                          SCREEN_WIDTH, SCREEN_HEIGHT, extra=_extra)

            if boss and boss.alive:
                self.hud.draw_boss_bar(self.screen, boss, SCREEN_WIDTH)

            if self.state == STATE_CLEAR_ANIM:
                self.clear_anim.draw(self.screen)

        elif self.state == STATE_REWARD:
            draw_scene(self.screen, self.current_level)
            self.reward_screen.draw(self.screen)

        elif self.state == STATE_GAMEOVER:
            if self.level_mgr:
                draw_scene(self.screen, self.current_level)
                self.level_mgr.draw(self.screen)
                self.player.draw(self.screen)
            self.gameover_screen.draw(self.screen)

        elif self.state == STATE_PAUSED:
            # Draw the game scene in the background
            shrink = 0
            boss = self.level_mgr.get_boss() if self.level_mgr else None
            if boss:
                shrink = boss.get_arena_shrink()
            draw_scene(self.screen, self.current_level, shrink)

            self.afterimage.draw(self.screen)

            if self.level_mgr:
                self.level_mgr.draw(self.screen)

            self.particles.draw(self.screen)
            self.player.draw(self.screen)
            font_sm = self.fonts['damage_small'] 
            font_md = self.fonts['damage']
            self.damage_numbers.draw(self.screen, font_sm, font_md)

            exp = self.level_mgr.exp if self.level_mgr else 0
            self.hud.draw(self.screen, self.player, exp, EXP_TO_CLEAR,
                          self.current_level,
                          self.spin_detector.compass_sector,
                          SCREEN_WIDTH, SCREEN_HEIGHT)

            if boss and boss.alive:
                self.hud.draw_boss_bar(self.screen, boss, SCREEN_WIDTH)

            # Draw the pause screen overlay
            self.pause_screen.draw(self.screen)

        elif self.state == STATE_FINAL:
            self.final_screen.draw(self.screen)

        fps = self.clock.get_fps()
        fps_surf = self.fonts['sm'].render(f"{fps:.0f}fps", True, STEEL_MID)
        self.screen.blit(fps_surf, (SCREEN_WIDTH - 55, 4))

        # ── 自動旋轉按鈕（右上角，fps 左側） ─────────────────────────
        self._draw_autospin_btn(self.screen)


if __name__ == '__main__':
    game = Game()
    game.run()
