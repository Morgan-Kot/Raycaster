import os
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

        is_moving = False
        if forward or strafe:
            is_moving = True
            length = math.hypot(forward, strafe)
            forward /= length
            strafe /= length
            dx = (math.cos(self.angle) * forward + math.cos(self.angle + math.pi / 2) * strafe)
            dy = (math.sin(self.angle) * forward + math.sin(self.angle + math.pi / 2) * strafe)
            dx *= speed * dt
            dy *= speed * dt
            self.try_move(dx, dy, level_map)

        return is_moving

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

class Projectile:
    def __init__(self, x, y, angle):
        self.x = x
        self.y = y
        self.vx = math.cos(angle) * config.BULLET_SPEED
        self.vy = math.sin(angle) * config.BULLET_SPEED
        self.alive = True

    def update(self, dt, level_map, enemies):
        if not self.alive:
            return None
        self.x += self.vx * dt
        self.y += self.vy * dt

        if is_wall(self.x, self.y, level_map):
            self.alive = False
            return None

        for e in enemies:
            if e.alive:
                if math.hypot(e.x - self.x, e.y - self.y) <= e.radius:
                    e.hp = max(0, e.hp - config.GUN_DAMAGE)
                    e.hit_flash = config.HIT_FLASH_DURATION
                    if e.hp <= 0:
                        e.alive = False
                    self.alive = False
                    return e
        return None

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

def generate_stone_texture(size=config.TEX_SIZE, seed=1337):
    rng = random.Random(seed)
    tex = pygame.Surface((size, size))

    base = 175
    for y in range(size):
        for x in range(size):
            n = rng.randint(-22, 22)
            v = max(0, min(255, base + n))
            tex.set_at((x, y), (v, v, v))

    block_w, block_h = size // 4, size // 4
    mortar = (60, 60, 60)
    highlight = (170, 170, 170)
    for by in range(0, size, block_h):
        row_offset = (block_w // 2) if (by // block_h) % 2 else 0
        for bx in range(-block_w, size + block_w, block_w):
            x0 = bx + row_offset
            pygame.draw.rect(tex, mortar, (x0, by, block_w, block_h), width=2)
            pygame.draw.line(tex, highlight, (x0 + 2, by + 2), (x0 + block_w - 3, by + 2))
            pygame.draw.line(tex, highlight, (x0 + 2, by + 2), (x0 + 2, by + block_h - 3))

    for _ in range(size * 2):
        x, y = rng.randrange(size), rng.randrange(size)
        c = tex.get_at((x, y))
        d = max(0, c.r - rng.randint(10, 40))
        tex.set_at((x, y), (d, d, d))

    return tex

def build_wall_textures():
    stone = generate_stone_texture()
    textures = {}
    for wall_id, color in config.WALL_COLORS.items():
        lit = stone.copy()
        lit.fill(color, special_flags=pygame.BLEND_RGB_MULT)

        shaded = lit.copy()
        dark = tuple(int(c * config.SIDE_SHADE) for c in (255, 255, 255))
        shaded.fill(dark, special_flags=pygame.BLEND_RGB_MULT)

        textures[wall_id] = (lit, shaded)
    return textures

def generate_enemy_sprite():
    w, h = 16, 26
    img = pygame.Surface((w, h), pygame.SRCALPHA)

    body_color = (70, 40, 90)
    body_dark = (45, 25, 60)
    eye_color = (255, 60, 40)

    pygame.draw.polygon(img, body_color, [(3, 25), (2, 14), (4, 8), (12, 8), (14, 14), (13, 25)])
    pygame.draw.ellipse(img, body_color, (4, 2, 8, 8))
    pygame.draw.polygon(img, body_dark, [(9, 8), (12, 8), (14, 14), (13, 25), (9, 25)])
    pygame.draw.rect(img, eye_color, (5, 5, 2, 2))
    pygame.draw.rect(img, eye_color, (9, 5, 2, 2))
    pygame.draw.line(img, body_dark, (3, 15), (0, 21), 2)
    pygame.draw.line(img, body_dark, (13, 15), (16, 21), 2)

    return img

def generate_boss_sprite():
    w, h = 22, 30
    img = pygame.Surface((w, h), pygame.SRCALPHA)

    body_color = (110, 20, 20)
    body_dark = (60, 10, 10)
    robe_color = (25, 10, 12)
    eye_color = (255, 150, 30)

    pygame.draw.polygon(img, robe_color, [(2, 29), (1, 16), (4, 9), (18, 9), (21, 16), (20, 29)])
    pygame.draw.polygon(img, body_color, [(6, 29), (5, 16), (7, 11), (15, 11), (17, 16), (16, 29)])
    pygame.draw.polygon(img, body_dark, [(11, 11), (15, 11), (17, 16), (16, 29), (11, 29)])
    pygame.draw.ellipse(img, body_color, (6, 2, 10, 9))
    pygame.draw.polygon(img, (30, 30, 30), [(6, 5), (2, 0), (7, 3)])
    pygame.draw.polygon(img, (30, 30, 30), [(16, 5), (20, 0), (15, 3)])
    pygame.draw.rect(img, eye_color, (7, 6, 3, 2))
    pygame.draw.rect(img, eye_color, (12, 6, 3, 2))
    pygame.draw.line(img, body_dark, (4, 17), (0, 25), 3)
    pygame.draw.line(img, body_dark, (18, 17), (22, 25), 3)

    return img

def generate_gun_sprite():
    if os.path.exists(config.WEAPONS_DIR):
        for ext in [".png", ".bmp", ".jpg"]:
            path = os.path.join(config.WEAPONS_DIR, "gun" + ext)
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    return pygame.transform.scale(img, (96, 80))
                except Exception:
                    pass

    w, h = 96, 80
    img = pygame.Surface((w, h), pygame.SRCALPHA)

    steel = (90, 95, 105)
    steel_dark = (45, 48, 55)
    steel_light = (140, 145, 160)
    wood = (85, 48, 25)
    wood_dark = (50, 28, 15)
    glove = (30, 30, 35)

    pygame.draw.polygon(img, wood, [(20, 42), (68, 42), (62, 74), (30, 74)])
    pygame.draw.polygon(img, wood_dark, [(52, 42), (68, 42), (62, 74), (46, 74)])

    pygame.draw.rect(img, steel_dark, (10, 16, 70, 28))
    pygame.draw.rect(img, steel, (12, 18, 66, 24))

    pygame.draw.rect(img, steel_dark, (0, 8, 64, 16))
    pygame.draw.rect(img, steel, (0, 10, 62, 12))
    pygame.draw.line(img, steel_light, (2, 10), (60, 10), 2)

    pygame.draw.polygon(img, glove, [(38, 52), (96, 52), (96, 80), (30, 80)])
    pygame.draw.circle(img, (20, 20, 22), (58, 62), 14)

    return img

def cast_ray(px, py, angle, level_map):
    ray_dx = math.cos(angle)
    ray_dy = math.sin(angle)

    map_x, map_y = int(px), int(py)

    delta_dist_x = abs(1.0 / ray_dx) if ray_dx != 0 else 1e30
    delta_dist_y = abs(1.0 / ray_dy) if ray_dy != 0 else 1e30

    if ray_dx < 0:
        step_x = -1
        side_dist_x = (px - map_x) * delta_dist_x
    else:
        step_x = 1
        side_dist_x = (map_x + 1.0 - px) * delta_dist_x

    if ray_dy < 0:
        step_y = -1
        side_dist_y = (py - map_y) * delta_dist_y
    else:
        step_y = 1
        side_dist_y = (map_y + 1.0 - py) * delta_dist_y

    side = 0
    wall_id = None
    map_h = len(level_map) if level_map else 40
    map_w = len(level_map[0]) if level_map else 40

    for _ in range(256):
        if side_dist_x < side_dist_y:
            side_dist_x += delta_dist_x
            map_x += step_x
            side = 0
        else:
            side_dist_y += delta_dist_y
            map_y += step_y
            side = 1

        if level_map and 0 <= map_y < map_h and 0 <= map_x < map_w:
            ch = level_map[map_y][map_x]
            if ch != ".":
                wall_id = ch
                break
        else:
            wall_id = "1"
            break

    if side == 0:
        dist = side_dist_x - delta_dist_x
        hit_y = py + dist * ray_dy
        wall_x = hit_y - math.floor(hit_y)
    else:
        dist = side_dist_y - delta_dist_y
        hit_x = px + dist * ray_dx
        wall_x = hit_x - math.floor(hit_x)

    return dist, wall_id, side, wall_x

def render_scene(surface, player, textures, zbuffer, level_map):
    horizon = int(config.RENDER_H // 2 + player.pitch)
    floor_start = max(0, min(config.RENDER_H, horizon))

    surface.fill(config.CEILING_COLOR, (0, 0, config.RENDER_W, floor_start))
    surface.fill(config.FLOOR_COLOR, (0, floor_start, config.RENDER_W, config.RENDER_H - floor_start))

    start_angle = player.angle - config.HALF_FOV

    for col in range(config.NUM_RAYS):
        ray_angle = start_angle + col * config.STEP_ANGLE

        dist, wall_id, side, wall_x = cast_ray(player.x, player.y, ray_angle, level_map)

        dist *= math.cos(ray_angle - player.angle)
        dist = max(dist, 0.0001)
        zbuffer[col] = dist

        height_mult = 1.3 if wall_id == "7" else config.WALL_HEIGHT_SCALE
        wall_h = int((config.RENDER_H / dist) * height_mult)
        wall_h = min(wall_h, config.RENDER_H * 4)

        y0 = max(0, horizon - wall_h // 2)
        y1 = min(config.RENDER_H, horizon + wall_h // 2)
        draw_h = max(1, y1 - y0)

        lit_tex, shaded_tex = textures.get(wall_id, textures["1"])
        tex = shaded_tex if side == 1 else lit_tex

        tex_x = min(config.TEX_SIZE - 1, int(wall_x * config.TEX_SIZE))
        column = tex.subsurface((tex_x, 0, 1, config.TEX_SIZE))
        column = pygame.transform.scale(column, (1, draw_h))

        shade = max(0.2, 1.0 - dist / config.MAX_DEPTH)
        fog = int(255 * shade)
        column.fill((fog, fog, fog), special_flags=pygame.BLEND_RGB_MULT)

        surface.blit(column, (col, y0))

def render_enemies_and_bullets(surface, player, enemies, bullets, zbuffer, sprite_img, boss_sprite_img):
    horizon = int(config.RENDER_H // 2 + player.pitch)
    render_list = []

    for e in enemies:
        if not e.alive and e.hit_flash <= 0:
            continue
        dx = e.x - player.x
        dy = e.y - player.y
        dist = math.hypot(dx, dy)
        if dist < 1e-4:
            continue
        angle_to = math.atan2(dy, dx)
        rel = (angle_to - player.angle + math.pi) % (2 * math.pi) - math.pi
        if abs(rel) > config.HALF_FOV + 0.4:
            continue
        render_list.append((dist, rel, "enemy", e))

    for b in bullets:
        if not b.alive:
            continue
        dx = b.x - player.x
        dy = b.y - player.y
        dist = math.hypot(dx, dy)
        if dist < 1e-4:
            continue
        angle_to = math.atan2(dy, dx)
        rel = (angle_to - player.angle + math.pi) % (2 * math.pi) - math.pi
        if abs(rel) > config.HALF_FOV + 0.4:
            continue
        render_list.append((dist, rel, "bullet", b))

    render_list.sort(key=lambda t: -t[0])

    for dist, rel, item_type, item in render_list:
        perp_dist = dist * math.cos(rel)
        if perp_dist < 0.1:
            continue

        if item_type == "enemy":
            e = item
            img = boss_sprite_img if e.is_boss else sprite_img
            unit_h = (config.RENDER_H / perp_dist) * config.WALL_HEIGHT_SCALE
            sprite_h = unit_h * e.height_scale
            aspect = img.get_width() / img.get_height()
            sprite_w = sprite_h * aspect

            screen_x_center = ((rel + config.HALF_FOV) / config.FOV) * config.RENDER_W
            x0 = screen_x_center - sprite_w / 2
            y_bottom = horizon + unit_h / 2
            y_top = y_bottom - sprite_h

            sw = max(1, int(sprite_w))
            sh = max(1, int(sprite_h))
            scaled_sprite = pygame.transform.scale(img, (sw, sh))

            if e.hit_flash > 0:
                tint = (255, 255, 255)
            else:
                shade = max(0.35, 1.0 - perp_dist / config.MAX_DEPTH)
                g = int(255 * shade)
                tint = (g, g, g)
            tinted = scaled_sprite.copy()
            tinted.fill(tint, special_flags=pygame.BLEND_RGB_MULT)

            any_visible = False
            for i in range(sw):
                col = int(x0) + i
                if 0 <= col < config.RENDER_W and perp_dist < zbuffer[col]:
                    strip = tinted.subsurface((i, 0, 1, sh))
                    surface.blit(strip, (col, int(y_top)))
                    any_visible = True

            if e.alive and any_visible and not e.is_boss:
                bar_w = max(4, int(sprite_w))
                bar_h = max(2, int(sprite_h * 0.07))
                bar_x = int(x0)
                bar_y = int(y_top) - bar_h - 3

                hp_frac = max(0.0, min(1.0, e.hp / e.max_hp))
                pygame.draw.rect(surface, (20, 20, 20), (bar_x, bar_y, bar_w, bar_h))
                fill_color = (60, 200, 70) if hp_frac > 0.3 else (210, 60, 50)
                pygame.draw.rect(surface, fill_color, (bar_x, bar_y, int(bar_w * hp_frac), bar_h))
                pygame.draw.rect(surface, (10, 10, 10), (bar_x, bar_y, bar_w, bar_h), width=1)

        elif item_type == "bullet":
            screen_x_center = ((rel + config.HALF_FOV) / config.FOV) * config.RENDER_W
            col = int(screen_x_center)
            if 0 <= col < config.RENDER_W and perp_dist < zbuffer[col]:
                by = int(horizon)
                pygame.draw.circle(surface, (255, 240, 120), (col, by), max(1, int(4 / perp_dist)))

def draw_weapon(surface, gun_img, gun_state, dt):
    if gun_state["cooldown_timer"] > 0:
        gun_state["cooldown_timer"] = max(0.0, gun_state["cooldown_timer"] - dt)
    if gun_state["recoil_timer"] > 0:
        gun_state["recoil_timer"] = max(0.0, gun_state["recoil_timer"] - dt)
    if gun_state["flash_timer"] > 0:
        gun_state["flash_timer"] = max(0.0, gun_state["flash_timer"] - dt)

    gun_w, gun_h = gun_img.get_size()
    gx = config.RENDER_W - gun_w - 2
    gy = config.RENDER_H - gun_h

    if gun_state["recoil_timer"] > 0:
        gy += 6
        gx += 2

    surface.blit(gun_img, (gx, gy))

    if gun_state["flash_timer"] > 0:
        flash_x = gx + 4
        flash_y = gy + 8
        pygame.draw.circle(surface, (255, 235, 160), (flash_x, flash_y), 14)
        pygame.draw.circle(surface, (255, 255, 255), (flash_x, flash_y), 7)

def draw_crosshair(surface):
    cx = config.RENDER_W // 2
    cy = config.RENDER_H // 2
    color = (230, 230, 230)
    pygame.draw.line(surface, color, (cx - 4, cy), (cx - 1, cy))
    pygame.draw.line(surface, color, (cx + 1, cy), (cx + 4, cy))
    pygame.draw.line(surface, color, (cx, cy - 4), (cx, cy - 1))
    pygame.draw.line(surface, color, (cx, cy + 1), (cx, cy + 4))

def shoot(player, gun_state):
    if gun_state.get("cooldown_timer", 0.0) > 0:
        return None
    gun_state["cooldown_timer"] = config.FIRE_RATE_COOLDOWN
    gun_state["recoil_timer"] = config.RECOIL_DURATION
    gun_state["flash_timer"] = config.FLASH_DURATION
    return Projectile(player.x + math.cos(player.angle) * 0.3, player.y + math.sin(player.angle) * 0.3, player.angle)

def render_minimap(surface, player, enemies, level_map, scale=2, ox=4, oy=4):
    if not level_map:
        return
    map_h = len(level_map)
    map_w = len(level_map[0])
    for y in range(map_h):
        for x in range(map_w):
            ch = level_map[y][x]
            rect = pygame.Rect(ox + x * scale, oy + y * scale, scale, scale)
            if ch == ".":
                pygame.draw.rect(surface, (25, 25, 30), rect)
            else:
                pygame.draw.rect(surface, config.WALL_COLORS.get(ch, (255, 0, 255)), rect)

    for e in enemies:
        if e.alive:
            ex = ox + int(e.x * scale)
            ey = oy + int(e.y * scale)
            pygame.draw.circle(surface, (255, 60, 40), (ex, ey), 1)

    px = ox + int(player.x * scale)
    py = oy + int(player.y * scale)
    pygame.draw.circle(surface, (255, 255, 0), (px, py), 1)
    end_x = px + math.cos(player.angle) * scale
    end_y = py + math.sin(player.angle) * scale
    pygame.draw.line(surface, (255, 255, 0), (px, py), (end_x, end_y), 1)

def draw_player_hp_bar(surface, player, font):
    bar_w, bar_h = 70, 8
    margin = 5
    x = config.RENDER_W - bar_w - margin
    y = margin

    hp_frac = max(0.0, min(1.0, player.hp / config.PLAYER_MAX_HP))
    fill_color = (60, 200, 70) if hp_frac > 0.3 else (210, 60, 50)

    pygame.draw.rect(surface, (20, 20, 20), (x, y, bar_w, bar_h))
    pygame.draw.rect(surface, fill_color, (x, y, int(bar_w * hp_frac), bar_h))
    pygame.draw.rect(surface, (230, 230, 230), (x, y, bar_w, bar_h), width=1)

    label = font.render(f"HP {player.hp}", True, (255, 255, 255))
    label_rect = label.get_rect(center=(x + bar_w // 2, y + bar_h // 2))
    surface.blit(label, label_rect)

def draw_boss_hp_bar(surface, boss, font):
    bar_w, bar_h = 150, 10
    x = config.RENDER_W // 2 - bar_w // 2
    y = 5

    hp_frac = max(0.0, min(1.0, boss.hp / boss.max_hp))

    name_label = font.render(boss.name, True, (255, 140, 60))
    name_rect = name_label.get_rect(center=(config.RENDER_W // 2, y - 1))
    surface.blit(name_label, name_rect)

    pygame.draw.rect(surface, (20, 20, 20), (x, y + 6, bar_w, bar_h))
    pygame.draw.rect(surface, (170, 30, 30), (x, y + 6, int(bar_w * hp_frac), bar_h))
    pygame.draw.rect(surface, (230, 230, 230), (x, y + 6, bar_w, bar_h), width=1)

def draw_damage_flash(surface, flash_overlay, player):
    if player.damage_flash <= 0:
        return
    alpha = int(140 * (player.damage_flash / config.PLAYER_DAMAGE_FLASH_DURATION))
    flash_overlay.set_alpha(max(0, min(255, alpha)))
    surface.blit(flash_overlay, (0, 0))

def draw_tab_overlay(surface, font, fps, enemies_left, kill_count, status_str, current_level_name):
    overlay = pygame.Surface((240, 140), pygame.SRCALPHA)
    overlay.fill((15, 15, 25, 230))
    pygame.draw.rect(overlay, (220, 180, 60), (0, 0, 240, 140), width=1, border_radius=3)

    lines = [
        f"{current_level_name}",
        f"FPS:{fps:.0f}  Left:{enemies_left}  Kills:{kill_count}",
        f"Status: {status_str}",
        "",
        "WASD:Move  Mouse:Look  L-Click:Fire",
        "LSHIFT:Run  M:Minimap  F:Fullscreen"
    ]

    for i, line in enumerate(lines):
        color = (255, 220, 80) if i == 0 or i == 4 else (220, 220, 220)
        lbl = font.render(line, True, color)
        overlay.blit(lbl, (8, 6 + i * 18))

    x = config.RENDER_W // 2 - 120
    y = config.RENDER_H // 2 - 70
    surface.blit(overlay, (x, y))

def draw_main_menu(surface, title_font, font, level_display_name, mouse_pos):
    surface.fill((15, 12, 20))

    title = title_font.render("RETRO RAYCASTER", True, (230, 60, 40))
    sub = font.render("3D Castle Engine", True, (160, 160, 180))
    surface.blit(title, title.get_rect(center=(config.RENDER_W // 2, 35)))
    surface.blit(sub, sub.get_rect(center=(config.RENDER_W // 2, 52)))

    play_rect = pygame.Rect(config.RENDER_W // 2 - 60, 75, 120, 22)
    lvl_rect = pygame.Rect(config.RENDER_W // 2 - 60, 102, 120, 22)
    set_rect = pygame.Rect(config.RENDER_W // 2 - 60, 129, 120, 22)
    exit_rect = pygame.Rect(config.RENDER_W // 2 - 60, 156, 120, 22)

    for r, txt in [(play_rect, "PLAY GAME"), (lvl_rect, f"LVL: {level_display_name}"),
                   (set_rect, "SETTINGS"), (exit_rect, "EXIT")]:
        hov = r.collidepoint(mouse_pos)
        c = (80, 140, 80) if hov else (50, 50, 65)
        pygame.draw.rect(surface, c, r, border_radius=3)
        pygame.draw.rect(surface, (220, 220, 220), r, width=1, border_radius=3)
        lbl = font.render(txt, True, (255, 255, 255))
        surface.blit(lbl, lbl.get_rect(center=r.center))

    return play_rect, lvl_rect, set_rect, exit_rect

def draw_settings_menu(surface, title_font, font, sound_mgr, mouse_pos):
    surface.fill((15, 12, 20))

    title = title_font.render("SETTINGS", True, (240, 200, 60))
    surface.blit(title, title.get_rect(center=(config.RENDER_W // 2, 25)))

    vol_lbl = font.render(f"Volume: {int(sound_mgr.volume * 100)}%", True, (220, 220, 220))
    surface.blit(vol_lbl, (config.RENDER_W // 2 - 65, 48))

    vol_down_rect = pygame.Rect(config.RENDER_W // 2 + 25, 45, 18, 16)
    vol_up_rect = pygame.Rect(config.RENDER_W // 2 + 48, 45, 18, 16)

    for r, txt in [(vol_down_rect, "-"), (vol_up_rect, "+")]:
        hov = r.collidepoint(mouse_pos)
        c = (120, 120, 150) if hov else (60, 60, 80)
        pygame.draw.rect(surface, c, r, border_radius=2)
        pygame.draw.rect(surface, (220, 220, 220), r, width=1, border_radius=2)
        lbl = font.render(txt, True, (255, 255, 255))
        surface.blit(lbl, lbl.get_rect(center=r.center))

    ctrl_box = pygame.Rect(config.RENDER_W // 2 - 120, 72, 240, 88)
    pygame.draw.rect(surface, (25, 25, 35), ctrl_box, border_radius=3)
    pygame.draw.rect(surface, (100, 100, 120), ctrl_box, width=1, border_radius=3)

    ctrls = [
        "CONTROLS:",
        "WASD - Move & Footsteps",
        "Mouse / Arrows - Pitch & Yaw",
        "Left Click - Shoot Bullets",
        "M Key - Hold for Minimap",
        "TAB Key - Hold for Stats"
    ]
    for i, line in enumerate(ctrls):
        c = (255, 200, 60) if i == 0 else (200, 200, 210)
        lbl = font.render(line, True, c)
        surface.blit(lbl, (ctrl_box.x + 8, ctrl_box.y + 6 + i * 13))

    back_rect = pygame.Rect(config.RENDER_W // 2 - 40, 168, 80, 20)
    hov = back_rect.collidepoint(mouse_pos)
    c = (140, 70, 70) if hov else (70, 50, 50)
    pygame.draw.rect(surface, c, back_rect, border_radius=3)
    pygame.draw.rect(surface, (220, 220, 220), back_rect, width=1, border_radius=3)
    lbl = font.render("BACK", True, (255, 255, 255))
    surface.blit(lbl, lbl.get_rect(center=back_rect.center))

    return vol_down_rect, vol_up_rect, back_rect

def get_respawn_button_rect():
    btn_w, btn_h = 90, 24
    x = config.RENDER_W // 2 - btn_w // 2
    y = config.RENDER_H // 2 + 15
    return pygame.Rect(x, y, btn_w, btn_h)

def draw_end_screen(surface, big_font, font, won, mouse_pos, boss_name="THE REVENANT"):
    overlay = pygame.Surface((config.RENDER_W, config.RENDER_H), pygame.SRCALPHA)
    overlay.fill((0, 10, 0, 190) if won else (10, 0, 0, 190))
    surface.blit(overlay, (0, 0))

    if won:
        title = big_font.render("YOU WIN", True, (240, 200, 60))
        subtitle = font.render(f"{boss_name} has fallen.", True, (220, 220, 220))
    else:
        title = big_font.render("GAME OVER", True, (220, 40, 40))
        subtitle = None

    title_rect = title.get_rect(center=(config.RENDER_W // 2, config.RENDER_H // 2 - 25))
    surface.blit(title, title_rect)
    if subtitle is not None:
        sub_rect = subtitle.get_rect(center=(config.RENDER_W // 2, config.RENDER_H // 2 - 5))
        surface.blit(subtitle, sub_rect)

    btn_rect = get_respawn_button_rect()
    hovered = btn_rect.collidepoint(mouse_pos)
    btn_color = (90, 160, 90) if hovered else (70, 70, 70)
    pygame.draw.rect(surface, btn_color, btn_rect, border_radius=3)
    pygame.draw.rect(surface, (230, 230, 230), btn_rect, width=1, border_radius=3)

    label = font.render("PLAY AGAIN" if won else "RESPAWN", True, (255, 255, 255))
    label_rect = label.get_rect(center=btn_rect.center)
    surface.blit(label, label_rect)