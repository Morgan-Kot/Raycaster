import math
import pygame
import config

def tile_at(x, y):
    ix, iy = int(x), int(y)
    if 0 <= iy < config.MAP_H and 0 <= ix < config.MAP_W:
        ch = config.MAP[iy][ix]
        return ch if ch != "." else None
    return "1"

def is_wall(x, y):
    return tile_at(x, y) is not None

class Player:
    def __init__(self, x, y, angle):
        self.x = x
        self.y = y
        self.angle = angle
        self.radius = 0.2
        self.hp = config.PLAYER_MAX_HP
        self.invuln_timer = 0.0
        self.damage_flash = 0.0

    def take_damage(self, amount):
        if self.invuln_timer > 0:
            return False
        self.hp = max(0, self.hp - amount)
        self.invuln_timer = config.PLAYER_HIT_COOLDOWN
        self.damage_flash = config.PLAYER_DAMAGE_FLASH_DURATION
        return True

    def try_move(self, dx, dy):
        if not is_wall(self.x + dx, self.y):
            self.x += dx
        if not is_wall(self.x, self.y + dy):
            self.y += dy

    def update(self, dt, keys, mouse_dx):
        self.angle += mouse_dx * config.MOUSE_SENS

        if keys[pygame.K_LEFT]:
            self.angle -= config.ROT_SPEED * dt
        if keys[pygame.K_RIGHT]:
            self.angle += config.ROT_SPEED * dt

        speed = config.MOVE_SPEED
        if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
            speed *= config.RUN_MULT

        forward = 0.0
        strafe = 0.0
        if keys[pygame.K_w]:
            forward += 1.0
        if keys[pygame.K_s]:
            forward -= 1.0
        if keys[pygame.K_d]:
            strafe += 1.0
        if keys[pygame.K_a]:
            strafe -= 1.0

        if forward or strafe:
            length = math.hypot(forward, strafe)
            forward /= length
            strafe /= length
            dx = (math.cos(self.angle) * forward + math.cos(self.angle + math.pi / 2) * strafe)
            dy = (math.sin(self.angle) * forward + math.sin(self.angle + math.pi / 2) * strafe)
            dx *= speed * dt
            dy *= speed * dt
            self.try_move(dx, dy)