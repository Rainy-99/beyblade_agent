# draw_utils.py
import pygame
import math
from colors import *

def draw_rounded_rect(surface, color, rect, radius=6, border=0, border_color=None):
    """Draw a rounded rectangle."""
    x, y, w, h = rect
    pygame.draw.rect(surface, color, (x + radius, y, w - 2*radius, h))
    pygame.draw.rect(surface, color, (x, y + radius, w, h - 2*radius))
    for cx, cy in [(x+radius, y+radius), (x+w-radius, y+radius),
                   (x+radius, y+h-radius), (x+w-radius, y+h-radius)]:
        pygame.draw.circle(surface, color, (cx, cy), radius)
    if border and border_color:
        pygame.draw.rect(surface, border_color, (x + radius, y, w - 2*radius, h), border)
        pygame.draw.rect(surface, border_color, (x, y + radius, w, h - 2*radius), border)
        for cx, cy in [(x+radius, y+radius), (x+w-radius, y+radius),
                       (x+radius, y+h-radius), (x+w-radius, y+h-radius)]:
            pygame.draw.circle(surface, border_color, (cx, cy), radius, border)

def draw_bar(surface, x, y, w, h, value, max_value, fg_color, bg_color=STEEL_MID, radius=4):
    """Draw a progress bar."""
    draw_rounded_rect(surface, bg_color, (x, y, w, h), radius)
    fill_w = int(w * max(0, min(1, value / max_value)))
    if fill_w > 0:
        draw_rounded_rect(surface, fg_color, (x, y, fill_w, h), radius)

def draw_text(surface, text, font, color, x, y, align="left", shadow=None, shadow_color=None):
    """Draw text with optional shadow."""
    rendered = font.render(str(text), True, color)
    rect = rendered.get_rect()
    if align == "center":
        rect.centerx = x
        rect.top = y
    elif align == "right":
        rect.right = x
        rect.top = y
    else:
        rect.left = x
        rect.top = y
    if shadow_color is not None:
        shadow_surf = font.render(str(text), True, shadow_color)
        surface.blit(shadow_surf, (rect.x + 1, rect.y + 1))
    elif shadow:
        shadow_surf = font.render(str(text), True, shadow[0])
        surface.blit(shadow_surf, (rect.x + shadow[1], rect.y + shadow[2]))
    surface.blit(rendered, rect)
    return rect

def draw_gear(surface, color, cx, cy, outer_r, inner_r, teeth, angle=0):
    """Draw a gear shape."""
    points = []
    tooth_count = teeth
    for i in range(tooth_count * 2):
        a = angle + math.pi * i / tooth_count
        r = outer_r if i % 2 == 0 else inner_r
        points.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    if len(points) >= 3:
        pygame.draw.polygon(surface, color, points)

def lerp_color(c1, c2, t):
    """Linearly interpolate between two colors."""
    t = max(0, min(1, t))
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))

def alpha_surf(w, h, color, alpha):
    """Create a surface with given color and alpha."""
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    s.fill(rgba(color, alpha))
    return s

def rgba(color, alpha):
    """Safely build an (R, G, B, A) tuple from a color tuple and alpha int."""
    r = int(color[0]); g = int(color[1]); b = int(color[2])
    a = max(0, min(255, int(alpha)))
    return (r, g, b, a)
