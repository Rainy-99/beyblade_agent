# enemies.py
import pygame
import math
import random
from colors import *
from constants import *
import draw_utils as du

class Enemy:
    """Base enemy class."""
    def __init__(self, x, y, hp, attack, exp, radius=12):
        self.x = float(x)
        self.y = float(y)
        self.hp = hp
        self.max_hp = hp
        self.attack = attack  # RPM damage
        self.exp = exp
        self.radius = radius
        self.alive = True
        self.vx = 0.0
        self.vy = 0.0
        self.angle = 0.0
        self.mass = 1.0
        self._boost_cooldown = 0.0  # 加速帶冷卻計時器
        # v1.8: 擊退抗性（越高越難被彈飛）
        self.knockback_resistance = 1.0

    def take_damage(self, dmg):
        self.hp -= dmg
        if self.hp <= 0:
            self.alive = False
            return True
        return False

    def on_knockback(self, push_vx, push_vy):
        """v1.8: 被玩家撞飛時呼叫，子類別可覆蓋以實作特殊行為。"""
        self.vx += push_vx
        self.vy += push_vy

    def update(self, dt, player_x, player_y):
        self.x += self.vx * dt
        self.y += self.vy * dt
        # Clamp to play area (unless indestructible)
        self.x = max(PLAY_LEFT + self.radius, min(PLAY_RIGHT - self.radius, self.x))
        self.y = max(PLAY_TOP + self.radius, min(PLAY_BOTTOM - self.radius, self.y))

    def collides_with(self, px, py, pr):
        dx = self.x - px
        dy = self.y - py
        return math.sqrt(dx*dx + dy*dy) < (self.radius + pr)

    def draw_hp_bar(self, surface):
        if self.hp >= self.max_hp:
            return
        r = self.radius
        bar_w = max(20, int(r * 1.8))
        bar_h = 4
        bx = int(self.x) - bar_w // 2
        by = int(self.y) - r - 10
        hp_ratio = max(0.0, self.hp / self.max_hp)
        pygame.draw.rect(surface, (60, 20, 20), (bx, by, bar_w, bar_h))
        if hp_ratio > 0.5:
            fill_color = (64, 200, 112)
        elif hp_ratio > 0.25:
            fill_color = (232, 120, 32)
        else:
            fill_color = (232, 64, 64)
        fill_w = int(bar_w * hp_ratio)
        if fill_w > 0:
            pygame.draw.rect(surface, fill_color, (bx, by, fill_w, bar_h))
        pygame.draw.rect(surface, (74, 81, 104), (bx, by, bar_w, bar_h), 1)

    def draw(self, surface):
        pygame.draw.circle(surface, DANGER_RED, (int(self.x), int(self.y)), self.radius)


# ── Level 1 Enemies ──────────────────────────────────────────────────────

class WoodChip(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, hp=3, attack=10, exp=3, radius=18)
        self.knockback_resistance = 0.7   # v1.8: 輕小，容易彈飛
        angle = random.uniform(0, math.pi * 2)
        self.vx = math.cos(angle) * 40
        self.vy = math.sin(angle) * 40
        self.angle = 0.0
        self.dir_timer = random.uniform(1, 3)
        self.material = 'wood'  # v0.11: 木头材料标记
        self.weapon = None      # v0.11: 可能装上的武器（None, 'scythe', 'staff', 'hammer'）

    def update(self, dt, px, py):
        self.angle = (self.angle + 60 * dt) % 360
        
        # 1. Apply existing velocity (knockback carries over from last frame)
        self.x += self.vx * dt
        self.y += self.vy * dt
        
        # 2. Apply friction to bleed off knockback
        self.vx *= max(0, 1 - 4.0 * dt)
        self.vy *= max(0, 1 - 4.0 * dt)
        
        # 3. Steering: compute desired velocity
        dx = px - self.x
        dy = py - self.y
        dist = math.sqrt(dx*dx + dy*dy) or 1
        target_vx = dx / dist * 90
        target_vy = dy / dist * 90
        
        # 4. Blend toward target (gradually steer, don't snap instantly)
        blend = min(1.0, 8.0 * dt)
        self.vx += (target_vx - self.vx) * blend
        self.vy += (target_vy - self.vy) * blend
        
        # Boundary bouncing
        if self.x < PLAY_LEFT + self.radius: self.x = PLAY_LEFT+self.radius; self.vx *= -1
        if self.x > PLAY_RIGHT - self.radius: self.x = PLAY_RIGHT-self.radius; self.vx *= -1
        if self.y < PLAY_TOP + self.radius: self.y = PLAY_TOP+self.radius; self.vy *= -1
        if self.y > PLAY_BOTTOM - self.radius: self.y = PLAY_BOTTOM-self.radius; self.vy *= -1

    def draw(self, surface):
        cx, cy = int(self.x), int(self.y)
        pts = []
        for i in range(4):
            a = math.radians(self.angle + i * 60)
            r = self.radius if i % 2 == 0 else self.radius * 0.75
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        pygame.draw.polygon(surface, WOOD_WARM, pts)
        pygame.draw.polygon(surface, WOOD_GRAIN, pts, 2)
        self.draw_hp_bar(surface)


class IronNail(Enemy):
    def __init__(self, x, y, tx, ty):
        super().__init__(x, y, hp=5, attack=30, exp=5, radius=14)
        self.knockback_resistance = 1.0   # v1.8: 標準抗性
        dx = tx - x; dy = ty - y
        dist = math.sqrt(dx*dx + dy*dy) or 1
        self.vx = dx / dist * 40
        self.vy = dy / dist * 40
        self.moving = True
        self.angle = math.degrees(math.atan2(dy, dx))
        # 記錄目標位置，到達後停止
        self.tx = float(tx)
        self.ty = float(ty)
        self._passed_target = False

    def update(self, dt, px, py):
        if not self.moving:
            return

        # 0.96 per frame → dt-based: friction = 0.96^(dt*60)
        friction = 0.96 ** (dt * 60)
        self.vx *= friction
        self.vy *= friction

        self.x += self.vx * dt * 60
        self.y += self.vy * dt * 60

        speed = math.sqrt(self.vx**2 + self.vy**2)

        # Check passed target
        dx_now = self.tx - self.x
        dy_now = self.ty - self.y
        if dx_now * self.vx + dy_now * self.vy < 0:
            self._passed_target = True

        # Stop only when nearly stationary AND past target
        if speed < 0.3 and self._passed_target:
            self.moving = False
            self.vx = self.vy = 0
            return

        # Boundary handling
        if self.x < PLAY_LEFT + self.radius:
            self.x = PLAY_LEFT + self.radius
            if self._passed_target: self.moving = False
            else: self.vx = abs(self.vx)
        if self.x > PLAY_RIGHT - self.radius:
            self.x = PLAY_RIGHT - self.radius
            if self._passed_target: self.moving = False
            else: self.vx = -abs(self.vx)
        if self.y < PLAY_TOP + self.radius:
            self.y = PLAY_TOP + self.radius
            if self._passed_target: self.moving = False
            else: self.vy = abs(self.vy)
        if self.y > PLAY_BOTTOM - self.radius:
            self.y = PLAY_BOTTOM - self.radius
            if self._passed_target: self.moving = False
            else: self.vy = -abs(self.vy)

    def draw(self, surface):
        cx, cy = int(self.x), int(self.y)
        a = math.radians(self.angle)
        x1 = cx - int(12 * math.cos(a)); y1 = cy - int(12 * math.sin(a))
        x2 = cx + int(12 * math.cos(a)); y2 = cy + int(12 * math.sin(a))
        pygame.draw.line(surface, STEEL_CHROME, (x1, y1), (x2, y2), 5)
        pygame.draw.circle(surface, ASH_WHITE, (x2, y2), 3)
        if self.moving:
            for i in range(4):
                offset = (i - 1.5) * 4
                sx = cx + int(offset * math.sin(a)) - int(16 * math.cos(a))
                sy = cy - int(offset * math.cos(a)) - int(16 * math.sin(a))
                ex = sx - int(24 * math.cos(a))
                ey = sy - int(24 * math.sin(a))
                # pygame.draw.line(surface, STEEL_LIGHT, (sx, sy), (ex, ey), 1)
        self.draw_hp_bar(surface)
class RollingStone(Enemy):
    # ── v0.5 重設計：從場外生成、直撲玩家、1.5 倍速 ──────────────────
    ENTRY_SPEED    = 45.0   # 入場衝擊速度（原 30 × 1.5）
    MIN_ROLL_SPEED = 12.0   # 最低滾動速度（原 8 × 1.5）

    def __init__(self, x, y, target_x=None, target_y=None):
        super().__init__(x, y, hp=14, attack=40, exp=12, radius=28)
        # 若提供玩家座標，直線朝玩家衝入；否則隨機方向（相容舊呼叫）
        if target_x is not None and target_y is not None:
            dx = target_x - x
            dy = target_y - y
            dist = math.sqrt(dx*dx + dy*dy) or 1
            self.vx = dx / dist * self.ENTRY_SPEED
            self.vy = dy / dist * self.ENTRY_SPEED
        else:
            angle = random.uniform(0, math.pi * 2)
            self.vx = math.cos(angle) * self.ENTRY_SPEED
            self.vy = math.sin(angle) * self.ENTRY_SPEED
        self.angle   = 0.0
        self._inside = False   # 是否已進入場地（場外不做 wall-bounce）
        self.knockback_resistance = 2.5   # v1.8: 重量球，難以彈飛

    def update(self, dt, px, py):
        # 旋轉角速度隨速度增大而加快
        speed_now = math.sqrt(self.vx**2 + self.vy**2)
        self.angle = (self.angle + (speed_now / self.ENTRY_SPEED) * 80 * dt) % 360

        # 1. 移動
        self.x += self.vx * dt
        self.y += self.vy * dt

        # 2. 摩擦衰減（僅在場地內才衰減，保持入場衝力）
        if self._inside:
            self.vx *= max(0, 1 - 3.0 * dt)
            self.vy *= max(0, 1 - 3.0 * dt)

        # 3. 偵測是否進入場地
        in_bounds = (PLAY_LEFT + self.radius < self.x < PLAY_RIGHT  - self.radius and
                     PLAY_TOP  + self.radius < self.y < PLAY_BOTTOM - self.radius)
        if in_bounds:
            self._inside = True

        # 4. 場地內：維持最低滾速 + 彈牆
        if self._inside:
            speed = math.sqrt(self.vx**2 + self.vy**2)
            if speed < self.MIN_ROLL_SPEED:
                if speed > 0.1:
                    self.vx = (self.vx / speed) * self.MIN_ROLL_SPEED
                    self.vy = (self.vy / speed) * self.MIN_ROLL_SPEED
                else:
                    angle = random.uniform(0, math.pi * 2)
                    self.vx = math.cos(angle) * self.MIN_ROLL_SPEED
                    self.vy = math.sin(angle) * self.MIN_ROLL_SPEED

            if self.x < PLAY_LEFT  + self.radius: self.x = PLAY_LEFT  + self.radius; self.vx =  abs(self.vx)
            if self.x > PLAY_RIGHT - self.radius: self.x = PLAY_RIGHT - self.radius; self.vx = -abs(self.vx)
            if self.y < PLAY_TOP   + self.radius: self.y = PLAY_TOP   + self.radius; self.vy =  abs(self.vy)
            if self.y > PLAY_BOTTOM- self.radius: self.y = PLAY_BOTTOM- self.radius; self.vy = -abs(self.vy)

    def draw(self, surface):
        cx, cy = int(self.x), int(self.y)
        r = self.radius
        pygame.draw.circle(surface, (106, 90, 74), (cx, cy), r)
        # Cracks
        for i in range(3):
            a = math.radians(self.angle + i * 120)
            x1 = cx + int(r * 0.3 * math.cos(a))
            y1 = cy + int(r * 0.3 * math.sin(a))
            x2 = cx + int(r * 0.85 * math.cos(a + 0.5))
            y2 = cy + int(r * 0.85 * math.sin(a + 0.5))
            pygame.draw.line(surface, (50, 40, 30), (x1, y1), (x2, y2), 2)
        pygame.draw.circle(surface, (80, 70, 55), (cx, cy), r, 2)
        self.draw_hp_bar(surface)


# ── Level 2 Enemies ──────────────────────────────────────────────────────

class BambooShoot(Enemy):
    def __init__(self, x, y, slot_id=None):
        super().__init__(x, y, hp=5, attack=15, exp=5, radius=8)
        self.slot_id = slot_id  # kept for any remaining references; unused
        self.grow_timer = 10.0
        self.hardened = False
        self.grow_anim = 0.0
        self.mass = 1.0
        self.vx = self.vy = 0

    def update(self, dt, px, py):
        if not self.hardened:
            self.grow_timer -= dt
            if self.grow_timer <= 0:
                self.hardened = True
                self.hp = 99999
                self.max_hp = 99999
                self.attack = 45          # Phase 2 ATK
                self.exp = 0
                self.radius = 10
                self.mass = 999.0
                self.grow_anim = 0.0
        else:
            self.grow_anim = min(1.0, self.grow_anim + dt / 0.5)

    def get_pillar_rect(self):
        """v0.10: return full pillar bounding rect for hardened bamboo collision.
        Returns (left, top, width, height) or None if not hardened.
        """
        if not self.hardened:
            return None
        t = self.grow_anim
        h = max(1, int(60 * t)) if t > 0 else 60
        cx, cy = int(self.x), int(self.y)
        return (cx - 9, cy - h, 18, h)   # 9px half-width, full height

    def take_damage(self, dmg):
        if self.hardened:
            return False
        return super().take_damage(dmg)

    def draw(self, surface):
        if not self.alive:
            return
        cx, cy = int(self.x), int(self.y)
        if not self.hardened:
            t = self.grow_timer / 10.0
            if t > 0.6:
                color = (130, 153, 76)
            elif t > 0.3:
                color = (130, 153, 76)
            else:
                import time as _time
                color = DANGER_RED if int(_time.time() * 2.5) % 2 == 0 else (70, 120, 50)
            height = 8 + int((1 - t) * 12)
            pygame.draw.ellipse(surface, color, (cx - 8, cy - height, 16, height * 2))
            if t > 0:
                ring_color = DANGER_RED if t < 0.3 else ASH_WHITE
                ring_surf = pygame.Surface((24, 24), pygame.SRCALPHA)
                pygame.draw.arc(ring_surf,
                                (int(ring_color[0]), int(ring_color[1]),
                                 int(ring_color[2]), 200),
                                (0, 0, 24, 24), 0, math.pi * 2 * t, 3)
                surface.blit(ring_surf, (cx - 12, cy - height - 14))
            self.draw_hp_bar(surface)
        else:
            t = self.grow_anim
            h = max(1, int(60 * t)) if t > 0 else 60
            pygame.draw.rect(surface, (42, 74, 40), (cx - 7, cy - h, 14, h))

            # Joints
            for seg in range(3):
                ny = cy - int(h * (seg + 1) / 3)
                if ny >= cy - h:
                    pygame.draw.rect(surface, (28, 50, 26), (cx - 8, ny - 2, 16, 4))

            if t > 0.8:
                pygame.draw.ellipse(surface, (130, 153, 76),
                                    (cx - 10, cy - h - 8, 20, 10))


# ── Level 3 Enemies ──────────────────────────────────────────────────────

class Screw(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, hp=22, attack=22, exp=3, radius=14)
        self.knockback_resistance = 0.6   # v1.8: 小巧，容易被彈偏
        angle = random.uniform(0, math.pi * 2)
        self.vx = math.cos(angle) * 170
        self.vy = math.sin(angle) * 170
        self.dir_timer = random.uniform(0.5, 1.5)
        self.angle = 0.0
        self._knock_timer = 0.0   # v0.12: 被彈飛後暫停轉向

    def update(self, dt, px, py):
        # 1. Apply existing velocity (knockback carries over from last frame)
        self.x += self.vx * dt
        self.y += self.vy * dt

        # 2. Apply friction - lighter during knockback so enemy actually flies
        if self._knock_timer > 0:
            self._knock_timer -= dt
            self.vx *= max(0, 1 - 1.5 * dt)
            self.vy *= max(0, 1 - 1.5 * dt)
        else:
            self.vx *= max(0, 1 - 4.0 * dt)
            self.vy *= max(0, 1 - 4.0 * dt)
            # 3. Steering: compute desired velocity
            dx = px - self.x
            dy = py - self.y
            dist = math.sqrt(dx*dx + dy*dy) or 1
            target_vx = dx / dist * 170
            target_vy = dy / dist * 170

            # 4. Blend toward target (gradually steer, don't snap instantly)
            blend = min(1.0, 3.0 * dt)
            self.vx += (target_vx - self.vx) * blend
            self.vy += (target_vy - self.vy) * blend

        self.angle = (self.angle + 360 * dt) % 360

        # Boundary bouncing
        if self.x < PLAY_LEFT + self.radius: self.x = PLAY_LEFT+self.radius; self.vx *= -1
        if self.x > PLAY_RIGHT - self.radius: self.x = PLAY_RIGHT-self.radius; self.vx *= -1
        if self.y < PLAY_TOP + self.radius: self.y = PLAY_TOP+self.radius; self.vy *= -1
        if self.y > PLAY_BOTTOM - self.radius: self.y = PLAY_BOTTOM-self.radius; self.vy *= -1

    def on_knockback(self, push_vx, push_vy):
        """v0.12: 被撞飛時暫停轉向，讓擊退效果實際生效。"""
        self.vx += push_vx
        self.vy += push_vy
        self._knock_timer = 0.55  # 0.55秒內不再強制轉向

    def draw(self, surface):
        cx, cy = int(self.x), int(self.y)
        pygame.draw.circle(surface, STEEL_CHROME, (cx, cy), self.radius)
        # Cross slot
        a = math.radians(self.angle)
        for da in [0, math.pi/2]:
            x1 = cx + int(self.radius * 0.8 * math.cos(a + da))
            y1 = cy + int(self.radius * 0.8 * math.sin(a + da))
            x2 = cx - int(self.radius * 0.8 * math.cos(a + da))
            y2 = cy - int(self.radius * 0.8 * math.sin(a + da))
            pygame.draw.line(surface, STEEL_DARK, (x1, y1), (x2, y2), 2)
        self.draw_hp_bar(surface)


class Gear(Enemy):
    def __init__(self, x, y, size=1):
        # size: 1=small, 2=medium, 3=large
        sizes = [(20, 28, 55, 4, 8), (32, 55, 112, 8, 12), (44, 90, 165, 14, 16)]
        r, hp, atk, exp, teeth = sizes[size - 1]
        speed = [80, 60, 40][size - 1]
        super().__init__(x, y, hp=hp, attack=atk, exp=exp, radius=r)
        # v1.8: 體型越大越難彈飛
        self.knockback_resistance = [0.9, 1.5, 2.8][size - 1]
        self._near_merge = False   # v0.9 (3-B): flagged by level_manager
        self.size = size
        self.teeth = teeth
        self.speed = speed
        self.angle = 0.0
        self._knock_timer = 0.0   # v0.12: 被彈飛後暫停轉向

    def update(self, dt, px, py):
        # 1. Apply existing velocity (knockback carries over)
        self.x += self.vx * dt
        self.y += self.vy * dt

        # 2. Apply friction - lighter during knockback so enemy actually flies
        if self._knock_timer > 0:
            self._knock_timer -= dt
            self.vx *= max(0, 1 - 1.5 * dt)
            self.vy *= max(0, 1 - 1.5 * dt)
        else:
            self.vx *= max(0, 1 - 4.0 * dt)
            self.vy *= max(0, 1 - 4.0 * dt)
            # 3. Steering: compute desired velocity
            dx = px - self.x
            dy = py - self.y
            dist = math.sqrt(dx*dx + dy*dy) or 1
            target_vx = dx / dist * self.speed
            target_vy = dy / dist * self.speed

            # 4. Blend toward target (gradually steer, don't snap instantly)
            blend = min(1.0, 3.0 * dt)
            self.vx += (target_vx - self.vx) * blend
            self.vy += (target_vy - self.vy) * blend

        self.x = max(PLAY_LEFT+self.radius, min(PLAY_RIGHT-self.radius, self.x))
        self.y = max(PLAY_TOP+self.radius, min(PLAY_BOTTOM-self.radius, self.y))
        self.angle = (self.angle + 120 * dt) % 360

    def on_knockback(self, push_vx, push_vy):
        """v0.12: 被撞飛時暫停轉向，讓擊退效果實際生效。"""
        self.vx += push_vx
        self.vy += push_vy
        self._knock_timer = 0.55

    def draw(self, surface):
        import time as _t
        cx, cy = int(self.x), int(self.y)
        r = self.radius
        color = (90, 64, 40)
        # v0.9 (3-B): magnetic merge glow
        if self._near_merge:
            pulse = 0.5 + 0.5 * math.sin(_t.time() * 10)
            g = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
            pygame.draw.circle(g, (255, 200, 50, int(70 * pulse)), (r*2, r*2), r + 10)
            surface.blit(g, (cx - r*2, cy - r*2))
        if self.size == 3:
            pygame.draw.circle(surface, (int(WARN_ORANGE[0]), int(WARN_ORANGE[1]), int(WARN_ORANGE[2]), int(80)), (cx, cy), r + 4)
        du.draw_gear(surface, color, cx, cy, r + 4, r, self.teeth, math.radians(self.angle))
        pygame.draw.circle(surface, (80, 55, 30), (cx, cy), r - 2)
        pygame.draw.circle(surface, STEEL_LIGHT, (cx, cy), 4)
        self.draw_hp_bar(surface)


class Sawblade(Enemy):
    """
    蓄力型鋸刃：每次「主動接觸」玩家累積一格能量（共3格），
    蓄滿後等待 0.5s 預警，再以 500px/s 高速衝刺。
    """
    def __init__(self, x, y):
        super().__init__(x, y, hp=50, attack=130, exp=12, radius=28)
        self.charge = 0           # 0-3，蓄力格數
        self.dashing = False
        self.dash_timer = 0.0
        self.dash_vx = 0.0
        self.dash_vy = 0.0
        self.pre_dash = 0.0       # 預警倒數
        self.angle = 0.0
        # 接觸冷卻：避免單次接觸重複計數
        self.contact_cooldown = 0.0
        self.knockback_resistance = 1.2   # v1.8: 中等抗性
        self._knock_timer = 0.0   # v0.12: 被彈飛後滑行，不追蹤玩家

    def update(self, dt, px, py):
        self.angle = (self.angle + 240 * dt) % 360

        if self.contact_cooldown > 0:
            self.contact_cooldown -= dt

        if self._knock_timer > 0:
            # v0.12: 被撞飛狀態：依慣性滑行，不追蹤玩家
            self._knock_timer -= dt
            self.x += self.vx * dt
            self.y += self.vy * dt
            self.vx *= max(0, 1 - 1.5 * dt)
            self.vy *= max(0, 1 - 1.5 * dt)
        elif self.dashing:
            self.dash_timer -= dt
            self.x += self.dash_vx * dt
            self.y += self.dash_vy * dt
            if self.dash_timer <= 0:
                self.dashing = False
                self.charge = 0
                self.dash_vx = self.dash_vy = 0
        elif self.pre_dash > 0:
            self.pre_dash -= dt
            if self.pre_dash <= 0:
                dx = px - self.x; dy = py - self.y
                dist = math.sqrt(dx*dx + dy*dy) or 1
                self.dash_vx = dx / dist * 500
                self.dash_vy = dy / dist * 500
                self.dashing = True
                self.dash_timer = 0.55
        else:
            # 追蹤玩家：175px/s，能形成壓迫但玩家仍可閃避
            dx = px - self.x; dy = py - self.y
            dist = math.sqrt(dx*dx + dy*dy) or 1
            self.vx = dx / dist * 175
            self.vy = dy / dist * 175
            self.x += self.vx * dt
            self.y += self.vy * dt

            # 蓄力判定：接近 95px 即計數（不需要實際碰撞）
            touch_dist = 95
            if dist < touch_dist and self.contact_cooldown <= 0:
                self.charge = min(2, self.charge + 1)
                self.contact_cooldown = 0.55     # 兩次蓄力最短間隔
                if self.charge >= 2:             # 蓄滿 2 格即發動
                    self.pre_dash = 0.50

        self.x = max(PLAY_LEFT+self.radius, min(PLAY_RIGHT-self.radius, self.x))
        self.y = max(PLAY_TOP+self.radius, min(PLAY_BOTTOM-self.radius, self.y))


    def on_knockback(self, push_vx, push_vy):
        """v0.12: 被撞飛時進入滑行狀態，重置蓄力。"""
        self.vx += push_vx
        self.vy += push_vy
        self.charge   = 0
        self.dashing  = False
        self.pre_dash = 0.0
        self._knock_timer = 0.65  # 0.65秒滑行，讓擊退效果實際生效

    def draw(self, surface):
        cx, cy = int(self.x), int(self.y)
        r = self.radius
        color = (112, 128, 144)
        du.draw_gear(surface, color, cx, cy, r + 3, r - 2, 16, math.radians(self.angle))
        pygame.draw.circle(surface, (80, 90, 100), (cx, cy), r - 4)
        # 蓄力條（2 格）
        for i in range(2):
            seg_color = SPIN_BLUE if i < self.charge else STEEL_MID
            pygame.draw.rect(surface, seg_color,
                             (cx - 10 + i * 11, cy - r - 12, 9, 6),
                             border_radius=2)
        # 預警紅圈
        if self.pre_dash > 0:
            pygame.draw.circle(surface, DANGER_RED, (cx, cy), r + 6, 2)
        # 衝刺時橘色光暈
        if self.dashing:
            glow = pygame.Surface((r*4, r*4), pygame.SRCALPHA)
            pygame.draw.circle(glow, (255, 160, 30, 80), (r*2, r*2), r + 10)
            surface.blit(glow, (cx - r*2, cy - r*2))
        self.draw_hp_bar(surface)

# ── Level 4 Enemies ──────────────────────────────────────────────────────

class TankTop(Enemy):
    """
    重量型陀螺 — 速度慢、難擊退，在場地中心半徑內繞圈。
    HP: 300  ATK: 40  EXP: 8
    除非被撞飛，否則不會主動接觸加速帶。
    """
    ORBIT_RADIUS = 175

    def __init__(self, x, y):
        super().__init__(x, y, hp=160, attack=80, exp=12, radius=22)
        self.mass = 4.0
        self.angle = 0.0
        self.orbit_angle = random.uniform(0, math.pi * 2)
        self.orbit_dir   = random.choice([-1, 1])
        self.orbit_speed = 0.5        # rad/s
        self.knocked     = False      # True 時被彈飛，暫時失控
        self.knock_timer = 0.0
        self.knockback_resistance = 3.0   # v1.8: 重量型，極難彈飛
      # L4: 重量衝撞，對玩家擊退 ×1.4

    def update(self, dt, px, py):
        self.angle = (self.angle + 30 * dt) % 360

        cx = (PLAY_LEFT + PLAY_RIGHT) / 2
        cy = (PLAY_TOP  + PLAY_BOTTOM) / 2

        if self.knocked:
            # 被彈飛：依慣性滑行，慢慢減速
            self.x += self.vx * dt
            self.y += self.vy * dt
            self.vx *= max(0, 1 - 2.0 * dt)
            self.vy *= max(0, 1 - 2.0 * dt)
            self.knock_timer -= dt
            speed = math.sqrt(self.vx**2 + self.vy**2)
            if self.knock_timer <= 0 or speed < 8:
                self.knocked = False
                # 重新對準繞圈軌道
                dx = self.x - cx; dy = self.y - cy
                self.orbit_angle = math.atan2(dy, dx)
        else:
            # 正常繞圈
            self.orbit_angle += self.orbit_dir * self.orbit_speed * dt
            tx = cx + math.cos(self.orbit_angle) * self.ORBIT_RADIUS
            ty = cy + math.sin(self.orbit_angle) * self.ORBIT_RADIUS
            dx = tx - self.x; dy = ty - self.y
            dist = math.sqrt(dx*dx + dy*dy) or 1
            spd  = 55.0
            self.vx += (dx / dist * spd - self.vx) * min(1.0, 5.0 * dt)
            self.vy += (dy / dist * spd - self.vy) * min(1.0, 5.0 * dt)
            self.x += self.vx * dt
            self.y += self.vy * dt

        # Boundary clamp
        if self.x < PLAY_LEFT  + self.radius: self.x = PLAY_LEFT  + self.radius; self.vx =  abs(self.vx)
        if self.x > PLAY_RIGHT - self.radius: self.x = PLAY_RIGHT - self.radius; self.vx = -abs(self.vx)
        if self.y < PLAY_TOP   + self.radius: self.y = PLAY_TOP   + self.radius; self.vy =  abs(self.vy)
        if self.y > PLAY_BOTTOM- self.radius: self.y = PLAY_BOTTOM- self.radius; self.vy = -abs(self.vy)

    def on_knockback(self, vx, vy):
        """外部碰撞時呼叫，讓 Tank 進入被彈飛狀態。"""
        self.knocked     = True
        self.knock_timer = 1.2
        self.vx += vx * 0.4   # 重量型：只接受 40% 擊退
        self.vy += vy * 0.4

    def draw(self, surface):
        cx, cy = int(self.x), int(self.y)
        r = self.radius
        a = math.radians(self.angle)
        # 厚重六邊形
        pts = [(cx + r * math.cos(a + i * math.pi/3),
                cy + r * math.sin(a + i * math.pi/3)) for i in range(6)]
        pygame.draw.polygon(surface, (80, 90, 110), pts)
        pygame.draw.polygon(surface, STEEL_LIGHT, pts, 3)
        # 中心鋼鉚
        pygame.draw.circle(surface, STEEL_CHROME, (cx, cy), 7)
        pygame.draw.circle(surface, ASH_WHITE,    (cx, cy), 7, 2)
        # HP bar
        self.draw_hp_bar(surface)


class RunnerTop(Enemy):
    """
    干擾型陀螺 — 在加速帶上高速繞圈，試圖撞開玩家。
    HP: 200  ATK: 25  EXP: 5
    使用場地中心、加速帶半徑相同的圓形軌跡。
    """
    # 與 Level4BoostTrack 相同的幾何參數
    TRACK_RADIUS = 285   # 與 R0 保持一致
    ORBIT_SPEED  = 2.2   # rad/s (繞一圈約 2.9 秒)

    def __init__(self, x, y, orbit_dir=None):
        super().__init__(x, y, hp=160, attack=50, exp=5, radius=14)
        self.mass  = 0.8
        self.angle = 0.0
        cx = (PLAY_LEFT + PLAY_RIGHT) / 2
        cy = (PLAY_TOP  + PLAY_BOTTOM) / 2
        dx = x - cx; dy = y - cy
        self.orbit_angle = math.atan2(dy, dx)
        self.orbit_dir   = orbit_dir if orbit_dir else random.choice([-1, 1])
        self._boost_fx   = 0.0   # 加速特效計時
        self._knocked_timer = 0.0   # v1.8: 脫離軌道計時
        self.knockback_resistance = 0.8   # v1.8: 輕盈，容易彈離軌道

    def update(self, dt, px, py):
        self.angle = (self.angle + 400 * dt) % 360

        cx = (PLAY_LEFT + PLAY_RIGHT) / 2
        cy = (PLAY_TOP  + PLAY_BOTTOM) / 2

        # v1.8: 脫離軌道狀態（被彈後短暫自由滑行）
        if self._knocked_timer > 0:
            self._knocked_timer -= dt
            self.x += self.vx * dt
            self.y += self.vy * dt
            self.vx *= max(0, 1 - 2.5 * dt)
            self.vy *= max(0, 1 - 2.5 * dt)
            # 重新對準軌道入射角
            if self._knocked_timer <= 0:
                dx_ot = self.x - cx; dy_ot = self.y - cy
                self.orbit_angle = math.atan2(dy_ot, dx_ot)
            self.x = max(PLAY_LEFT + self.radius, min(PLAY_RIGHT - self.radius, self.x))
            self.y = max(PLAY_TOP  + self.radius, min(PLAY_BOTTOM - self.radius, self.y))
            return

        # 沿軌道繞圈
        self.orbit_angle += self.orbit_dir * self.ORBIT_SPEED * dt
        tx = cx + math.cos(self.orbit_angle) * self.TRACK_RADIUS
        ty = cy + math.sin(self.orbit_angle) * self.TRACK_RADIUS

        dx = tx - self.x; dy = ty - self.y
        dist = math.sqrt(dx*dx + dy*dy) or 1
        spd  = 240.0
        self.vx += (dx / dist * spd - self.vx) * min(1.0, 10.0 * dt)
        self.vy += (dy / dist * spd - self.vy) * min(1.0, 10.0 * dt)
        self.x += self.vx * dt
        self.y += self.vy * dt

        self._boost_fx = max(0, self._boost_fx - dt)

        # Boundary clamp
        self.x = max(PLAY_LEFT  + self.radius, min(PLAY_RIGHT  - self.radius, self.x))
        self.y = max(PLAY_TOP   + self.radius, min(PLAY_BOTTOM - self.radius, self.y))

    def on_knockback(self, push_vx, push_vy):
        """v1.8: 被撞飛後暫時脫離軌道，短暫自由滑行。"""
        self.vx += push_vx
        self.vy += push_vy
        self._knocked_timer = 1.5   # 1.5 秒脫軌

    def draw(self, surface):
        cx, cy = int(self.x), int(self.y)
        r = self.radius
        a = math.radians(self.angle)
        # 橢圓形流線體
        pygame.draw.circle(surface, (60, 200, 60), (cx, cy), r)
        # 速度紋（3條斜線）
        for i in range(3):
            la = a + i * math.pi / 1.5
            x1 = cx + int(r * 0.3 * math.cos(la))
            y1 = cy + int(r * 0.3 * math.sin(la))
            x2 = cx + int(r * 0.9 * math.cos(la))
            y2 = cy + int(r * 0.9 * math.sin(la))
            pygame.draw.line(surface, (140, 255, 100), (x1, y1), (x2, y2), 2)
        pygame.draw.circle(surface, (30, 140, 30), (cx, cy), r, 2)
        self.draw_hp_bar(surface)


class SplittingTop(Enemy):
    """
    分裂型陀螺 — 被擊敗後分裂成兩個較小的陀螺，一直遞迴到 HP < 11 為止。
    HP: 100 → 50 → 25 → 12 → 停止分裂
    ATK: 20  EXP: 隨分裂層遞減
    """
    def __init__(self, x, y, generation=0):
        hp_values  = [100, 50, 25, 12]
        atk_values = [20, 17, 14, 11]
        base_hp  = int(hp_values[generation] * 0.8)
        base_atk = int(atk_values[generation] * 2.0)
        base_exp = max(2,  6   - generation)
        base_rad = max(8,  18  - generation * 3)
        super().__init__(x, y, hp=base_hp, attack=base_atk, exp=base_exp, radius=base_rad)
        self.generation = generation
        self.mass  = 1.0
        self.angle = 0.0
        angle      = random.uniform(0, math.pi * 2)
        spd        = 100 + generation * 30
        self.vx    = math.cos(angle) * spd
        self.vy    = math.sin(angle) * spd
        self.dir_timer = random.uniform(1.5, 3.0)
        # v1.8: 世代越高越輕，越容易彈飛
        self.knockback_resistance = max(0.4, 0.9 - generation * 0.15)

    def can_split(self):
        return (self.generation < 3 and
                100 // (2 ** (self.generation + 1)) >= 11)

    def update(self, dt, px, py):
        self.angle = (self.angle + 200 * dt) % 360

        # 追蹤玩家（世代越高速度越快）
        dx = px - self.x; dy = py - self.y
        dist = math.sqrt(dx*dx + dy*dy) or 1
        spd  = 100 + self.generation * 40
        tvx  = dx / dist * spd
        tvy  = dy / dist * spd

        blend = min(1.0, 4.0 * dt)
        self.vx += (tvx - self.vx) * blend
        self.vy += (tvy - self.vy) * blend

        self.x += self.vx * dt
        self.y += self.vy * dt

        # Boundary bounce
        if self.x < PLAY_LEFT  + self.radius: self.x = PLAY_LEFT  + self.radius; self.vx =  abs(self.vx)
        if self.x > PLAY_RIGHT - self.radius: self.x = PLAY_RIGHT - self.radius; self.vx = -abs(self.vx)
        if self.y < PLAY_TOP   + self.radius: self.y = PLAY_TOP   + self.radius; self.vy =  abs(self.vy)
        if self.y > PLAY_BOTTOM- self.radius: self.y = PLAY_BOTTOM- self.radius; self.vy = -abs(self.vy)

    def draw(self, surface):
        cx, cy = int(self.x), int(self.y)
        r = self.radius
        a = math.radians(self.angle)
        # 顏色隨世代改變：0=橙, 1=黃, 2=白, 3=淡藍
        colors = [(220, 140, 30), (220, 200, 40), (200, 200, 200), (140, 180, 230)]
        color  = colors[min(self.generation, 3)]
        # 齒輪狀
        teeth = max(4, 8 - self.generation * 2)
        for i in range(teeth):
            ta = a + i * (2 * math.pi / teeth)
            # 外齒
            ox = cx + int((r + 4) * math.cos(ta))
            oy = cy + int((r + 4) * math.sin(ta))
            pygame.draw.circle(surface, color, (ox, oy), 3)
        pygame.draw.circle(surface, color, (cx, cy), r)
        pygame.draw.circle(surface, ASH_WHITE, (cx, cy), r, 2)
        # 中心代數標記
        pygame.draw.circle(surface, VOID_BLACK, (cx, cy), max(3, r // 3))
        self.draw_hp_bar(surface)


# ── Level 4 Boost Track Geometry ─────────────────────────────────────────


# ══════════════════════════════════════════════════════════════════════
#  MiniTop  （Boss Phase 2 召喚的小型衝刺陀螺）
# ══════════════════════════════════════════════════════════════════════
class MiniTop(Enemy):
    """Boss Phase 2 召喚的小型衝刺陀螺。
    從 Boss 中心出發，高速衝向玩家方向；
    碰到玩家後依物理碰撞反彈，根據玩家攻擊量扣血。
    """
    def __init__(self, x, y, target_x, target_y):
        super().__init__(x, y, hp=100, attack=50, exp=0, radius=12)
        dx = target_x - x
        dy = target_y - y
        dist = math.sqrt(dx * dx + dy * dy) or 1.0
        self.vx = dx / dist * 380.0
        self.vy = dy / dist * 380.0
        self.mass = 0.6
        self._spin = 0.0
        self._spawn_immune = 0.5  # 生成後 0.5s 無敵，防止 Phase 3 散開瞬間被 shockwave 秒殺

    def take_damage(self, dmg):
        if self._spawn_immune > 0:
            return False
        return super().take_damage(dmg)

    def update(self, dt, px, py):
        if not self.alive:
            return
        if self._spawn_immune > 0:
            self._spawn_immune -= dt
        self._spin = (self._spin + 360 * dt) % 360
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.x < PLAY_LEFT  + self.radius: self.x = PLAY_LEFT  + self.radius; self.vx =  abs(self.vx)
        if self.x > PLAY_RIGHT - self.radius: self.x = PLAY_RIGHT - self.radius; self.vx = -abs(self.vx)
        if self.y < PLAY_TOP   + self.radius: self.y = PLAY_TOP   + self.radius; self.vy =  abs(self.vy)
        if self.y > PLAY_BOTTOM- self.radius: self.y = PLAY_BOTTOM- self.radius; self.vy = -abs(self.vy)

    def draw(self, surface):
        if not self.alive:
            return
        cx, cy = int(self.x), int(self.y)
        r = self.radius
        # 外環 - 金色
        pygame.draw.circle(surface, ENERGY_GOLD, (cx, cy), r + 3, 2)
        # 本體 - 深紅
        pygame.draw.circle(surface, (180, 40, 30), (cx, cy), r)
        # 旋轉三葉刀片
        a_rad = math.radians(self._spin)
        for i in range(3):
            ba = a_rad + i * math.pi * 2 / 3
            tip_x = cx + int((r + 6) * math.cos(ba))
            tip_y = cy + int((r + 6) * math.sin(ba))
            hub_x = cx + int(r * 0.4 * math.cos(ba + math.pi))
            hub_y = cy + int(r * 0.4 * math.sin(ba + math.pi))
            pygame.draw.line(surface, ENERGY_GOLD, (hub_x, hub_y), (tip_x, tip_y), 3)
        # 中心
        pygame.draw.circle(surface, ASH_WHITE, (cx, cy), 3)
        pygame.draw.circle(surface, (180, 40, 30), (cx, cy), r, 2)
        self.draw_hp_bar(surface)


def generate_boost_track_points(cx, cy):
    """
    產生 Level 4 加速帶軌跡點（和設計稿相同的幾何：大圓弧 + 上方開口切線）。
    cx, cy: 場地中心座標
    回傳 list of (x, y)
    """
    R0    = 285   # 介於 260(1280) 和 310(1600) 之間
    ALPHA = math.radians(10)
    Y_TOP = 200

    points = []
    start_angle = math.pi / 2 + ALPHA
    end_angle   = 2 * math.pi + math.pi / 2 - ALPHA
    segments    = 300
    for i in range(segments + 1):
        theta = start_angle + (end_angle - start_angle) * (i / segments)
        x = cx + R0 * math.cos(theta)
        y = cy - R0 * math.sin(theta)
        points.append((x, y))

    x_corner1 = cx + Y_TOP * math.tan(ALPHA)
    y_corner1  = cy - Y_TOP
    points.append((x_corner1, y_corner1))

    x_corner2 = cx - Y_TOP * math.tan(ALPHA)
    y_corner2  = cy - Y_TOP
    points.append((x_corner2, y_corner2))

    return points


# ── Level 5 Boss ─────────────────────────────────────────────────────────
def lerp_color(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
# ══════════════════════════════════════════════════════════════════════
#  BossFragment  （Phase 3 爆炸碎片）
# ══════════════════════════════════════════════════════════════════════
class BossFragment:
    def __init__(self, x, y, angle, speed=320, damage=30):
        self.x       = float(x)
        self.y       = float(y)
        self.vx      = math.cos(angle) * speed
        self.vy      = math.sin(angle) * speed
        self.bounced = False
        self.alive   = True
        self.radius  = 9
        self.damage  = damage
        self._pulse  = 0.0          # 視覺脈動用
 
    def update(self, dt):
        self._pulse = (self._pulse + dt * 6) % (2 * math.pi)
        self.x += self.vx * dt
        self.y += self.vy * dt
        if not self.bounced:
            if self.x < PLAY_LEFT  or self.x > PLAY_RIGHT:
                self.vx *= -1; self.bounced = True
            if self.y < PLAY_TOP   or self.y > PLAY_BOTTOM:
                self.vy *= -1; self.bounced = True
        else:
            if (self.x < PLAY_LEFT - 40 or self.x > PLAY_RIGHT  + 40 or
                    self.y < PLAY_TOP  - 40 or self.y > PLAY_BOTTOM + 40):
                self.alive = False
 
    def collides(self, px, py, pr):
        dx = self.x - px; dy = self.y - py
        return math.sqrt(dx*dx + dy*dy) < (self.radius + pr)
 
    def draw(self, surface):
        r = self.radius + int(2 * math.sin(self._pulse))
        pygame.draw.circle(surface, WARN_ORANGE,  (int(self.x), int(self.y)), r)
        pygame.draw.circle(surface, DANGER_RED,   (int(self.x), int(self.y)), r, 2)
 
 
# ══════════════════════════════════════════════════════════════════════
#  BossBullet  （螺旋彈幕 / 環形彈幕）
# ══════════════════════════════════════════════════════════════════════
class BossBullet:
    def __init__(self, x, y, angle, speed=280, damage=20,
                 color=DANGER_RED, radius=7, homing=False):
        self.x       = float(x)
        self.y       = float(y)
        self.vx      = math.cos(angle) * speed
        self.vy      = math.sin(angle) * speed
        self.speed   = speed
        self.damage  = damage
        self.color   = color
        self.radius  = radius
        self.alive   = True
        self.homing  = homing
        self._age    = 0.0
 
    def update(self, dt, px=None, py=None):
        self._age += dt
        # 追蹤子彈：前 0.8 秒緩慢轉向玩家
        if self.homing and px is not None and self._age < 0.8:
            dx = px - self.x; dy = py - self.y
            d  = math.sqrt(dx*dx + dy*dy) or 1
            tx = dx / d * self.speed; ty = dy / d * self.speed
            blend = min(1.0, 3.0 * dt)
            self.vx += (tx - self.vx) * blend
            self.vy += (ty - self.vy) * blend
 
        self.x += self.vx * dt
        self.y += self.vy * dt
        if (self.x < PLAY_LEFT - 30 or self.x > PLAY_RIGHT  + 30 or
                self.y < PLAY_TOP  - 30 or self.y > PLAY_BOTTOM + 30):
            self.alive = False
 
    def collides(self, px, py, pr):
        dx = self.x - px; dy = self.y - py
        return math.sqrt(dx*dx + dy*dy) < (self.radius + pr)
 
    def draw(self, surface):
        pygame.draw.circle(surface, self.color,
                           (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surface, ASH_WHITE,
                           (int(self.x), int(self.y)), self.radius, 1)
 
 
# ══════════════════════════════════════════════════════════════════════
#  BossLaser  （鐳射掃射）
# ══════════════════════════════════════════════════════════════════════
class BossLaser:
    """持續型鐳射，會緩慢跟蹤玩家。"""
    def __init__(self, ox, oy, angle, damage_per_sec=80, duration=1.8):
        self.ox          = float(ox)
        self.oy          = float(oy)
        self.angle       = float(angle)      # radians
        self.damage_ps   = damage_per_sec
        self.alive       = True
        self.timer       = duration
        self.width       = 8
        self.length      = 900
        self._flash      = 0.0
 
    def update(self, dt, px, py, boss_x, boss_y, turn_speed=1.2):
        self.ox     = boss_x
        self.oy     = boss_y
        self._flash = (self._flash + dt * 10) % (2 * math.pi)
 
        # 緩慢轉向玩家
        target_a = math.atan2(py - self.oy, px - self.ox)
        diff = (target_a - self.angle + math.pi) % (2 * math.pi) - math.pi
        self.angle += max(-turn_speed * dt,
                          min(turn_speed * dt, diff))
 
        self.timer -= dt
        if self.timer <= 0:
            self.alive = False
 
    def hits_player(self, px, py, pr):
        """簡化：檢查玩家中心到鐳射線段的距離。"""
        ex = self.ox + math.cos(self.angle) * self.length
        ey = self.oy + math.sin(self.angle) * self.length
        dx = ex - self.ox; dy = ey - self.oy
        t  = max(0.0, min(1.0,
             ((px - self.ox)*dx + (py - self.oy)*dy) / (dx*dx + dy*dy + 1e-9)))
        cx = self.ox + t*dx; cy = self.oy + t*dy
        return math.sqrt((px-cx)**2 + (py-cy)**2) < pr + self.width
 
    def draw(self, surface):
        alpha = int(180 + 60 * math.sin(self._flash))
        ex = int(self.ox + math.cos(self.angle) * self.length)
        ey = int(self.oy + math.sin(self.angle) * self.length)
        surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        # 外光暈
        pygame.draw.line(surf,
                         (LASER_CYAN[0], LASER_CYAN[1], LASER_CYAN[2], alpha//3),
                         (int(self.ox), int(self.oy)), (ex, ey), self.width + 8)
        # 核心
        pygame.draw.line(surf,
                         (LASER_CYAN[0], LASER_CYAN[1], LASER_CYAN[2], alpha),
                         (int(self.ox), int(self.oy)), (ex, ey), self.width)
        pygame.draw.line(surf,
                         (255, 255, 255, alpha),
                         (int(self.ox), int(self.oy)), (ex, ey), 2)
        surface.blit(surf, (0, 0))
 
 
# ══════════════════════════════════════════════════════════════════════
#  招式池
# ══════════════════════════════════════════════════════════════════════
ATTACK_POOL = {
    1: [('charge', 25), ('spiral', 20), ('orbit', 10), ('ring', 45)],
    2: [('charge', 30), ('laser', 30), ('spiral', 25), ('ring', 15)],
    3: [('charge', 20), ('laser',  20), ('spiral', 20),
        ('ring',   20), ('homing', 20)],
}
 
 
def _weighted_choice(pool, exclude=None):
    filtered = [(a, w) for a, w in pool if a != exclude]
    total    = sum(w for _, w in filtered)
    r        = random.uniform(0, total)
    for name, weight in filtered:
        r -= weight
        if r <= 0:
            return name
    return filtered[-1][0]
 
 
# ══════════════════════════════════════════════════════════════════════
#  Boss  主體
# ══════════════════════════════════════════════════════════════════════
class Boss(Enemy):
    """
    Boss 敵人 — 三階段 AI 狀態機。
    Changes vs original:
      - [刪除] absorbed_skill / skill_timer（機制已移除，殘留清除）
      - [刪除] spawn_sawblade signal（從未被觸發，移除避免混淆）
      - [修正] arena_shrink 新增 _advance_arena_shrink() 讓縮圈可正常運作
      - [改名] summon signal 改為 spawn_minion，語意更清晰
      - [整理] 移除 update() 中孤立的 skill_timer 殘留註解
    """

    # ── 初始化 ────────────────────────────────────────────────────────
    def __init__(self, x, y, player_material=None):
        super().__init__(x, y, hp=50000, attack=250, exp=500, radius=80)
        self.player_material = player_material

        # ── 基礎屬性 ──────────────────────────────────────────────────
        self.phase        = 1
        self.angle        = 0.0
        self.base_speed   = 200.0
        self.speed        = self.base_speed
        self.move_vx      = 0.0
        self.move_vy      = 0.0

        # ── AI 狀態機 ─────────────────────────────────────────────────
        self.ai_state        = 'orbit'
        self.ai_timer        = 2.0
        self.orbit_dir       = 1
        self.orbit_radius    = 200
        self.charge_vx       = 0.0
        self.charge_vy       = 0.0
        self.charge_hit_done = False
        self.last_attack     = None

        # ── 衝刺預警 ──────────────────────────────────────────────────
        self.pre_charge_timer = 0.0
        self.pre_charging     = False
        self.aim_px           = 0.0
        self.aim_py           = 0.0
        self._charge_speed_m  = 1.0

        # ── 螺旋彈幕 ─────────────────────────────────────────────────
        self.spiral_timer    = 0.0
        self.spiral_active   = False
        self.spiral_duration = 0.0
        self.spiral_angle    = 0.0
        self.spiral_bullets: list[BossBullet] = []

        # ── 環形彈幕 ─────────────────────────────────────────────────
        self.ring_pending = False

        # ── 追蹤彈幕 ─────────────────────────────────────────────────
        self.homing_pending = False

        # ── 鐳射 ─────────────────────────────────────────────────────
        self.laser: BossLaser | None = None
        self.laser_pre_timer  = 0.0
        self.laser_pre_active = False
        self.laser_aim_angle  = 0.0

        # ── Phase 3 蓄力爆炸 ─────────────────────────────────────────
        self.spin_up_timer    = 0.0
        self.spinning         = False
        self.explode_cd       = 5.0
        self.explode_cooldown = 9.0
        self.fragments: list[BossFragment] = []

        # ── Phase 3 縮圈 ─────────────────────────────────────────────
        # shrink_count / arena_shrink 需搭配 _advance_arena_shrink() 使用
        self.shrink_count  = 0
        self.shrink_timer  = 10.0    # 每隔 10 秒縮圈一次（Phase 3）
        self.arena_shrink  = 0       # 當前縮圈像素量，由 _advance_arena_shrink 遞增

        # ── 進場緩衝（5 秒內只移動不攻擊） ──────────────────────────
        self._intro_timer = 5.0

        # ── HUD 技能名稱顯示 ─────────────────────────────────────────
        self._skill_name       = ''
        self._skill_name_timer = 0.0

        # ── Phase 轉換 ───────────────────────────────────────────────
        self.transition_timer   = 0.0
        self.invincible         = False
        self.ring_burst_pending = False

        # ── Enrage ───────────────────────────────────────────────────
        self.enraged       = False
        self._no_hit_timer = 0.0   # 玩家多久沒攻擊到 Boss；達閾值觸發 Enrage

        # ── 視覺 ─────────────────────────────────────────────────────
        self._hit_flash   = 0.0
        self._phase_flash = 0.0
        self._idle_pulse  = 0.0

        # ── Phase 3 護盾（MiniTop 全滅才解除）────────────────────────
        self.shield_active   = False
        self._shield_spawned = False
        self.shield_value    = 0  # v1.9: 護盾值，0 時不再保護

        # ── 玩家碰撞 impulse / 硬直系統（v1.8）──────────────────────
        self._impulse_buffer = 0.0
        self._stagger_timer  = 0.0
        self._stagger_vx     = 0.0
        self._stagger_vy     = 0.0

        # ── 材質 passive ─────────────────────────────────────────────
        self.mat_speed_bonus  = 0.0
        self.mat_damage_bonus = 1.0
        if player_material == 'wood':
            self.mat_damage_bonus = 0.65
        elif player_material == 'steel':
            self.mat_speed_bonus  = 0.10
        elif player_material == 'titan':
            self.mat_speed_bonus  = 0.80
        self.speed = self.base_speed * (1 + self.mat_speed_bonus)

    # ══════════════════════════════════════════════════════════════════
    #  受傷（外部呼叫）
    # ══════════════════════════════════════════════════════════════════
    def take_damage(self, dmg):
        if self.invincible:
            return False
        
        # v1.9: 護盾優先承受傷害
        if getattr(self, 'shield_active', False) and getattr(self, 'shield_value', 0) > 0:
            self._hit_flash = 0.08
            self.shield_value = max(0, self.shield_value - dmg)
            # 當護盾被打空時停止保護
            if self.shield_value <= 0:
                self.shield_active = False
            return False  # 護盾未被打空前不算擊中 Boss
        
        dmg = int(dmg * self.mat_damage_bonus)
        result = super().take_damage(dmg)
        self._hit_flash = 0.12
        if not self.enraged:
            self._no_hit_timer = 0.0   # 玩家有在攻擊，重置惰性計時
        return result

    def receive_impulse(self, amount, push_vx, push_vy):
        """累積玩家碰撞衝擊，達閾值後觸發硬直狀態。"""
        if self.invincible or self.transition_timer > 0:
            return
        if self.ai_state == 'staggered':
            return
        self._impulse_buffer += amount
        thresholds = {1: 80, 2: 140, 3: 160}
        threshold  = thresholds.get(self.phase, 80)
        if self.enraged:
            threshold = int(threshold * 1.5)
        if self._impulse_buffer >= threshold:
            self._impulse_buffer = 0.0
            dur          = {1: 0.6,  2: 0.4,  3: 0.3 }.get(self.phase, 0.4)
            stagger_force= {1: 400,  2: 280,  3: 160 }.get(self.phase, 280)
            spd = math.sqrt(push_vx**2 + push_vy**2) or 1
            self._stagger_vx    = (push_vx / spd) * stagger_force
            self._stagger_vy    = (push_vy / spd) * stagger_force
            self._stagger_timer = dur
            self.ai_state       = 'staggered'
            self._skill_name       = '硬直！'
            self._skill_name_timer = dur

    # ══════════════════════════════════════════════════════════════════
    #  Phase 3 縮圈推進（外部在適當時機呼叫，或由 update 內觸發）
    # ══════════════════════════════════════════════════════════════════
    def _advance_arena_shrink(self):
        """每次呼叫使競技場向內縮 20px，最多縮 5 次。"""
        MAX_SHRINKS     = 5
        SHRINK_PX_EACH  = 20
        if self.shrink_count >= MAX_SHRINKS:
            return
        self.shrink_count += 1
        self.arena_shrink  = self.shrink_count * SHRINK_PX_EACH

    # ══════════════════════════════════════════════════════════════════
    #  狀態進入
    # ══════════════════════════════════════════════════════════════════
    def _enter_orbit(self, duration=None):
        self.ai_state = 'orbit'
        base_dur = {1: 1.0, 2: 1.2, 3: 0.7}.get(self.phase, 1.0)
        if self.enraged:
            base_dur *= 0.5
        if duration is None:
            duration = base_dur
        self.ai_timer     = duration + random.uniform(-0.3, 0.3)
        self.orbit_dir    = random.choice([-1, 1])
        self.orbit_radius = {1: 200, 2: 100, 3: 70}.get(self.phase, 200)

    def _enter_pre_charge(self, px, py, speed_mult=1.0):
        """0.45 秒預警後衝刺。"""
        self.ai_state         = 'pre_charge'
        self.pre_charge_timer = 0.45
        self.pre_charging     = True
        self.aim_px           = px
        self.aim_py           = py
        self._charge_speed_m  = speed_mult

    def _launch_charge(self):
        self.ai_state        = 'charge'
        self.pre_charging    = False
        self.charge_hit_done = False
        dur = {1: 0.55, 2: 0.50, 3: 0.45}.get(self.phase, 0.55)
        if self.enraged:
            dur *= 0.8
        self.ai_timer = dur
        spd = (self.speed
               * {1: 3.2, 2: 3.8, 3: 4.5}.get(self.phase, 3.2)
               * self._charge_speed_m
               * (1.3 if self.enraged else 1.0))
        dx = self.aim_px - self.x
        dy = self.aim_py - self.y
        d  = math.sqrt(dx*dx + dy*dy) or 1
        self.charge_vx   = dx / d * spd
        self.charge_vy   = dy / d * spd
        self.last_attack = 'charge'

    def _enter_retreat(self, px, py):
        self.ai_state = 'retreat'
        self.ai_timer = 0.5
        dx = self.x - px; dy = self.y - py
        d  = math.sqrt(dx*dx + dy*dy) or 1
        self.charge_vx = dx / d * self.speed * 2.2
        self.charge_vy = dy / d * self.speed * 2.2

    def _enter_spiral(self):
        self.ai_state      = 'spiral'
        self.spiral_active = True
        dur = {1: 2.5, 2: 3.0, 3: 3.5}.get(self.phase, 2.5)
        if self.enraged:
            dur *= 1.3
        self.spiral_duration = dur
        self.spiral_timer    = 0.0
        self.spiral_angle    = self.angle
        self.last_attack     = 'spiral'

    def _enter_ring(self):
        self.ai_state     = 'ring_pre'
        self.ai_timer     = 0.6
        self.ring_pending = False
        self.last_attack  = 'ring'

    def _enter_homing(self, px, py):
        self.ai_state       = 'homing_pre'
        self.ai_timer       = 0.5
        self.aim_px, self.aim_py = px, py
        self.homing_pending = False
        self.last_attack    = 'homing'

    def _enter_laser_pre(self, px, py):
        self.ai_state         = 'laser_pre'
        self.laser_pre_timer  = 0.8
        self.laser_pre_active = True
        self.laser_aim_angle  = math.atan2(py - self.y, px - self.x)
        self.last_attack      = 'laser'

    def _launch_laser(self):
        dur  = {1: 1.5, 2: 2.0, 3: 2.5}.get(self.phase, 1.8)
        turn = {1: 0.8, 2: 1.2, 3: 1.6}.get(self.phase, 1.0)
        if self.enraged:
            dur *= 1.2; turn *= 1.3
        self.laser = BossLaser(
            self.x, self.y,
            self.laser_aim_angle,
            damage_per_sec=100 * self.phase,   # 90 → 100 balance（不隨彈幕 ×2）
            duration=dur,
        )
        self.laser._turn_spd  = turn
        self.laser_pre_active = False
        self.ai_state         = 'laser_fire'
        self.ai_timer         = dur + 0.1

    # ══════════════════════════════════════════════════════════════════
    #  移動執行
    # ══════════════════════════════════════════════════════════════════
    def _do_orbit(self, dt, px, py, dist, speed_mult=1.0):
        radius = self.orbit_radius
        dx = self.x - px; dy = self.y - py
        d  = dist or 1

        radial_force = (d - radius) / max(radius, 1)
        rvx = -(dx / d) * radial_force * self.speed * 2.5
        rvy = -(dy / d) * radial_force * self.speed * 2.5
        tvx = -dy / d * self.speed * speed_mult * self.orbit_dir
        tvy =  dx / d * self.speed * speed_mult * self.orbit_dir

        blend = min(1.0, 8.0 * dt)
        self.move_vx += (rvx + tvx - self.move_vx) * blend
        self.move_vy += (rvy + tvy - self.move_vy) * blend
        self.x += self.move_vx * dt
        self.y += self.move_vy * dt

        # 距離過近時後退（Phase 1 也防角落壓制）
        close_threshold = self.radius + (80 if self.phase == 1 else 60)
        if dist < close_threshold:
            self._enter_retreat(px, py)

    def _do_charge(self, dt):
        self.x += self.charge_vx * dt
        self.y += self.charge_vy * dt
        self.charge_vx *= max(0, 1 - 0.9 * dt)
        self.charge_vy *= max(0, 1 - 0.9 * dt)
        if self.x < PLAY_LEFT  + self.radius: self.x = PLAY_LEFT  + self.radius; self.charge_vx =  abs(self.charge_vx)
        if self.x > PLAY_RIGHT - self.radius: self.x = PLAY_RIGHT - self.radius; self.charge_vx = -abs(self.charge_vx)
        if self.y < PLAY_TOP   + self.radius: self.y = PLAY_TOP   + self.radius; self.charge_vy =  abs(self.charge_vy)
        if self.y > PLAY_BOTTOM- self.radius: self.y = PLAY_BOTTOM- self.radius; self.charge_vy = -abs(self.charge_vy)

    def _do_retreat(self, dt):
        self.x += self.charge_vx * dt
        self.y += self.charge_vy * dt

    # ══════════════════════════════════════════════════════════════════
    #  彈幕生成
    # ══════════════════════════════════════════════════════════════════
    def _spawn_spiral_bullet(self):
        arms = {1: 2, 2: 3, 3: 4}.get(self.phase, 2)
        for i in range(arms):
            a   = math.radians(self.spiral_angle) + i * (2 * math.pi / arms)
            spd = 240 + self.phase * 30
            self.spiral_bullets.append(
                BossBullet(self.x, self.y, a,
                           speed=spd,
                           damage=(20 + self.phase * 5) * 2,   # ×2 balance
                           color=lerp_color(DANGER_RED, WARN_ORANGE,
                                            self.phase / 3)))

    def _fire_ring(self, count=12, speed=260, homing=False):
        bullets = []
        for i in range(count):
            a = i * (2 * math.pi / count)
            # 追蹤彈幕因自動瞄準只 ×1.5；一般環形 ×2
            base_dmg = 25 + self.phase * 5
            dmg = int(base_dmg * (1.5 if homing else 2.0))   # balance
            b = BossBullet(self.x, self.y, a,
                           speed=speed,
                           damage=dmg,
                           color=ENERGY_GOLD if not homing else ENRAGE_PURPLE,
                           homing=homing)
            bullets.append(b)
        return bullets

    def _fire_fragments_explosion(self):
        frags = []
        count = 12 + self.shrink_count * 2
        for i in range(count):
            a = math.radians(i * (360 / count))
            frags.append(BossFragment(self.x, self.y, a,
                                      speed=280 + random.randint(0, 60),
                                      damage=52))   # 35 × 1.5 balance
        return frags

    # ══════════════════════════════════════════════════════════════════
    #  Phase 轉換
    # ══════════════════════════════════════════════════════════════════
    def _trigger_phase2(self, player):
        self.phase            = 2
        self.invincible       = True
        self.transition_timer = 1.8
        self._phase_flash     = 1.8
        self.ring_burst_pending = True
        self.speed = self.base_speed * (1 + self.mat_speed_bonus) * 1.3
        self.laser = None
        self._enter_orbit(duration=2.0)

    def _trigger_phase3(self):
        self.phase            = 3
        self.invincible       = True
        self.transition_timer = 2.0
        self._phase_flash     = 2.0
        self.ring_burst_pending = True
        self.speed = self.base_speed * (1 + self.mat_speed_bonus) * 1.7
        self.explode_cd       = 5.0
        self.explode_cooldown = 12.0   # 9 → 12 balance（彈片傷害提升後延長冷卻）
        self.laser = None
        self._enter_orbit(duration=1.0)
        self.shield_active     = True
        self._shield_spawned   = True
        self.shield_value      = 9999  # v1.9: 初始護盾值
        self.max_shield_value  = 9999

    # ══════════════════════════════════════════════════════════════════
    #  AI 決策
    # ══════════════════════════════════════════════════════════════════
    def _ai_update(self, dt, px, py):
        dx   = px - self.x; dy = py - self.y
        dist = math.sqrt(dx*dx + dy*dy) or 1

        # 進場緩衝：只繞圈，不攻擊
        if self._intro_timer > 0:
            self._intro_timer -= dt
            self._do_orbit(dt, px, py, dist, 1.0)
            return

        # 硬直狀態
        if self.ai_state == 'staggered':
            self._stagger_timer -= dt
            self.x += self._stagger_vx * dt
            self.y += self._stagger_vy * dt
            self._stagger_vx *= max(0, 1 - 5.0 * dt)
            self._stagger_vy *= max(0, 1 - 5.0 * dt)
            self.x = max(PLAY_LEFT + self.radius, min(PLAY_RIGHT - self.radius, self.x))
            self.y = max(PLAY_TOP  + self.radius, min(PLAY_BOTTOM - self.radius, self.y))
            if self._stagger_timer <= 0:
                self._enter_orbit(duration=0.5)
            return

        # 衝刺預警
        if self.ai_state == 'pre_charge':
            self.pre_charge_timer -= dt
            self.aim_px = px; self.aim_py = py
            if self.pre_charge_timer <= 0:
                self._skill_name       = '高速衝刺'
                self._skill_name_timer = 1.5
                self._launch_charge()
            return

        # 鐳射前搖
        if self.ai_state == 'laser_pre':
            self.laser_pre_timer -= dt
            self.laser_aim_angle  = math.atan2(py - self.y, px - self.x)
            if self.laser_pre_timer <= 0:
                self._skill_name       = '追蹤雷射'
                self._skill_name_timer = 1.5
                self._launch_laser()
            return

        # 鐳射射擊中
        if self.ai_state == 'laser_fire':
            self.ai_timer -= dt
            if self.laser:
                self.laser.update(dt, px, py, self.x, self.y,
                                  turn_speed=getattr(self.laser, '_turn_spd', 1.0))
                if not self.laser.alive:
                    self.laser = None
            if self.ai_timer <= 0:
                self.laser = None
                self._enter_orbit()
            return

        # 環形彈幕前搖
        if self.ai_state == 'ring_pre':
            self.ai_timer -= dt
            if self.ai_timer <= 0:
                self._skill_name       = '環形齊射'
                self._skill_name_timer = 1.5
                self.ring_pending = True
                self._enter_orbit()
            return

        # 追蹤彈幕前搖
        if self.ai_state == 'homing_pre':
            self.ai_timer -= dt
            if self.ai_timer <= 0:
                self._skill_name       = '追蹤彈幕'
                self._skill_name_timer = 1.5
                self.homing_pending = True
                self._enter_orbit()
            return

        # 螺旋彈幕
        if self.ai_state == 'spiral':
            self.ai_timer -= dt
            if self.ai_timer <= 0 or self.spiral_duration <= 0:
                self.spiral_active = False
                self._enter_orbit()
            return

        self.ai_timer -= dt

        speed_mult = {1: 1.0, 2: 1.4, 3: 1.8}.get(self.phase, 1.0)
        if self.enraged:
            speed_mult *= 1.2

        pool = ATTACK_POOL[self.phase]

        # ── Phase 1 ──────────────────────────────────────────────────
        if self.phase == 1:
            if self.ai_state == 'orbit':
                self._do_orbit(dt, px, py, dist, speed_mult)
                if self.ai_timer <= 0:
                    nxt = _weighted_choice(pool, self.last_attack)
                    if nxt == 'charge':
                        self._enter_pre_charge(px, py)
                    elif nxt == 'spiral':
                        self._enter_spiral()
                        self.ai_timer = self.spiral_duration
                    elif nxt == 'ring':
                        self._enter_ring()
                    else:
                        self._enter_orbit()
            elif self.ai_state == 'charge':
                self._do_charge(dt)
                if self.ai_timer <= 0:
                    self._enter_orbit()
            elif self.ai_state == 'retreat':
                self._do_retreat(dt)
                if self.ai_timer <= 0:
                    self._enter_orbit()

        # ── Phase 2 ──────────────────────────────────────────────────
        elif self.phase == 2:
            if self.ai_state == 'orbit':
                self._do_orbit(dt, px, py, dist, speed_mult)
                if self.ai_timer <= 0:
                    nxt = _weighted_choice(pool, self.last_attack)
                    if nxt == 'charge':
                        self._enter_pre_charge(px, py, speed_mult=1.2)
                    elif nxt == 'spiral':
                        self._enter_spiral()
                        self.ai_timer = self.spiral_duration
                    elif nxt == 'laser':
                        self._enter_laser_pre(px, py)
                    elif nxt == 'ring':
                        self._enter_ring()
                    else:
                        self._enter_retreat(px, py)
            elif self.ai_state == 'charge':
                self._do_charge(dt)
                if self.ai_timer <= 0:
                    self._enter_orbit()
            elif self.ai_state == 'retreat':
                self._do_retreat(dt)
                if self.ai_timer <= 0:
                    self._enter_pre_charge(px, py, speed_mult=1.3)

        # ── Phase 3 ──────────────────────────────────────────────────
        elif self.phase == 3:
            if self.ai_state == 'orbit':
                self._do_orbit(dt, px, py, dist, speed_mult)
                if self.ai_timer <= 0:
                    nxt = _weighted_choice(pool, self.last_attack)
                    if nxt == 'charge':
                        self._enter_pre_charge(px, py)
                    elif nxt == 'spiral':
                        self._enter_spiral()
                        self.ai_timer = self.spiral_duration
                    elif nxt == 'laser':
                        self._enter_laser_pre(px, py)
                    elif nxt == 'ring':
                        self._enter_ring()
                    elif nxt == 'homing':
                        self._enter_homing(px, py)
                    else:
                        self._enter_retreat(px, py)
            elif self.ai_state == 'charge':
                self._do_charge(dt)
                if self.ai_timer <= 0:
                    self._enter_orbit()
            elif self.ai_state == 'retreat':
                self._do_retreat(dt)
                if self.ai_timer <= 0:
                    self._enter_pre_charge(px, py, speed_mult=1.2)

    # ══════════════════════════════════════════════════════════════════
    #  主 update（每幀呼叫，回傳 signals dict）
    # ══════════════════════════════════════════════════════════════════
    def update(self, dt, px, py, player=None) -> dict:
        signals = {
            'bullets':                [],
            'fragments':              [],
            'laser':                  None,
            'screen_shake':           0,
            'damage_player':          0,
            'spawn_phase3_mini_tops': False,
            'skill_name':             '',
        }

        self._idle_pulse  = (self._idle_pulse + dt * 2) % (2 * math.pi)
        self._hit_flash   = max(0.0, self._hit_flash  - dt)
        self._phase_flash = max(0.0, self._phase_flash - dt)
        self.angle        = (self.angle + 90 * dt) % 360

        # HUD 技能名稱
        if self._skill_name_timer > 0:
            self._skill_name_timer -= dt
            signals['skill_name'] = self._skill_name
        else:
            self._skill_name = ''

        # ── Phase 檢查 ───────────────────────────────────────────────
        hp_pct = self.hp / self.max_hp
        if self.phase == 1 and hp_pct <= 0.70:
            self._trigger_phase2(player)
            signals['screen_shake'] = 18
        elif self.phase == 2 and hp_pct <= 0.35:
            self._trigger_phase3()
            signals['screen_shake'] = 24
            signals['spawn_phase3_mini_tops'] = True

        # ── 轉換無敵期 ───────────────────────────────────────────────
        if self.transition_timer > 0:
            self.transition_timer -= dt
            if self.transition_timer <= 0:
                self.invincible = False
                if self.ring_burst_pending:
                    self.ring_burst_pending = False
                    cnt = 12 + self.phase * 4
                    signals['bullets']      = self._fire_ring(count=cnt, speed=240)
                    signals['screen_shake'] = 14
            return signals

        # ── Enrage 計時 ──────────────────────────────────────────────
        if not self.enraged:
            self._no_hit_timer += dt
            if self._no_hit_timer >= 60.0:   # 60 秒不攻擊才觸發，懲罰龜縮而非弱者
                self.enraged          = True
                self.speed           *= 1.4
                self.explode_cooldown = 8.0
                signals['screen_shake'] = 20

        # ── Phase 3 蓄力爆炸 ─────────────────────────────────────────
        if self.phase == 3:
            self.explode_cd -= dt
            if self.explode_cd <= 0 and not self.spinning:
                self.spinning      = True
                self.spin_up_timer = 2.0
                self.ai_state      = 'spinning'
                self.laser         = None

            if self.spinning:
                self.spin_up_timer -= dt
                self.angle = (self.angle + 480 * dt) % 360
                if self.spin_up_timer <= 0:
                    frags = self._fire_fragments_explosion()
                    self.fragments.extend(frags)
                    signals['fragments']    = frags
                    signals['screen_shake'] = 30
                    self.spinning   = False
                    self.explode_cd = self.explode_cooldown
                    self._enter_orbit(duration=1.5)
                return signals

            # Phase 3 縮圈計時
            self.shrink_timer -= dt
            if self.shrink_timer <= 0:
                self.shrink_timer = 10.0
                self._advance_arena_shrink()

        # ── Fragment 更新 ────────────────────────────────────────────
        self.fragments = [f for f in self.fragments if f.alive]
        for f in self.fragments:
            f.update(dt)

        # ── 螺旋彈幕生成 ─────────────────────────────────────────────
        if self.spiral_active:
            self.spiral_duration -= dt
            rate = {1: 0.10, 2: 0.08, 3: 0.06}.get(self.phase, 0.10)
            if self.enraged:
                rate *= 0.7
            self.spiral_timer += dt
            while self.spiral_timer >= rate:
                self.spiral_timer -= rate
                self._spawn_spiral_bullet()
                rot = {1: 5, 2: 7, 3: 9}.get(self.phase, 5)
                self.spiral_angle += rot
            signals['bullets'].extend(self.spiral_bullets)
            self.spiral_bullets.clear()

        # ── AI 決策 ──────────────────────────────────────────────────
        self._ai_update(dt, px, py)

        # ── 環形 / 追蹤彈幕發射 ──────────────────────────────────────
        if self.ring_pending:
            self.ring_pending = False
            cnt = 12 + self.phase * 4
            signals['bullets'].extend(self._fire_ring(count=cnt))
            signals['screen_shake'] = 8

        if self.homing_pending:
            self.homing_pending = False
            cnt = 6 + self.phase * 2
            signals['bullets'].extend(
                self._fire_ring(count=cnt, speed=200, homing=True))

        # ── 鐳射 signal ──────────────────────────────────────────────
        if self.laser and not self.laser.alive:
            self.laser = None
        signals['laser'] = self.laser

        # ── 衝刺碰撞傷害 ─────────────────────────────────────────────
        if self.ai_state == 'charge' and not self.charge_hit_done:
            dx = px - self.x; dy = py - self.y
            if math.sqrt(dx*dx + dy*dy) < self.radius + 30:
                signals['damage_player'] = self.get_effective_attack() // 2   # ÷2 balance
                self.charge_hit_done     = True
                signals['screen_shake']  = 12

        # ── 邊界夾限 ─────────────────────────────────────────────────
        self.x = max(PLAY_LEFT + self.radius, min(PLAY_RIGHT - self.radius, self.x))
        self.y = max(PLAY_TOP  + self.radius, min(PLAY_BOTTOM - self.radius, self.y))

        return signals

    # ══════════════════════════════════════════════════════════════════
    #  對外查詢
    # ══════════════════════════════════════════════════════════════════
    def get_arena_shrink(self):
        return self.arena_shrink

    def get_effective_attack(self):
        atk = self.attack
        if   self.phase == 2: atk = int(atk * 1.3)
        elif self.phase == 3: atk = int(atk * 1.6)
        if self.enraged:      atk = int(atk * 1.3)
        return atk

    # ══════════════════════════════════════════════════════════════════
    #  繪製
    # ══════════════════════════════════════════════════════════════════
    def draw(self, surface):
        if not self.alive:
            return
        cx, cy = int(self.x), int(self.y)
        r      = self.radius
        a_rad  = math.radians(self.angle)

        # ── Phase 3 護盾光圈 ─────────────────────────────────────────
        if getattr(self, 'shield_active', False):
            import time as _t
            pulse     = 0.5 + 0.5 * math.sin(_t.time() * 4)
            aura_r    = r + 18 + int(pulse * 8)
            aura_alpha= int(140 + 90 * pulse)
            aura_surf = pygame.Surface((aura_r * 4, aura_r * 4), pygame.SRCALPHA)
            ac = aura_r * 2
            pygame.draw.circle(aura_surf, (255, 215, 0, aura_alpha), (ac, ac), aura_r, 8)
            pygame.draw.circle(aura_surf, (255, 215, 0, 50),         (ac, ac), aura_r)
            surface.blit(aura_surf, (cx - ac, cy - ac))

        # ── 階段顏色 ─────────────────────────────────────────────────
        if self._hit_flash > 0:
            color = ASH_WHITE
        elif self.enraged:
            t     = 0.5 + 0.5 * math.sin(self._idle_pulse * 4)
            color = lerp_color(DANGER_RED, ENRAGE_PURPLE, t)
        elif self.phase == 1:
            color = STEEL_CHROME
        elif self.phase == 2:
            t     = (0.66 - self.hp / self.max_hp) / 0.33
            color = lerp_color(STEEL_CHROME, DANGER_RED, t)
        else:
            color = WARN_ORANGE

        # ── Phase 轉換閃光暈 ─────────────────────────────────────────
        if self._phase_flash > 0:
            alpha = int(200 * (self._phase_flash / 2.0))
            glow  = pygame.Surface((r * 5, r * 5), pygame.SRCALPHA)
            fc    = ENRAGE_PURPLE if self.phase >= 3 else DANGER_RED
            pygame.draw.circle(glow, (*fc, alpha), (r * 5 // 2, r * 5 // 2), r * 2)
            surface.blit(glow, (cx - r * 5 // 2, cy - r * 5 // 2),
                         special_flags=pygame.BLEND_RGBA_ADD)

        # ── Phase 3 光暈 ─────────────────────────────────────────────
        if self.phase == 3:
            pulse_r = r + int(8 * math.sin(self._idle_pulse))
            glow    = pygame.Surface((r * 3, r * 3), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*WARN_ORANGE, 55), (r * 3 // 2, r * 3 // 2), pulse_r)
            surface.blit(glow, (cx - r * 3 // 2, cy - r * 3 // 2),
                         special_flags=pygame.BLEND_RGBA_ADD)

        # ── Enrage 光暈 ──────────────────────────────────────────────
        if self.enraged:
            glow = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*ENRAGE_PURPLE, 40), (r * 2, r * 2), r + 12)
            surface.blit(glow, (cx - r * 2, cy - r * 2),
                         special_flags=pygame.BLEND_RGBA_ADD)

        # ── 主體六邊形 ───────────────────────────────────────────────
        pts = []
        for i in range(6):
            a = a_rad + i * math.pi / 3
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        pygame.draw.polygon(surface, color,      pts)
        pygame.draw.polygon(surface, STEEL_DARK, pts, 3)

        # ── 尖刺 ─────────────────────────────────────────────────────
        spike_color = (ENRAGE_PURPLE if self.enraged
                       else DANGER_RED if self.phase >= 2
                       else STEEL_LIGHT)
        spike_len = 14 + int(4 * math.sin(self._idle_pulse * 2))
        for i in range(8):
            a  = a_rad + i * math.pi / 4
            x1 = cx + int(r * math.cos(a))
            y1 = cy + int(r * math.sin(a))
            x2 = cx + int((r + spike_len) * math.cos(a))
            y2 = cy + int((r + spike_len) * math.sin(a))
            pygame.draw.line(surface, spike_color, (x1, y1), (x2, y2), 3)

        # ── 眼睛 ─────────────────────────────────────────────────────
        eye_color = (ENRAGE_PURPLE if self.enraged
                     else DANGER_RED if self.phase >= 2
                     else STEEL_DARK)
        pygame.draw.circle(surface, eye_color, (cx, cy), 10)
        pygame.draw.circle(surface, ASH_WHITE,  (cx, cy), 10, 2)

        # ── 硬直閃光環（v1.8）────────────────────────────────────────
        if self.ai_state == 'staggered' and self._stagger_timer > 0:
            max_dur      = {1: 0.6, 2: 0.4, 3: 0.3}.get(self.phase, 0.4)
            s_alpha      = int(220 * (self._stagger_timer / max(0.01, max_dur)))
            stagger_surf = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
            pygame.draw.circle(stagger_surf, (255, 255, 100, s_alpha),
                               (r * 2, r * 2), r + 16, 5)
            surface.blit(stagger_surf, (cx - r * 2, cy - r * 2))
            pygame.draw.circle(surface, ENERGY_GOLD, (cx, cy), r + 4, 2)
            for i in range(6):
                a  = a_rad + i * math.pi / 3 * 2
                ex = cx + int((r + 8) * math.cos(a))
                ey = cy + int((r + 8) * math.sin(a))
                pygame.draw.circle(surface, WARN_ORANGE, (ex, ey), 5)

        # ── 衝刺預警瞄準線 ───────────────────────────────────────────
        if self.ai_state == 'pre_charge' and self.pre_charging:
            t          = max(0, 1.0 - self.pre_charge_timer / 0.45)
            line_alpha = int(60 + 180 * t)
            dx = self.aim_px - self.x; dy = self.aim_py - self.y
            d  = math.sqrt(dx*dx + dy*dy) or 1
            ex = int(self.x + dx / d * 1200)
            ey = int(self.y + dy / d * 1200)
            aim_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            pygame.draw.line(aim_surf,
                             (232, 64, 64, line_alpha),
                             (cx, cy), (ex, ey),
                             max(1, int(4 * t)))
            surface.blit(aim_surf, (0, 0))
            pygame.draw.circle(surface, DANGER_RED,
                               (int(self.aim_px), int(self.aim_py)),
                               int(22 * t), 2)

        # ── 鐳射前搖瞄準線 ───────────────────────────────────────────
        if self.ai_state == 'laser_pre' and self.laser_pre_active:
            t  = max(0, 1.0 - self.laser_pre_timer / 0.8)
            la = int(40 + 160 * t)
            ex = int(self.x + math.cos(self.laser_aim_angle) * 1200)
            ey = int(self.y + math.sin(self.laser_aim_angle) * 1200)
            ls = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            pygame.draw.line(ls,
                             (LASER_CYAN[0], LASER_CYAN[1], LASER_CYAN[2], la),
                             (cx, cy), (ex, ey),
                             max(1, int(3 * t)))
            surface.blit(ls, (0, 0))

        # ── 鐳射本體 ─────────────────────────────────────────────────
        if self.laser:
            self.laser.draw(surface)

        # ── 彈片 ─────────────────────────────────────────────────────
        for f in self.fragments:
            f.draw(surface)



# ══════════════════════════════════════════════════════════════════════
#  Afterimage  (L4 splinter_echo effect)
# ══════════════════════════════════════════════════════════════════════
class Afterimage:
    """
    殘影類別 - 由 splinter_echo 驅動產生，2秒後消失。
    碰觸敵人時造成 8 傷害（每敵一次）。
    """
    def __init__(self, x, y, lifetime=2.0):
        self.x = float(x)
        self.y = float(y)
        self.lifetime = lifetime  # Total lifetime in seconds
        self.max_lifetime = lifetime
        self.alive = True
        self.radius = 15  # Similar to player radius
        self.hit_enemies = set()  # Track which enemies have been hit (by ID)
    
    def update(self, dt):
        """Update lifetime and mark as dead when expired."""
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.alive = False
    
    def collides_with(self, enemy_x, enemy_y, enemy_radius):
        """Check collision with an enemy."""
        dx = self.x - enemy_x
        dy = self.y - enemy_y
        return dx*dx + dy*dy < (self.radius + enemy_radius) ** 2
    
    def draw(self, surface):
        """v1.7: Gold pulsing ghost for splinter_echo drive — clearly visible."""
        if not self.alive:
            return
        import time as _t
        progress = self.lifetime / self.max_lifetime   # 1.0 → 0.0

        pad    = 10
        r      = self.radius
        size   = r + pad
        s      = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        center = size

        # ── inner soft fill (golden tint) ────────────────────────────
        fill_alpha = int(55 * progress)
        pygame.draw.circle(s, (220, 180, 30, fill_alpha), (center, center), r)

        # ── main ring (gold → orange as it ages) ─────────────────────
        ring_alpha = int(210 * progress)
        if progress > 0.5:
            ring_col = (230, 210, 50, ring_alpha)
        else:
            ring_col = (255, 150, 30, ring_alpha)
        pygame.draw.circle(s, ring_col, (center, center), r, 2)

        # ── outer pulsing halo (fast flicker shows it's "alive") ─────
        pulse = 0.5 + 0.5 * math.sin(_t.time() * 10 + self.x * 0.05)
        halo_alpha = int(160 * progress * pulse)
        pygame.draw.circle(s, (255, 230, 80, halo_alpha), (center, center), r + 4, 1)

        # ── small center dot ─────────────────────────────────────────
        dot_alpha = int(180 * progress)
        pygame.draw.circle(s, (255, 255, 200, dot_alpha), (center, center), 3)

        surface.blit(s, (int(self.x) - size, int(self.y) - size))
class ArenaMine:
    """第五關靜止地雷，玩家靠近時爆炸。"""
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.radius = 16
        self.trigger_radius = 70   # 觸發距離 (v0.5: 60→70)
        self.alive = True
        self.exploding = False
        self.explode_timer = 0.3   # 爆炸前警示時間
        self.warned = False        # 是否已進入警示
        self.warn_timer = 0.0

    def update(self, dt, px, py):
        if not self.alive:
            return
        dx = px - self.x; dy = py - self.y
        dist = math.sqrt(dx*dx + dy*dy)

        if self.exploding:
            self.explode_timer -= dt
            if self.explode_timer <= 0:
                self.alive = False
        elif dist < self.trigger_radius:
            self.warned = True
            self.warn_timer += dt
            if self.warn_timer >= 0.4:   # 警示 0.4 秒後爆炸
                self.exploding = True
                self.explode_timer = 0.15
        else:
            self.warn_timer = max(0, self.warn_timer - dt * 2)
            if self.warn_timer == 0:
                self.warned = False

    def check_damage(self, px, py):
        """爆炸時檢查是否打中玩家，回傳傷害量或 0。"""
        if not self.exploding:
            return 0
        dx = px - self.x; dy = py - self.y
        if math.sqrt(dx*dx + dy*dy) < self.trigger_radius + 20:
            return 80   # 爆炸傷害 80 RPM
        return 0

    def draw(self, surface):
        if not self.alive:
            return
        cx, cy = int(self.x), int(self.y)

        if self.exploding:
            # 爆炸閃光
            r = int(self.trigger_radius * (1 + (0.3 - self.explode_timer) / 0.3))
            pygame.draw.circle(surface, WARN_ORANGE, (cx, cy), r)
            pygame.draw.circle(surface, ENERGY_GOLD, (cx, cy), r // 2)
        elif self.warned:
            # 警示閃爍（紅色）
            import time as _time
            flash = int(_time.time() * 8) % 2 == 0
            color = DANGER_RED if flash else WARN_ORANGE
            pygame.draw.circle(surface, color, (cx, cy), self.radius)
            # 警示圈
            alpha_r = int(self.trigger_radius * (self.warn_timer / 0.4))
            warn_surf = pygame.Surface((alpha_r*2+2, alpha_r*2+2), pygame.SRCALPHA)
            pygame.draw.circle(warn_surf, (232, 64, 64, 80),
                               (alpha_r+1, alpha_r+1), alpha_r, 2)
            surface.blit(warn_surf, (cx - alpha_r - 1, cy - alpha_r - 1))
        else:
            # 普通狀態
            pygame.draw.circle(surface, STEEL_MID, (cx, cy), self.radius)
            pygame.draw.circle(surface, DANGER_RED, (cx, cy), self.radius, 3)
            # 中心十字
            pygame.draw.line(surface, DANGER_RED,
                             (cx - 6, cy), (cx + 6, cy), 2)
            pygame.draw.line(surface, DANGER_RED,
                             (cx, cy - 6), (cx, cy + 6), 2)
