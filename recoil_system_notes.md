# Recoil System Design Notes

## 設計目標

舊系統（`get_rebound_multiplier()`）只考慮玩家自身裝備，碰到任何敵人的彈開感完全相同。
新系統引入「材質對材質」交互，讓碰撞有物理質感，也讓裝備選擇在對抗特定關卡時產生策略意義。

---

## MATERIAL_RECOIL_MATRIX 設計說明

### 核心原則

| 情境 | 值域 | 理由 |
|------|------|------|
| 輕材（wood）撞硬材（titan） | 1.6 | 最大反彈：木材無法吸收衝擊 |
| 重材（titan）撞輕材（wood） | 0.6 | 最小反彈：鈦合金質量壓制 |
| 同材對撞 | 1.0 | 對稱交互，公平基準 |
| 無材質玩家 fallback | 1.0～1.3 | 隨敵人硬度線性懲罰 |
| 無材質敵人（大多數敵人）| 0.7～1.0 | 按玩家材質重量給予相應減緩 |

### 完整矩陣值（玩家材質 × 敵人材質）

```
             wood   steel  titan  plastic  None
wood         1.0    1.3    1.6    0.8      1.0
steel        0.8    1.0    1.2    0.7      0.9
titan        0.6    0.75   1.0    0.5      0.7
None         1.0    1.1    1.3    0.9      1.0
```

### 遊戲語境對應

- **木頭 vs 鈦合金（1.6）**：L3+ 如遇到有 titan 屬性的衍生敵人，木頭玩家需格外謹慎
- **鈦合金 vs 木頭（0.6）**：鈦合金玩家打 L1 WoodChip 幾乎不受力——強調其「重量感」
- **None（無材質）vs 鋼鐵（1.1）**：L1 無裝備時，鐵釘（IronNail 無材質）給予略高的反作用力
- **鈦合金 vs None（0.7）**：鈦合金玩家打大多數普通敵人（無材質）彈開減輕，呼應其「重量不易被推動」設定

---

## 各修正層說明

### 層 1：材質矩陣（基礎）

查表邏輯（含 fallback）：
```python
force = MATRIX.get((p_mat, e_mat), MATRIX.get((None, e_mat), 1.0))
```
若兩個 key 都不存在，默認 1.0（中性）。

### 層 2：配件 / 驅動器

| 條件 | 修正 | 說明 |
|------|------|------|
| `drive == 'recoil_dampener'` | ×0.55（覆蓋） | 反震阻尼直接覆蓋，不與配件疊加，避免過度減弱 |
| `accessory == 'axis'` | ×0.75 | 穩定軸心，大幅減少位移 |
| `accessory == 'gear_ring'` | ×0.85 | 咬合環抓地，略減位移 |

`recoil_dampener` 使用「覆蓋」而非「疊加」的原因：若允許 axis + recoil_dampener 同時生效，力道會被壓縮到 0.75 × 0.55 = 0.41，使玩家幾乎免疫彈開，破壞平衡。

### 層 3：王冠核心（低轉懲罰）

```python
if core == 'crown' and rpm_ratio < 0.30:
    force *= 1.0 + 0.2 × (1.0 - rpm_ratio / 0.30)
```

- RPM @ 30%：+0%（無額外懲罰）
- RPM @ 0%：+20%（最多 ×1.2）

這與攻擊加成的設計對稱：王冠在低轉時攻擊更強，但彈得也更遠——高風險高回報。

### 層 4：混沌核心（方向偏移）

`direction_offset_deg += random.uniform(-15.0, 15.0)`

偏移量在 `take_hit` 中套用到 dx/dy 方向向量，不影響力道大小。
與舊系統行為一致（舊系統偏移 ±math.pi/12 ≈ ±15°）。

### 層 5：碰撞類型

`collision_type == 'weapon'` → 整體 ×0.5

武器尖端觸碰（非整體碰撞）傳遞的力道天然偏小。
注意 `take_hit` 的 `base_force` 在 `weapon_only` 時已使用較小公式，此 ×0.5 在其上再度減半，使武器命中的反作用力約為體碰撞的 1/3。

### 層 6：相對速度縮放

```python
speed_factor = clamp(relative_speed / 300, 0.5, 2.0)
```

| 情境 | 相對速度 | speed_factor |
|------|---------|-------------|
| 靜止重疊校正 | ~0 px/s | 0.5（下限） |
| 正常移動碰撞 | ~200 px/s | 0.67 |
| 標準速度碰撞 | 300 px/s | 1.0（基準）|
| 衝刺/加速帶碰撞 | 600 px/s | 2.0（上限）|

300 px/s 為基準點是因為玩家移速 240 px/s，加上追蹤敵人的合向速度約在此附近。

### 層 7：敵人武器修正

| 武器 | 效果 | 設計理由 |
|------|------|---------|
| hammer | ×1.4 | 重擊感，提示玩家保持距離 |
| scythe | +20° 方向偏轉 | 側切效果：被擊後方向難以預測，破壞逃跑路線 |
| staff | ×0.9 + 0.2s 額外暈眩 | 力道較輕但控制效果更強，增加「被推住」的體感 |

---

## 與現有系統的整合

### take_hit 雙路徑設計

```
傳入 recoil_result → 新路徑（材質矩陣系統）
未傳入             → 舊路徑（get_rebound_multiplier() + drive 邏輯）
```

舊路徑保留用途：
- 竹子牆壁碰撞（`_enforce_bamboo_walls`）
- Boss 鐳射/子彈傷害（`no_knockback=True`）
- 其他特殊傷害來源

### level_manager.py 呼叫點

在每次 `player.take_hit()` 前插入：
```python
_col_type = 'weapon' if (weapon_hit and not body_hit) else 'body'
_rel_vx = self.player.vx - getattr(e, 'vx', 0.0)
_rel_vy = self.player.vy - getattr(e, 'vy', 0.0)
_rel_spd = math.sqrt(_rel_vx**2 + _rel_vy**2)
_recoil = self.player.calc_collision_recoil(e, _col_type, _rel_spd)
self.player.take_hit(..., recoil_result=_recoil)
```

相對速度在碰撞前取樣（玩家速度 - 敵人速度），反映兩者實際的衝量差。

### drive dampener 視覺效果保留

在新路徑下，`recoil_dampener` 的力道減輕已在 `calc_collision_recoil` 中完成（×0.55）。
`take_hit` 新路徑仍會觸發：
- `self._recoil_shield = 0.3`（0.3s 減傷）
- `self._drive_flash_timer`（綠色護盾光圈動畫）

保證視覺回饋不丟失。

---

## 數值調整指南

所有新增常數均在 `constants.py` 的 `# ── Collision Recoil System ──` 區塊：

| 常數 | 說明 | 調整方向 |
|------|------|---------|
| `MATERIAL_RECOIL_MATRIX` | 各組合倍率 | 逐格微調，保持對稱性 |
| `RECOIL_WEAPON_HIT_MULT` | 武器命中倍率（0.5）| 調高 → 武器命中更有力 |
| `RECOIL_SPEED_DIV` | 速度基準點（300）| 調高 → 高速碰撞感覺更輕 |
| `RECOIL_SPEED_MIN/MAX` | 速度因子上下限 | 縮小範圍 → 更線性一致 |
| `RECOIL_ENEMY_HAMMER_MULT` | 錘子敵人倍率（1.4）| 調高 → 更有重擊感 |
| `RECOIL_ENEMY_SCYTHE_DEG` | 鐮刀偏轉角（20°）| 調高 → 側切感更強 |
| `RECOIL_ENEMY_STAFF_STUN` | 法杖暈眩（0.2s）| 調高 → 法杖控制更強 |
