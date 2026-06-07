# particles.py
import pygame
import math
import random
import time as _time
from colors import *


# ── Drive ability ring effect ─────────────────────────────────────────────
class DriveRing:
    """
    Expanding ring overlay for drive ability visual feedback.
    delay: seconds before the ring starts expanding (for staggered bursts).
    """
    def __init__(self, x, y, color, max_radius, duration, width=3, delay=0.0):
        self.x          = float(x)
        self.y          = float(y)
        self.color      = color
        self.max_radius = max_radius
        self.duration   = duration
        self.width      = width
        self.age        = -delay
        self.alive      = True

    def update(self, dt):
        self.age += dt
        if self.age >= self.duration:
            self.alive = False

    def draw(self, surface):
        if self.age < 0:
            return
        t      = self.age / self.duration
        radius = int(self.max_radius * t)
        alpha  = max(0, int(230 * (1.0 - t ** 0.7)))
        if radius < 1 or alpha == 0:
            return
        size = radius + self.width + 2
        s    = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        r, g, b = self.color
        pygame.draw.circle(s, (r, g, b, alpha), (size, size), radius, self.width)
        surface.blit(s, (int(self.x) - size, int(self.y) - size))


class Particle:
    def __init__(self, x, y, vx, vy, color, size, lifetime):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.size = size
        self.lifetime = lifetime
        self.age = 0

    def update(self, dt):
        self.age += dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 80 * dt  # slight gravity

    def draw(self, surface):
        t = self.age / self.lifetime
        alpha = max(0, min(255, int(255 * (1.0 - t))))
        size = max(1, int(self.size * (1.0 - t * 0.8)))  # don't shrink to 0
        if alpha == 0:
            return
        r = max(0, min(255, int(self.color[0])))
        g = max(0, min(255, int(self.color[1])))
        b = max(0, min(255, int(self.color[2])))
        s = pygame.Surface((size*2+2, size*2+2), pygame.SRCALPHA)
        pygame.draw.circle(s, (r, g, b, alpha), (size, size), size)
        surface.blit(s, (int(self.x) - size, int(self.y) - size))

    @property
    def alive(self):
        return self.age < self.lifetime


class ParticleSystem:
    def __init__(self):
        self.particles   = []
        self.drive_rings = []   # v1.7: drive ability ring effects

    def emit(self, x, y, count, color, speed_range=(60,160), size_range=(2,5),
             lifetime_range=(0.4, 1.0), angle_range=(0, 360)):
        for _ in range(count):
            angle = math.radians(random.uniform(*angle_range))
            speed = random.uniform(*speed_range)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            size = random.uniform(*size_range)
            lt = random.uniform(*lifetime_range)
            self.particles.append(Particle(x, y, vx, vy, color, size, lt))

    def emit_spark(self, x, y, direction, count=6):
        """Emit collision sparks in a direction."""
        base_angle = math.degrees(math.atan2(direction[1], direction[0]))
        for _ in range(count):
            angle = math.radians(base_angle + random.uniform(-40, 40))
            speed = random.uniform(80, 200)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            self.particles.append(Particle(x, y, vx, vy, ASH_WHITE,
                                           random.uniform(2, 5), 0.15))

    # ── v1.7: drive ability visual effects ───────────────────────────────

    def emit_recoil_ring(self, x, y):
        """Green absorbing ring for recoil_dampener — single tight pulse."""
        self.drive_rings.append(DriveRing(x, y, (80, 240, 40), 48, 0.28, width=3))

    def emit_shockwave_ring(self, x, y):
        """Three staggered blue expanding rings for shockwave."""
        for i in range(3):
            self.drive_rings.append(
                DriveRing(x, y, (100, 170, 255), 130, 0.45, width=2, delay=i * 0.07))

    def emit_splinter_burst(self, x, y):
        """Gold spark burst for splinter_echo kill / boss hit."""
        self.emit(x, y, 14, (220, 200, 40),
                  speed_range=(50, 200), size_range=(2, 5),
                  lifetime_range=(0.25, 0.65))
        # inner bright white flash ring
        self.drive_rings.append(DriveRing(x, y, (255, 240, 160), 36, 0.20, width=2))

    # ─────────────────────────────────────────────────────────────────────

    def emit_clear(self, x, y):
        """Emit level clear particles."""
        self.emit(x, y, 28, ENERGY_GOLD, (80, 160), (3, 6), (0.8, 1.2))

    def emit_bamboo_grow(self, x, y):
        self.emit(x, y, 5, SUCCESS_GREEN, (40, 80), (2, 4), (0.3, 0.6),
                  angle_range=(220, 320))

    def emit_gear_merge(self, x, y):
        for _ in range(12):
            angle = math.radians(random.uniform(0, 360))
            speed = random.uniform(60, 150)
            self.particles.append(Particle(x, y, math.cos(angle)*speed,
                                           math.sin(angle)*speed,
                                           WARN_ORANGE, random.uniform(3, 6), 0.25))

    def update(self, dt):
        for p in self.particles:
            p.update(dt)
        for r in self.drive_rings:
            r.update(dt)
        self.particles   = [p for p in self.particles if p.alive]
        self.drive_rings = [r for r in self.drive_rings if r.alive]

    def draw(self, surface):
        # rings drawn first (behind particles)
        for r in self.drive_rings:
            r.draw(surface)
        for p in self.particles:
            p.draw(surface)

class DamageNumber:
    """碰撞時在敵人頭上浮現的傷害數字。"""
    def __init__(self, x, y, amount, crit=False):
        self.x        = float(x)
        self.y        = float(y)
        self.amount   = float(amount)
        self.crit     = crit
        self.age      = 0.0
        self.lifetime = 0.9 if crit else 0.7
        self.vy       = -90 if crit else -70
        self.vx       = random.uniform(-18, 18)
 
    def update(self, dt):
        self.age += dt
        self.y   += self.vy * dt
        self.x   += self.vx * dt
        self.vy  *= max(0, 1 - 4 * dt)
 
    @property
    def alive(self):
        return self.age < self.lifetime
 
    def draw(self, surface, font_sm, font_md):
        t     = self.age / self.lifetime
        alpha = max(0, int(255 * (1.0 - t ** 1.5)))
        amt_str = f"{self.amount:.1f}" if self.amount % 1 else str(int(self.amount))
        if self.crit:
            font  = font_md
            color = (255, 140, 0)   # 亮橘色
            text  = f"-{amt_str}"
        else:
            font  = font_sm
            color = ENERGY_GOLD
            text  = f"-{amt_str}"
        surf    = font.render(text, True, color)
        outline = font.render(text, True, (0, 0, 0))
        if self.crit:
            # 放大至 1.4× 一般數字（font_sm=20px, 目標=28px, 從 font_md 24px ×1.17）
            w, h = surf.get_size()
            nw, nh = int(w * 1.17), int(h * 1.17)
            surf    = pygame.transform.smoothscale(surf,    (nw, nh))
            outline = pygame.transform.smoothscale(outline, (nw, nh))
        surf.set_alpha(alpha)
        outline.set_alpha(alpha // 2)
        bx = int(self.x) - surf.get_width() // 2
        by = int(self.y)
        surface.blit(outline, (bx + 1, by + 1))
        surface.blit(surf,    (bx,     by))
 
 
class DamageNumberSystem:
    """管理所有浮動傷害數字。"""
    def __init__(self):
        self.numbers: list[DamageNumber] = []
 
    def emit(self, x, y, amount, crit=False):
        offset_x = random.uniform(-10, 10)
        self.numbers.append(DamageNumber(x + offset_x, y - 20, amount, crit))
 
    def update(self, dt):
        self.numbers = [n for n in self.numbers if n.alive]
        for n in self.numbers:
            n.update(dt)
 
    def draw(self, surface, font_sm, font_md):
        for n in self.numbers:
            n.draw(surface, font_sm, font_md)
 
class Afterimage:
    """Player dash afterimage effect."""
    def __init__(self):
        self.images = []  # list of (surface, x, y, age, lifetime)

    def add(self, surf, x, y):
        self.images.append([surf.copy(), x, y, 0, 0.3])

    def update(self, dt):
        for img in self.images:
            img[3] += dt
        self.images = [i for i in self.images if i[3] < i[4]]

    def draw(self, surface):
        for surf, x, y, age, lt in self.images:
            t = age / lt
            alpha = int(180 * (1 - t))
            surf.set_alpha(alpha)
            surface.blit(surf, (int(x) - surf.get_width()//2,
                                int(y) - surf.get_height()//2))
