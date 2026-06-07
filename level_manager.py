# level_manager.py
import pygame
import math
import random
from enemies import *
from constants import *

import math as _math

def _check_hit(player, enemy):
    px, py = player.x, player.y
    ex, ey = enemy.x, enemy.y
    dx, dy = ex - px, ey - py
    dist = _math.sqrt(dx*dx + dy*dy) or 0.001
    angle_to_enemy = _math.atan2(dy, dx)

    body_r = player.radius + enemy.radius
    body_hit = dist < body_r

    weapon_hit = False
    if not body_hit and player.weapon:
        weapon_configs = {
            'scythe': (16, [0, _math.pi],                           0.52),
            'staff':  (28, [0, _math.pi/2, _math.pi, 3*_math.pi/2], 0.52),
            'hammer': (36, [0],                                      0.60),
        }
        if player.weapon in weapon_configs:
            reach, offsets, tol = weapon_configs[player.weapon]
            weapon_r = player.radius + reach + enemy.radius
            if dist < weapon_r:
                rot = _math.radians(player.angle)
                for off in offsets:
                    tip_angle = rot + off
                    diff = (angle_to_enemy - tip_angle + _math.pi) % (2*_math.pi) - _math.pi
                    if abs(diff) < tol:
                        weapon_hit = True
                        break

    return body_hit, weapon_hit

class LevelManager:
    def __init__(self, level, player, audio=None):
        self.level = level
        self.player = player
        self.audio = audio   # v0.5: AudioManager reference for in-level SFX
        self.enemies = []
        self.exp = 0
        self.cleared = False
        self.time_elapsed = 0.0
        self.afterimages = []  # L4 splinter_echo effect
        self._setup()

    def play_collision_sound(self, material=None):
        """
        播放碰撞音效的中央方法。
        
        自動判定材質與關卡，簡化所有碰撞聲音的調用。
        
        Args:
            material: 材質類型 (MATERIAL_STEEL, MATERIAL_WOOD, MATERIAL_PLASTIC 或 None)
                      如果為 None，優先使用玩家的材質，否則根據關卡判定。
        
        Returns:
            True 如果成功播放，False 如果在冷卻期內或無 audio manager
        
        Example:
            self.play_collision_sound()  # 自動使用玩家材質
            self.play_collision_sound(MATERIAL_WOOD)  # 強制使用木頭音效
        """
        if not self.audio:
            return False
        
        # 若未指定材質，優先使用玩家材質，否則讓 audio manager 自動判定
        if material is None:
            material = getattr(self.player, 'material', None)
        
        return self.audio.play_hit_sfx(level=self.level, material=material)

    def _setup(self):
        if self.level == 1:
            self._setup_l1()
        elif self.level == 2:
            self._setup_l2()
        elif self.level == 3:
            self._setup_l3()
        elif self.level == 4:
            self._setup_l4()
        elif self.level == 5:
            self._setup_l5()

# ── Level 1 ──────────────────────────────────────────────────────────


    def _enforce_bamboo_walls(self):
        """v0.10 FIX: Called every frame after player.update() to guarantee
        no bamboo penetration regardless of player speed.
        Runs circle-vs-rect push-out for every hardened bamboo.
        Also applies damage (RPM loss) and clash_trimmed sound on contact.
        Green bamboo: attack=60, Brown/crumbling bamboo: attack=90.
        """
        import math as _m
        pr = self.player.radius
        for e in self.enemies:
            if not isinstance(e, BambooShoot) or not e.hardened or not e.alive:
                continue
            rect = e.get_pillar_rect()
            if not rect:
                continue
            rl, rt, rw, rh = rect
            hit_this_frame = False
            # Run push-out until player is fully outside (max 8 iterations)
            for _ in range(8):
                lx = self.player.x; ly = self.player.y
                # Fast reject
                if lx < rl - pr or lx > rl + rw + pr:
                    break
                if ly < rt - pr or ly > rt + rh + pr:
                    break
                # Closest point on rect
                cx_r = max(rl, min(lx, rl + rw))
                cy_r = max(rt, min(ly, rt + rh))
                dx = lx - cx_r; dy = ly - cy_r
                dist = _m.sqrt(dx*dx + dy*dy)
                if dist >= pr:
                    break   # already outside
                hit_this_frame = True
                # Deep inside (centre is inside rect): eject on shortest axis
                if dist < 0.001:
                    # Find which wall is closest
                    opts = [
                        (lx - rl,          0, -1),        # left wall
                        (rl + rw - lx,     0,  1),        # right wall
                        (ly - rt,          1, -1),        # top wall
                        (rt + rh - ly,     1,  1),        # bottom wall
                    ]
                    gap, axis, sign = min(opts, key=lambda x: x[0])
                    if axis == 0:
                        self.player.x = (rl - pr - 1) if sign < 0 else (rl + rw + pr + 1)
                        self.player.vx = abs(self.player.vx) * sign
                    else:
                        self.player.y = (rt - pr - 1) if sign < 0 else (rt + rh + pr + 1)
                        self.player.vy = abs(self.player.vy) * sign
                else:
                    # Normal push-out
                    nx = dx / dist; ny = dy / dist
                    self.player.x += nx * (pr - dist + 1.0)
                    self.player.y += ny * (pr - dist + 1.0)
                    dot = self.player.vx * nx + self.player.vy * ny
                    if dot < 0:
                        self.player.vx -= 0.5 * dot * nx
                        self.player.vy -= 0.5 * dot * ny
            # 碰撞當幀：施加傷害 + 自動判定音效
            # 綠色竹子 attack=60，咖啡色龜裂竹子 attack=90
            if hit_this_frame:
                self.player.take_hit(e.x, e.y, e.attack, e.attack)
                self.player.vx *= 0.55
                self.player.vy *= 0.55
                self.play_collision_sound()

    def _setup_l1(self):
        # 設定玩家初始位置
        cx = (PLAY_LEFT + PLAY_RIGHT) // 2
        cy = (PLAY_TOP + PLAY_BOTTOM) // 2
        self.player.x = float(cx)
        self.player.y = float(cy)
        self.player.vx = 0.0
        self.player.vy = 0.0

        # 立即生成初始敵人
        for _ in range(3):
            x = random.randint(PLAY_LEFT + 80, PLAY_RIGHT - 80)
            y = random.randint(PLAY_TOP + 80, PLAY_BOTTOM - 80)
            self.enemies.append(WoodChip(x, y))
        
        self.nail_timer = 0.0
        self.nail_interval = 5.0 / 3
        self.stone_timer = 0.0
        self.stone_interval = 20.0 / 3
        self.stone_count = 0

        # 木片補充計時器
        self.woodchip_timer = 0.0
        self.woodchip_interval = 3.5    # 每 3.5 秒補一片
        self.woodchip_max = 6           # 場上最多 6 個木片同時存在
        self._rolling_stone_warned = False  # v0.5: 滾石預警
        self._rolling_warn_timer = 0.0
        self._rolling_warn_side  = -1      # v0.5: 來自哪個方向（0上1右2下3左）

    def _update_l1(self, dt):
        # 旋轉提示（只跑一次）
        if self.exp <= 3 and not getattr(self, '_spin_tutorial_shown', False):
            self._spin_tutorial_shown = True
            self._tutorial_msg = '[ 旋轉滑鼠補充轉速！ ]'
            self._tutorial_timer = 3.5
        if getattr(self, '_tutorial_timer', 0) > 0:
            self._tutorial_timer -= dt

        # 木片補充
        self.woodchip_timer += dt
        if self.woodchip_timer >= self.woodchip_interval:
            self.woodchip_timer = 0
            wood_count = sum(1 for e in self.enemies
                            if isinstance(e, WoodChip) and e.alive)
            if wood_count < self.woodchip_max:
                side = random.randint(0, 3)
                margin = 60
                if side == 0:
                    x = random.randint(PLAY_LEFT+margin, PLAY_RIGHT-margin)
                    y = PLAY_TOP + margin
                elif side == 1:
                    x = PLAY_RIGHT - margin
                    y = random.randint(PLAY_TOP+margin, PLAY_BOTTOM-margin)
                elif side == 2:
                    x = random.randint(PLAY_LEFT+margin, PLAY_RIGHT-margin)
                    y = PLAY_BOTTOM - margin
                else:
                    x = PLAY_LEFT + margin
                    y = random.randint(PLAY_TOP+margin, PLAY_BOTTOM-margin)
                self.enemies.append(WoodChip(x, y))

        # 鐵釘生成
        self.nail_timer += dt
        if self.nail_timer >= self.nail_interval:
            self.nail_timer = 0
            self._spawn_nail()

        # 滾石生成（EXP >= 40 才開始）
        if self.exp >= 40:
            self.stone_timer += dt
            if self.stone_timer >= self.stone_interval and self.stone_count < 3:
                self.stone_timer = 0
                self.stone_count += 1
                self._spawn_rolling_stone()

    def _spawn_nail(self):
        """從場地四邊內側生成鐵釘，朝玩家方向飛去。"""
        side = random.randint(0, 3)
        margin = 40
        if side == 0:   sx, sy = random.randint(PLAY_LEFT+margin, PLAY_RIGHT-margin), PLAY_TOP + margin
        elif side == 1: sx, sy = PLAY_RIGHT - margin, random.randint(PLAY_TOP+margin, PLAY_BOTTOM-margin)
        elif side == 2: sx, sy = random.randint(PLAY_LEFT+margin, PLAY_RIGHT-margin), PLAY_BOTTOM - margin
        else:           sx, sy = PLAY_LEFT + margin, random.randint(PLAY_TOP+margin, PLAY_BOTTOM-margin)
        tx = int(self.player.x) + random.randint(-30, 30)
        ty = int(self.player.y) + random.randint(-30, 30)
        self.enemies.append(IronNail(sx, sy, tx, ty))

    def _spawn_rolling_stone(self):
        """v0.5: 從場地外側生成滾石，直撲玩家；同步觸發 HUD 警告。
        0=上  1=右  2=下  3=左
        滾石在邊界外 60px 生成，玩家看到警告時石頭已在路上。
        """
        r   = 28   # stone radius
        side = random.randint(0, 3)
        if side == 0:    # 上方進入
            sx = random.randint(PLAY_LEFT + 80, PLAY_RIGHT - 80)
            sy = PLAY_TOP - r * 3
        elif side == 1:  # 右方進入
            sx = PLAY_RIGHT + r * 3
            sy = random.randint(PLAY_TOP + 80, PLAY_BOTTOM - 80)
        elif side == 2:  # 下方進入
            sx = random.randint(PLAY_LEFT + 80, PLAY_RIGHT - 80)
            sy = PLAY_BOTTOM + r * 3
        else:            # 左方進入
            sx = PLAY_LEFT - r * 3
            sy = random.randint(PLAY_TOP + 80, PLAY_BOTTOM - 80)

        stone = RollingStone(sx, sy,
                             target_x=self.player.x,
                             target_y=self.player.y)
        self.enemies.append(stone)



    # ── Level 2 ──────────────────────────────────────────────────────────

    def _setup_l2(self):
        # 設定玩家初始位置
        cx = (PLAY_LEFT + PLAY_RIGHT) // 2
        cy = (PLAY_TOP + PLAY_BOTTOM) // 2
        self.player.x = float(cx)
        self.player.y = float(cy)
        self.player.vx = 0.0
        self.player.vy = 0.0

        self.bamboo_spawn_timer = 0.0
        self.bamboo_spawn_interval = 2.5    # 每 2.5 秒補一株
        self.bamboo_soft_max = 7            # 軟竹筍上限（可被打的）
        self.bamboo_hard_max = 3            # 硬竹子上限 (v0.5: 5→3，避免場地堵死)
        
        # 立即生成初始竹筍
        placed = []
        attempts = 0
        while len(placed) < 5 and attempts < 200:
            attempts += 1
            x = random.randint(PLAY_LEFT + 80, PLAY_RIGHT - 80)
            y = random.randint(PLAY_TOP + 80, PLAY_BOTTOM - 80)
            if all(math.sqrt((x-px)**2 + (y-py)**2) >= 80 for px, py in placed):
                placed.append((x, y))
                self.enemies.append(BambooShoot(x, y))

    def _update_l2(self, dt):
        # 分開計算軟竹筍與硬竹子數量（這是原本 bug 的根源）
        soft_count = sum(1 for e in self.enemies
                        if isinstance(e, BambooShoot) and e.alive
                        and not e.hardened)
        hard_count = sum(1 for e in self.enemies
                        if isinstance(e, BambooShoot) and e.alive
                        and e.hardened)


        # 補充軟竹筍（只看軟竹筍數量，不受硬竹子影響）
        self.bamboo_spawn_timer += dt
        if (self.bamboo_spawn_timer >= self.bamboo_spawn_interval
                and soft_count < self.bamboo_soft_max):
            self.bamboo_spawn_timer = 0

            # 確保新竹筍不會生在現有竹子或竹林太近的地方
            for _ in range(10):
                x = random.randint(PLAY_LEFT + 80, PLAY_RIGHT - 80)
                y = random.randint(PLAY_TOP + 80, PLAY_BOTTOM - 80)
                too_close = False
                for e in self.enemies:
                    if isinstance(e, BambooShoot) and e.alive:
                        # 軟竹筍：radius=8，檢查中心距離 >= 80
                        # 硬竹子：pillar 寬 18px，高 0-60px，檢查邊界距離
                        if e.hardened:
                            # 硬竹子已變成支柱，檢查柱子邊界
                            rect = e.get_pillar_rect()
                            if rect:
                                rl, rt, rw, rh = rect
                                cx_r = max(rl, min(x, rl + rw))
                                cy_r = max(rt, min(y, rt + rh))
                                dist_to_pillar = math.sqrt((x - cx_r)**2 + (y - cy_r)**2)
                                # 新竹筍 radius=8，與柱子距離要 >= 80
                                if dist_to_pillar < 80 + 8:
                                    too_close = True
                                    break
                        else:
                            # 軟竹筍：直接用圓心距離檢查
                            dx = e.x - x
                            dy = e.y - y
                            # 軟竹筍 radius=8，新竹筍 radius=8，距離 < 80 就算重疊
                            if math.sqrt(dx*dx + dy*dy) < 80:
                                too_close = True
                                break
                if not too_close:
                    self.enemies.append(BambooShoot(x, y))
                    break

    # ── Level 3 ──────────────────────────────────────────────────────────

    def _setup_l3(self):
        # 設定玩家初始位置
        cx = (PLAY_LEFT + PLAY_RIGHT) // 2
        cy = (PLAY_TOP + PLAY_BOTTOM) // 2
        self.player.x = float(cx)
        self.player.y = float(cy)
        self.player.vx = 0.0
        self.player.vy = 0.0

        self.gear_timer    = 0.0
        self.gear_interval = 8.0 / 3
        self.saw_timer     = 14.0          # 預熱：EXP 30 達到後約 4s 首隻登場
        self.saw_interval  = 10.0          # 兩隻間隔 10s，讓玩家充分體驗每隻
        self.saw_max_alive = 2            # 場上最多同時 2 隻（死了就補）
        self.screw_timer    = 0.0
        self.screw_interval = 3          # 補充稍快
        self.screw_max      = 6            # 上限提升至 6 隻
        
        # 立即生成初始螺絲
        for _ in range(4):
            x = random.randint(PLAY_LEFT + 80, PLAY_RIGHT - 80)
            y = random.randint(PLAY_TOP + 80, PLAY_BOTTOM - 80)
            self.enemies.append(Screw(x, y))

    def _update_l3(self, dt):
        # 難度節奏：
        # EXP  0–24 : 只有 Screw
        # EXP 25+   : Gear Small 出現（最多 3 個）
        # EXP 45+   : Gear Medium 可直接生成（最多 2+2）
        # EXP 30+   : Sawblade 開始計時，存活上限 2，死了補新的
        _particles = getattr(self, '_particles_ref', None)

        # ── Screw 補充 ──────────────────────────────────────────
        screw_alive = sum(1 for e in self.enemies if isinstance(e, Screw) and e.alive)
        self.screw_timer += dt
        if self.screw_timer >= self.screw_interval and screw_alive < self.screw_max:
            self.screw_timer = 0
            side = random.randint(0, 3)
            if side == 0:   sx, sy = random.randint(PLAY_LEFT+60, PLAY_LEFT+200),  random.randint(PLAY_TOP+60, PLAY_TOP+200)
            elif side == 1: sx, sy = random.randint(PLAY_RIGHT-200, PLAY_RIGHT-60), random.randint(PLAY_TOP+60, PLAY_TOP+200)
            elif side == 2: sx, sy = random.randint(PLAY_LEFT+60, PLAY_LEFT+200),  random.randint(PLAY_BOTTOM-200, PLAY_BOTTOM-60)
            else:           sx, sy = random.randint(PLAY_RIGHT-200, PLAY_RIGHT-60), random.randint(PLAY_BOTTOM-200, PLAY_BOTTOM-60)
            self.enemies.append(Screw(sx, sy))

        # ── Gear 生成（EXP 門檻）──────────────────────────────
        gear_all   = [e for e in self.enemies if isinstance(e, Gear) and e.alive]
        gear_small = [g for g in gear_all if g.size == 1]
        gear_med   = [g for g in gear_all if g.size == 2]

        self.gear_timer += dt

        if self.exp >= 25:
            spawn_size = 1
            if self.exp >= 45:
                spawn_size = 2 if (len(gear_med) < 2 and len(gear_small) >= 1) else 1

            small_cap = 3 if self.exp < 45 else 2
            med_cap   = 0 if self.exp < 45 else 2
            total_cap = small_cap + med_cap

            if self.gear_timer >= self.gear_interval and len(gear_all) < total_cap:
                self.gear_timer = 0
                if spawn_size == 2 and len(gear_med) < med_cap:
                    g_size = 2
                elif len(gear_small) < small_cap:
                    g_size = 1
                else:
                    g_size = None

                if g_size:
                    side = random.randint(0, 3)
                    if side == 0:   gx, gy = random.randint(PLAY_LEFT+20, PLAY_RIGHT-20), PLAY_TOP + 20
                    elif side == 1: gx, gy = PLAY_RIGHT-20, random.randint(PLAY_TOP+20, PLAY_BOTTOM-20)
                    elif side == 2: gx, gy = random.randint(PLAY_LEFT+20, PLAY_RIGHT-20), PLAY_BOTTOM-20
                    else:           gx, gy = PLAY_LEFT+20, random.randint(PLAY_TOP+20, PLAY_BOTTOM-20)
                    self.enemies.append(Gear(gx, gy, g_size))

        # Gear merging（同尺寸接觸 → 升一級，Large 不再升）
        gears = [e for e in self.enemies if isinstance(e, Gear) and e.alive and e.size < 3]
        for g in gears:
            g._near_merge = False
        for i in range(len(gears)):
            for j in range(i+1, len(gears)):
                ga, gb = gears[i], gears[j]
                if ga.size == gb.size:
                    dx = ga.x - gb.x; dy = ga.y - gb.y
                    dist_gg = math.sqrt(dx*dx + dy*dy)
                    warn_d = ga.radius + gb.radius + 44
                    if dist_gg < warn_d:
                        ga._near_merge = True; gb._near_merge = True
                    if dist_gg < ga.radius + gb.radius + 2:
                        new_size = min(3, ga.size + 1)
                        mx = int((ga.x+gb.x)//2); my = int((ga.y+gb.y)//2)
                        new_gear = Gear(mx, my, new_size)
                        ga.alive = False; gb.alive = False
                        self.enemies.append(new_gear)
                        if _particles:
                            import random as _rnd
                            for _ in range(14):
                                a = _rnd.uniform(0, 3.14159*2)
                                _particles.emit_spark(mx, my,
                                    (math.cos(a)*2.5, math.sin(a)*2.5), count=2)

        # ── Sawblade 生成（EXP 60 後，存活數 < saw_max_alive 就補）──
        if self.exp >= 60:
            self.saw_timer += dt
            saw_alive = sum(1 for e in self.enemies if isinstance(e, Sawblade) and e.alive)
            if self.saw_timer >= self.saw_interval and saw_alive < self.saw_max_alive:
                self.saw_timer = 0
                x = random.randint(PLAY_LEFT + 80, PLAY_RIGHT - 80)
                y = random.randint(PLAY_TOP + 80, PLAY_BOTTOM - 80)
                self.enemies.append(Sawblade(x, y))

    # ── Level 5 ──────────────────────────────────────────────────────────

    # ── Level 4 ──────────────────────────────────────────────────────────

    def _setup_l4(self):
        """
        超級加速X碰碰場地
        通關條件：累計擊敗 50 個敵方陀螺（self.exp 每擊殺 +1，通關閾值 50）
        加速帶幾何：同設計稿（R0=260, ALPHA=10°, Y_TOP=180）
        """

        # 設定玩家初始位置
        cx = (PLAY_LEFT + PLAY_RIGHT) // 2
        cy = (PLAY_TOP + PLAY_BOTTOM) // 2
        self.player.x = float(cx)
        self.player.y = float(cy)
        self.player.vx = 0.0
        self.player.vy = 0.0

        # 敵人生成延遲計時器（給玩家3秒時間移動避免重疊）
        self._spawn_delay = 1.5

        self._l4_cx = cx
        self._l4_cy = cy

        self._l4_ring_r      = 285   # 完整圓環半徑
        self._boost_track_width = 18 # 繪製寬度 (px)

        # 傳送門動畫計時
        self._portal_angle = 0.0

        # 通關計數（以敵人擊殺數計，不是 EXP）
        self._kill_count    = 0
        self._kill_count_frac = 0.0  # v0.5: 分裂陀螺分數計數
        self._boost_hud_timer = 0.0  # v0.5: 加速帶 HUD 計時
        self._kill_target   = 50
        self.exp            = 0       # 用作進度顯示 (0~100)

        # 敵人生成計時
        self._spawn_timer    = 0.0
        self._spawn_interval = 2.5    # 每 2.5 秒嘗試生成
        self._on_field_limit = 18     # 場上同時最多 18 個
        self._tank_limit     = 4      # 重量型上限
        self._runner_limit   = 6      # 干擾型上限

        # 場上陀螺超出 (重量+干擾) ≤ 10 的約束在 _get_heavy_count() 中計算
        # 保存初始敵人生成配置（延遲3秒後在 _update_l4 中生成）
        self._initial_enemies_l4 = [
            'runner', 'runner', 'splitting', 'splitting'
        ]
        self._initial_enemies_spawned = False

        # 玩家被加速帶牽引的狀態
        self._player_boosted        = False
        self._player_boost_active   = False
        self._player_boost_past_centre = False
        self._player_boost_entered  = False
        self._player_boost_cooldown = 0.0
        self._player_ring_lock = 0.0   # 綠圈彈射後的速度鎖定剩餘時間（秒）
        self._player_ring_locked_vx = 0.0
        self._player_ring_locked_vy = 0.0

    def _get_heavy_count(self):
        return sum(1 for e in self.enemies
                   if isinstance(e, (TankTop, RunnerTop)) and e.alive)

    def _spawn_enemy_l4(self, force_type=None):
        """在場地中心傳送門附近生成一個 Level 4 敵人。"""
        from enemies import TankTop, RunnerTop, SplittingTop
        cx, cy = self._l4_cx, self._l4_cy

        heavy_count   = sum(1 for e in self.enemies if isinstance(e, (TankTop, RunnerTop)) and e.alive)
        tank_count    = sum(1 for e in self.enemies if isinstance(e, TankTop)   and e.alive)
        runner_count  = sum(1 for e in self.enemies if isinstance(e, RunnerTop) and e.alive)
        split_count   = sum(1 for e in self.enemies if isinstance(e, SplittingTop) and e.alive)
        total_count   = sum(1 for e in self.enemies if e.alive)

        if total_count >= self._on_field_limit:
            return

        # 決定類型
        if force_type == 'tank':
            etype = 'tank'
        elif force_type == 'runner':
            etype = 'runner'
        elif force_type == 'splitting':
            etype = 'splitting'
        else:
            # 動態機率：優先填滿干擾型，重量型謹慎生成
            choices = []
            if heavy_count < 10 and tank_count < self._tank_limit:
                choices.append('tank')
            if heavy_count < 10 and runner_count < self._runner_limit:
                choices.extend(['runner', 'runner'])
            choices.extend(['splitting', 'splitting', 'splitting'])
            etype = random.choice(choices) if choices else 'splitting'

        # 從傳送門（中心附近）生成，加隨機偏移
        angle  = random.uniform(0, math.pi * 2)
        dist   = random.uniform(20, 60)
        sx     = cx + math.cos(angle) * dist
        sy     = cy + math.sin(angle) * dist
        sx     = max(PLAY_LEFT + 40, min(PLAY_RIGHT  - 40, sx))
        sy     = max(PLAY_TOP  + 40, min(PLAY_BOTTOM - 40, sy))

        if etype == 'tank':
            self.enemies.append(TankTop(sx, sy))
        elif etype == 'runner':
            self.enemies.append(RunnerTop(sx, sy))
        else:
            self.enemies.append(SplittingTop(sx, sy))

    def _point_near_polyline(self, px, py, pts, threshold):
        """檢查 (px,py) 是否距離折線段 pts 任一段 <= threshold。"""
        for i in range(len(pts) - 1):
            ax, ay = pts[i]
            bx, by = pts[i+1]
            dx = bx - ax; dy = by - ay
            seg_len_sq = dx*dx + dy*dy
            if seg_len_sq < 1:
                continue
            t = max(0.0, min(1.0, ((px - ax)*dx + (py - ay)*dy) / seg_len_sq))
            cx_ = ax + t * dx; cy_ = ay + t * dy
            if (px - cx_)**2 + (py - cy_)**2 <= threshold * threshold:
                return True, (cx_, cy_, ax, ay, bx, by)
        return False, None

    def _boost_tangent_dir(self, seg_ax, seg_ay, seg_bx, seg_by):
        """
        計算加速帶切線方向，強制為逆時針（相對場地中心）。
        回傳 (vx, vy) 單位向量。
        """
        dx = seg_bx - seg_ax; dy = seg_by - seg_ay
        seg_len = math.sqrt(dx*dx + dy*dy) or 1
        tx = dx / seg_len; ty = dy / seg_len

        # 判斷逆時針：切線與 (中心→線段中點) 叉積
        mid_x = (seg_ax + seg_bx) / 2 - self._l4_cx
        mid_y = (seg_ay + seg_by) / 2 - self._l4_cy
        cross = mid_x * ty - mid_y * tx
        if cross < 0:   # 如果目前方向是順時針，翻轉
            tx, ty = -tx, -ty
        return tx, ty

    def _clamp_player_to_ring(self):
        """安全 clamp：在 level_manager.update 後執行，確保玩家不穿出邊界。"""
        if not hasattr(self, '_l4_ring_r'):
            return
        cx_r, cy_r = self._l4_cx, self._l4_cy
        ring_r = self._l4_ring_r
        pr = self.player.radius

        dx = self.player.x - cx_r
        dy = self.player.y - cy_r
        dist = math.sqrt(dx*dx + dy*dy) or 1.0

        limit = ring_r - pr - 2
        if dist >= limit:
            nx = dx / dist
            ny = dy / dist
            dot = self.player.vx * nx + self.player.vy * ny
            if dot > 0:
                self.player.vx -= 2 * dot * nx
                self.player.vy -= 2 * dot * ny
            self.player.x = cx_r + nx * (limit - 1)
            self.player.y = cy_r + ny * (limit - 1)

    def _update_l4(self, dt):
        from enemies import TankTop, RunnerTop, SplittingTop
        px, py = self.player.x, self.player.y

        # ── 綠圈彈射鎖定計時器 ──────────────────────────────────────
        # player.update() 已先於本函數執行，這裡只負責計時與過期清旗
        if self._player_ring_lock > 0:
            self._player_ring_lock -= dt
            if self._player_ring_lock <= 0:
                self._player_ring_lock = 0.0
                self.player._track_boost_active = False

        # ── 敵人生成延遲計時（3秒後生成初始敵人）─────────────────────
        if self._spawn_delay > 0:
            self._spawn_delay -= dt
            # 延遲期間不進行敵人生成
            if self._spawn_delay <= 0 and not self._initial_enemies_spawned:
                for enemy_type in self._initial_enemies_l4:
                    self._spawn_enemy_l4(force_type=enemy_type)
                self._initial_enemies_spawned = True
            return

        # ── 傳送門旋轉動畫 ───────────────────────────────────────────
        self._portal_angle = (self._portal_angle + 90 * dt) % 360

        # ── 綠色軌道邊界：圓弧段用圓形檢查，頂部三段用線段檢查 ─────
        ring_r = self._l4_ring_r
        cx_r, cy_r = self._l4_cx, self._l4_cy

        _BOUNCE_BOOST  = 3.0
        _BOOST_MAX_SPD = 1800.0


        def _apply_boost(ref_vx, ref_vy):
            spd = math.sqrt(ref_vx*ref_vx + ref_vy*ref_vy) or 1.0
            scale = min(spd * _BOUNCE_BOOST, _BOOST_MAX_SPD) / spd
            return ref_vx * scale, ref_vy * scale

        def _bounce_off_track(obj_x, obj_y, vx, vy, radius):
            dx = obj_x - cx_r
            dy = obj_y - cy_r
            dist = math.sqrt(dx*dx + dy*dy) or 1.0
            limit = ring_r - radius
            if dist >= limit:
                nx = dx / dist
                ny = dy / dist
                dot = vx*nx + vy*ny
                rvx, rvy = _apply_boost(vx - 2*dot*nx, vy - 2*dot*ny)
                return cx_r + nx*(limit-1), cy_r + ny*(limit-1), rvx, rvy, True
            return obj_x, obj_y, vx, vy, False

        new_x, new_y, new_vx, new_vy, bounced = _bounce_off_track(
            px, py, self.player.vx, self.player.vy, self.player.radius)
        if bounced:
            # 立即補上本幀的反彈位移，不等下一幀才感受加速
            self.player.x  = new_x + new_vx * dt
            self.player.y  = new_y + new_vy * dt
            self.player.vx = new_vx
            self.player.vy = new_vy
            self._player_ring_lock      = 0.55
            self._player_ring_locked_vx = new_vx
            self._player_ring_locked_vy = new_vy
            self.player._track_boost_active = True
            self.player.hit_flash = 0.10   # 玩家閃白表示彈射
        self._player_boosted = False

        # ── 敵人同樣受綠圈邊界限制 ────────────────────────────────────
        for e in self.enemies:
            if not e.alive:
                continue
            new_ex, new_ey, new_evx, new_evy, e_bounced = _bounce_off_track(
                e.x, e.y, e.vx, e.vy, e.radius)
            e.x  = new_ex
            e.y  = new_ey
            e.vx = new_evx
            e.vy = new_evy
            if e_bounced:
                e._ring_lock        = 0.35
                e._ring_locked_vx   = new_evx
                e._ring_locked_vy   = new_evy

        # ── 敵人生成 ─────────────────────────────────────────────────
        self._spawn_timer += dt
        if self._spawn_timer >= self._spawn_interval:
            self._spawn_timer = 0
            if self._kill_count < self._kill_target:
                self._spawn_enemy_l4()

        # ── 通關進度更新 (EXP 作為進度條) ────────────────────────────
        self.exp = int(self._kill_count / self._kill_target * EXP_TO_CLEAR)
        self.exp = min(EXP_TO_CLEAR, self.exp)



    def _setup_l5(self):
        cx = (PLAY_LEFT + PLAY_RIGHT) // 2
        cy = (PLAY_TOP + PLAY_BOTTOM) // 2

        self.player.x = float(cx)
        self.player.y = float(cy)
        self.player.vx = 0.0
        self.player.vy = 0.0

        # 立即初始化 Boss 和地雷
        self.boss = Boss(float(PLAY_RIGHT - 120), float(PLAY_TOP + 120), self.player.material)
        self.enemies.append(self.boss)

        self.mines = []
        self.boss_bullets = []          # ← 新增：管理 Boss 發射的子彈
        self._spawn_mines(count=4)

    def _spawn_mines(self, count=3):
        """在場地隨機位置生成地雷，避開玩家、Boss 和已有地雷。"""
        placed = 0
        attempts = 0
        while placed < count and attempts < 60:
            attempts += 1
            x = float(random.randint(PLAY_LEFT + 80, PLAY_RIGHT - 80))
            y = float(random.randint(PLAY_TOP + 80, PLAY_BOTTOM - 80))

            dx = x - self.player.x; dy = y - self.player.y
            if math.sqrt(dx*dx + dy*dy) < 160:
                continue

            if self.boss.alive:
                dx = x - self.boss.x; dy = y - self.boss.y
                if math.sqrt(dx*dx + dy*dy) < 200:
                    continue

            too_close = False
            for m in self.mines:
                dx = x - m.x; dy = y - m.y
                if math.sqrt(dx*dx + dy*dy) < 110:
                    too_close = True
                    break
            if too_close:
                continue

            self.mines.append(ArenaMine(x, y))
            placed += 1

    def _update_l5(self, dt, boss_signals: dict):
        px, py = self.player.x, self.player.y

        # ── 地雷更新 ─────────────────────────────────────────────────
        for mine in self.mines:
            mine.update(dt, px, py)
            dmg = mine.check_damage(px, py)
            if dmg > 0:
                self.player.take_hit(mine.x, mine.y, dmg, dmg, no_stun=True)
                self.play_collision_sound()

        self.mines = [m for m in self.mines if m.alive]

        if self.boss.alive:
            target_count = {1: 4, 2: 0, 3: 0}.get(self.boss.phase, 4)
        else:
            target_count = 0
        shortage = target_count - len(self.mines)
        if shortage > 0:
            self._spawn_mines(count=shortage)
        elif shortage < 0:
            # Phase 轉換後移除多餘地雷（Phase 2/3 不使用地雷）
            self.mines = self.mines[:target_count]

        # ── Boss signals 處理 ────────────────────────────────────────

        # 1. 新子彈（螺旋 / 環形 / 追蹤彈幕）
        for bullet in boss_signals.get('bullets', []):
            self.boss_bullets.append(bullet)

        # Phase 3 護盾啟動：均勻散射 10 顆 MiniTop
        if boss_signals.get('spawn_phase3_mini_tops'):
            import math as _m
            for i in range(10):
                angle = _m.radians(i * 36)          # 均勻 36° 間隔
                spread = 200                          # 散射距離（px）
                tx = self.boss.x + _m.cos(angle) * spread
                ty = self.boss.y + _m.sin(angle) * spread
                self.enemies.append(MiniTop(self.boss.x, self.boss.y, tx, ty))

        # Phase 3 護盾：護盾值隨 MiniTop 存活數量同步，進度可視化
        if getattr(self.boss, 'shield_active', False):
            alive_minis = [e for e in self.enemies if isinstance(e, MiniTop) and e.alive]
            if not alive_minis:
                self.boss.shield_active = False
                self.boss.shield_value = 0
            else:
                max_sv = getattr(self.boss, 'max_shield_value', 9999)
                self.boss.shield_value = len(alive_minis) * (max_sv // 10)

        # spawn_mine / spawn_sawblade signals intentionally ignored

        # 3. 衝刺直接碰撞傷害
        direct_dmg = boss_signals.get('damage_player', 0)
        if direct_dmg > 0:
            self.player.take_hit(self.boss.x, self.boss.y, direct_dmg, direct_dmg, no_knockback=True, no_stun=True)
            self.play_collision_sound()

        # v0.9 (3-E): store boss skill name for HUD
        skill_name = boss_signals.get('skill_name', '')
        if skill_name:
            self._boss_skill_label = skill_name
            self._boss_skill_timer = 1.5
        if hasattr(self, '_boss_skill_timer') and self._boss_skill_timer > 0:
            self._boss_skill_timer -= dt



        # 4. 鐳射持續傷害
        laser = boss_signals.get('laser')
        if laser and laser.hits_player(px, py, self.player.radius):
            frame_dmg = laser.damage_ps * dt
            self.player.take_hit(self.boss.x, self.boss.y, frame_dmg, frame_dmg, no_knockback=True, no_stun=True)
            # v1.9: 鐳射不觸發碰撞音效

        # 5. Boss 子彈移動 & 碰撞玩家
        alive_bullets = []
        for b in self.boss_bullets:
            b.update(dt, px, py)
            if b.alive:
                if b.collides(px, py, self.player.radius):
                    self.player.take_hit(b.x, b.y, b.damage, b.damage, no_knockback=True, no_stun=True)
                    # v1.9: 彈幕不觸發碰撞音效
                    b.alive = False
                else:
                    alive_bullets.append(b)
        self.boss_bullets = alive_bullets

        # 6. Boss 碎片碰撞玩家（Phase 3 爆炸碎片由 Boss 自行管理）
        for frag in self.boss.fragments:
            if frag.alive and frag.collides(px, py, self.player.radius):
                self.player.take_hit(frag.x, frag.y, 60, 60, no_knockback=True, no_stun=True)
                # v1.9: 碎片不觸發碰撞音效
                frag.alive = False

    # ── Main Update ──────────────────────────────────────────────────────

    def update(self, dt, particles=None, damage_numbers=None):
        self._particles_ref = particles   # v0.9: available to sub-update methods
        px, py = self.player.x, self.player.y
        self.time_elapsed += dt

        # v0.9 (2-A): live style meter — recalc aggr/surv from chosen items
        try:
            from screens import REWARD_WEIGHTS
            def _score(dim):
                return sum(REWARD_WEIGHTS.get(item, {}).get(dim, 0)
                           for item in [self.player.material, self.player.weapon,
                                        self.player.accessory,
                                        getattr(self.player,'drive',None), self.player.core]
                           if item)
            self.player._style_aggr = _score('AGGR')
            self.player._style_surv = _score('SURV')
        except Exception:
            pass

        # ── Boss 優先更新，取得 signals ──────────────────────────────
        boss_signals = {}
        if self.level == 5 and hasattr(self, 'boss') and self.boss.alive:
            boss_signals = self.boss.update(dt, px, py, self.player)

        # ── Level-specific spawning ───────────────────────────────────
        if self.level == 1:
            self._update_l1(dt)
        elif self.level == 2:
            self._update_l2(dt)
        elif self.level == 3:
            self._update_l3(dt)
        elif self.level == 4:
            self._update_l4(dt)
        elif self.level == 5:
            self._update_l5(dt, boss_signals)

        # ── 更新所有敵人（Boss 已更新過，跳過）────────────────────────
        for e in self.enemies:
            if e.alive:
                if self.level == 5 and isinstance(e, Boss):
                    pass    # 已在上方更新
                elif self.level == 4 and getattr(e, '_ring_lock', 0) > 0:
                    # 綠圈彈射鎖定：維持反射速度，跳過 AI，0.35s 後自動恢復
                    e._ring_lock -= dt
                    if e._ring_lock < 0:
                        e._ring_lock = 0.0
                    else:
                        # 強制還原反彈速度，防止摩擦侵蝕
                        e.vx = getattr(e, '_ring_locked_vx', e.vx)
                        e.vy = getattr(e, '_ring_locked_vy', e.vy)
                    e.x += e.vx * dt
                    e.y += e.vy * dt
                    # 撞牆則提前解除鎖定
                    if e.x < PLAY_LEFT + e.radius:
                        e.x = PLAY_LEFT + e.radius; e.vx = abs(e.vx); e._ring_lock = 0.0
                    if e.x > PLAY_RIGHT - e.radius:
                        e.x = PLAY_RIGHT - e.radius; e.vx = -abs(e.vx); e._ring_lock = 0.0
                    if e.y < PLAY_TOP + e.radius:
                        e.y = PLAY_TOP + e.radius; e.vy = abs(e.vy); e._ring_lock = 0.0
                    if e.y > PLAY_BOTTOM - e.radius:
                        e.y = PLAY_BOTTOM - e.radius; e.vy = -abs(e.vy); e._ring_lock = 0.0
                elif self.level == 4 and getattr(e, '_boost_active', False):
                    # 加速帶衝刺中：AI 暫停，手動移動 + 牆壁碰撞即解除 boost
                    e.x += e.vx * dt
                    e.y += e.vy * dt
                    wall_hit = False
                    if e.x < PLAY_LEFT + e.radius:
                        e.x = PLAY_LEFT + e.radius; e.vx = abs(e.vx); wall_hit = True
                    if e.x > PLAY_RIGHT - e.radius:
                        e.x = PLAY_RIGHT - e.radius; e.vx = -abs(e.vx); wall_hit = True
                    if e.y < PLAY_TOP + e.radius:
                        e.y = PLAY_TOP + e.radius; e.vy = abs(e.vy); wall_hit = True
                    if e.y > PLAY_BOTTOM - e.radius:
                        e.y = PLAY_BOTTOM - e.radius; e.vy = -abs(e.vy); wall_hit = True
                    if wall_hit:
                        e._boost_active   = False
                        e._boost_past_ctr = False
                        e._boost_cd       = 0.0
                else:
                    e.update(dt, self.player.x, self.player.y)

        # ── v0.10: 竹子牆壁強制推出（在碰撞迴圈之前執行）────────────
        if self.level == 2:
            self._enforce_bamboo_walls()

        # ── 碰撞偵測：玩家 ↔ 敵人 ────────────────────────────────────
        p_reach = self.player.get_collision_radius()
        kill_list = []

        for e in self.enemies[:]:
            if not e.alive:
                continue

            if isinstance(e, BambooShoot) and e.hardened:
                # 推出 + 傷害 + 音效已由 _enforce_bamboo_walls() 統一處理
                continue

            body_hit, weapon_hit = _check_hit(self.player, e)

            if not body_hit and not weapon_hit:
                continue

            # 任何碰撞 → 立即解除雙方的加速帶 boost 與綠圈鎖定
            if self.level == 4:
                if self._player_boost_active:
                    self._player_boost_active      = False
                    self._player_boost_past_centre = False
                    self._player_boost_cd_timer    = 0.0
                    self._player_boosted           = False
                    self.player._track_boost_active = False
                if self._player_ring_lock > 0:
                    self._player_ring_lock = 0.0
                    self.player._track_boost_active = False
                if getattr(e, '_boost_active', False):
                    e._boost_active   = False
                    e._boost_past_ctr = False
                    e._boost_cd       = 0.0

            if body_hit:
                dist_val = _math.sqrt((e.x-px)**2 + (e.y-py)**2) or 0.001
                overlap = (self.player.radius + e.radius) - dist_val
                if overlap > 0:
                    nx = (px - e.x) / dist_val
                    ny = (py - e.y) / dist_val
                    enemy_mass = getattr(e, 'mass', 1.0)
                    push_ratio = 1.0 / (1.0 + enemy_mass)
                    # 「反震阻尼」drive：玩家被推開距離減少 30%
                    if isinstance(e, Boss):
                        player_push = 0.0
                    else:
                        player_push = (1 - push_ratio)
                    if getattr(self.player, 'drive', None) == 'recoil_dampener':
                        player_push *= 0.70
                        # BUG FIX: show drive flash on boss body-collision too
                        # (player.take_hit is skipped for Boss, so flash must be set here)
                        self.player._drive_flash_timer = 0.45
                        self.player._drive_flash_label = '反震阻尼！'
                        # v1.7: green absorbing ring at player position
                        if particles:
                            particles.emit_recoil_ring(self.player.x, self.player.y)
                    self.player.x += nx * overlap * player_push
                    self.player.y += ny * overlap * player_push
                    # v0.10: L5 魔王關 Boss 也會被推開（雙向碰撞）
                    # 玩家不移動（player_push=0），Boss 必須補回完整 overlap
                    if isinstance(e, Boss) and self.level == 5:
                        e.x -= nx * overlap
                        e.y -= ny * overlap
                    elif not isinstance(e, Boss):
                        e.x -= nx * overlap * push_ratio
                        e.y -= ny * overlap * push_ratio

            # 相對速度（爆擊判定 + 後續反作用力共用）
            _rel_vx  = self.player.vx - getattr(e, 'vx', 0.0)
            _rel_vy  = self.player.vy - getattr(e, 'vy', 0.0)
            _rel_spd = _math.sqrt(_rel_vx * _rel_vx + _rel_vy * _rel_vy)

            atk        = self.player.effective_attack()
            gear_bonus = 5 if self.player.accessory == 'gear_ring' else 0
            is_crit    = _rel_spd >= CRIT_SPEED_THRESHOLD
            total_dmg  = (atk + gear_bonus) * (CRIT_DAMAGE_MULT if is_crit else 1.0)
            killed     = e.take_damage(total_dmg)

            # 「衝擊波」drive：撞擊時對 120px 範圍內所有敵人造成 15 傷害
            if body_hit and getattr(self.player, 'drive', None) == 'shockwave':
                _hit_any = False
                for other in self.enemies:
                    if other.alive and other is not e:
                        dx_s = other.x - e.x; dy_s = other.y - e.y
                        if _math.sqrt(dx_s*dx_s + dy_s*dy_s) < 120:
                            other.take_damage(15)
                            _hit_any = True
                            if particles:
                                particles.emit_spark(other.x, other.y,
                                                     (dx_s, dy_s), 3)
                # BUG FIX: L5 mines are in self.mines (not self.enemies) — scan them too
                if self.level == 5 and hasattr(self, 'mines'):
                    for mine in self.mines:
                        if mine.alive and not mine.exploding:
                            dx_s = mine.x - e.x; dy_s = mine.y - e.y
                            if _math.sqrt(dx_s*dx_s + dy_s*dy_s) < 120:
                                mine.exploding = True   # shockwave detonates nearby mines
                                mine.explode_timer = 0.15
                                _hit_any = True
                                if particles:
                                    particles.emit_spark(mine.x, mine.y,
                                                         (dx_s, dy_s), 4)
                # BUG FIX: hitting the Boss itself counts — always show drive feedback in L5
                if not _hit_any and isinstance(e, Boss):
                    e.take_damage(15)   # direct bonus hit on Boss
                    _hit_any = True
                    if particles:
                        particles.emit_spark(e.x, e.y, (px - e.x, py - e.y), 3)
                    # v1.8: 衝擊波給 Boss 額外大量 impulse
                    if self.level == 5:
                        dist_sw = _math.sqrt((e.x-px)**2 + (e.y-py)**2) or 0.001
                        nx_sw = (px - e.x) / dist_sw; ny_sw = (py - e.y) / dist_sw
                        e.receive_impulse(self.player.effective_attack() * 10.0,
                                          -nx_sw * 100, -ny_sw * 100)
                if _hit_any:
                    self.player._drive_flash_timer = 0.6
                    self.player._drive_flash_label = '衝擊波！'
                    # v1.7: expanding blue rings from enemy impact point
                    if particles:
                        particles.emit_shockwave_ring(e.x, e.y)

            # 「碎片殘響」drive（L5 Boss 戰特殊觸發）
            # v1.6 BUG FIX: splinter_echo only triggers on kill; Boss never dies mid-fight,
            # so add a body_hit trigger (40% chance) to give the drive actual presence in L5.
            if (body_hit and self.level == 5
                    and getattr(self.player, 'drive', None) == 'splinter_echo'
                    and isinstance(e, Boss)):
                if random.random() < 0.40:
                    for _ in range(random.randint(1, 2)):
                        offset_angle = random.uniform(0, math.pi * 2)
                        offset_dist  = random.uniform(e.radius, e.radius + 30)
                        ax = e.x + math.cos(offset_angle) * offset_dist
                        ay = e.y + math.sin(offset_angle) * offset_dist
                        self.afterimages.append(Afterimage(ax, ay, lifetime=2.0))
                    self.player._drive_flash_timer = 0.5
                    self.player._drive_flash_label = '碎片殘響！'
                    # v1.7: gold spark burst at boss impact
                    if particles:
                        particles.emit_splinter_burst(e.x, e.y)


            if damage_numbers:
                _crown_crit = (self.player.core == 'crown' and
                               self.player.rpm / self.player.rpm_max < 0.30)
                damage_numbers.emit(e.x, e.y - e.radius, total_dmg,
                                    crit=(is_crit or _crown_crit))

            if particles:
                particles.emit_spark(e.x, e.y, (px - e.x, py - e.y), 5)

            if body_hit:
                dist_val = _math.sqrt((e.x-px)**2 + (e.y-py)**2) or 0.001
                nx = (px - e.x) / dist_val
                ny = (py - e.y) / dist_val
                enemy_mass = getattr(e, 'mass', 1.0)
                # v1.8: 擊退力道 = 玩家攻擊倍率 × 基礎值 ÷ (質量 × 敵人抗性)
                # v0.12: 基值 15→180，確保敵人被撞後實際飛出去
                player_atk_ratio = self.player.effective_attack() / max(1, BASE_ATTACK)
                knockback_str = (180.0 * player_atk_ratio) / (
                    enemy_mass * getattr(e, 'knockback_resistance', 1.0))
                push_vx = -nx * knockback_str
                push_vy = -ny * knockback_str
                # v0.10: L5 魔王關 Boss 雙向碰撞 + impulse 累積
                if isinstance(e, Boss) and self.level == 5:
                    # 直接給予小量速度（手感回饋）
                    e.vx += push_vx * 0.35
                    e.vy += push_vy * 0.35
                    # 累積衝擊值，達閾值觸發硬直
                    e.receive_impulse(self.player.effective_attack() * 5.0,
                                      push_vx, push_vy)
                elif not isinstance(e, Boss):
                    e.on_knockback(push_vx, push_vy)
                    if isinstance(e, IronNail):
                        e._passed_target = False

            elif weapon_hit and not isinstance(e, Boss):
                dist_val = _math.sqrt((e.x-px)**2 + (e.y-py)**2) or 0.001
                nx = (px - e.x) / dist_val
                ny = (py - e.y) / dist_val
                enemy_mass = getattr(e, 'mass', 1.0)
                player_atk_ratio = self.player.effective_attack() / max(1, BASE_ATTACK)
                knockback_str = (180.0 * player_atk_ratio * 0.30) / (
                    enemy_mass * getattr(e, 'knockback_resistance', 1.0))
                e.on_knockback(-nx * knockback_str, -ny * knockback_str)
                if isinstance(e, IronNail):
                    e._passed_target = False

            if isinstance(e, Boss):
                # 玩家接觸 Boss 本體時：受到接觸傷害、播放音效（不被彈開）
                if body_hit:
                    effective_atk = e.get_effective_attack()
                    _recoil = self.player.calc_collision_recoil(e, 'body', _rel_spd)
                    self.player.take_hit(e.x, e.y, effective_atk // 2, effective_atk,
                                        recoil_result=_recoil, no_knockback=True)
                    self.play_collision_sound()
            else:
                effective_atk = e.attack
                if weapon_hit and not body_hit:
                    spin_dmg = effective_atk * 0.30
                else:
                    spin_dmg = effective_atk
                # 計算碰撞反作用力（材質矩陣 + 裝備修正 + 速度縮放）
                _col_type = 'weapon' if (weapon_hit and not body_hit) else 'body'
                _recoil = self.player.calc_collision_recoil(e, _col_type, _rel_spd)
                self.player.take_hit(e.x, e.y, spin_dmg, effective_atk,
                                     weapon_only=(weapon_hit and not body_hit),
                                     recoil_result=_recoil)
                # v0.11: 優先用玩家的材質，若玩家是木頭且裝備武器則用 STEEL（clash_trimmed.wav）
                # v0.12: 若玩家無材質且非 L1，改用敵人材質決定音效（WoodChip → wood.wav）
                collision_material = self.player.material
                if self.player.weapon and self.player.material == MATERIAL_WOOD:
                    collision_material = MATERIAL_STEEL
                elif collision_material is None and self.level != 1:
                    enemy_mat = getattr(e, 'material', None)
                    if enemy_mat == MATERIAL_WOOD:
                        collision_material = MATERIAL_WOOD
                self.play_collision_sound(collision_material)

            # v0.5: 移除 on_hit_player() 呼叫（邏輯已在 Sawblade.update() 內部處理，見 QA S1-04）

            if killed:
                kill_list.append(e)

        # ── 擊殺處理 ─────────────────────────────────────────────────
        new_enemies = []   # 本幀新生成的敵人（分裂等）
        for e in kill_list:
            self.exp = min(EXP_TO_CLEAR, self.exp + e.exp)

            # Level 4: 擊殺計數 (v0.5: Gen0=1, Gen1=0.5, Gen2+=0不計，避免通關過快)
            if self.level == 4:
                if isinstance(e, SplittingTop):
                    if e.generation == 0:
                        self._kill_count_frac += 1.0
                    elif e.generation == 1:
                        self._kill_count_frac += 0.5
                    # Gen 2+ 不計入（分裂小碎片）
                    self._kill_count = int(self._kill_count_frac)
                else:
                    self._kill_count += 1

                # 分裂邏輯：SplittingTop 且下一代 HP ≥ 11
                if isinstance(e, SplittingTop) and e.can_split():
                    next_gen = e.generation + 1
                    if 100 // (2 ** next_gen) >= 11:
                        for _ in range(2):
                            offset_a = random.uniform(0, math.pi * 2)
                            sx = e.x + math.cos(offset_a) * (e.radius + 5)
                            sy = e.y + math.sin(offset_a) * (e.radius + 5)
                            new_enemies.append(SplittingTop(sx, sy, next_gen))

                # 「衝擊波」drive 已在碰撞時即時處理，擊殺時無需額外邏輯
                # 舊「磁力場」邏輯移除（已改為 shockwave）

            # 「碎片殘響」drive：生成殘影（BUG FIX：移出 level==4 區塊，L4/L5 均有效）
            if self.player.drive == 'splinter_echo':
                num_afterimages = random.randint(3, 4)
                for _ in range(num_afterimages):
                    offset_angle = random.uniform(0, math.pi * 2)
                    offset_dist = random.uniform(e.radius, e.radius + 30)
                    ax = e.x + math.cos(offset_angle) * offset_dist
                    ay = e.y + math.sin(offset_angle) * offset_dist
                    self.afterimages.append(Afterimage(ax, ay, lifetime=2.0))
                self.player._drive_flash_timer = 0.5
                self.player._drive_flash_label = '碎片殘響！'
                # v1.7: gold spark explosion at kill position
                if particles:
                    particles.emit_splinter_burst(e.x, e.y)

            if self.player.core == 'chaos':
                for other in self.enemies:
                    if other.alive and other is not e:
                        dx = other.x - e.x; dy = other.y - e.y
                        if math.sqrt(dx*dx + dy*dy) < 80:
                            other.take_damage(10)

        # 加入本幀新生成的分裂陀螺
        self.enemies.extend(new_enemies)

        # ── 碰撞後邊界強制修正：防止敵人被撞出界外 ──────────────────────
        for e in self.enemies:
            if not e.alive or isinstance(e, BambooShoot):
                continue
            if e.x < PLAY_LEFT + e.radius:
                e.x = PLAY_LEFT + e.radius
                if e.vx < 0: e.vx *= -1
            elif e.x > PLAY_RIGHT - e.radius:
                e.x = PLAY_RIGHT - e.radius
                if e.vx > 0: e.vx *= -1
            if e.y < PLAY_TOP + e.radius:
                e.y = PLAY_TOP + e.radius
                if e.vy < 0: e.vy *= -1
            elif e.y > PLAY_BOTTOM - e.radius:
                e.y = PLAY_BOTTOM - e.radius
                if e.vy > 0: e.vy *= -1

        # ── 竹子最終強制推出（每幀結尾再跑一次，保證無論如何不穿透）──
        if self.level == 2:
            pr = self.player.radius
            for e in self.enemies:
                if not (isinstance(e, BambooShoot) and e.hardened):
                    continue
                rect = e.get_pillar_rect()
                if not rect:
                    continue
                rl, rt, rw, rh = rect
                lx_ = self.player.x; ly_ = self.player.y
                if not (rl - pr < lx_ < rl + rw + pr and rt - pr < ly_ < rt + rh + pr):
                    continue
                cx_r = max(rl, min(lx_, rl + rw))
                cy_r = max(rt,  min(ly_, rt + rh))
                dx_  = lx_ - cx_r; dy_ = ly_ - cy_r
                dist_r = _math.sqrt(dx_*dx_ + dy_*dy_) or 0.001
                if dist_r < pr:
                    nx_ = dx_ / dist_r; ny_ = dy_ / dist_r
                    self.player.x += nx_ * (pr - dist_r + 0.5)
                    self.player.y += ny_ * (pr - dist_r + 0.5)
                    dot = self.player.vx * nx_ + self.player.vy * ny_
                    if dot < 0:
                        self.player.vx -= (1 + 0.65) * dot * nx_
                        self.player.vy -= (1 + 0.65) * dot * ny_
                elif dist_r == 0:
                    self.player.y = rt - pr - 1
                    self.player.vy = -abs(self.player.vy)

        # -- v0.12: L4 ring clamp after collisions --
        if self.level == 4:
            self._clamp_player_to_ring()


        # ── Afterimage 更新與碰撞 ─────────────────────────────────
        # 更新所有残影
        for ag in self.afterimages[:]:
            ag.update(dt)
            if not ag.alive:
                self.afterimages.remove(ag)
                continue
            
            # 检查残影与敌人的碰撞
            for e in self.enemies:
                if not e.alive:
                    continue
                
                # 使用ID追踪防止多次伤害同一个敌人
                enemy_id = id(e)
                if ag.collides_with(e.x, e.y, e.radius):
                    if enemy_id not in ag.hit_enemies:
                        ag.hit_enemies.add(enemy_id)
                        e.take_damage(5)  # v0.5: 8→5

        # ── 清除死亡敵人 ─────────────────────────────────────────────
        self.enemies = [e for e in self.enemies if e.alive]

        # ── 通關判定 ─────────────────────────────────────────────────
        if not self.cleared:
            if self.level == 5:
                if hasattr(self, 'boss') and not self.boss.alive:
                    self.cleared = True
                    self.exp = EXP_TO_CLEAR
            elif self.level == 4:
                if self._kill_count >= self._kill_target:
                    self.cleared = True
                    self.exp = EXP_TO_CLEAR
            elif self.exp >= EXP_TO_CLEAR:
                self.cleared = True

    def draw(self, surface):
        # Level 4 加速帶（繪製在敵人之下）
        if self.level == 4 and hasattr(self, '_l4_ring_r'):
            self._draw_l4_track(surface)

        for e in self.enemies:
            e.draw(surface)
        if self.level == 5 and hasattr(self, 'mines'):
            for mine in self.mines:
                mine.draw(surface)
        # Boss 子彈
        if self.level == 5 and hasattr(self, 'boss_bullets'):
            for b in self.boss_bullets:
                b.draw(surface)
        
        # 殘影（splinter_echo drive）— BUG FIX：不再限定 level==4，L5 同樣繪製
        if hasattr(self, 'afterimages'):
            for ag in self.afterimages:
                if ag.alive:
                    ag.draw(surface)

    def _draw_l4_track(self, surface):
        """繪製第四關加速帶軌跡與中心傳送門。"""
        cx  = int(self._l4_cx)
        cy  = int(self._l4_cy)
        ring_r = self._l4_ring_r
        tw     = self._boost_track_width

        # ── 加速帶（完整圓環） ───────────────────────────────────────
        glow_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (80, 240, 40, 40),  (cx, cy), ring_r, tw * 3)
        pygame.draw.circle(glow_surf, (80, 240, 40, 100), (cx, cy), ring_r, tw)
        pygame.draw.circle(glow_surf, (160, 255, 80, 180),(cx, cy), ring_r, 3)
        surface.blit(glow_surf, (0, 0))

        # ── 傳送門（場地中心） ───────────────────────────────────────
        portal_r  = 28
        a_rad     = math.radians(self._portal_angle)
        portal_surf = pygame.Surface((portal_r*4, portal_r*4), pygame.SRCALPHA)
        pcx = portal_r * 2
        pcy = portal_r * 2
        # 外旋轉光環
        pygame.draw.circle(portal_surf, (40, 220, 220, 80),  (pcx, pcy), portal_r + 8)
        pygame.draw.circle(portal_surf, (40, 220, 220, 160), (pcx, pcy), portal_r + 8, 3)
        # 旋轉刻痕
        for i in range(6):
            a = a_rad + i * math.pi / 3
            x1 = pcx + int((portal_r + 4) * math.cos(a))
            y1 = pcy + int((portal_r + 4) * math.sin(a))
            x2 = pcx + int((portal_r + 10) * math.cos(a))
            y2 = pcy + int((portal_r + 10) * math.sin(a))
            pygame.draw.line(portal_surf, (40, 220, 220, 200), (x1, y1), (x2, y2), 2)
        # 內核
        pygame.draw.circle(portal_surf, (20, 180, 180, 200), (pcx, pcy), portal_r)
        pygame.draw.circle(portal_surf, (200, 255, 255, 220),(pcx, pcy), portal_r // 2)
        surface.blit(portal_surf, (cx - portal_r*2, cy - portal_r*2))

    def get_boss(self):
        if self.level == 5:
            return getattr(self, 'boss', None)
        return None