# screens.py
import os
import pygame
import math
import time
from colors import *
from constants import *
import draw_utils as du

# ── Reward definitions ────────────────────────────────────────────────────

REWARDS = {
    1: [
        {
            'id': 'wood', 'name': '木頭陀螺',
            'desc': ['降速 -10%', '攻擊力 x0.8', '穩健型打法'],
            'type': 'material', 'color': WOOD_WARM
        },
        {
            'id': 'steel', 'name': '不鏽鋼陀螺',
            'desc': ['降速 +5 %', '攻擊力 x1.2', '萬能通用型'],
            'type': 'material', 'color': STEEL_CHROME
        },
        {
            'id': 'titan', 'name': '鈦合金陀螺',
            'desc': ['降速 +18%', '攻擊力 x1.5', '速攻激進型'],
            'type': 'material', 'color': TITAN_DARK
        },
    ],
    2: [
        {
            'id': 'scythe', 'name': '鐮刀',
            'desc': ['攻擊力 +5', '攻擊範圍 +16px', '雙刃對稱'],
            'type': 'weapon', 'color': STEEL_CHROME
        },
        {
            'id': 'staff', 'name': '金箍棒',
            'desc': ['攻擊力 +2', '攻擊範圍 +28px', '四方向延伸'],
            'type': 'weapon', 'color': ENERGY_GOLD
        },
        {
            'id': 'hammer', 'name': '重鎚',
            'desc': ['攻擊力 +8', '攻擊範圍 +36px', '補速效率 /2', '降速速度 x1.15'],  # v0.5 balance
            'type': 'weapon', 'color': STEEL_LIGHT
        },
    ],
    3: [
        {
            'id': 'axis', 'name': '鋼鐵軸心',
            'desc': ['最高轉速 +10%', '受擊降速 -25%', '防禦型配件'],
            'type': 'accessory', 'color': STEEL_LIGHT
        },
        {
            'id': 'gear_ring', 'name': '齒輪外環',
            'desc': ['碰撞額外 +5 傷害', '受擊降速 -15%', '攻防兼備'],
            'type': 'accessory', 'color': WOOD_WARM
        },
        {
            'id': 'dash_tape', 'name': '衝刺卡帶',
            'desc': ['連走2.5秒觸發衝刺', '衝刺200px/600px/s', '衝刺1秒無敵'],  # v0.5: 3→2.5s
            'type': 'accessory', 'color': SPIN_BLUE
        },
    ],
    4: [
        {
            'id': 'recoil_dampener', 'name': '反震阻尼',
            'desc': ['被彈開的反作用力 -45%', '碰撞後 0.3s 受傷 -15%', '穩定控制'],  # v0.5 buffer
            'type': 'drive', 'color': (80, 240, 40)
        },
        {
            'id': 'shockwave', 'name': '衝擊波',
            'desc': ['撞擊敵人時發出衝擊波', '範圍 120px 內額外 15 傷害', '連鎖清場'],
            'type': 'drive', 'color': (120, 160, 255)
        },
        {
            'id': 'splinter_echo', 'name': '碎片殘響',
            'desc': ['擊殺後留下殘影 2 秒', '殘影碰觸敵人造成 5 傷害', '連鎖分裂'],  # v0.5: 8→5
            'type': 'drive', 'color': (220, 200, 40)
        },
    ],
    5: [
        {
            'id': 'chaos', 'name': '混沌核心',
            'desc': ['擊殺時爆衝擊波', '波及周圍敵人10傷害', '崩解之力'],
            'type': 'core', 'color': (128, 96, 255)
        },
        {
            'id': 'shield', 'name': '魔王的盾',
            'desc': ['30%機率完全無效化降速', '被動防禦', '抵抗之力'],
            'type': 'core', 'color': STEEL_SHINE
        },
        {
            'id': 'crown', 'name': '廢墟王冠',
            'desc': ['低轉速時傷害提升', '轉速<30%傷害最多+50%', '壓制之力'],
            'type': 'core', 'color': (176, 168, 152)
        },
    ],
}

# ── 新型人格系統：獎勵權重矩陣 ────────────────────────────────────

REWARD_WEIGHTS = {
    # 第1關：材質選擇
    'wood': {'CTRL': 3, 'AGGR': 0, 'SURV': 3, 'RISK': 0, 'FLEX': 0, 'TEMPO': 1},  # v0.5: SURV 2→3
    'steel': {'CTRL': 0, 'AGGR': 1, 'SURV': 0, 'RISK': 0, 'FLEX': 3, 'TEMPO': 2},
    'titan': {'CTRL': 0, 'AGGR': 3, 'SURV': 0, 'RISK': 2, 'FLEX': 0, 'TEMPO': 1},
    
    # 第2關：武器選擇
    'scythe': {'CTRL': 2, 'AGGR': 3, 'SURV': 0, 'RISK': 0, 'FLEX': 1, 'TEMPO': 0},
    'staff': {'CTRL': 2, 'AGGR': 1, 'SURV': 0, 'RISK': 0, 'FLEX': 3, 'TEMPO': 0},
    'hammer': {'CTRL': 0, 'AGGR': 3, 'SURV': 1, 'RISK': 2, 'FLEX': 0, 'TEMPO': 0},
    
    # 第3關：配件選擇
    'axis': {'CTRL': 3, 'AGGR': 0, 'SURV': 3, 'RISK': 0, 'FLEX': 0, 'TEMPO': 2},
    'gear_ring': {'CTRL': 0, 'AGGR': 2, 'SURV': 2, 'RISK': 0, 'FLEX': 3, 'TEMPO': 0},  # v0.5: SURV 1→2
    'dash_tape': {'CTRL': 0, 'AGGR': 2, 'SURV': 0, 'RISK': 3, 'FLEX': 0, 'TEMPO': 2},
    
    # 第4關：驅動選擇
    'recoil_dampener': {'CTRL': 3, 'AGGR': 0, 'SURV': 3, 'RISK': 0, 'FLEX': 0, 'TEMPO': 2},  # v0.5: SURV 2→3
    'shockwave': {'CTRL': 0, 'AGGR': 3, 'SURV': 0, 'RISK': 2, 'FLEX': 1, 'TEMPO': 0},
    'splinter_echo': {'CTRL': 0, 'AGGR': 2, 'SURV': 1, 'RISK': 3, 'FLEX': 0, 'TEMPO': 0},
    
    # 第5關：核心選擇
    'chaos': {'CTRL': 0, 'AGGR': 3, 'SURV': 0, 'RISK': 3, 'FLEX': 0, 'TEMPO': 1},
    'shield': {'CTRL': 2, 'AGGR': 0, 'SURV': 3, 'RISK': 1, 'FLEX': 0, 'TEMPO': 0},
    'crown': {'CTRL': 0, 'AGGR': 2, 'SURV': 3, 'RISK': 0, 'FLEX': 0, 'TEMPO': 3},
}

# v0.5: 道具心理傾向小標籤（在獎勵畫面顯示，幫助玩家感知心理維度）
REWARD_PSYCHE_TAGS = {
    'wood':             '[ 穩定信號 ]',
    'steel':            '[ 廣域評估 ]',
    'titan':            '[ 高波動 ]',
    'scythe':           '[ 前壓型 ]',
    'staff':            '[ 校準型 ]',
    'hammer':           '[ 爆發風險 ]',
    'axis':             '[ 韌性核心 ]',
    'gear_ring':        '[ 攻防均衡 ]',
    'dash_tape':        '[ 節奏賭注 ]',
    'recoil_dampener':  '[ 韌性核心 ]',
    'shockwave':        '[ 前壓型 ]',
    'splinter_echo':    '[ 高波動 ]',
    'chaos':            '[ 混沌爆發 ]',
    'shield':           '[ 防禦核心 ]',
    'crown':            '[ 節拍守護 ]',
}

# 主人格標籤文案
PRIMARY_ARCHETYPES = {
    'CTRL':  '穩健型',
    'AGGR':  '侵略型',
    'SURV':  '續戰型',
    'RISK':  '膽識型',
    'FLEX':  '靈活型',
    'TEMPO': '節奏型',
}

# 副人格修飾語對照
SECONDARY_MODIFIERS = {
    'RISK':  '膽識型',
    'AGGR':  '侵略型',
    'SURV':  '續戰型',
    'CTRL':  '穩健型',
    'FLEX':  '靈活型',
    'TEMPO': '節奏型',
}

# 組合描述文案庫
PERSONALITY_DESCRIPTIONS = {
    ('CTRL', 'RISK'): '你表面上是一個喜歡掌控局面的人。但系統在你的選擇紀錄裡發現了另一件事：你偶爾會押一個旁人不會押的注。這不矛盾——這代表你的控場，不是來自迴避風險，而是來自對風險有自己的計算方式。系統偵測到對立傾向共存。這類玩家通常比他們自己意識到的更難被預判。',
    
    ('AGGR', 'RISK'): '你的選擇傳遞了一個很清晰的訊號：你不打算讓局面慢慢演變。你要在它還沒展開之前就介入。這種打法要求你對時機的判斷非常準確。你選擇了可以爆發的工具，也接受它們帶來的不穩定。你知道自己在賭什麼——你只是覺得這個賭注值得。系統標記：此類型玩家的關鍵時刻決策速度顯著高於平均。',
    
    ('CTRL', 'SURV'): '你的選擇組合在說一件事：你不怕打持久戰。你不依賴單一的爆發點，也不假設局面會迅速結束。你在建構一個即便被打、被干擾，也能繼續運作的系統。這讓你在混亂的局面裡比大多數人更沉得住氣。系統標記：此類型玩家在長局的勝率隨時間遞增。',
    
    ('SURV', 'AGGR'): '你不是防守型玩家——你只是用防守的方式在進攻。你的邏輯是：先讓自己撐下去，然後在對方以為你快倒的時候反擊。這需要一種特殊的耐心，和對時機的敏銳感。你的選擇顯示你兩樣都有。系統標記：此類型玩家的反擊頻率在低轉速狀態下不降反升。',
    
    ('RISK', 'AGGR'): '你選的東西，每一個都在等一個條件成立。一旦成立，你要確保它的輸出是最大的。這種策略看起來像是在賭，但你心裡有一套清楚的邏輯：在正確的時機爆發一次，比分散風險打十次更有效率。系統觀察到你一直在等那個時機。系統標記：此類型玩家的單回合峰值傷害為所有類型最高。',
    
    ('FLEX', 'CTRL'): '你不容易被定義，這本身就是你的優勢。你的選擇顯示你在評估的不是「這個最強」，而是「這個在最多情況下不會是最弱的」。你在最佳化的是下限，不是上限。這讓你在大多數情境下都能保持穩定發揮。系統標記：此類型玩家的表現在不同關卡設計間的方差最低。',
    
    ('TEMPO', 'SURV'): '你把轉速當作一個需要守護的東西——不是因為你害怕降速，而是因為你知道轉速代表你還在掌握節奏。你的配置告訴系統：即便被打，被干擾，你仍然有辦法繼續執行你的計劃。這種穩定性不是偶然，是你有意識地選擇出來的結果。系統標記：此類型玩家在受擊後的恢復速度高於平均。',
    
    ('AGGR', 'TEMPO'): '你的選擇裡有一個其他玩家不一定看得出來的邏輯：你在等自己的狀態到位，然後再出手。你不是亂衝的那種激進——你的每一次施壓背後，都有一個你自己才清楚的時機判斷。你看起來很快，但其實你一直在等。系統標記：此類型玩家的輸出爆發窗口集中在轉速峰值前後 1.5 秒。',
    
    ('CTRL', 'FLEX'): '你在建構的不是一個「最強」的配置，而是一個在最多情況下都不會崩潰的配置。你偏好穩定，但你也知道死守一個策略是危險的。所以你留了後路——你的選擇裡始終有那麼一點彈性，讓你在局面變化時有辦法應對。系統標記：此類型玩家在中後期局面的決策失誤率顯著低於平均。',
    
    ('RISK', 'TEMPO'): '你的選擇透露了一個矛盾的特質：你接受不確定性，但你又同時在追蹤一個非常具體的指標。你不是隨機的——你的波動是有條件的。你在等一個轉速窗口，等一個觸發條件。在那個條件成立之前，你看起來很難預測。在那之後，你完全清楚自己要做什麼。系統標記：此類型玩家的行為在特定轉速閾值前後呈現明顯分歧。',
    
    ('FLEX', 'FLEX'): '你在這5關的選擇沒有收斂到一個明確的方向——但這本身就是一個很清楚的訊號。你一直在做的，是評估。不是因為你不知道自己要什麼，而是因為你的判斷告訴你：太早確定方向，是一種風險。你在等一個你自己才知道的時機點，才會完全亮出手牌。系統標記：此類型玩家通常在遊戲後期才展現出完整的策略意圖。',
    
    ('SURV', 'TEMPO'): '你對「轉速低」這件事，有一種其他玩家沒有的從容。不是因為你不在意——而是因為你的整個配置，就是為了在轉速低的狀態下也能繼續打。你把別人視為劣勢的狀態，變成了你自己的運作環境。這是一種需要時間才能理解的策略。系統標記：此類型玩家在低轉速狀態下的傷害輸出高於所有類型平均。',

    # ── v0.5 新增：補足高頻缺失組合，降低 fallback 觸發率 ─────────────────

    ('SURV', 'CTRL'): '你在建造的不是一個攻擊引擎——你在建造一個堡壘。你的選擇告訴系統：你不想在局面還沒明朗之前就耗盡資源。你把「撐住」本身當作一種主動行為，而不是被動退守。這種玩法對大多數人來說需要相當的耐心，而你的配置顯示你已經有了。系統標記：此類型玩家的平均存活時間在所有類型中排名第一。',

    ('SURV', 'RISK'): '你接受「現在受傷」的成本，因為你相信你之後還會在場上。你的防守不是因為你怕——而是因為你要確保你的高波動操作有足夠的底氣去執行。你把韌性當作槓桿，不是盾牌。系統標記：此類型玩家在高傷害情境下的連續作戰能力顯著高於平均。',

    ('CTRL', 'AGGR'): '你有控場能力，但你不打算只用它來防守。你的選擇顯示你把局面的穩定性當作一個出手的條件——一旦條件成立，你要確保輸出是有效的。你看起來像在等待，但其實你一直在準備。系統標記：此類型玩家在局面轉折點的輸出轉換速度高於平均。',

    ('TEMPO', 'FLEX'): '你有一種很特殊的感知方式：你在追蹤一個具體的節奏閾值，但你同時保持著廣域的觀察。你不會固執地執行一個計劃——你在等那個計劃需要更新的時機，然後立刻調整。這讓你的行為在旁人眼中看起來有點難以預測。系統標記：此類型玩家的策略轉換成功率在所有類型中最高。',

    ('FLEX', 'SURV'): '你的評估不是在找最強的選擇——你在找最不容易崩潰的路線。你把生存能力當作評估框架的基礎，然後在這個框架內選擇最靈活的配置。這讓你的策略既有韌性又有彈性。系統標記：此類型玩家在長時間局面中的狀態保持能力優於平均。',

    ('FLEX', 'AGGR'): '你保留了評估的空間，但你同時傾向於在條件對的時候快速施壓。你不是那種會猶豫很久的玩家——你在等的，是一個讓你確信「現在出手是對的」的時機。系統標記：此類型玩家的攻擊決策窗口比單純的前壓型更精準。',

    ('RISK', 'CTRL'): '你押注，但你押的是有把握的注。你的選擇顯示你在容忍波動的同時，也在為那些波動建立緩衝。你不是隨機的——你的風險是被計算過的。系統標記：此類型玩家的高風險操作失敗後的復原速度高於平均。',

    ('TEMPO', 'AGGR'): '你有一個很精確的攻擊節奏。你不在意一直在施壓——你在意的是每一次出手都在轉速正確的時機。你的攻擊性是有條件的，這讓它比單純的衝刺更有效率。系統標記：此類型玩家的有效命中率在攻擊型類型中最高。',

    ('AGGR', 'CTRL'): '你在主動施壓，但你的施壓方式不是亂打——你在用一套你自己清楚的邏輯在推進局面。你想要控制的不只是自己的狀態，還有整個戰場的節奏。這種組合在別人眼裡看起來很霸氣，但背後有你自己的計算。系統標記：此類型玩家的位移控制能力在攻擊型類型中最強。',

    ('AGGR', 'SURV'): '你在最大化輸出的同時，也在確保你還留著力氣繼續打。你不是那種全押一把的玩家——你想要的是可以一直打下去的能力。系統標記：此類型玩家的持續輸出能力顯著高於純攻擊型玩家。',
}


def draw_beyblade_preview(surface, cx, cy, r, angle_rad, reward_id, level):
    """Draw a spinning beyblade preview for a reward card."""
    # Base disc color
    if level == 1:
        if reward_id == 'wood':
            pygame.draw.circle(surface, WOOD_WARM, (cx, cy), r)
            # 4 radial grain lines
            for i in range(4):
                a = angle_rad + i * math.pi / 2
                x1 = cx + int(r * 0.2 * math.cos(a))
                y1 = cy + int(r * 0.2 * math.sin(a))
                x2 = cx + int(r * 0.85 * math.cos(a))
                y2 = cy + int(r * 0.85 * math.sin(a))
                pygame.draw.line(surface, WOOD_GRAIN, (x1, y1), (x2, y2), 1)
            # 3 notch circles
            for i in range(3):
                a = angle_rad + i * 2 * math.pi / 3
                nx = cx + int(r * 0.9 * math.cos(a))
                ny = cy + int(r * 0.9 * math.sin(a))
                pygame.draw.circle(surface, VOID_BLACK, (nx, ny), 2)
        elif reward_id == 'steel':
            pygame.draw.circle(surface, STEEL_CHROME, (cx, cy), r)
            # 8 thin radial lines with alpha
            line_surf = pygame.Surface((r * 3, r * 3), pygame.SRCALPHA)
            for i in range(8):
                a = angle_rad + i * math.pi / 4
                lx1 = int(r * 0.2 * math.cos(a))
                ly1 = int(r * 0.2 * math.sin(a))
                lx2 = int(r * 0.85 * math.cos(a))
                ly2 = int(r * 0.85 * math.sin(a))
                pygame.draw.line(line_surf, (int(STEEL_SHINE[0]), int(STEEL_SHINE[1]), int(STEEL_SHINE[2]), 60),
                                (lx1 + r, ly1 + r), (lx2 + r, ly2 + r), 1)
            surface.blit(line_surf, (cx - r, cy - r), special_flags=pygame.BLEND_RGBA_ADD)
        elif reward_id == 'titan':
            pygame.draw.circle(surface, TITAN_DARK, (cx, cy), r)
            pygame.draw.circle(surface, TITAN_BLUE, (cx, cy), r, 2)
            # 6 radial lines
            for i in range(6):
                a = angle_rad + i * math.pi / 3
                x1 = cx + int(r * 0.2 * math.cos(a))
                y1 = cy + int(r * 0.2 * math.sin(a))
                x2 = cx + int(r * 0.85 * math.cos(a))
                y2 = cy + int(r * 0.85 * math.sin(a))
                pygame.draw.line(surface, TITAN_BLUE, (x1, y1), (x2, y2), 1)
    elif level == 2:
        # Base steel disc
        pygame.draw.circle(surface, STEEL_CHROME, (cx, cy), r)
        if reward_id == 'scythe':
            # 2 symmetric curved blades
            blade_pts1 = []
            blade_pts2 = []
            for j in range(11):
                t = j / 10.0
                a = angle_rad + t * math.pi * 0.6
                dist = r + 5 + t * 15
                bx = int(cx + dist * math.cos(a))
                by = int(cy + dist * math.sin(a))
                blade_pts1.append((bx, by))
            for j in range(11):
                t = j / 10.0
                a = angle_rad + math.pi + t * math.pi * 0.6
                dist = r + 5 + t * 15
                bx = int(cx + dist * math.cos(a))
                by = int(cy + dist * math.sin(a))
                blade_pts2.append((bx, by))
            if len(blade_pts1) > 1:
                pygame.draw.lines(surface, STEEL_CHROME, False, blade_pts1, 3)
            if len(blade_pts2) > 1:
                pygame.draw.lines(surface, STEEL_CHROME, False, blade_pts2, 3)
        elif reward_id == 'staff':
            # 4 gold rods at 90° intervals
            for i in range(4):
                a = angle_rad + i * math.pi / 2
                x1 = cx + int(r * math.cos(a))
                y1 = cy + int(r * math.sin(a))
                x2 = cx + int((r + 28) * math.cos(a))
                y2 = cy + int((r + 28) * math.sin(a))
                pygame.draw.line(surface, ENERGY_GOLD, (x1, y1), (x2, y2), 4)
                pygame.draw.circle(surface, ENERGY_GOLD, (x2, y2), 3)
        elif reward_id == 'hammer':
            # Hammer head and handle
            a = angle_rad
            hx = cx + int((r + 36) * math.cos(a))
            hy = cy + int((r + 36) * math.sin(a))
            # Hammer head (grey rectangle)
            head_w, head_h = 16, 10
            head_cos = math.cos(a)
            head_sin = math.sin(a)
            handle_pts = [(cx, cy), (hx - int(6 * head_sin), hy + int(6 * head_cos))]
            pygame.draw.line(surface, WOOD_GRAIN, handle_pts[0], handle_pts[1], 3)
            pygame.draw.rect(surface, STEEL_MID, (hx - head_w//2, hy - head_h//2, head_w, head_h))
    elif level == 3:
        pygame.draw.circle(surface, STEEL_CHROME, (cx, cy), r)
        if reward_id == 'axis':
            pygame.draw.circle(surface, STEEL_LIGHT, (cx, cy), 8)
            pygame.draw.circle(surface, STEEL_LIGHT, (cx, cy), 8, 2)
        elif reward_id == 'gear_ring':
            du.draw_gear(surface, WOOD_WARM, cx, cy, r + 10, r + 4, 12, angle_rad)
        elif reward_id == 'dash_tape':
            # Cassette tape
            pygame.draw.rect(surface, VOID_BLACK, (cx - 8, cy - 5, 16, 10), border_radius=2)
            pygame.draw.rect(surface, SPIN_BLUE, (cx - 6, cy - 3, 5, 6))
            pygame.draw.rect(surface, ENERGY_GOLD, (cx + 1, cy - 3, 5, 6))
            # Glow ring (smaller to prevent clipping)
            glow_size = int(r * 2.2)
            glow_surf = pygame.Surface((glow_size, glow_size), pygame.SRCALPHA)
            glow_center = glow_size // 2
            pygame.draw.circle(glow_surf, (int(SPIN_BLUE_GLOW[0]), int(SPIN_BLUE_GLOW[1]), int(SPIN_BLUE_GLOW[2]), 60),
                              (glow_center, glow_center), int(r * 0.8))
            surface.blit(glow_surf, (cx - glow_center, cy - glow_center), special_flags=pygame.BLEND_RGBA_ADD)
    elif level == 4:
        pygame.draw.circle(surface, (30, 40, 55), (cx, cy), r)
        if reward_id == 'recoil_dampener':
            # 減震彈簧紋：兩條平行弧線
            for sign in [-1, 1]:
                spring_pts = []
                for si in range(7):
                    t_s = si / 6.0
                    sx = cx + sign * int(r * 0.35) + int(r * 0.25 * math.cos(angle_rad + t_s * math.pi * 2))
                    sy = cy - int(r * 0.6) + int(r * 1.2 * t_s)
                    spring_pts.append((sx, sy))
                if len(spring_pts) > 1:
                    pygame.draw.lines(surface, (80, 240, 40), False, spring_pts, 2)
            pygame.draw.circle(surface, (80, 240, 40), (cx, cy), r, 2)
        elif reward_id == 'shockwave':
            # 衝擊波同心圓
            for i in range(3):
                wave_r = int(r * (0.3 + i * 0.25))
                wave_surf = pygame.Surface((r*3, r*3), pygame.SRCALPHA)
                alpha_w = 200 - i * 50
                pygame.draw.circle(wave_surf, (120, 160, 255, alpha_w),
                                   (r, r), wave_r, 2)
                surface.blit(wave_surf, (cx - r, cy - r))
        elif reward_id == 'splinter_echo':
            # 殘影圓
            for i in range(3):
                a2 = angle_rad + i * 2 * math.pi / 3
                ex = cx + int(r * 0.7 * math.cos(a2))
                ey = cy + int(r * 0.7 * math.sin(a2))
                ghost_s = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
                pygame.draw.circle(ghost_s, (220, 200, 40, 80), (r, r), r // 2)
                surface.blit(ghost_s, (ex - r, ey - r))
    elif level == 5:
        pygame.draw.circle(surface, STEEL_CHROME, (cx, cy), r)
        if reward_id == 'chaos':
            # 4 crack lines from center
            for i in range(4):
                a = angle_rad + i * math.pi / 2
                x1 = cx + int(r * 0.3 * math.cos(a))
                y1 = cy + int(r * 0.3 * math.sin(a))
                x2 = cx + int(r * 0.8 * math.cos(a))
                y2 = cy + int(r * 0.8 * math.sin(a))
                pygame.draw.line(surface, (128, 96, 255), (x1, y1), (x2, y2), 2)
        elif reward_id == 'shield':
            # Mirror overlay
            mirror_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(mirror_surf, (int(ASH_WHITE[0]), int(ASH_WHITE[1]), int(ASH_WHITE[2]), 60), (r, r), r)
            surface.blit(mirror_surf, (cx - r, cy - r), special_flags=pygame.BLEND_RGBA_ADD)
            pygame.draw.circle(surface, ASH_WHITE, (cx, cy), r, 2)
        elif reward_id == 'crown':
            # 6 spike circles
            for i in range(6):
                a = angle_rad + i * math.pi / 3
                sx = cx + int(r * 0.95 * math.cos(a))
                sy = cy + int(r * 0.95 * math.sin(a))
                pygame.draw.circle(surface, (176, 168, 152), (sx, sy), 3)
    
    # Outline and center dot
    pygame.draw.circle(surface, STEEL_LIGHT, (cx, cy), r, 2)
    pygame.draw.circle(surface, ASH_WHITE, (cx, cy), 3)


class RewardScreen:
    def __init__(self, level, fonts):
        self.level = level
        self.fonts = fonts
        self.rewards = REWARDS[level]
        self.hover = -1
        self.selected = -1
        self.confirm_timer = 0.0
        self.done = False
        self.choice = None
        self.preview_angles = [0.0, 0.0, 0.0]

        # Card positions
        self.card_w = 240
        self.card_h = 320
        self.card_gap = 32
        total_w = self.card_w * 3 + self.card_gap * 2
        self.start_x = (SCREEN_WIDTH - total_w) // 2
        self.card_y = (SCREEN_HEIGHT - self.card_h) // 2

    def handle_event(self, event):
        if self.selected >= 0:
            return
        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            self.hover = -1
            for i in range(3):
                rx = self.start_x + i * (self.card_w + self.card_gap)
                if rx <= mx < rx + self.card_w and self.card_y <= my < self.card_y + self.card_h:
                    self.hover = i
        if event.type == pygame.MOUSEBUTTONDOWN and self.hover >= 0:
            self.selected = self.hover
            self.choice = self.rewards[self.hover]['id']
            self.confirm_timer = 0.6

    def update(self, dt):
        # Animate preview rotations
        for i in range(3):
            speed = 180 if i == self.hover else 90
            self.preview_angles[i] = (self.preview_angles[i] + speed * dt) % 360
        
        if self.selected >= 0:
            self.confirm_timer -= dt
            if self.confirm_timer <= 0:
                self.done = True

    def draw(self, surface):
        # Dim background
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((int(VOID_BLACK[0]), int(VOID_BLACK[1]), int(VOID_BLACK[2]), 200))
        surface.blit(overlay, (0, 0))

        # Top gold line
        pygame.draw.line(surface, ENERGY_GOLD, (0, 8), (SCREEN_WIDTH, 8), 2)

        # Title
        font_title = self.fonts['title']
        du.draw_text(surface, " 選擇你的獎勵 ", font_title, ENERGY_GOLD,
                     SCREEN_WIDTH // 2, 30, align="center")

        # Cards
        for i, reward in enumerate(self.rewards):
            rx = self.start_x + i * (self.card_w + self.card_gap)
            ry = self.card_y
            hover = (i == self.hover)
            selected = (i == self.selected)
            fade = (self.selected >= 0 and i != self.selected)

            self._draw_card(surface, rx, ry, reward, hover, selected, fade, i)

        # Footer hint
        font_sm = self.fonts['sm']
        if self.selected < 0:
            du.draw_text(surface, "點擊選擇｜選擇後無法反悔", font_sm, BONE_WHITE,
                         SCREEN_WIDTH // 2, SCREEN_HEIGHT - 40, align="center")

    def _draw_card(self, surface, x, y, reward, hover, selected, fade, card_index):
        w, h = self.card_w, self.card_h
        offset_y = -4 if hover else 0
        y += offset_y

        alpha = 80 if fade else 255

        # Card background
        card_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        card_color = STEEL_MID if hover else STEEL_DARK
        border_color = (ENERGY_GOLD if selected else
                        (SPIN_BLUE if hover else STEEL_LIGHT))
        border_w = 2

        pygame.draw.rect(card_surf, (int(card_color[0]), int(card_color[1]), int(card_color[2]), int(240)), (0, 0, w, h), border_radius=8)
        pygame.draw.rect(card_surf, (int(border_color[0]), int(border_color[1]), int(border_color[2]), int(255)), (0, 0, w, h), border_w,
                         border_radius=8)

        # v0.9 (2-B): style hint when card is selected
        if selected:
            try:
                from screens import REWARD_WEIGHTS
                wts = REWARD_WEIGHTS.get(reward.get('id',''), {})
                dim_max = max(wts, key=wts.get) if wts else None
                _HINT = {
                    'CTRL':  '穩健型',
                    'AGGR':  '侵略型',
                    'SURV':  '續戰型',
                    'RISK':  '膽識型',
                    'FLEX':  '靈活型',
                    'TEMPO': '節奏型',
                }
                hint_txt = _HINT.get(dim_max, '') if dim_max else ''
                if hint_txt:
                    hf = self.fonts['sm']
                    hs = hf.render(hint_txt, True, ENERGY_GOLD)
                    card_surf.blit(hs, (w//2 - hs.get_width()//2, -22))
            except Exception:
                pass

        # Preview beyblade
        icon_cx, icon_cy = w // 2, 72
        icon_r = 32
        angle_rad = math.radians(self.preview_angles[card_index])
        draw_beyblade_preview(card_surf, icon_cx, icon_cy, icon_r, angle_rad, reward['id'], self.level)

        # Name
        font_card = self.fonts['card']
        name_surf = font_card.render(reward['name'], True, ASH_WHITE)
        card_surf.blit(name_surf, (w//2 - name_surf.get_width()//2, 125))

        # Divider
        pygame.draw.line(card_surf, (int(STEEL_LIGHT[0]), int(STEEL_LIGHT[1]), int(STEEL_LIGHT[2]), int(180)), (16, 155), (w-16, 155), 1)

        # Description
        font_sm = self.fonts['sm']
        for j, line in enumerate(reward['desc']):
            color = BONE_WHITE
            if '+' in line or '×1' in line or '÷' not in line:
                pass
            desc_surf = font_sm.render(f"* {line}", True, color)
            card_surf.blit(desc_surf, (16, 168 + j * 22))

        card_surf.set_alpha(alpha)
        surface.blit(card_surf, (x, y))


class TitleScreen:
    _BEYBLADE_SIZE = 180

    def __init__(self, fonts):
        self.fonts = fonts
        self.blink_timer = 0.0
        self.show_prompt = True
        self.title_y = -80
        self.anim_timer = 0.0

        self._bb_frames = self._load_beyblade_frames()
        self._bb_frame_idx   = 0
        self._bb_frame_timer = 0.0
        self._bb_frame_dur   = 0.08
        self._bb_x = float(SCREEN_WIDTH + self._BEYBLADE_SIZE)
        self._bb_target_x = float(SCREEN_WIDTH - 180)
        self._bb_y = float(SCREEN_HEIGHT * 0.72)
        self._bb_entered = False

    def _load_beyblade_frames(self):
        frames = []
        img_dir = os.path.join(os.path.dirname(__file__), 'img')
        for i in range(1, 5):
            loaded = None
            for ext in ('.PNG', '.png', '.jpg', '.jpeg'):
                path = os.path.join(img_dir, f'beyblade_{i}{ext}')
                if os.path.exists(path):
                    try:
                        raw  = pygame.image.load(path).convert_alpha()
                        surf = pygame.transform.scale(
                            raw, (self._BEYBLADE_SIZE, self._BEYBLADE_SIZE))
                        loaded = surf
                    except Exception:
                        pass
                    break
            frames.append(loaded)
        return frames

    def update(self, dt):
        self.anim_timer += dt
        if self.title_y < 0:
            self.title_y = min(0, self.title_y + 200 * dt)
        self.blink_timer += dt
        if self.blink_timer > 0.6:
            self.blink_timer = 0
            self.show_prompt = not self.show_prompt

        if not self._bb_entered:
            self._bb_x -= 600 * dt
            if self._bb_x <= self._bb_target_x:
                self._bb_x = self._bb_target_x
                self._bb_entered = True

        if self._bb_frames:
            self._bb_frame_timer += dt
            if self._bb_frame_timer >= self._bb_frame_dur:
                self._bb_frame_timer -= self._bb_frame_dur
                self._bb_frame_idx = (self._bb_frame_idx + 1) % len(self._bb_frames)

    def draw(self, surface):
        surface.fill(VOID_BLACK)

        # Subtle grid
        for x in range(0, SCREEN_WIDTH, 60):
            pygame.draw.line(surface, STEEL_DARK, (x, 0), (x, SCREEN_HEIGHT), 1)
        for y in range(0, SCREEN_HEIGHT, 60):
            pygame.draw.line(surface, STEEL_DARK, (0, y), (SCREEN_WIDTH, y), 1)

        # 陀螺動畫
        if self._bb_frames:
            frame = self._bb_frames[self._bb_frame_idx % len(self._bb_frames)]
            if frame is not None:
                half = self._BEYBLADE_SIZE // 2
                surface.blit(frame, (int(self._bb_x) - half, int(self._bb_y) - half))

        # Title
        title_font = self.fonts['big']
        title_surf = title_font.render("陀螺特工", True, ENERGY_GOLD)
        title_shadow = title_font.render("陀螺特工", True, (60, 40, 0))
        tx = SCREEN_WIDTH // 2 - title_surf.get_width() // 2
        ty = int(200 + self.title_y)
        surface.blit(title_shadow, (tx + 3, ty + 3))
        surface.blit(title_surf, (tx, ty))

        sub_font = self.fonts['title']
        sub_surf = sub_font.render("BEYBLADE AGENT", True, STEEL_LIGHT)
        surface.blit(sub_surf, (SCREEN_WIDTH//2 - sub_surf.get_width()//2, ty + 80))

        # Instructions
        if self.anim_timer > 0.6:
            inst_font = self.fonts['card']
            instructions = [
                ("WASD / 方向鍵", "移動"),
                ("滑鼠旋轉",       "補充轉速"),
                ("碰撞敵人",       "造成傷害+降低轉速"),
                ("轉速歸零",       "Game Over"),
            ]
            ix = SCREEN_WIDTH // 2 - 140
            iy = 370
            for key, val in instructions:
                k_surf = inst_font.render(key, True, BONE_WHITE)
                v_surf = inst_font.render(val, True, ASH_WHITE)
                surface.blit(k_surf, (ix, iy))
                surface.blit(v_surf, (ix + 200, iy))
                iy += 34

        # Prompt
        if self.show_prompt and self.anim_timer > 1.0:
            prompt_font = self.fonts['card']
            prompt = "-- 按空白鍵開始 --"
            p_surf = prompt_font.render(prompt, True, ENERGY_GOLD)
            surface.blit(p_surf, (SCREEN_WIDTH//2 - p_surf.get_width()//2, 560))

        # Version
        ver_font = self.fonts['sm']
        ver_surf = ver_font.render("v1.2", True, STEEL_MID)
        surface.blit(ver_surf, (SCREEN_WIDTH - 40, SCREEN_HEIGHT - 24))


class LevelIntroScreen:
    NAMES = {1: '木製道場', 2: '靜謐竹林', 3: '廢棄工廠', 4: '超級加速碰碰場', 5: '廢墟競技場'}
    SUBTITLES = {1: 'Round 1', 2: 'Round 2', 3: 'Round 3', 4: 'Round 4', 5: 'FINAL ROUND'}

    def __init__(self, level, fonts):
        self.level = level
        self.fonts = fonts
        self.timer = 3.0
        self.done = False

    def update(self, dt):
        self.timer -= dt
        if self.timer <= 0:
            self.done = True

    def draw(self, surface):
        surface.fill(VOID_BLACK)
        t = 1 - max(0, self.timer) / 3.0  # 0→1

        # Slide in effect
        offset = int((1 - t) * 80) if t < 0.3 else 0

        title_font = self.fonts['big']
        card_font = self.fonts['card']

        name = self.NAMES.get(self.level, f'Level {self.level}')
        subtitle = self.SUBTITLES.get(self.level, '')

        # Number
        num_surf = title_font.render(str(self.level), True, ENERGY_GOLD)
        nx = SCREEN_WIDTH // 2 - num_surf.get_width() // 2 + offset
        surface.blit(num_surf, (nx, 220))

        # Name
        name_surf = self.fonts['title'].render(name, True, ASH_WHITE)
        surface.blit(name_surf, (SCREEN_WIDTH//2 - name_surf.get_width()//2 + offset, 330))

        # Subtitle
        sub_surf = card_font.render(subtitle, True, STEEL_LIGHT)
        surface.blit(sub_surf, (SCREEN_WIDTH//2 - sub_surf.get_width()//2, 390))

        # Timer bar
        bar_w = 300
        bx = (SCREEN_WIDTH - bar_w) // 2
        elapsed = 3.0 - self.timer
        pygame.draw.rect(surface, STEEL_MID, (bx, 460, bar_w, 6), border_radius=3)
        fill = int(bar_w * min(1.0, elapsed / 3.0))
        if fill > 0:
            pygame.draw.rect(surface, ENERGY_GOLD, (bx, 460, fill, 6), border_radius=3)


class GameOverScreen:
    def __init__(self, fonts):
        self.fonts = fonts
        self.alpha = 0.0
        self.done = False
        self.choice = None  # 'retry' or 'menu'
        self.shake = 0.0
        self.hover_retry = False
        self.hover_menu = False

    def update(self, dt):
        self.alpha = min(220, self.alpha + 120 * dt)
        if self.shake > 0:
            self.shake -= dt
        
        # Update hover states
        mx, my = pygame.mouse.get_pos()
        
        # Retry button hover detection
        retry_text = "[R] 重試本關"
        retry_width = self.fonts['card'].render(retry_text, True, BONE_WHITE).get_width()
        retry_x = SCREEN_WIDTH // 2 - 160 - retry_width // 2
        retry_x_end = retry_x + retry_width
        self.hover_retry = (retry_x - 15 <= mx <= retry_x_end + 15 and 420 - 15 <= my <= 420 + 25)
        
        # Menu button hover detection
        menu_text = "[M] 回主選單"
        menu_width = self.fonts['card'].render(menu_text, True, BONE_WHITE).get_width()
        menu_x = SCREEN_WIDTH // 2 + 160 - menu_width // 2
        menu_x_end = menu_x + menu_width
        self.hover_menu = (menu_x - 15 <= mx <= menu_x_end + 15 and 420 - 15 <= my <= 420 + 25)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                self.choice = 'retry'; self.done = True
            elif event.key == pygame.K_m or event.key == pygame.K_ESCAPE:
                self.choice = 'menu'; self.done = True
        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            
            # Retry button click detection
            retry_text = "[R] 重試本關"
            retry_width = self.fonts['card'].render(retry_text, True, BONE_WHITE).get_width()
            retry_x = SCREEN_WIDTH // 2 - 160 - retry_width // 2
            retry_x_end = retry_x + retry_width
            if (retry_x - 15 <= mx <= retry_x_end + 15 and 420 - 15 <= my <= 420 + 25):
                self.choice = 'retry'; self.done = True
            
            # Menu button click detection
            menu_text = "[M] 回主選單"
            menu_width = self.fonts['card'].render(menu_text, True, BONE_WHITE).get_width()
            menu_x = SCREEN_WIDTH // 2 + 160 - menu_width // 2
            menu_x_end = menu_x + menu_width
            if (menu_x - 15 <= mx <= menu_x_end + 15 and 420 - 15 <= my <= 420 + 25):
                self.choice = 'menu'; self.done = True

    def draw(self, surface):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((int(VOID_BLACK[0]), int(VOID_BLACK[1]), int(VOID_BLACK[2]), int(int(self.alpha))))
        surface.blit(overlay, (0, 0))

        import random
        shake_x = random.randint(-3, 3) if self.alpha < 200 else 0

        title_font = self.fonts['big']
        go_surf = title_font.render("GAME OVER", True, DANGER_RED)
        go_shadow = title_font.render("GAME OVER", True, (80, 0, 0))
        tx = SCREEN_WIDTH // 2 - go_surf.get_width() // 2 + shake_x
        surface.blit(go_shadow, (tx + 3, 243))
        surface.blit(go_surf, (tx, 240))

        card_font = self.fonts['card']
        sub = card_font.render("陀螺已停止旋轉...", True, BONE_WHITE)
        surface.blit(sub, (SCREEN_WIDTH//2 - sub.get_width()//2, 330))

        # Buttons - centered side by side
        self._draw_button(surface, card_font, "[R] 重試本關", SCREEN_WIDTH // 2 - 160, 420, self.hover_retry)
        self._draw_button(surface, card_font, "[M] 回主選單", SCREEN_WIDTH // 2 + 160, 420, self.hover_menu)

    def _draw_button(self, surface, font, text, cx, y, hover):
        color = ENERGY_GOLD if hover else BONE_WHITE
        surf = font.render(text, True, color)
        surface.blit(surf, (cx - surf.get_width()//2, y))


class FinalScreen:
    def __init__(self, player, fonts):
        self.player = player
        self.fonts = fonts
        self.angle = 0.0
        self.done = False
        self.choice = None
 
        self.personality_primary = None
        self.personality_secondary = None
        self.personality_description = None
        self._calculate_personality()
 
    # ── 人格計算（邏輯不變）────────────────────────────────────────────
 
    def _calculate_personality(self):
        p = self.player
        scores = {'CTRL': 0, 'AGGR': 0, 'SURV': 0, 'RISK': 0, 'FLEX': 0, 'TEMPO': 0}
 
        for attr in (p.material, p.weapon, p.accessory,
                     getattr(p, 'drive', None), p.core):
            if attr and attr in REWARD_WEIGHTS:
                for dim, weight in REWARD_WEIGHTS[attr].items():
                    scores[dim] += weight
 
        dim_priority = ['CTRL', 'SURV', 'AGGR', 'FLEX', 'RISK', 'TEMPO']
        max_score = max(scores.values()) if scores.values() else 0
        for dim in dim_priority:
            if scores[dim] == max_score:
                self.personality_primary = dim
                break
 
        second_score = -1
        for dim in dim_priority:
            if dim != self.personality_primary and scores[dim] > second_score:
                second_score = scores[dim]
        for dim in dim_priority:
            if dim != self.personality_primary and scores[dim] == second_score:
                self.personality_secondary = dim
                break
 
        self._generate_description()
 
    def _generate_description(self):
        primary   = self.personality_primary
        secondary = self.personality_secondary
        desc_key  = (primary, secondary)
        if desc_key in PERSONALITY_DESCRIPTIONS:
            self.personality_description = PERSONALITY_DESCRIPTIONS[desc_key]
        else:
            alt_key = (secondary, primary)
            if alt_key in PERSONALITY_DESCRIPTIONS:
                self.personality_description = PERSONALITY_DESCRIPTIONS[alt_key]
            else:
                self.personality_description = '系統分析完成。你是一個複雜的玩家。'
 
    # ── 週期更新 ───────────────────────────────────────────────────────
 
    def update(self, dt):
        self.angle = (self.angle + 90 * dt) % 360
 
    # ── 事件處理 ───────────────────────────────────────────────────────
 
    def handle_event(self, event):
        BOT_BAR = 52
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                self.choice = 'retry';  self.done = True
            elif event.key in (pygame.K_ESCAPE, pygame.K_m):
                self.choice = 'menu';   self.done = True
        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            btn_y   = SCREEN_HEIGHT - BOT_BAR // 2
            retry_x = SCREEN_WIDTH  // 4
            menu_x  = 3 * SCREEN_WIDTH // 4
            if abs(mx - retry_x) < 110 and abs(my - btn_y) < 26:
                self.choice = 'retry';  self.done = True
            if abs(mx - menu_x)  < 110 and abs(my - btn_y) < 26:
                self.choice = 'menu';   self.done = True
 
    # ── 雷達圖（點在軸線上）────────────────────────────────────────────
 
    def _draw_radar(self, surface, cx, cy, r, scores, max_val=12):
        """
        六維雷達圖。每個分數頂點嚴格落在對應軸線上：
            vertex_i = ( val_i * r * cos(i*60° - 90°),
                         val_i * r * sin(i*60° - 90°) )
        """
        DIMS = ['CTRL', 'AGGR', 'RISK', 'TEMPO', 'FLEX', 'SURV']
        DIM_LABELS = {
            'CTRL':  '續戰型', 'AGGR':  '侵略型',
            'RISK':  '膽識型', 'TEMPO': '節奏型',
            'FLEX':  '靈活型', 'SURV':  '穩健型',
        }
        DIM_COLORS = {
            'CTRL':  (80,  144, 255), 'AGGR':  (232,  64,  64),
            'RISK':  (232, 180,  74), 'TEMPO': ( 60, 217, 138),
            'FLEX':  (155, 114, 255), 'SURV':  (255, 140,  60),
        }
        n = len(DIMS)
 
        # 網格底層
        grid_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        for ring in range(1, 6):
            ring_pts = []
            for i in range(n):
                a  = math.radians(i * 360 / n - 90)
                rv = r * ring / 5
                ring_pts.append((cx + rv * math.cos(a), cy + rv * math.sin(a)))
            alpha = 30 if ring < 5 else 70
            pygame.draw.polygon(grid_surf, (255, 255, 255, alpha), ring_pts, 1)
 
        # 軸線（從圓心射出）
        for i in range(n):
            a = math.radians(i * 360 / n - 90)
            pygame.draw.line(grid_surf, (255, 255, 255, 25),
                             (int(cx), int(cy)),
                             (int(cx + r * math.cos(a)), int(cy + r * math.sin(a))), 1)
        surface.blit(grid_surf, (0, 0))
 
        # 分數多邊形頂點 — 嚴格在各軸線上
        pts = []
        for i, dim in enumerate(DIMS):
            a   = math.radians(i * 360 / n - 90)
            val = min(1.0, scores.get(dim, 0) / max_val)
            pts.append((cx + r * val * math.cos(a),
                        cy + r * val * math.sin(a)))
 
        dominant   = max(scores, key=scores.get) if any(scores.values()) else 'CTRL'
        fill_color = DIM_COLORS.get(dominant, (80, 144, 255))
 
        if len(pts) >= 3:
            poly_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            pygame.draw.polygon(poly_surf, (*fill_color, 48), pts)
            pygame.draw.polygon(poly_surf, (*fill_color, 215), pts, 2)
            surface.blit(poly_surf, (0, 0))
 
            # 點：落在軸線上的精確位置
            for j, pt in enumerate(pts):
                dim   = DIMS[j]
                pcol  = DIM_COLORS[dim]
                dot_r = 6 if dim == dominant else 4
                pygame.draw.circle(surface, pcol,
                                   (int(pt[0]), int(pt[1])), dot_r)
                pygame.draw.circle(surface, (255, 255, 255),
                                   (int(pt[0]), int(pt[1])), dot_r, 1)
 
        # 標籤（貼近軸端點外側）
        try:
            label_font = self.fonts['card_bold']
        except KeyError:
            label_font = self.fonts['card']
 
        LABEL_GAP = 12   # 頂點到標籤邊緣的距離
        for i, dim in enumerate(DIMS):
            a     = math.radians(i * 360 / n - 90)
            tip_x = cx + (r + LABEL_GAP) * math.cos(a)
            tip_y = cy + (r + LABEL_GAP) * math.sin(a)
            col   = DIM_COLORS[dim]
            lsurf = label_font.render(DIM_LABELS[dim], True, col)
            lw, lh = lsurf.get_size()
            cos_a = math.cos(a)
            mid_y = int(tip_y - lh // 2)
 
            if cos_a > 0.2:       # 右側：左對齊於 tip_x
                surface.blit(lsurf, (int(tip_x) + 4, mid_y))
            elif cos_a < -0.2:    # 左側：右對齊於 tip_x
                surface.blit(lsurf, (int(tip_x) - lw - 4, mid_y))
            else:                  # 上/下：水平置中
                blit_y = (int(tip_y) - lh - 4 if math.sin(a) < 0
                          else int(tip_y) + 4)
                surface.blit(lsurf, (int(tip_x - lw // 2), blit_y))
 
    # ── 主繪製 ─────────────────────────────────────────────────────────
 
    def draw(self, surface):
        surface.fill((6, 8, 14))
        p = self.player
 
        # 字型指派
        try:
            big_title    = self.fonts['big']          # 58px bold — 頂部標題
            label_24     = self.fonts['damage']       # 24px bold — 你的陀螺
            type_title   = self.fonts['title']        # 32px bold — 人格主類型
            label_bold   = self.fonts['card_bold']    # 20px bold — 材質名/副標/按鈕
            body_font    = self.fonts['card']         #  20px     — 描述/節點文字
            hint_font    = self.fonts['sm']           # 14px      — 節點圓圈內標籤
        except KeyError:
            big_title  = self.fonts['title']
            label_24   = self.fonts['title']
            type_title = self.fonts['title']
            label_bold = self.fonts['card']
            body_font  = self.fonts['card']
            hint_font  = self.fonts['sm']
 
        # ── 版型常數 ────────────────────────────────────────────────────
        TOP_BAR     = 70
        BOT_BAR     = 52
        CONTENT_TOP = TOP_BAR + 24          # 94
        CONTENT_BOT = SCREEN_HEIGHT - BOT_BAR  # 648
        LEFT_W      = int(SCREEN_WIDTH * 0.32)  # 400
        DIVX        = LEFT_W
        RIGHT_W     = SCREEN_WIDTH - DIVX       # 850
        lx          = DIVX // 2                 # 200  左欄中線
        rx          = DIVX + RIGHT_W // 2       # 825  右欄中線
 
        # ── TOP BAR ─────────────────────────────────────────────────────
        pygame.draw.rect(surface, (10, 13, 22), (0, 0, SCREEN_WIDTH, TOP_BAR))
        pygame.draw.line(surface, ENERGY_GOLD,
                         (0, TOP_BAR), (SCREEN_WIDTH, TOP_BAR), 2)
        t_surf = big_title.render("陀螺特工  -  通關", True, ENERGY_GOLD)
        max_title_w = SCREEN_WIDTH - 240
        if t_surf.get_width() > max_title_w:
            scale  = max_title_w / t_surf.get_width()
            t_surf = pygame.transform.smoothscale(
                t_surf, (int(t_surf.get_width() * scale),
                         int(t_surf.get_height() * scale)))
        surface.blit(t_surf, (SCREEN_WIDTH // 2 - t_surf.get_width() // 2,
                               (TOP_BAR - t_surf.get_height()) // 2))
 
        # 垂直分隔線
        pygame.draw.line(surface, (28, 36, 55),
                         (DIVX, TOP_BAR + 8), (DIVX, CONTENT_BOT - 8), 1)
 
        # ══════════════════════════════════════════════════════════════
        #  左欄  (每個元素間隔一律 16px；陀螺標題↔陀螺展示間隔 24px；
        #         節點清單額外下移 36px；節點間距 24px gap)
        # ══════════════════════════════════════════════════════════════
        y = CONTENT_TOP   # 94
 
        # 「你的陀螺：」— font 24px，中心 x = lx - 80 = 120
        lbl_surf = label_24.render("你的陀螺：", True, (160, 175, 210))
        LABEL_CX = lx - 80   # 120
        surface.blit(lbl_surf, (LABEL_CX - lbl_surf.get_width() // 2, y))
        y += lbl_surf.get_height() + 24   # gap 24 → 陀螺頂端
 
        # 陀螺旋轉展示
        BEYBLADE_R  = 64
        beyblade_cy = y + BEYBLADE_R
        a_rad = math.radians(self.angle)
        mat_color = {'wood': WOOD_WARM, 'steel': STEEL_CHROME,
                     'titan': TITAN_DARK}.get(p.material, SPIN_BLUE)
 
        glow = pygame.Surface((BEYBLADE_R * 3, BEYBLADE_R * 3), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*mat_color, 25),
                           (BEYBLADE_R + BEYBLADE_R // 2,
                            BEYBLADE_R + BEYBLADE_R // 2), BEYBLADE_R + 14)
        surface.blit(glow, (lx - BEYBLADE_R - BEYBLADE_R // 2,
                             beyblade_cy - BEYBLADE_R - BEYBLADE_R // 2))
 
        pygame.draw.circle(surface, mat_color, (lx, beyblade_cy), BEYBLADE_R)
        for i in range(10):
            a = a_rad + i * math.pi / 5
            pygame.draw.line(surface, STEEL_LIGHT,
                (lx + int(BEYBLADE_R * 0.14 * math.cos(a)),
                 beyblade_cy + int(BEYBLADE_R * 0.14 * math.sin(a))),
                (lx + int(BEYBLADE_R * 0.86 * math.cos(a)),
                 beyblade_cy + int(BEYBLADE_R * 0.86 * math.sin(a))), 2)
        pygame.draw.circle(surface, ENERGY_GOLD, (lx, beyblade_cy), 9)
        pygame.draw.circle(surface, STEEL_LIGHT, (lx, beyblade_cy), BEYBLADE_R, 2)
        y = beyblade_cy + BEYBLADE_R + 16   # gap 16 → 材質名頂端
 
        # 材質名
        mat_name = {'wood': '木頭', 'steel': '不鏽鋼', 'titan': '鈦合金'}.get(
            p.material, '-')
        mn = label_bold.render(mat_name, True, mat_color)
        surface.blit(mn, (lx - mn.get_width() // 2, y))
        y += mn.get_height() + 16 + 36   # gap 16 + 額外 36 → 節點清單頂端
 
        # 選擇路徑節點（L1–L5）
        # gap 24px between nodes → center-to-center = 22(dia) + 24 = 46px
        choices = [
            ('L1', getattr(p, 'material', None),
             {'wood': '木頭材質', 'steel': '不鏽鋼材質', 'titan': '鈦合金材質'}),
            ('L2', getattr(p, 'weapon', None),
             {'scythe': '鐮刀', 'staff': '金箍棒', 'hammer': '重鎚'}),
            ('L3', getattr(p, 'accessory', None),
             {'axis': '鋼鐵軸心', 'gear_ring': '齒輪外環', 'dash_tape': '衝刺卡帶'}),
            ('L4', getattr(p, 'drive', None),
             {'recoil_dampener': '反震阻尼', 'shockwave': '衝擊波',
              'splinter_echo':   '碎片殘響'}),
            ('L5', getattr(p, 'core', None),
             {'chaos': '混沌核心', 'shield': '魔王盾', 'crown': '廢墟王冠'}),
        ]
        STEP_COLORS  = [(80, 144, 255), (60, 217, 138), (232, 180, 74),
                        (155, 114, 255), (232, 64, 64)]
        NODE_R       = 11
        NODE_SPACING = 46   # center-to-center
        node_x       = lx   # 節點圓心 x = 欄位中線
 
        for idx, (lbl, val, nm) in enumerate(choices):
            ny   = y + NODE_R + idx * NODE_SPACING
            col  = STEP_COLORS[idx]
            item = nm.get(val, '?') if val else '?'
 
            # 連接線
            if idx < len(choices) - 1:
                pygame.draw.line(surface, (40, 50, 70),
                                 (node_x, ny + NODE_R),
                                 (node_x, ny + NODE_SPACING - NODE_R), 1)
            # 節點圓圈
            pygame.draw.circle(surface, col, (node_x, ny), NODE_R)
            pygame.draw.circle(surface, (6, 8, 14), (node_x, ny), NODE_R - 4)
            # 圓圈內標籤
            lf = hint_font.render(lbl, True, col)
            surface.blit(lf, (node_x - lf.get_width() // 2,
                               ny    - lf.get_height() // 2))
            # 項目文字
            it = body_font.render(item, True, (220, 228, 240))
            surface.blit(it, (node_x + NODE_R + 8, ny - it.get_height() // 2))
 
        # ══════════════════════════════════════════════════════════════
        #  右欄
        # ══════════════════════════════════════════════════════════════
        scores = {'CTRL': 0, 'AGGR': 0, 'SURV': 0, 'RISK': 0, 'FLEX': 0, 'TEMPO': 0}
        for attr in (p.material, p.weapon, p.accessory,
                     getattr(p, 'drive', None), p.core):
            if attr and attr in REWARD_WEIGHTS:
                for dim, wt in REWARD_WEIGHTS[attr].items():
                    scores[dim] += wt
 
        # 雷達圖：R=80，中心 y=222（TOP_BAR + 24 + 16 + R）
        RADAR_R  = 80
        RADAR_CY = TOP_BAR + 24 + 16 + RADAR_R + 16   # 222
        self._draw_radar(surface, rx, RADAR_CY, RADAR_R, scores)
 
        # 人格主類型：雷達底部 + 64gap
        primary_label   = PRIMARY_ARCHETYPES.get(self.personality_primary,   '未知型')
        secondary_label = PRIMARY_ARCHETYPES.get(self.personality_secondary, '')
 
        ty = RADAR_CY + RADAR_R + 64 + 16   # 222+80+64 = 366
        ts = type_title.render(primary_label, True, ENERGY_GOLD)
        surface.blit(ts, (rx - ts.get_width() // 2, ty))
        ty += ts.get_height() + 4
 
        # 副類型傾向
        if secondary_label:
            ss = label_bold.render(secondary_label + " 傾向", True, (160, 175, 130))
            surface.blit(ss, (rx - ss.get_width() // 2, ty))
            ty += ss.get_height() + 16 + 4
        else:
            ty += 20
 
        # 分隔線
        sep_x0 = DIVX + int(RIGHT_W * 0.05)
        sep_x1 = SCREEN_WIDTH - int(RIGHT_W * 0.05)
        pygame.draw.line(surface, (35, 44, 65), (sep_x0, ty), (sep_x1, ty + 16), 1)
        ty += 20
 
        # 描述文字
        TEXT_W  = int(RIGHT_W * 0.88)
        text_x  = DIVX + int(RIGHT_W * 0.06)
        line_h  = int(body_font.size('A')[1] * 1.55)
        max_y   = CONTENT_BOT 
 
        if self.personality_description:
            for line in self._wrap_text_px(self.personality_description,
                                           TEXT_W, body_font):
                if ty + line_h > max_y:
                    break
                surface.blit(body_font.render(line, True, (210, 218, 232)),
                             (text_x, ty))
                ty += line_h
 
        # ── 底部操作列 ───────────────────────────────────────────────────
        pygame.draw.line(surface, (25, 32, 48),
                         (0, SCREEN_HEIGHT - BOT_BAR),
                         (SCREEN_WIDTH, SCREEN_HEIGHT - BOT_BAR), 1)
        rh = label_bold.render("[R] 重新遊戲", True, (122, 136, 170))
        mh = label_bold.render("[M] 回主選單", True, (122, 136, 170))
        by = SCREEN_HEIGHT - BOT_BAR // 2
        surface.blit(rh, (SCREEN_WIDTH // 4 - rh.get_width() // 2,
                           by - rh.get_height() // 2))
        surface.blit(mh, (3 * SCREEN_WIDTH // 4 - mh.get_width() // 2,
                           by - mh.get_height() // 2))
 
    # ── 文字換行工具 ────────────────────────────────────────────────────
 
    def _wrap_text(self, text, max_len):
        words   = text.split('。')
        lines   = []
        current = ''
        for word in words:
            if len(current) + len(word) <= max_len:
                current += word + '。'
            else:
                if current:
                    lines.append(current)
                current = word + '。'
        if current:
            lines.append(current)
        return lines
 
    def _wrap_text_px(self, text, max_px, font):
        """以像素寬度換行，填滿每行後再換行。"""
        lines   = []
        current = ''
        for ch in text:
            test = current + ch
            if font.size(test)[0] <= max_px:
                current = test
            else:
                if current:
                    lines.append(current)
                current = ch
        if current:
            lines.append(current)
        return lines

class PauseScreen:
    """暫停頁：數值面板（左欄）+ 裝備清單＋操作按鈕（右欄）。
    使用固定卡片尺寸，避免動態高度計算造成溢出。
    """

    # ── 固定卡片尺寸（螢幕 1250×700）───────────────────────────────
    CARD_W  = 1020
    CARD_H  = 550          # 固定高度，不再動態計算
    CARD_PAD = 26

    # 左欄：數值統計
    COL_L_X = 26           # 距卡片左緣
    COL_L_W = 430
    # 分隔線
    DIV_X   = 472          # = COL_L_X + COL_L_W + 16
    # 右欄：裝備 + 按鈕
    COL_R_X = 494          # = DIV_X + 22
    COL_R_W = 500          # = CARD_W - COL_R_X - CARD_PAD

    # Header 高度
    HEADER_H = 52

    # 字體行距
    ROW_TITLE = 26         # 小節標題行高（fn_card）
    ROW_DATA  = 21         # 數值列行高（fn_sm）
    GAP_SEC   = 12         # 小節間距

    # ── 顏色 ────────────────────────────────────────────────────────
    _GOLD   = (255, 208,  50)
    _ORANGE = (255, 154,  30)
    _GREEN  = ( 77, 200, 122)
    _RED    = (227,  90,  90)
    _BLUE   = ( 91, 176, 240)
    _WHITE  = (194, 191, 186)
    _DIM    = (100, 108, 128)
    _BG     = ( 16,  18,  24)
    _PANEL  = ( 24,  28,  38)
    _BORDER = ( 52,  58,  74)

    SLOT_COLORS = {
        'material':  (140, 200,  80),
        'weapon':    (220, 110,  60),
        'accessory': ( 91, 176, 240),
        'drive':     (170, 130, 255),
        'core':      (240, 190,  50),
    }
    SLOT_LABELS = {
        'material': '材質', 'weapon': '武器', 'accessory': '配件',
        'drive': '驅動', 'core': '核心',
    }
    ITEM_NAMES = {
        'wood': '木頭', 'steel': '不鏽鋼', 'titan': '鈦合金',
        'scythe': '鐮刀', 'staff': '金箍棒', 'hammer': '重鎚',
        'axis': '鋼軸心', 'gear_ring': '齒輪環', 'dash_tape': '衝刺帶',
        'recoil_dampener': '反震阻尼', 'shockwave': '衝擊波',
        'splinter_echo': '碎片殘響',
        'chaos': '混沌核', 'shield': '魔王盾', 'crown': '廢墟冠',
    }

    # ── 初始化 ──────────────────────────────────────────────────────
    def __init__(self, fonts, player=None, level=1):
        self.fonts  = fonts
        self.player = player
        self.level  = level
        self.done   = False
        self.choice = None

        self._hover     = None
        self._btn_rects = {}

        # 卡片絕對座標（固定，不在 draw 裡重算）
        self._card_x = (SCREEN_WIDTH  - self.CARD_W) // 2   # 125
        self._card_y = (SCREEN_HEIGHT - self.CARD_H) // 2   # 75

    # ── 輸入 ────────────────────────────────────────────────────────
    def update(self, dt):
        mx, my = pygame.mouse.get_pos()
        self._hover = None
        for name, rect in self._btn_rects.items():
            if rect.collidepoint(mx, my):
                self._hover = name
                break

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if   event.key == pygame.K_ESCAPE: self.choice = 'resume';  self.done = True
            elif event.key == pygame.K_r:       self.choice = 'restart'; self.done = True
            elif event.key == pygame.K_m:       self.choice = 'menu';    self.done = True
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for name, rect in self._btn_rects.items():
                if rect.collidepoint(event.pos):
                    self.choice = name; self.done = True; return

    # ── 主繪製 ──────────────────────────────────────────────────────
    def draw(self, surface):
        # 遮罩
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((13, 13, 15, 200))
        surface.blit(overlay, (0, 0))

        cx = self._card_x
        cy = self._card_y
        cw = self.CARD_W
        ch = self.CARD_H

        # 卡片背景（不用 SRCALPHA Surface，直接畫在 surface）
        pygame.draw.rect(surface, self._BG,
                         (cx, cy, cw, ch), border_radius=8)
        pygame.draw.rect(surface, self._BORDER,
                         (cx, cy, cw, ch), 1, border_radius=8)

        fn_sm   = self.fonts['sm']
        fn_card = self.fonts['card']

        # Header
        self._draw_header(surface, cx, cy, fn_card, fn_sm)

        # Header 分隔線
        sep_y = cy + self.HEADER_H
        pygame.draw.line(surface, self._BORDER,
                         (cx + 1, sep_y), (cx + cw - 1, sep_y), 1)

        body_top = sep_y + 14

        # 左欄
        self._draw_left_col(surface,
                            cx + self.COL_L_X, body_top,
                            cx + self.COL_L_X + self.COL_L_W,
                            fn_card, fn_sm)

        # 中央分隔線
        body_bot = cy + ch - 12
        pygame.draw.line(surface, self._BORDER,
                         (cx + self.DIV_X, body_top),
                         (cx + self.DIV_X, body_bot), 1)

        # 右欄
        self._draw_right_col(surface,
                             cx + self.COL_R_X, body_top,
                             fn_card, fn_sm)

    # ── Header ──────────────────────────────────────────────────────
    def _draw_header(self, surface, cx, cy, fn_card, fn_sm):
        # 左：PAUSED（金色，card 字體）
        title = fn_card.render("PAUSED", True, self._GOLD)
        surface.blit(title, (cx + self.CARD_PAD, cy + (self.HEADER_H - title.get_height()) // 2))

        # 右：LEVEL X / 5（badge，sm 字體）
        badge_text = f"LEVEL  {self.level} / 5"
        badge_surf = fn_sm.render(badge_text, True, self._WHITE)
        bw = badge_surf.get_width() + 24
        bh = badge_surf.get_height() + 10
        bx = cx + self.CARD_W - bw - self.CARD_PAD
        by = cy + (self.HEADER_H - bh) // 2
        pygame.draw.rect(surface, self._PANEL,  (bx, by, bw, bh), border_radius=4)
        pygame.draw.rect(surface, self._BORDER, (bx, by, bw, bh), 1, border_radius=4)
        surface.blit(badge_surf, (bx + 12, by + 5))

    # ── 左欄：數值面板 ───────────────────────────────────────────────
    def _draw_left_col(self, surface, x, y, right_edge, fn_card, fn_sm):
        player = self.player
        if not player:
            surface.blit(fn_sm.render("（無玩家資料）", True, self._DIM), (x, y))
            return

        from constants import RPM_DECAY, RPM_MAX, PLAYER_RADIUS
        import time as _t

        W   = right_edge - x     # 欄位寬度（用於右對齊）
        cur = [y]

        # ── 輔助函式 ────────────────────────────────────────────────
        def sec_title(text):
            """小節標題：用 fn_card，亮白"""
            s = fn_card.render(text, True, (230, 232, 240))
            surface.blit(s, (x, cur[0]))
            cur[0] += self.ROW_TITLE

        def row_base(label, val_str):
            """基礎數值列：灰色 label，白色 val"""
            surface.blit(fn_sm.render(label, True, self._DIM),   (x + 6,  cur[0]))
            vs = fn_sm.render(val_str, True, self._WHITE)
            surface.blit(vs, (x + W - vs.get_width(), cur[0]))
            cur[0] += self.ROW_DATA

        def row_bonus(label, val_str, col):
            surface.blit(fn_sm.render("  + " + label, True, col), (x + 6, cur[0]))
            vs = fn_sm.render("+" + val_str, True, col)
            surface.blit(vs, (x + W - vs.get_width(), cur[0]))
            cur[0] += self.ROW_DATA

        def row_neg(label, val_str, col):
            surface.blit(fn_sm.render("  - " + label, True, col), (x + 6, cur[0]))
            vs = fn_sm.render("-" + val_str, True, col)
            surface.blit(vs, (x + W - vs.get_width(), cur[0]))
            cur[0] += self.ROW_DATA

        def row_total(label, val_str, col):
            """合計列：略微縮排，加底線感"""
            cur[0] += 3
            pygame.draw.line(surface, self._BORDER,
                             (x + 4, cur[0]), (x + W, cur[0]), 1)
            cur[0] += 4
            surface.blit(fn_sm.render("= " + label, True, col), (x + 6, cur[0]))
            vs = fn_sm.render(val_str, True, col)
            surface.blit(vs, (x + W - vs.get_width(), cur[0]))
            cur[0] += self.ROW_DATA

        def cap_row(label, val_str):
            surface.blit(fn_sm.render(label, True, self._DIM),      (x + 6, cur[0]))
            vs = fn_sm.render(val_str, True, self._ORANGE)
            surface.blit(vs, (x + W - vs.get_width(), cur[0]))
            cur[0] += self.ROW_DATA

        # ── 攻擊 ────────────────────────────────────────────────────
        base_atk     = player.base_attack
        mat_mul      = {'wood': 0.8, 'titan': 1.35}.get(player.material, 1.0)
        base_after   = base_atk * mat_mul
        weapon_bonus = player.weapon_attack_bonus
        gear_bonus   = 5 if player.accessory == 'gear_ring' else 0
        crown_active = False
        crown_bonus  = 0.0
        if player.core == 'crown':
            ratio = player.rpm / max(1, player.rpm_max)
            if ratio < 0.30:
                crown_active = True
                crown_bonus  = round((base_after + weapon_bonus) * (0.50 * (1 - ratio / 0.30)), 1)
        total_atk = player.effective_attack() + gear_bonus

        sec_title("攻擊")
        row_base("基礎", str(int(base_after)))
        if player.material == 'wood':
            row_neg("Wood ×0.8",   f"{abs(base_atk*0.8-base_atk):.0f}", self._RED)
        elif player.material == 'titan':
            row_bonus("Titan ×1.35", f"{base_atk*0.35:.0f}", self._BLUE)
        if weapon_bonus > 0:
            wn = {'scythe':'Scythe','staff':'Staff','hammer':'Hammer'}.get(player.weapon, player.weapon)
            row_bonus(wn, str(weapon_bonus), self._GREEN)
        if gear_bonus > 0:
            row_bonus("Gear ring", str(gear_bonus), self._ORANGE)
        if crown_active:
            flash = self._RED if int(_t.time() * 4) % 2 == 0 else self._ORANGE
            row_bonus("Crown 爆發", f"{crown_bonus:.0f}", flash)
        if   total_atk < 10: atk_col = self._WHITE
        elif total_atk < 18: atk_col = self._GREEN
        elif total_atk < 26: atk_col = self._GOLD
        else:
            atk_col = self._RED if int(_t.time() * 3) % 2 == 0 else self._ORANGE
        row_total("合計", f"{total_atk:.1f}", atk_col)
        cur[0] += self.GAP_SEC

        # ── 降速 ────────────────────────────────────────────────────
        base_decay  = RPM_DECAY
        decay_items = []
        if player.material == 'wood':
            decay_items.append(("Wood",   round(base_decay * 0.95 - base_decay, 1)))
        elif player.material == 'titan':
            decay_items.append(("Titan",  round(base_decay * 1.18 - base_decay, 1)))
        if player.hammer_penalty:
            decay_items.append(("Hammer", round(base_decay * 1.5  - base_decay, 1)))
        total_decay = round(player.effective_decay(), 1)

        sec_title("降速 / 秒")
        row_base("基礎", str(base_decay))
        for lbl, bonus in decay_items:
            if bonus > 0: row_bonus(lbl, f"{bonus:.0f}", self._RED)
            else:         row_neg(lbl,   f"{abs(bonus):.0f}", self._GREEN)
        if   total_decay <= base_decay * 0.95: dc = self._GREEN
        elif total_decay <= base_decay:        dc = self._WHITE
        elif total_decay <= base_decay * 1.3:  dc = self._ORANGE
        else:                                  dc = self._RED
        row_total("合計", f"{total_decay:.1f}", dc)

        # ── 攻擊範圍 ────────────────────────────────────────────────
        if player.weapon:
            cur[0] += self.GAP_SEC
            base_reach  = PLAYER_RADIUS
            reach_bonus = player.weapon_reach
            total_reach = player.effective_reach()
            sec_title("攻擊範圍")
            row_base("基礎", str(base_reach))
            if reach_bonus > 0:
                wn = {'scythe':'Scythe','staff':'Staff','hammer':'Hammer'}.get(player.weapon, player.weapon)
                row_bonus(wn, str(reach_bonus), self._GREEN)
            row_total("合計", str(total_reach), self._WHITE)

        # ── 其他能力 ────────────────────────────────────────────────
        other_caps = []
        if player.rpm_max != RPM_MAX:
            other_caps.append(("最大轉速", f"{player.rpm_max}  (+{player.rpm_max - RPM_MAX})"))
        if player.accessory == 'dash_tape':    other_caps.append(("衝刺",     "持續移動觸發"))
        if player.accessory == 'axis':         other_caps.append(("鋼軸護盾", "受傷 -25%"))
        if player.accessory == 'gear_ring':    other_caps.append(("齒輪環",   "碰撞 +5 ATK"))
        if player.core == 'shield':            other_caps.append(("格擋",     "30% 機率格擋"))
        if player.core == 'chaos':             other_caps.append(("混沌爆炸", "擊殺時範圍傷害"))
        if player.core == 'crown':             other_caps.append(("低速爆發", "ATK +50%"))
        if player.drive == 'recoil_dampener':  other_caps.append(("反震阻尼", "被彈開 -45%"))
        elif player.drive == 'shockwave':      other_caps.append(("衝擊波",   "撞擊波及120px"))
        elif player.drive == 'splinter_echo':  other_caps.append(("碎片殘響", "擊殺/碰撞生殘影"))

        if other_caps:
            cur[0] += self.GAP_SEC
            pygame.draw.line(surface, self._BORDER,
                             (x, cur[0]), (x + W, cur[0]), 1)
            cur[0] += self.GAP_SEC
            sec_title("其他能力")
            for lbl, val in other_caps:
                cap_row(lbl, val)

    # ── 右欄：裝備清單 + 操作按鈕 ───────────────────────────────────
    def _draw_right_col(self, surface, x, y, fn_card, fn_sm):
        W     = self.COL_R_W
        cur_y = y

        # 欄標題
        lbl = fn_sm.render("LOADOUT", True, self._DIM)
        surface.blit(lbl, (x, cur_y))
        cur_y += 22

        # ── 5 個裝備 slot ────────────────────────────────────────────
        SLOT_H = 34
        SLOT_G = 6
        slots = [
            ('material',  getattr(self.player, 'material',  None) if self.player else None),
            ('weapon',    getattr(self.player, 'weapon',    None) if self.player else None),
            ('accessory', getattr(self.player, 'accessory', None) if self.player else None),
            ('drive',     getattr(self.player, 'drive',     None) if self.player else None),
            ('core',      getattr(self.player, 'core',      None) if self.player else None),
        ]
        for slot_type, val in slots:
            col = self.SLOT_COLORS[slot_type]
            # 背景
            pygame.draw.rect(surface, self._PANEL,
                             (x, cur_y, W, SLOT_H), border_radius=4)
            pygame.draw.rect(surface, self._BORDER,
                             (x, cur_y, W, SLOT_H), 1, border_radius=4)
            # 左：slot 標籤（DIM 色）
            lbl_s = fn_sm.render(self.SLOT_LABELS[slot_type], True, self._DIM)
            surface.blit(lbl_s, (x + 10, cur_y + (SLOT_H - lbl_s.get_height()) // 2))
            # 右：裝備名稱（slot 顏色）
            val_text = self.ITEM_NAMES.get(val, val) if val else "—"
            val_col  = col if val else self._BORDER
            val_s    = fn_sm.render(val_text, True, val_col)
            surface.blit(val_s, (x + W - val_s.get_width() - 10,
                                  cur_y + (SLOT_H - val_s.get_height()) // 2))
            cur_y += SLOT_H + SLOT_G

        # 分隔線
        cur_y += 12
        pygame.draw.line(surface, self._BORDER,
                         (x, cur_y), (x + W, cur_y), 1)
        cur_y += 16

        # ── 操作按鈕 ────────────────────────────────────────────────
        BTN_H = 42
        BTN_G = 8
        buttons = [
            ('resume',  '繼續遊戲', 'ESC', self._GOLD,  True),
            ('restart', '重新開始', 'R',   self._WHITE, False),
            ('menu',    '回主選單', 'M',   self._WHITE, False),
        ]
        self._btn_rects = {}

        for name, label, key_hint, base_col, is_primary in buttons:
            is_hover = (self._hover == name)

            # 按鈕背景色
            if is_primary:
                fill_col   = (52, 42,  8) if not is_hover else (70, 56, 10)
                border_col = (160, 130, 30) if not is_hover else self._GOLD
                text_col   = self._GOLD
            else:
                fill_col   = self._PANEL if not is_hover else (34, 38, 52)
                border_col = self._BORDER
                text_col   = self._WHITE if not is_hover else (220, 222, 232)

            pygame.draw.rect(surface, fill_col,
                             (x, cur_y, W, BTN_H), border_radius=5)
            pygame.draw.rect(surface, border_col,
                             (x, cur_y, W, BTN_H), 1, border_radius=5)

            # 主標籤（左，fn_card 字體）
            lbl_s = fn_card.render(label, True, text_col)
            surface.blit(lbl_s, (x + 16, cur_y + (BTN_H - lbl_s.get_height()) // 2))

            # 按鍵提示（右，fn_sm，背景 badge）
            hint_s  = fn_sm.render(key_hint, True, self._DIM)
            hint_bw = hint_s.get_width() + 12
            hint_bh = hint_s.get_height() + 6
            hint_bx = x + W - hint_bw - 10
            hint_by = cur_y + (BTN_H - hint_bh) // 2
            pygame.draw.rect(surface, self._BG,
                             (hint_bx, hint_by, hint_bw, hint_bh), border_radius=3)
            pygame.draw.rect(surface, self._BORDER,
                             (hint_bx, hint_by, hint_bw, hint_bh), 1, border_radius=3)
            surface.blit(hint_s, (hint_bx + 6, hint_by + 3))

            # ── 正確的 hit-test 矩形（使用傳入的絕對座標 x, cur_y）──
            self._btn_rects[name] = pygame.Rect(x, cur_y, W, BTN_H)

            cur_y += BTN_H + BTN_G


class ClearAnim:
    """Level clear animation overlay."""
    def __init__(self, fonts):
        self.fonts = fonts
        self.timer = 1.5
        self.done = False

    def update(self, dt):
        self.timer -= dt
        if self.timer <= 0:
            self.done = True

    def draw(self, surface):
        t = 1 - max(0, self.timer) / 1.5  # 0→1
        # Fade up
        alpha = int(min(255, max(0, math.sin(t * math.pi) * 255)))
        y_offset = int(-40 * t)

        font = self.fonts['big']
        text = "LEVEL CLEAR！"
        surf = font.render(text, True, SUCCESS_GREEN)
        surf.set_alpha(alpha)
        surface.blit(surf, (SCREEN_WIDTH//2 - surf.get_width()//2,
                            SCREEN_HEIGHT//2 + y_offset - 30))
