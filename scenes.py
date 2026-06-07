# scenes.py
import pygame
import random
import os
from colors import *
from constants import *

_deco_cache = {}
_bg_cache = {}
_overlay_surf = None

def _get_overlay():
    global _overlay_surf
    if _overlay_surf is None:
        _overlay_surf = pygame.Surface((PLAY_W, PLAY_H), pygame.SRCALPHA)
        _overlay_surf.fill((0, 0, 0, 110))
    return _overlay_surf

_BG_FILES = {
    1: 'Level1_bg.PNG',
    2: 'Level2_bg.PNG',
    3: 'Level3_bg.PNG',
    4: 'Level4_bg.PNG',
    5: 'Level5_bg.PNG',
}

def _get_bg(level):
    if level not in _bg_cache:
        img_dir = os.path.join(os.path.dirname(__file__), 'img')
        path = os.path.join(img_dir, _BG_FILES[level])
        try:
            raw = pygame.image.load(path).convert()
            _bg_cache[level] = pygame.transform.scale(raw, (PLAY_W, PLAY_H))
        except Exception:
            _bg_cache[level] = None
    return _bg_cache[level]

def _rgba(color, alpha):
    return (int(color[0]), int(color[1]), int(color[2]), max(0, min(255, int(alpha))))

def _get_deco(level):
    if level not in _deco_cache:
        _deco_cache[level] = _build_deco(level)
    return _deco_cache[level]

def _build_deco(level):
    """Pre-build static decoration surfaces."""
    deco = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    if level == 4:
        # Concentric rings (decorative)
        cx_s = (PLAY_LEFT + PLAY_RIGHT) // 2
        cy_s = (PLAY_TOP + PLAY_BOTTOM) // 2
        for radius in range(60, 480, 60):
            pygame.draw.circle(deco, _rgba((60, 180, 30), 18), (cx_s, cy_s), radius, 2)
    return deco

def draw_scene(surface, level, shrink=0):
    """Draw the background scene for a given level."""
    bg = _get_bg(level)
    if bg is not None:
        surface.blit(bg, (PLAY_LEFT, PLAY_TOP))
        surface.blit(_get_overlay(), (PLAY_LEFT, PLAY_TOP))
    else:
        floors = {1: SCENE_DOJO_FLOOR, 2: SCENE_BAMBOO_FLOOR,
                  3: SCENE_FACTORY_FLOOR, 4: SCENE_CIRCUIT_FLOOR, 5: SCENE_ARENA_FLOOR}
        floor_color = floors.get(level, STEEL_DARK)
        pygame.draw.rect(surface, floor_color,
                         (PLAY_LEFT, PLAY_TOP, PLAY_W, PLAY_H))

    deco = _get_deco(level)
    surface.blit(deco, (0, 0))

    border_colors = {1: WOOD_WARM, 2: (42, 74, 40), 3: STEEL_MID, 4: (20, 50, 20), 5: (90, 74, 58)}
    bc = border_colors.get(level, STEEL_MID)
    pygame.draw.rect(surface, bc, (0, 0, SCREEN_WIDTH, PLAY_TOP))
    pygame.draw.rect(surface, bc, (0, PLAY_BOTTOM, SCREEN_WIDTH, BORDER_WIDTH))
    pygame.draw.rect(surface, bc, (0, 0, PLAY_LEFT, SCREEN_HEIGHT))
    pygame.draw.rect(surface, bc, (PLAY_RIGHT, 0, BORDER_WIDTH, SCREEN_HEIGHT))
    pygame.draw.rect(surface, STEEL_LIGHT,
                     (PLAY_LEFT, PLAY_TOP, PLAY_W, PLAY_H), 2)


