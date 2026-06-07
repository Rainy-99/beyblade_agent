# spin_detector.py
import math

class SpinDetector:
    def __init__(self, cx, cy):
        self.cx = cx
        self.cy = cy
        self.last_move_angle = None   # direction of mouse velocity vector
        self.last_mx = None
        self.last_my = None
        self.accumulated = 0.0        # total signed degrees of direction rotation
        self.spins_completed = 0
        self.compass_sector = -1      # kept for HUD (unused)
        self.idle_timer = 0.0

    def update(self, dt, mx, my, player_x=None, player_y=None):
        completed = 0

        if self.last_mx is not None:
            dmx = mx - self.last_mx
            dmy = my - self.last_my
            move_dist = math.sqrt(dmx * dmx + dmy * dmy)

            if move_dist >= 2.0:
                # Track direction the mouse is MOVING, not where it is
                move_angle = math.degrees(math.atan2(dmy, dmx))

                if self.last_move_angle is not None:
                    delta = move_angle - self.last_move_angle
                    if delta > 180:
                        delta -= 360
                    elif delta < -180:
                        delta += 360

                    if abs(delta) > 0.5:
                        self.accumulated += delta
                        self.idle_timer = 0.0
                    else:
                        self.idle_timer += dt
                        if self.idle_timer > 1.2:
                            self.accumulated = 0.0

                self.last_move_angle = move_angle
            else:
                self.idle_timer += dt
                if self.idle_timer > 1.2:
                    self.accumulated = 0.0
                    self.last_move_angle = None

        self.last_mx = mx
        self.last_my = my

        while self.accumulated >= 360.0:
            self.accumulated -= 360.0
            completed += 1
            self.spins_completed += 1
        while self.accumulated <= -360.0:
            self.accumulated += 360.0
            completed += 1
            self.spins_completed += 1

        return completed

    def reset(self):
        self.last_move_angle = None
        self.last_mx = None
        self.last_my = None
        self.accumulated = 0.0
        self.idle_timer = 0.0
