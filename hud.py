# hud.py
import pygame
import math
import time
from colors import *
from constants import *
import draw_utils as du

class HUD:
    def __init__(self, fonts):
        self.fonts = fonts

    def draw(self, surface, player, exp, exp_max, level, spin_sector, screen_w, screen_h, extra=None):
        # ── RPM Bar ──────────────────────────────────────────────────────
        bar_x, bar_y = 20, 20
        bar_w, bar_h = 260, 18

        # Semi-transparent panel behind RPM / EXP bars
        panel_h = 80 if player.accessory == 'dash_tape' else 62
        _hud_panel = pygame.Surface((bar_w + 104, panel_h), pygame.SRCALPHA)
        pygame.draw.rect(_hud_panel, (0, 0, 0, 150), (0, 0, bar_w + 104, panel_h), border_radius=5)
        pygame.draw.rect(_hud_panel, (60, 70, 90, 100), (0, 0, bar_w + 104, panel_h), 1, border_radius=5)
        surface.blit(_hud_panel, (bar_x - 6, bar_y - 8))

        # Determine bar color
        rpm_ratio = player.rpm / player.rpm_max
        if player.rpm >= 600:
            bar_color = SPIN_BLUE
        elif player.rpm >= 300:
            bar_color = WARN_ORANGE
        else:
            # Flashing
            t = time.time()
            bar_color = DANGER_RED if int(t / 0.3) % 2 == 0 else DANGER_RED_DIM

        du.draw_bar(surface, bar_x, bar_y, bar_w, bar_h,
                    player.rpm, player.rpm_max, bar_color)
        # v0.9 (3-D): orange border when on boost track
        if getattr(player, 'rpm_decay_override', None) is not None:
            pygame.draw.rect(surface, WARN_ORANGE,
                             (bar_x - 2, bar_y - 2, bar_w + 4, bar_h + 4), 2)

        # Label
        font_sm = self.fonts['sm']
        du.draw_text(surface, "speed", font_sm, BONE_WHITE, bar_x + 2, bar_y - 2,
                     shadow_color=(0, 0, 0))
        du.draw_text(surface, f"{int(player.rpm)}/{player.rpm_max}",
                     font_sm, ASH_WHITE, bar_x + bar_w + 4, bar_y + 2,
                     shadow_color=(0, 0, 0))

        # Red vignette when dangerous
        if player.rpm < 300:
            t = time.time()
            alpha = int(30 + 30 * math.sin(t * 10))
            self._draw_vignette(surface, DANGER_RED, alpha, screen_w, screen_h)

        # Hit flash vignette
        if player.hit_flash > 0:
            self._draw_vignette(surface, DANGER_RED, 115, screen_w, screen_h)

        # ── EXP Bar ──────────────────────────────────────────────────────
        exp_x, exp_y = 20, 46
        _EXP_COLS = {1:(140,200,80),2:(80,180,80),3:(160,130,60),
                     4:(60,180,220),5:(180,60,220)}
        exp_col = _EXP_COLS.get(level, ENERGY_GOLD)
        du.draw_bar(surface, exp_x, exp_y, bar_w, 12,
                    exp, exp_max, exp_col, STEEL_DARK, 3)
        du.draw_text(surface, f"{exp}/{exp_max} EXP",
                     font_sm, BONE_WHITE, exp_x + bar_w + 4, exp_y + 1,
                     shadow_color=(0, 0, 0))

        # Dash charge bar (if has dash tape)
        if player.accessory == 'dash_tape':
            ch_x, ch_y = 20, 65
            charge_ratio = min(1.0, player.dash_charge / 3.0)
            dash_color = SPIN_BLUE_GLOW if charge_ratio >= 1.0 else SPIN_BLUE
            du.draw_bar(surface, ch_x, ch_y, 120, 6,
                        charge_ratio, 1.0, dash_color, STEEL_MID, 2)
            du.draw_text(surface, "DASH", font_sm, BONE_WHITE, ch_x + 124, ch_y - 1,
                         shadow_color=(0, 0, 0))
        # Attack dashboard moved to PauseScreen

        # ── v0.9 additions ────────────────────────────────────────────────
        extra = extra or {}

        # 7-A: spin tutorial message (L1)
        if extra.get('tutorial_msg') and extra.get('tutorial_timer', 0) > 0:
            self._draw_tutorial_msg(surface, extra['tutorial_msg'],
                                    extra['tutorial_timer'], screen_w, screen_h)



        # 3-E: boss skill name
        if extra.get('boss_skill') and extra.get('boss_skill_timer', 0) > 0:
            self._draw_boss_skill_label(surface, extra['boss_skill'],
                                        extra['boss_skill_timer'], screen_w, screen_h)

        # # ── Compass (bottom-right) ────────────────────────────────────────
        # cx = screen_w - 60
        # cy = screen_h - 60
        # compass_r = 24
        # pygame.draw.circle(surface, STEEL_DARK, (cx, cy), compass_r + 2)

        # # 4 quadrant sectors
        # sector_colors = [STEEL_MID] * 4
        # if 0 <= spin_sector <= 3:
        #     sector_colors[spin_sector] = SPIN_BLUE

        # for i, sc in enumerate(sector_colors):
        #     start_angle = -math.pi/2 + i * math.pi/2
        #     end_angle = start_angle + math.pi/2
        #     pts = [(cx, cy)]
        #     steps = 12
        #     for s in range(steps + 1):
        #         a = start_angle + (end_angle - start_angle) * s / steps
        #         pts.append((cx + compass_r * math.cos(a),
        #                      cy + compass_r * math.sin(a)))
        #     if len(pts) >= 3:
        #         pygame.draw.polygon(surface, sc, pts)

        # pygame.draw.circle(surface, SPIN_BLUE_GLOW, (cx, cy), 5)
        # pygame.draw.circle(surface, STEEL_LIGHT, (cx, cy), compass_r + 2, 1)

        # ── Stage indicator ───────────────────────────────────────────────
        # du.draw_text(surface, f"STAGE {level}/5", font_sm, BONE_WHITE,
        #              cx - compass_r - 8, cy - 8, align="right")

        # ── 裝備 Pills（左下角）────────────────────────────────────────

    def _draw_attack_dashboard(self, surface, player, screen_w, font_sm):
        """
        攻擊力面板（右上角）
        上半：攻擊、降速、攻擊範圍 = 基礎 + 加成
        下半：其他獲得的能力
        橘色 = 加成，白色 = 基礎，綠色 = 正面加成，紅色 = 負面
        """
        import time
        from constants import RPM_DECAY, RPM_MAX, PLAYER_RADIUS
 
        # ════════════════════════════════════════════════════════════
        #  計算所有數值
        # ════════════════════════════════════════════════════════════
 
        # 攻擊
        base_atk      = player.base_attack
        mat_atk_mul   = {'wood': 0.8, 'titan': 1.35}.get(player.material, 1.0)
        base_after_mat = base_atk * mat_atk_mul
        weapon_bonus  = player.weapon_attack_bonus
        gear_bonus    = 5 if player.accessory == 'gear_ring' else 0
        crown_bonus   = 0.0
        crown_active  = False
        if player.core == 'crown':
            ratio = player.rpm / player.rpm_max
            if ratio < 0.30:
                crown_active = True
                sub = base_after_mat + weapon_bonus
                crown_bonus = round(sub * (0.50 * (1 - ratio / 0.30)), 1)
        total_atk = player.effective_attack() + gear_bonus
 
        # 降速
        base_decay   = RPM_DECAY
        decay_labels = []
        if player.material == 'wood':
            decay_labels.append(("Wood",   round(base_decay * 0.95 - base_decay, 1)))
        elif player.material == 'titan':
            decay_labels.append(("Titan",  round(base_decay * 1.18 - base_decay, 1)))
        if player.hammer_penalty:
            decay_labels.append(("Hammer", round(base_decay * 1.5  - base_decay, 1)))
        total_decay = round(player.effective_decay(), 1)
 
        # 攻擊範圍
        base_reach  = PLAYER_RADIUS
        reach_bonus = player.weapon_reach
        total_reach = player.effective_reach()
 
        # 其他能力
        other_caps = []
        if player.rpm_max != RPM_MAX:
            other_caps.append(("最大轉速", f"{player.rpm_max}  (+{player.rpm_max - RPM_MAX})"))
        if player.accessory == 'dash_tape':
            other_caps.append(("衝刺",     "持續移動觸發"))
        if player.accessory == 'axis':
            other_caps.append(("鋼軸護盾", "受傷 -25%"))
        if player.accessory == 'gear_ring':
            other_caps.append(("齒輪環",   "碰撞 +5 ATK"))
        if player.core == 'shield':
            other_caps.append(("格擋",     "30% 機率格擋"))
        if player.core == 'chaos':
            other_caps.append(("混沌爆炸", "擊殺時範圍傷害"))
        if player.core == 'crown':
            other_caps.append(("低速爆發", "ATK +50%"))
        # v1.6 BUG FIX: drive abilities were missing from attack dashboard
        if player.drive == 'recoil_dampener':
            other_caps.append(("反震阻尼", "被彈開 -45% / 護盾"))
        elif player.drive == 'shockwave':
            other_caps.append(("衝擊波",   "撞擊波及120px +15"))
        elif player.drive == 'splinter_echo':
            other_caps.append(("碎片殘響", "擊殺/碰撞生殘影+5"))
 
        # ════════════════════════════════════════════════════════════
        #  面板高度動態計算
        # ════════════════════════════════════════════════════════════
        pad   = 10
        w     = 215
        ROW_H = 17
        GAP   = 6
 
        def count_rows_atk():
            n = 1   # base
            if player.material in ('wood', 'titan'): n += 1
            if weapon_bonus > 0:  n += 1
            if gear_bonus   > 0:  n += 1
            if crown_active:      n += 1
            n += 1  # total
            return n
 
        def count_rows_decay():
            return 1 + len(decay_labels) + 1
 
        def count_rows_reach():
            if not player.weapon: return 0
            return 1 + (1 if reach_bonus > 0 else 0) + 1
 
        TITLE_H = 15
        upper_h = (TITLE_H + count_rows_atk()   * ROW_H + GAP
                +  TITLE_H + count_rows_decay()  * ROW_H
                + (GAP + TITLE_H + count_rows_reach() * ROW_H if player.weapon else 0))
        lower_h = (GAP + 2 + GAP + len(other_caps) * ROW_H + 4) if other_caps else 0
        h = 8 + upper_h + lower_h + 8
 
        x = 18
        y = 75
 
        # ════════════════════════════════════════════════════════════
        #  面板背景
        # ════════════════════════════════════════════════════════════
        bg = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(bg, (*VOID_BLACK, 225), (0, 0, w, h), border_radius=6)
        pygame.draw.rect(bg, (*STEEL_MID,  220), (0, 0, w, h), 1, border_radius=6)
        surface.blit(bg, (x, y))
 
        cur_y = y + 8
 
        # ════════════════════════════════════════════════════════════
        #  輔助繪製函式
        # ════════════════════════════════════════════════════════════
        def title(text):
            nonlocal cur_y
            brightened_color = tuple(min(255, int(c * 1.5)) for c in BONE_WHITE)
            s = font_sm.render(text, True, brightened_color)
            surface.blit(s, (x + pad, cur_y))
            cur_y += TITLE_H
 
        def row_base(label, val):
            nonlocal cur_y
            surface.blit(font_sm.render(label, True, ASH_WHITE),
                         (x + pad, cur_y))
            vs = font_sm.render(str(val), True, ASH_WHITE)
            surface.blit(vs, (x + w - pad - vs.get_width(), cur_y))
            cur_y += ROW_H
 
        def row_bonus(label, val_str, color, negative=False):
            nonlocal cur_y
            prefix = "  - " if negative else "  + "
            surface.blit(font_sm.render(prefix + label, True, color),
                         (x + pad, cur_y))
            sign = "-" if negative else "+"
            vs = font_sm.render(sign + val_str, True, color)
            surface.blit(vs, (x + w - pad - vs.get_width(), cur_y))
            cur_y += ROW_H
 
        def row_total(label, val_str, color):
            nonlocal cur_y
            surface.blit(font_sm.render("= " + label, True, color),
                         (x + pad, cur_y))
            vs = font_sm.render(val_str, True, color)
            surface.blit(vs, (x + w - pad - vs.get_width(), cur_y))
            cur_y += ROW_H
 
        def divider():
            nonlocal cur_y
            cur_y += GAP
            pygame.draw.line(surface, STEEL_MID,
                             (x + pad, cur_y), (x + w - pad, cur_y), 1)
            cur_y += GAP
 
        # ════════════════════════════════════════════════════════════
        #  攻擊區塊
        # ════════════════════════════════════════════════════════════
        title("攻擊")
        row_base("基礎", int(base_after_mat))
 
        if player.material == 'wood':
            row_bonus("Wood ×0.8",
                      f"{abs(base_atk*0.8 - base_atk):.0f}",
                      DANGER_RED, negative=True)
        elif player.material == 'titan':
            row_bonus("Titan ×1.35",
                      f"{base_atk*0.35:.0f}",
                      SPIN_BLUE_GLOW)
 
        if weapon_bonus > 0:
            wname = {'scythe': 'Scythe', 'staff': 'Staff',
                     'hammer': 'Hammer'}.get(player.weapon, player.weapon)
            row_bonus(wname, str(weapon_bonus), SUCCESS_GREEN)
 
        if gear_bonus > 0:
            row_bonus("Gear ring", str(gear_bonus), WARN_ORANGE)
 
        if crown_active:
            t     = time.time()
            flash = DANGER_RED if int(t * 4) % 2 == 0 else WARN_ORANGE
            row_bonus("Crown 爆發", f"{crown_bonus:.0f}", flash)
 
        if   total_atk < 10: atk_col = ASH_WHITE
        elif total_atk < 18: atk_col = SUCCESS_GREEN
        elif total_atk < 26: atk_col = ENERGY_GOLD
        else:
            t = time.time()
            atk_col = DANGER_RED if int(t * 3) % 2 == 0 else WARN_ORANGE
        row_total("合計", f"{total_atk:.1f}", atk_col)
 
        cur_y += GAP
 
        # ════════════════════════════════════════════════════════════
        #  降速區塊
        # ════════════════════════════════════════════════════════════
        title("降速 / 秒")
        row_base("基礎", f"{base_decay}")
 
        for lbl, bonus in decay_labels:
            if bonus > 0:
                row_bonus(lbl, f"{bonus:.0f}", DANGER_RED)       # 降速變快（壞）
            else:
                row_bonus(lbl, f"{abs(bonus):.0f}", SUCCESS_GREEN, negative=True)  # 降速變慢（好）
 
        if   total_decay <= base_decay * 0.95: decay_col = SUCCESS_GREEN
        elif total_decay <= base_decay:        decay_col = ASH_WHITE
        elif total_decay <= base_decay * 1.3:  decay_col = WARN_ORANGE
        else:                                  decay_col = DANGER_RED
        row_total("合計", f"{total_decay:.1f}", decay_col)
 
        # ════════════════════════════════════════════════════════════
        #  攻擊範圍區塊（有武器才顯示）
        # ════════════════════════════════════════════════════════════
        if player.weapon:
            cur_y += GAP
            title("攻擊範圍")
            row_base("基礎", base_reach)
            if reach_bonus > 0:
                wname = {'scythe': 'Scythe', 'staff': 'Staff',
                         'hammer': 'Hammer'}.get(player.weapon, player.weapon)
                row_bonus(wname, str(reach_bonus), SUCCESS_GREEN)
            row_total("合計", str(total_reach), ASH_WHITE)
 
        # ════════════════════════════════════════════════════════════
        #  分隔線 + 其他能力
        # ════════════════════════════════════════════════════════════
        if other_caps:
            divider()
            for label, val_str in other_caps:
                surface.blit(font_sm.render(label, True, ASH_WHITE),
                             (x + pad, cur_y))
                vs = font_sm.render(val_str, True, WARN_ORANGE)
                surface.blit(vs, (x + w - pad - vs.get_width(), cur_y))
                cur_y += ROW_H
        
    # ── v0.9 helper methods ──────────────────────────────────────────────

    def _draw_tutorial_msg(self, surface, msg, timer, screen_w, screen_h):
        """7-A: spin tutorial — fades out over 3.5s, centred screen."""
        alpha = int(min(1.0, timer / 0.8) * 220)
        try:
            fnt = self.fonts['title']
        except KeyError:
            fnt = self.fonts['card']
        s = fnt.render(msg, True, ENERGY_GOLD)
        surf = pygame.Surface(s.get_size(), pygame.SRCALPHA)
        surf.blit(s, (0, 0))
        surf.set_alpha(alpha)
        surface.blit(surf, (screen_w//2 - s.get_width()//2,
                             screen_h//2 - 60))

    def _draw_loadout_icons(self, surface, player, screen_h):
        """1-C: Show equipped item names, bottom-left.
        Instead of cryptic single-character labels, show the actual item name
        so the player always knows what they have equipped.
        """
        ITEM_NAMES = {
            # material
            'wood':             '木頭',
            'steel':            '不鏽鋼',
            'titan':            '鈦合金',
            # weapon
            'scythe':           '鐮刀',
            'staff':            '金箍棒',
            'hammer':           '重鎚',
            # accessory
            'axis':             '鋼軸心',
            'gear_ring':        '齒輪環',
            'dash_tape':        '衝刺帶',
            # drive
            'recoil_dampener':  '反震阻尼',
            'shockwave':        '衝擊波',
            'splinter_echo':    '碎片殘響',
            # core
            'chaos':            '混沌核',
            'shield':           '魔王盾',
            'crown':            '廢墟冠',
        }
        SLOT_COLORS = {
            'material':  (140, 200, 100),   # 綠 — 材質
            'weapon':    (220, 100,  60),   # 橙紅 — 武器
            'accessory': (100, 180, 240),   # 藍 — 配件
            'drive':     (170, 120, 255),   # 紫 — 驅動
            'core':      (240, 190,  50),   # 金 — 核心
        }
        slots = [
            ('material',  getattr(player, 'material',  None)),
            ('weapon',    getattr(player, 'weapon',    None)),
            ('accessory', getattr(player, 'accessory', None)),
            ('drive',     getattr(player, 'drive',     None)),
            ('core',      getattr(player, 'core',      None)),
        ]
        fn  = self.fonts['sm']
        ix  = 20
        iy  = screen_h - 30
        PAD = 5     # horizontal padding inside pill
        GAP = 8     # gap between pills

        # Gather drive flash state from player for activation feedback
        drive_flash   = getattr(player, '_drive_flash_timer', 0.0)
        drive_label   = getattr(player, '_drive_flash_label', '')

        for slot_type, val in slots:
            if not val:
                continue
            label     = ITEM_NAMES.get(val, val)
            col       = SLOT_COLORS[slot_type]

            # Drive pill pulses bright white when active
            if slot_type == 'drive' and drive_flash > 0:
                pulse = min(1.0, drive_flash / 0.6)
                bright = tuple(min(255, int(c + (255 - c) * pulse * 0.6)) for c in col)
                border_col = bright
                bg_col = (int(20 + 50 * pulse), int(20 + 50 * pulse), int(40 + 80 * pulse))
            else:
                border_col = col
                bg_col = (14, 18, 28)

            txt_surf  = fn.render(label, True, col if slot_type != 'drive' or drive_flash <= 0 else (255, 255, 255))
            pill_w    = txt_surf.get_width() + PAD * 2
            pill_h    = txt_surf.get_height() + 2

            # Dark pill background + coloured border
            pygame.draw.rect(surface, bg_col,
                             (ix, iy, pill_w, pill_h), border_radius=3)
            pygame.draw.rect(surface, border_col,
                             (ix, iy, pill_w, pill_h), 1 if drive_flash <= 0 or slot_type != 'drive' else 2, border_radius=3)
            surface.blit(txt_surf, (ix + PAD, iy + 1))

            # Show activation label floating above the drive pill
            if slot_type == 'drive' and drive_flash > 0 and drive_label:
                alpha = min(255, int(drive_flash / 0.6 * 220))
                try:
                    fn_mid = self.fonts['card']
                except Exception:
                    fn_mid = fn
                lbl_surf = fn_mid.render(drive_label, True, (255, 255, 120))
                lbl_s = pygame.Surface(lbl_surf.get_size(), pygame.SRCALPHA)
                lbl_s.blit(lbl_surf, (0, 0))
                lbl_s.set_alpha(alpha)
                surface.blit(lbl_s, (ix + pill_w // 2 - lbl_surf.get_width() // 2,
                                     iy - lbl_surf.get_height() - 4))

            ix += pill_w + GAP

    def _draw_style_meter(self, surface, player, screen_w, screen_h):
        """2-A: Show concrete RPM stats instead of abstract aggr/surv meter.
        Displays current decay rate and attack power so the player can
        see the actual effect of their chosen items at a glance.
        """
        fn  = self.fonts['sm']
        rx  = screen_w - 130   # right-align block
        ry  = screen_h - 30

        # Current effective decay (RPM/s lost automatically)
        decay = player.effective_decay()
        decay_col = (WARN_ORANGE if decay > 30 else
                     (100, 220, 120) if decay < 22 else (180, 190, 210))
        d_lbl  = fn.render("轉速耗損:", True, (120, 130, 150))
        d_val  = fn.render(f"{decay:.0f}/s", True, decay_col)
        surface.blit(d_lbl, (rx, ry))
        surface.blit(d_val, (rx + d_lbl.get_width() + 4, ry))

        # Effective attack power
        atk   = player.effective_attack()
        atk_col = (ENERGY_GOLD if atk > 8 else (180, 190, 210))
        a_lbl  = fn.render("攻擊力:", True, (120, 130, 150))
        a_val  = fn.render(f"{atk:.1f}", True, atk_col)
        surface.blit(a_lbl, (rx, ry - 16))
        surface.blit(a_val, (rx + a_lbl.get_width() + 4, ry - 16))

    def _draw_boss_skill_label(self, surface, skill_name, timer, screen_w, screen_h):
        pass

    def draw_boss_bar(self, surface, boss, screen_w):
        bw = 400
        bx = (screen_w - bw) // 2
        by = 12
        bh = 20

        # Background
        pygame.draw.rect(surface, STEEL_DARK, (bx, by, bw, bh), border_radius=4)

        # Fill color by phase
        hp_pct = boss.hp / boss.max_hp
        if boss.phase == 3:
            t = pygame.time.get_ticks() / 500
            bc = ENERGY_GOLD if int(t) % 2 == 0 else WARN_ORANGE
        elif boss.phase == 2:
            bc = WARN_ORANGE
        else:
            bc = DANGER_RED

        fill_w = int(bw * max(0, hp_pct))
        if fill_w > 0:
            pygame.draw.rect(surface, bc, (bx, by, fill_w, bh), border_radius=4)

        # Phase lines at 70% and 35% (v0.5: updated from 66%/33%)
        for pct in [0.70, 0.35]:
            lx = bx + int(bw * pct)
            pygame.draw.line(surface, VOID_BLACK, (lx, by), (lx, by + bh), 2)

        # Label
        font_sm = self.fonts['sm']
        du.draw_text(surface, "BOSS", font_sm, DANGER_RED, bx - 4, by + 2,
                     align="right", shadow_color=(0, 0, 0))
        du.draw_text(surface, f"{boss.hp}/{boss.max_hp}", font_sm, ASH_WHITE,
                     bx + bw + 4, by + 2, shadow_color=(0, 0, 0))

        # Shield bar（Phase 3 護盾）
        if getattr(boss, 'shield_active', False) or getattr(boss, 'shield_value', 0) > 0:
            max_sv  = getattr(boss, 'max_shield_value', 9999) or 1
            sv      = getattr(boss, 'shield_value', 0)
            s_ratio = max(0.0, sv / max_sv)
            sh      = 10
            sy      = by + bh + 4
            pygame.draw.rect(surface, STEEL_DARK, (bx, sy, bw, sh), border_radius=3)
            if s_ratio > 0:
                pygame.draw.rect(surface, (255, 215, 0),
                                 (bx, sy, int(bw * s_ratio), sh), border_radius=3)
            pygame.draw.rect(surface, ASH_WHITE, (bx, sy, bw, sh), 1, border_radius=3)

    def _draw_vignette(self, surface, color, alpha, w, h):
        thickness = 60
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        for i in range(thickness):
            a = int(alpha * (1 - i / thickness))
            pygame.draw.rect(s, (int(color[0]), int(color[1]), int(color[2]), int(a)), (i, i, w - 2*i, h - 2*i), 1)
        surface.blit(s, (0, 0))

    # ── v0.5: 新增 HUD 通知方法 ────────────────────────────────────────────

    def draw_boost_notification(self, surface, timer, screen_w, screen_h):
        """已停用：綠圈邊界改為物理反射，不顯示提示文字。"""
        return

    def draw_rolling_stone_warning(self, surface, timer, screen_w, side=-1):
        """v0.5 重設計：滾石來襲警告 — 大字 + 方向箭頭 + 閃爍紅色 Banner。
        side: 0=上  1=右  2=下  3=左  (-1=不顯示箭頭)
        """
        if timer <= 0:
            return

        t = time.time()
        # 快速閃爍（6Hz），讓警告很顯眼
        pulse = math.sin(t * 6 * math.pi)   # -1 ~ 1
        visible = pulse > -0.3              # 約 65% duty cycle

        # 淡出：最後 0.6s 漸漸消失
        fade = min(1.0, timer / 0.6)

        if not visible:
            return

        # ── 全寬紅色半透明 Banner ──────────────────────────────────────
        banner_h = 54
        banner_y = 60
        banner   = pygame.Surface((screen_w, banner_h), pygame.SRCALPHA)
        base_alpha = int(fade * (160 + 60 * abs(pulse)))   # 120~220 隨脈動
        banner.fill((160, 10, 10, base_alpha))
        # 頂/底邊亮紅框線
        pygame.draw.line(banner, (255, 60, 60, 255), (0, 0),         (screen_w, 0),          3)
        pygame.draw.line(banner, (255, 60, 60, 200), (0, banner_h-1),(screen_w, banner_h-1),  2)
        surface.blit(banner, (0, banner_y))

        # ── 主標題：大字 bold ──────────────────────────────────────────
        try:
            font_warn = self.fonts['title']   # 32px bold
        except Exception:
            font_warn = self.fonts['sm']

        label = "!! 滾石來襲！"
        # 文字發光：先畫一層偏移陰影
        shadow = font_warn.render(label, True, (60, 0, 0))
        surface.blit(shadow, (screen_w // 2 - shadow.get_width() // 2 + 2,
                               banner_y + (banner_h - shadow.get_height()) // 2 + 2))
        # 主文字：交替純白/亮紅造成閃動感
        text_color = (255, 255, 255) if int(t * 8) % 2 == 0 else (255, 80, 80)
        surf = font_warn.render(label, True, text_color)
        surf.set_alpha(int(fade * 255))
        tx = screen_w // 2 - surf.get_width() // 2
        ty = banner_y + (banner_h - surf.get_height()) // 2
        surface.blit(surf, (tx, ty))

        # ── 方向箭頭（三角形指示器）─────────────────────────────────
        if side < 0:
            return

        arrow_color  = (255, 80, 80, int(fade * 220))
        arrow_size   = 22
        margin_edge  = 14      # 離場地邊距

        cx = screen_w // 2
        # 場地中心 y（估算，若需精確可傳入）
        from constants import PLAY_TOP, PLAY_BOTTOM, PLAY_LEFT, PLAY_RIGHT
        cy_mid = (PLAY_TOP + PLAY_BOTTOM) // 2

        def draw_arrow(pts):
            arr_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            pygame.draw.polygon(arr_surf, arrow_color, pts)
            surface.blit(arr_surf, (0, 0))

        s = arrow_size
        pulse_scale = 1.0 + 0.18 * abs(pulse)   # 箭頭隨脈動縮放
        s = int(s * pulse_scale)

        if side == 0:    # ↓ 從上方進入 → 箭頭在場地上緣，向下指
            ax, ay = cx, PLAY_TOP + margin_edge + s
            draw_arrow([(ax, ay), (ax - s, ay - s*2), (ax + s, ay - s*2)])
        elif side == 1:  # ← 從右方進入 → 箭頭在場地右緣，向左指
            ax, ay = PLAY_RIGHT - margin_edge - s, cy_mid
            draw_arrow([(ax, ay), (ax + s*2, ay - s), (ax + s*2, ay + s)])
        elif side == 2:  # ↑ 從下方進入 → 箭頭在場地下緣，向上指
            ax, ay = cx, PLAY_BOTTOM - margin_edge - s
            draw_arrow([(ax, ay), (ax - s, ay + s*2), (ax + s, ay + s*2)])
        else:            # → 從左方進入 → 箭頭在場地左緣，向右指
            ax, ay = PLAY_LEFT + margin_edge + s, cy_mid
            draw_arrow([(ax, ay), (ax - s*2, ay - s), (ax - s*2, ay + s)])

    def draw_phase_transition(self, surface, boss_phase, screen_w):
        """v0.5: Boss Phase 過渡提示"""
        if boss_phase not in (2, 3):
            return
        t = time.time()
        if int(t * 2) % 2 != 0:
            return
        font_sm = self.fonts['sm']
        msg = "PHASE 2 — ENRAGED" if boss_phase == 2 else "PHASE 3 — FINAL"
        color = WARN_ORANGE if boss_phase == 2 else DANGER_RED
        surf = font_sm.render(msg, True, color)
        surface.blit(surf, (screen_w // 2 - surf.get_width() // 2, 75))
