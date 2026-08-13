import math
import random
import pygame
import config

def tile_at(x, y, level_map):
    ix, iy = int(x), int(y)
    if level_map and 0 <= iy < len(level_map) and 0 <= ix < len(level_map[0]):
        ch = level_map[iy][ix]
        return ch if ch != "." else None
    return "1"

def is_wall(x, y, level_map):
    return tile_at(x, y, level_map) is not None

class Player:
    def __init__(self, x, y, angle):
        self.x = x
        self.y = y
        self.angle = angle
        self.pitch = 0.0
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

    def try_move(self, dx, dy, level_map):
        if not is_wall(self.x + dx, self.y, level_map):
            self.x += dx
        if not is_wall(self.x, self.y + dy, level_map):
            self.y += dy

    def update(self, dt, keys, mouse_dx, mouse_dy, level_map):
        self.angle += mouse_dx * config.MOUSE_SENS
        self.pitch -= mouse_dy * config.PITCH_SENS * 100.0
        self.pitch = max(-config.MAX_PITCH, min(config.MAX_PITCH, self.pitch))

        if keys[pygame.K_LEFT]:
            self.angle -= config.ROT_SPEED * dt
        if keys[pygame.K_RIGHT]:
            self.angle += config.ROT_SPEED * dt
        if keys[pygame.K_UP]:
            self.pitch = min(config.MAX_PITCH, self.pitch + config.ROT_SPEED * 15.0 * dt)
        if keys[pygame.K_DOWN]:
            self.pitch = max(-config.MAX_PITCH, self.pitch - config.ROT_SPEED * 15.0 * dt)

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
            self.try_move(dx, dy, level_map)

class Enemy:
    def __init__(self, x, y, max_hp=config.ENEMY_MAX_HP, contact_damage=config.ENEMY_CONTACT_DAMAGE,
                 speed=config.ENEMY_SPEED, radius=config.ENEMY_RADIUS, height_scale=config.ENEMY_HEIGHT_SCALE,
                 is_boss=False, name=None):
        self.x = x
        self.y = y
        self.max_hp = max_hp
        self.hp = max_hp
        self.contact_damage = contact_damage
        self.speed = speed
        self.radius = radius
        self.height_scale = height_scale
        self.is_boss = is_boss
        self.name = name
        self.alive = True
        self.hit_flash = 0.0

    def update(self, dt, player, level_map):
        if not self.alive:
            return
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy)
        if dist <= config.ENEMY_STOP_DIST or dist < 1e-4:
            return

        dx /= dist
        dy /= dist
        step_x = dx * self.speed * dt
        step_y = dy * self.speed * dt

        if not is_wall(self.x + step_x, self.y, level_map):
            self.x += step_x
        if not is_wall(self.x, self.y + step_y, level_map):
            self.y += step_y

def get_open_tiles(level_map):
    tiles = []
    if not level_map:
        return tiles
    for y in range(len(level_map)):
        for x in range(len(level_map[0])):
            if level_map[y][x] == ".":
                tiles.append((x + 0.5, y + 0.5))
    return tiles

def spawn_enemies(level_map, e_cfg):
    candidates = [(4.5, 3.5), (13.5, 3.5), (10.5, 7.5), (6.5, 11.5), (12.5, 11.5)]
    enemies = []
    for x, y in candidates:
        if not is_wall(x, y, level_map):
            enemies.append(Enemy(
                x, y,
                max_hp=e_cfg.get("max_hp", config.ENEMY_MAX_HP),
                contact_damage=e_cfg.get("contact_damage", config.ENEMY_CONTACT_DAMAGE),
                speed=e_cfg.get("speed", config.ENEMY_SPEED)
            ))
    return enemies

def spawn_random_enemy(player, level_map, e_cfg, attempts=30):
    open_tiles = get_open_tiles(level_map)
    min_dist = e_cfg.get("spawn_min_dist", config.ENEMY_SPAWN_MIN_DIST)
    if not open_tiles:
        return Enemy(1.5, 1.5)
    for _ in range(attempts):
        x, y = random.choice(open_tiles)
        if math.hypot(x - player.x, y - player.y) >= min_dist:
            return Enemy(
                x, y,
                max_hp=e_cfg.get("max_hp", config.ENEMY_MAX_HP),
                contact_damage=e_cfg.get("contact_damage", config.ENEMY_CONTACT_DAMAGE),
                speed=e_cfg.get("speed", config.ENEMY_SPEED)
            )
    x, y = random.choice(open_tiles)
    return Enemy(
        x, y,
        max_hp=e_cfg.get("max_hp", config.ENEMY_MAX_HP),
        contact_damage=e_cfg.get("contact_damage", config.ENEMY_CONTACT_DAMAGE),
        speed=e_cfg.get("speed", config.ENEMY_SPEED)
    )

def spawn_boss(player, level_map, b_cfg, attempts=30):
    open_tiles = get_open_tiles(level_map)
    min_dist = b_cfg.get("spawn_min_dist", config.BOSS_SPAWN_MIN_DIST)
    if not open_tiles:
        x, y = 2.5, 2.5
    else:
        for _ in range(attempts):
            x, y = random.choice(open_tiles)
            if math.hypot(x - player.x, y - player.y) >= min_dist:
                break
        else:
            x, y = random.choice(open_tiles)
    return Enemy(
        x, y,
        max_hp=b_cfg.get("max_hp", config.BOSS_MAX_HP),
        contact_damage=b_cfg.get("contact_damage", config.BOSS_CONTACT_DAMAGE),
        speed=b_cfg.get("speed", config.BOSS_SPEED),
        radius=b_cfg.get("radius", config.BOSS_RADIUS),
        height_scale=b_cfg.get("height_scale", config.BOSS_HEIGHT_SCALE),
        is_boss=True,
        name=b_cfg.get("name", config.BOSS_NAME)
    )