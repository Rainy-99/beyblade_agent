# constants.py

SCREEN_WIDTH = 1250
SCREEN_HEIGHT = 700
FPS = 60

# Play area
BORDER_WIDTH = 24
PLAY_LEFT = BORDER_WIDTH
PLAY_TOP = BORDER_WIDTH
PLAY_RIGHT = SCREEN_WIDTH - BORDER_WIDTH
PLAY_BOTTOM = SCREEN_HEIGHT - BORDER_WIDTH
PLAY_W = PLAY_RIGHT - PLAY_LEFT
PLAY_H = PLAY_BOTTOM - PLAY_TOP

# Player defaults
RPM_INIT = 800
RPM_MAX = 1000
RPM_DECAY = 22        # v0.9: 30→22 (strategy breathing room)
RPM_PER_SPIN = 85     # v0.9: 75→85 (spin feel more satisfying)
BASE_ATTACK = 3
PLAYER_SPEED = 288   # 240 × 1.2
PLAYER_RADIUS = 36
STUN_DURATION = 0.45
REBOUND_FACTOR = 6.0

# EXP to clear level
EXP_TO_CLEAR = 100

# Game states
STATE_TITLE = "title"
STATE_LEVEL_INTRO = "level_intro"
STATE_PLAYING = "playing"
STATE_PAUSED = "paused"
STATE_REWARD = "reward"
STATE_GAMEOVER = "gameover"
STATE_CLEAR_ANIM = "clear_anim"
STATE_FINAL = "final"

# Quadrant IDs (for spin detection)
# 0=top-right, 1=bottom-right, 2=bottom-left, 3=top-left
QUADRANT_SEQUENCE_CW  = [0, 1, 2, 3]
QUADRANT_SEQUENCE_CCW = [0, 3, 2, 1]

# ── Collision Sound Materials ──────────────────────────────────────────
MATERIAL_STEEL   = 'steel'    # 不鏽鋼/鈦合金 → clash_trimmed.wav
MATERIAL_WOOD    = 'wood'     # 木頭 → wood.wav
MATERIAL_PLASTIC = 'plastic'  # 塑膠 (L1) → plastic.wav

# ── Collision Recoil System ────────────────────────────────────────────
# 玩家材質 × 敵人材質 → 反作用力倍率
# 輕材撞硬材彈更遠；重材撞輕材幾乎不動
MATERIAL_RECOIL_MATRIX = {
    ('wood',  'wood'):    1.0,
    ('wood',  'steel'):   1.3,
    ('wood',  'titan'):   1.6,
    ('wood',  'plastic'): 0.8,
    ('wood',   None):     1.0,   # 無材質敵人視為中性
    ('steel', 'wood'):    0.8,
    ('steel', 'steel'):   1.0,
    ('steel', 'titan'):   1.2,
    ('steel', 'plastic'): 0.7,
    ('steel',  None):     0.9,
    ('titan', 'wood'):    0.6,
    ('titan', 'steel'):   0.75,
    ('titan', 'titan'):   1.0,
    ('titan', 'plastic'): 0.5,
    ('titan',  None):     0.7,
    (None,   'wood'):     1.0,   # 玩家無材質時的 fallback
    (None,   'steel'):    1.1,
    (None,   'titan'):    1.3,
    (None,   'plastic'):  0.9,
    (None,    None):      1.0,
}

RECOIL_WEAPON_HIT_MULT   = 0.5    # 武器碰撞反作用力較輕
RECOIL_SPEED_DIV         = 300.0  # 速度標準化基準（px/s）
RECOIL_SPEED_MIN         = 0.5    # 速度因子下限（慢速輕觸不暴衝）
RECOIL_SPEED_MAX         = 2.0    # 速度因子上限（高速碰撞更強）
RECOIL_ENEMY_HAMMER_MULT = 1.2    # 敵人錘子武器：重擊效果
RECOIL_ENEMY_SCYTHE_DEG  = 20.0   # 敵人鐮刀武器：側切偏轉角度（度）
RECOIL_ENEMY_STAFF_MULT  = 0.9    # 敵人法杖武器：力道稍輕
RECOIL_ENEMY_STAFF_STUN  = 0.2    # 敵人法杖武器：附加暈眩時間（秒）

# ── Critical Hit System ────────────────────────────────────────────────
CRIT_SPEED_THRESHOLD = 420.0   # 相對速度 (px/s) 門檻：超過即觸發爆擊
CRIT_DAMAGE_MULT     = 2.0     # 爆擊傷害倍率

