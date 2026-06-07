# player.py
import pygame
import math
from colors import *
from constants import *
import draw_utils as du

class Player:
    def __init__(self):
        self.x = PLAY_LEFT + PLAY_W // 2
        self.y = PLAY_TOP + PLAY_H // 2
        self.vx = 0.0
        self.vy = 0.0
        self.rpm = RPM_INIT
        self.rpm_max = RPM_MAX
        self.rpm_decay = RPM_DECAY  # per second
        self.base_attack = BASE_ATTACK
        self.speed = PLAYER_SPEED
        self.radius = PLAYER_RADIUS
        self.angle = 0.0  # rotation angle in degrees

        self.stun_timer = 0.0
        self.invincible_timer = 0.0  # for dash

        # Equipment
        self.material = None     # 'wood', 'steel', 'titan'
        self.weapon = None       # 'scythe', 'staff', 'hammer'
        self.accessory = None    # 'axis', 'gear_ring', 'dash_tape'
        self.core = None         # 'chaos', 'shield', 'crown'
        self.drive = None        # 'recoil_dampener', 'shockwave', 'splinter_echo' (Level 4)
        self.rpm_decay_override = None  # 若設定，暫時覆蓋 rpm_decay（Level 4 加速帶）

        # Weapon/accessory params
        self.weapon_attack_bonus = 0
        self.weapon_reach = 0
        self.weapon_count = 0
        self.hammer_penalty = False

        # Dash tape state
        self.dash_charge = 0.0   # seconds of continuous movement
        self.dash_cooldown = 0.0
        self.is_dashing = False
        self.dash_timer = 0.0
        self.dash_dx = 0.0
        self.dash_dy = 0.0

        # Visual
        self.hit_flash = 0.0
        self.afterimages = []
        self._recoil_shield = 0.0
        self._intro_hit_pending = True   # v0.9 (1-A): first-hit demo effect
        self._staff_flash_timer = 0.0   # v0.9: staff four-way flash
        # 2-A: live style meter scores (updated by LevelManager)
        self._style_aggr = 0
        self._style_surv = 0

        # Level 4 track boost lock
        self._track_boost_active = False   # 加速帶衝刺中，鎖定速度方向

        # Drive activation flash (UI feedback for all three drives)
        self._drive_flash_timer = 0.0      # counts down from 0.6s on activation
        self._drive_flash_label = ''       # e.g. '衝擊波！' shown at pill


    # ── stats derived from equipment ─────────────────────────────────────

    def get_material_color(self):
        if self.material == 'wood':
            return WOOD_WARM
        elif self.material == 'titan':
            return TITAN_DARK
        else:
            return SPIN_BLUE

    def effective_decay(self):
        # 若有暫時覆蓋（如 Level 4 加速帶），直接使用
        if self.rpm_decay_override is not None:
            return self.rpm_decay_override
        base = self.rpm_decay
        if self.material == 'wood':
            base *= 0.9
        elif self.material == 'steel':
            base *= 1.05
        elif self.material == 'titan':
            base *= 1.2
        if self.hammer_penalty:
            base *= 1.15
        # v0.9 (4-A): low-RPM curve — below 25% RPM, decay accelerates
        ratio = self.rpm / self.rpm_max
        if ratio < 0.25:
            base *= 1.0 + 0.4 * (1 - ratio / 0.25)   # up to ×1.4 at 0 rpm
        return base

    def effective_attack(self):
        mat = 1.0
        if self.material == 'wood':
            mat = 0.8
        elif self.material == 'titan':
            mat = 1.7   # 1.5→1.7: 3×1.7=5.1, 恰好一擊破竹筍(hp=5)
        elif self.material == 'steel':
            mat = 1.2
        base = (self.base_attack * mat) + self.weapon_attack_bonus
        # Crown core: low RPM bonus
        if self.core == 'crown':
            ratio = self.rpm / self.rpm_max
            if ratio < 0.30:
                bonus = 1.0 + 0.50 * (1 - ratio / 0.30)
                base *= bonus
        return base

    def effective_reach(self):
        return self.radius + self.weapon_reach

    def get_rebound_multiplier(self):
        """v1.8: 玩家被彈開的位移倍率，完全由自身裝備決定。"""
        # 衝刺膠帶衝刺中：免疫位移
        if self.accessory == 'dash_tape' and self.is_dashing:
            return 0.0
        mult = 1.0
        # 材質
        if self.material == 'wood':
            mult *= 1.1     # 輕巧，被彈略遠
        elif self.material == 'steel':
            mult *= 0.85    # 重量，被彈略近
        elif self.material == 'titan':
            mult *= 1.3     # 攻高換取更大位移
        # 配件
        if self.accessory == 'axis':
            mult *= 0.75    # 穩定軸心，大幅減少位移
        elif self.accessory == 'gear_ring':
            mult *= 0.85    # 咬合環抓地，略減位移
        # 核心
        if self.core == 'crown':
            ratio = self.rpm / max(1, self.rpm_max)
            if ratio < 0.30:
                mult *= 1.0 + 0.20 * (1 - ratio / 0.30)  # 低轉時最多 ×1.2
        # drive 的 recoil_dampener 在 take_hit 內另行處理
        return mult

    def rpm_spin_gain(self):
        if self.hammer_penalty:
            return RPM_PER_SPIN / 2.0  # v0.5: ÷3→÷2, 重鎚補速效率提升
        return RPM_PER_SPIN

    # ── update ────────────────────────────────────────────────────────────

    def update(self, dt, keys, particles=None):
        # Stun
        if self.stun_timer > 0:
            self.stun_timer -= dt
            self.x += self.vx * dt
            self.y += self.vy * dt
            # Friction
            self.vx *= max(0, 1 - 3.1 * dt)
            self.vy *= max(0, 1 - 3.1 * dt)
        elif self._track_boost_active:
            # 加速帶衝刺：鎖定速度，不受輸入/摩擦影響，讓牆壁彈射正常生效
            self.x += self.vx * dt
            self.y += self.vy * dt
        elif self.is_dashing:
            self.dash_timer -= dt
            self.x += self.dash_dx * dt
            self.y += self.dash_dy * dt
            if self.dash_timer <= 0:
                self.is_dashing = False
                self.invincible_timer = 0
        else:
            # Normal movement
            dx = dy = 0
            if keys[pygame.K_w] or keys[pygame.K_UP]:    dy -= 1
            if keys[pygame.K_s] or keys[pygame.K_DOWN]:  dy += 1
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:  dx -= 1
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx += 1

            moving = dx != 0 or dy != 0
            if moving:
                length = math.sqrt(dx*dx + dy*dy)
                _spd = self.speed
                target_vx = dx / length * _spd
                target_vy = dy / length * _spd
                # 混合：用 8.0/s 的速率趨近目標速度，保留彈開殘餘動能
                blend = min(1.0, 8.0 * dt)
                self.vx += (target_vx - self.vx) * blend
                self.vy += (target_vy - self.vy) * blend
                # Dash tape charge
                if self.accessory == 'dash_tape' and self.dash_cooldown <= 0:
                    self.dash_charge += dt
                    if self.dash_charge >= 2.5:  # v0.5: 3.0→2.5s charge
                        # Trigger dash
                        self.dash_charge = 0
                        self.dash_cooldown = 2.5  # v0.5: 3.0→2.5s cooldown
                        self.is_dashing = True
                        self.dash_timer = 200 / 600  # 200px at 600px/s
                        self.dash_dx = (dx / length) * 600
                        self.dash_dy = (dy / length) * 600
                        self.invincible_timer = 1.0
            else:
                self.vx *= max(0, 1 - 12 * dt)
                self.vy *= max(0, 1 - 12 * dt)
                if self.accessory == 'dash_tape':
                    self.dash_charge = max(0, self.dash_charge - dt * 2)

            self.x += self.vx * dt
            self.y += self.vy * dt

        # Dash cooldown
        if self.dash_cooldown > 0:
            self.dash_cooldown -= dt
        if self.invincible_timer > 0:
            self.invincible_timer -= dt

        # Clamp to play area with wall collision penalty
        new_x = max(PLAY_LEFT + self.radius, min(PLAY_RIGHT - self.radius, self.x))
        new_y = max(PLAY_TOP + self.radius, min(PLAY_BOTTOM - self.radius, self.y))
        wall_hit_x = (new_x != self.x)
        wall_hit_y = (new_y != self.y)
        self.x = new_x
        self.y = new_y

        if wall_hit_x: self.vx *= -1
        if wall_hit_y: self.vy *= -1
        if (wall_hit_x or wall_hit_y) and self.stun_timer <= 0 and self.invincible_timer <= 0:
            self.rpm -= 15
            self.rpm = max(0, self.rpm)
            self.stun_timer = 0.3
            self.hit_flash = 0.12
            # 牆壁碰撞立即解除加速帶 boost
            self._track_boost_active = False

        # v0.5: 反震阻尼碰後減傷計時
        if self._recoil_shield > 0:
            self._recoil_shield -= dt

        # Drive activation flash countdown
        if self._drive_flash_timer > 0:
            self._drive_flash_timer -= dt

        # RPM decay
        self.rpm -= self.effective_decay() * dt
        self.rpm = max(0, min(self.rpm_max, self.rpm))

        # Rotation
        ang_speed = (self.rpm / 1000) * 720  # deg/s
        self.angle = (self.angle + ang_speed * dt) % 360

        # Invincible flash
        if self.hit_flash > 0:
            self.hit_flash -= dt

    def take_hit(self, enemy_x, enemy_y, damage, attack_power,
                   weapon_only=False, no_knockback=False, recoil_result=None, no_stun=False):
        # 已在無敵幀或暈眩中 → 不再受傷
        if self.invincible_timer > 0 or self.stun_timer > 0:
            return
        # Shield core: 30% chance to negate
        if self.core == 'shield':
            import random
            if random.random() < 0.30:
                return
        # Gear ring: -15% reduction
        reduction = 1.0
        if self.accessory == 'gear_ring':
            reduction *= 0.85
        # Steel axis: -25% reduction
        if self.accessory == 'axis':
            reduction *= 0.75
        # v0.5: 反震阻尼碰後 0.3s 減傷 15%
        if self._recoil_shield > 0:
            reduction *= 0.85

        rpm_loss = damage * reduction
        self.rpm -= rpm_loss
        self._last_rpm_loss = rpm_loss  # v0.9 (4-B): for red damage numbers
        self.rpm = max(0, self.rpm)

        # Rebound direction
        dx = self.x - enemy_x
        dy = self.y - enemy_y
        dist = math.sqrt(dx*dx + dy*dy) or 1

        if recoil_result is not None:
            # 新系統：方向偏移由 calc_collision_recoil 統一計算
            off_deg = recoil_result.get('direction_offset_deg', 0.0)
            if off_deg != 0.0:
                cos_a = math.cos(math.radians(off_deg))
                sin_a = math.sin(math.radians(off_deg))
                dx, dy = dx * cos_a - dy * sin_a, dx * sin_a + dy * cos_a
                dist = math.sqrt(dx*dx + dy*dy) or 1
        elif self.core == 'chaos':
            # 舊路徑（未傳入 recoil_result 時保留，如竹子牆壁碰撞）
            import random as _rand
            chaos_angle = _rand.uniform(-math.pi / 12, math.pi / 12)
            cos_a = math.cos(chaos_angle); sin_a = math.sin(chaos_angle)
            dx, dy = dx * cos_a - dy * sin_a, dx * sin_a + dy * cos_a
            dist = math.sqrt(dx*dx + dy*dy) or 1

        if weapon_only:
            base_force = (8 + attack_power * 0.05) * 60
        else:
            base_force = (12 + attack_power * 0.1) * 60

        if recoil_result is not None:
            # 新系統：force 倍率已包含材質矩陣、裝備、速度等所有修正
            force = base_force * recoil_result['force']
            extra_stun = recoil_result.get('extra_stun', 0.0)
            if self.drive == 'recoil_dampener':
                # 力道已在 calc_collision_recoil 中套用 ×0.55，此處只觸發視覺效果
                self._recoil_shield = 0.3
                self._drive_flash_timer = 0.45
                self._drive_flash_label = '反震阻尼！'
        else:
            # 舊路徑：保留原始計算（供竹子牆/鐳射等未傳入 recoil_result 的呼叫）
            force = base_force * self.get_rebound_multiplier()
            extra_stun = 0.0
            if self.drive == 'recoil_dampener':
                force *= 0.55
                self._recoil_shield = 0.3
                self._drive_flash_timer = 0.45
                self._drive_flash_label = '反震阻尼！'

        if not no_knockback:
            self.vx = (dx / dist) * force
            self.vy = (dy / dist) * force
        if not no_stun:
            self.stun_timer = STUN_DURATION + extra_stun
        self.invincible_timer = 0.6
        self.hit_flash = 0.12

    def calc_collision_recoil(self, enemy, collision_type, relative_speed) -> dict:
        """計算碰撞後玩家被彈開的反作用力參數。

        Args:
            enemy: Enemy 物件（可含 material / weapon 屬性）
            collision_type: 'body' | 'weapon'
            relative_speed: 碰撞前兩者速度差（px/s）

        Returns:
            {'force': float, 'direction_offset_deg': float, 'extra_stun': float}
            force 為乘上 base_force 的純倍率。
        """
        import random as _rnd

        # 1. 材質對材質矩陣查表
        p_mat = self.material
        e_mat = getattr(enemy, 'material', None)
        force = MATERIAL_RECOIL_MATRIX.get(
            (p_mat, e_mat),
            MATERIAL_RECOIL_MATRIX.get((None, e_mat), 1.0)
        )

        direction_offset_deg = 0.0
        extra_stun = 0.0

        # 2. 配件 / 驅動器修正
        if self.drive == 'recoil_dampener':
            force *= 0.55   # 覆蓋式：不與配件疊加
        else:
            if self.accessory == 'axis':
                force *= 0.75
            elif self.accessory == 'gear_ring':
                force *= 0.85

        # 3. 王冠核心：低轉時彈得更遠（高風險設計）
        if self.core == 'crown':
            rpm_ratio = self.rpm / max(1, self.rpm_max)
            if rpm_ratio < 0.30:
                force *= 1.0 + 0.2 * (1.0 - rpm_ratio / 0.30)

        # 4. 混沌核心：方向隨機偏移 ±15°
        if self.core == 'chaos':
            direction_offset_deg += _rnd.uniform(-15.0, 15.0)

        # 5. 碰撞類型：武器命中反作用力較輕
        if collision_type == 'weapon':
            force *= RECOIL_WEAPON_HIT_MULT

        # 6. 相對速度縮放：慢速輕觸不暴衝，高速衝撞彈更遠
        speed_factor = max(RECOIL_SPEED_MIN,
                           min(RECOIL_SPEED_MAX, relative_speed / RECOIL_SPEED_DIV))
        force *= speed_factor

        # 7. 敵人武器修正
        e_weapon = getattr(enemy, 'weapon', None)
        if e_weapon == 'hammer':
            force *= RECOIL_ENEMY_HAMMER_MULT
        elif e_weapon == 'scythe':
            direction_offset_deg += RECOIL_ENEMY_SCYTHE_DEG
        elif e_weapon == 'staff':
            force *= RECOIL_ENEMY_STAFF_MULT
            extra_stun += RECOIL_ENEMY_STAFF_STUN

        return {
            'force': force,
            'direction_offset_deg': direction_offset_deg,
            'extra_stun': extra_stun,
        }

    def add_rpm(self, amount):
        self.rpm = min(self.rpm_max, self.rpm + amount)

    # ── drawing ───────────────────────────────────────────────────────────

    def draw(self, surface):
        cx, cy = int(self.x), int(self.y)
        r = self.radius
        angle_rad = math.radians(self.angle)

        # Material color
        main_color = self.get_material_color()

        # Invincible flash during dash
        if self.invincible_timer > 0 and int(self.invincible_timer * 10) % 2 == 0:
            main_color = ASH_WHITE

        # Main disc
        pygame.draw.circle(surface, main_color, (cx, cy), r)

        # Material-specific details
        if self.material == 'wood':
            self._draw_wood(surface, cx, cy, r, angle_rad)
        elif self.material == 'steel':
            self._draw_steel(surface, cx, cy, r, angle_rad)
        elif self.material == 'titan':
            self._draw_titan(surface, cx, cy, r, angle_rad)
        else:
            # Default: spin blue with simple lines
            for i in range(3):
                a = angle_rad + i * math.pi * 2 / 3
                x1 = cx + int(r * 0.3 * math.cos(a))
                y1 = cy + int(r * 0.3 * math.sin(a))
                x2 = cx + int(r * 0.85 * math.cos(a))
                y2 = cy + int(r * 0.85 * math.sin(a))
                pygame.draw.line(surface, SPIN_BLUE_GLOW, (x1, y1), (x2, y2), 2)

        # Weapon
        if self.weapon:
            self._draw_weapon(surface, cx, cy, angle_rad)

        # Accessory
        if self.accessory == 'axis':
            pygame.draw.circle(surface, STEEL_LIGHT, (cx, cy), 5)
            pygame.draw.circle(surface, STEEL_CHROME, (cx, cy), 3)
        elif self.accessory == 'gear_ring':
            du.draw_gear(surface, WOOD_WARM, cx, cy, r + 10, r + 5, 12, angle_rad)
        elif self.accessory == 'dash_tape':
            # Tape label in center
            pygame.draw.rect(surface, VOID_BLACK, (cx-8, cy-5, 16, 10), border_radius=2)
            pygame.draw.rect(surface, SPIN_BLUE, (cx-6, cy-3, 5, 6))
            pygame.draw.rect(surface, ENERGY_GOLD, (cx+1, cy-3, 5, 6))
            # Glow if charging
            if self.dash_charge > 0 and self.accessory == 'dash_tape':
                alpha = int(80 + 80 * (self.dash_charge / 3.0))
                glow = pygame.Surface((r*4, r*4), pygame.SRCALPHA)
                pygame.draw.circle(glow, (int(SPIN_BLUE_GLOW[0]), int(SPIN_BLUE_GLOW[1]), int(SPIN_BLUE_GLOW[2]), int(alpha)), (r*2, r*2), r*2)
                surface.blit(glow, (cx - r*2, cy - r*2), special_flags=pygame.BLEND_RGBA_ADD)

        # Core
        if self.core == 'chaos':
            for i in range(4):
                a = angle_rad + i * math.pi / 2
                x1 = cx + int(4 * math.cos(a))
                y1 = cy + int(4 * math.sin(a))
                x2 = cx + int(r * 0.6 * math.cos(a + 0.3))
                y2 = cy + int(r * 0.6 * math.sin(a + 0.3))
                pygame.draw.line(surface, (128, 96, 255), (x1, y1), (x2, y2), 1)
        elif self.core == 'shield':
            pygame.draw.circle(surface, ASH_WHITE, (cx, cy), r, 1)
        elif self.core == 'crown':
            for i in range(6):
                a = angle_rad + i * math.pi / 3
                px = cx + int((r - 2) * math.cos(a))
                py = cy + int((r - 2) * math.sin(a))
                pygame.draw.circle(surface, (176, 168, 152), (px, py), 2)

        # Outline
        outline_color = STEEL_LIGHT
        if self.hit_flash > 0:
            outline_color = DANGER_RED
        pygame.draw.circle(surface, outline_color, (cx, cy), r, 2)

        # ── v1.7: Drive ability visual indicators ────────────────────────
        if self.drive == 'recoil_dampener':
            # Active shield glow (0.3s window after taking a hit)
            if self._recoil_shield > 0:
                pulse  = self._recoil_shield / 0.3   # 1.0 → 0.0
                alpha  = int(130 * pulse)
                glow   = pygame.Surface(((r + 10) * 2, (r + 10) * 2), pygame.SRCALPHA)
                pygame.draw.circle(glow, (80, 240, 40, alpha),
                                   (r + 10, r + 10), r + 7)
                surface.blit(glow, (cx - r - 10, cy - r - 10))
                pygame.draw.circle(surface, (80, 240, 40), (cx, cy), r + 2, 2)
            else:
                # Steady thin green ring — "ready" indicator
                pygame.draw.circle(surface, (60, 180, 30), (cx, cy), r + 3, 1)

        elif self.drive == 'shockwave':
            # 4 outward tick marks that rotate with the beyblade
            for i in range(4):
                a   = angle_rad + i * math.pi / 2
                ix1 = cx + int((r + 2) * math.cos(a))
                iy1 = cy + int((r + 2) * math.sin(a))
                ix2 = cx + int((r + 7) * math.cos(a))
                iy2 = cy + int((r + 7) * math.sin(a))
                pygame.draw.line(surface, (100, 170, 255), (ix1, iy1), (ix2, iy2), 2)

        elif self.drive == 'splinter_echo':
            # 3 small gold dots orbiting faster than the body
            for i in range(3):
                a  = angle_rad * 1.8 + i * math.pi * 2 / 3
                ox = cx + int((r + 5) * math.cos(a))
                oy = cy + int((r + 5) * math.sin(a))
                pygame.draw.circle(surface, (220, 200, 40), (ox, oy), 2)

        # Center dot
        pygame.draw.circle(surface, ASH_WHITE, (cx, cy), 3)

    def _draw_wood(self, surface, cx, cy, r, angle_rad):
        pygame.draw.circle(surface, WOOD_WARM, (cx, cy), r)
        for i in range(4):
            a = angle_rad + i * math.pi / 4
            x1 = cx + int(r * 0.2 * math.cos(a))
            y1 = cy + int(r * 0.2 * math.sin(a))
            x2 = cx + int(r * 0.85 * math.cos(a))
            y2 = cy + int(r * 0.85 * math.sin(a))
            pygame.draw.line(surface, WOOD_GRAIN, (x1, y1), (x2, y2), 2)
        # Notches
        for i in range(3):
            a = angle_rad + i * math.pi * 2 / 3
            nx = cx + int(r * 0.9 * math.cos(a))
            ny = cy + int(r * 0.9 * math.sin(a))
            pygame.draw.circle(surface, VOID_BLACK, (nx, ny), 3)

    def _draw_steel(self, surface, cx, cy, r, angle_rad):
        pygame.draw.circle(surface, STEEL_CHROME, (cx, cy), r)
        for i in range(8):
            a = angle_rad + i * math.pi / 4
            x1 = cx + int(r * 0.1 * math.cos(a))
            y1 = cy + int(r * 0.1 * math.sin(a))
            x2 = cx + int(r * 0.9 * math.cos(a))
            y2 = cy + int(r * 0.9 * math.sin(a))
            s = pygame.Surface((1, int(math.sqrt((x2-x1)**2+(y2-y1)**2))), pygame.SRCALPHA)
            s.fill((int(STEEL_SHINE[0]), int(STEEL_SHINE[1]), int(STEEL_SHINE[2]), int(80)))
            pygame.draw.line(surface, (int(STEEL_SHINE[0]), int(STEEL_SHINE[1]), int(STEEL_SHINE[2]), int(60)), (x1, y1), (x2, y2), 1)

    def _draw_titan(self, surface, cx, cy, r, angle_rad):
        pygame.draw.circle(surface, TITAN_DARK, (cx, cy), r)
        pygame.draw.circle(surface, TITAN_BLUE, (cx, cy), r, 2)
        for i in range(6):
            a = angle_rad + i * math.pi / 3
            x1 = cx + int(r * 0.15 * math.cos(a))
            y1 = cy + int(r * 0.15 * math.sin(a))
            x2 = cx + int(r * 0.80 * math.cos(a))
            y2 = cy + int(r * 0.80 * math.sin(a))
            pygame.draw.line(surface, TITAN_BLUE, (x1, y1), (x2, y2), 1)

    def _draw_weapon(self, surface, cx, cy, angle_rad):
        if self.weapon == 'scythe':
            for i in range(2):
                a = angle_rad + i * math.pi
                # Scythe handle
                hx = cx + int((self.radius + 8) * math.cos(a))
                hy = cy + int((self.radius + 8) * math.sin(a))
                ex = cx + int((self.radius + 20) * math.cos(a))
                ey = cy + int((self.radius + 20) * math.sin(a))
                pygame.draw.line(surface, STEEL_CHROME, (hx, hy), (ex, ey), 3)
                # Blade arc
                bx = cx + int((self.radius + 22) * math.cos(a + 0.5))
                by = cy + int((self.radius + 22) * math.sin(a + 0.5))
                pygame.draw.line(surface, ASH_WHITE, (ex, ey), (bx, by), 2)

        elif self.weapon == 'staff':
            for i in range(4):
                a = angle_rad + i * math.pi / 2
                x1 = cx + int(self.radius * math.cos(a))
                y1 = cy + int(self.radius * math.sin(a))
                x2 = cx + int((self.radius + 28) * math.cos(a))
                y2 = cy + int((self.radius + 28) * math.sin(a))
                pygame.draw.line(surface, ENERGY_GOLD, (x1, y1), (x2, y2), 4)
                pygame.draw.circle(surface, ENERGY_GOLD, (x2, y2), 4)

        elif self.weapon == 'hammer':
            a = angle_rad
            hx = cx + int((self.radius + 36) * math.cos(a))
            hy = cy + int((self.radius + 36) * math.sin(a))
            # Handle
            pygame.draw.line(surface, (80, 60, 40), (cx, cy), (hx, hy), 4)
            # Head
            head_pts = []
            for da, dr in [(-0.3, 14), (0.3, 14), (0.3, 22), (-0.3, 22)]:
                head_pts.append((
                    cx + int((self.radius + 28 + dr * 0.5) * math.cos(a + da)),
                    cy + int((self.radius + 28 + dr * 0.5) * math.sin(a + da))
                ))
            if len(head_pts) == 4:
                pygame.draw.polygon(surface, (58, 58, 58), head_pts)
                pygame.draw.polygon(surface, STEEL_LIGHT, head_pts, 1)

    def get_collision_radius(self):
        return self.effective_reach()

    def render_snapshot(self):
        """Return a snapshot surface for afterimages."""
        size = (self.radius * 2 + 80) * 2
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        # Draw simplified version centered
        pygame.draw.circle(surf, (int(self.get_material_color()[0]), int(self.get_material_color()[1]), int(self.get_material_color()[2]), 180),
                           (size//2, size//2), self.radius)
        return surf
