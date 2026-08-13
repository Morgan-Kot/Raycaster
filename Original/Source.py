import math
import random
import sys

import pygame

# --------------------------------------------------------------------------- #
# CONFIG
# --------------------------------------------------------------------------- #

WINDOW_W, WINDOW_H = 1024, 640          # actual OS window size
RENDER_W, RENDER_H = 320, 200           # internal low-res buffer -> chunky pixels
FOV = math.pi / 3.0                     # 60 degrees
HALF_FOV = FOV / 2.0
MAX_DEPTH = 20.0
NUM_RAYS = RENDER_W
STEP_ANGLE = FOV / NUM_RAYS

MOVE_SPEED = 3.2          # tiles / second
RUN_MULT = 1.8
ROT_SPEED = 2.6           # radians / second (keyboard)
MOUSE_SENS = 0.0075

WALL_HEIGHT_SCALE = 0.9   # tweak projected wall height

TEX_SIZE = 64            # procedural texture resolution (square) 64 default
SIDE_SHADE = 0.7          # darkening multiplier for N/S vs E/W faces

SKY_WIDTH = 720           # full 360-degree wrap width for the skybox strip
SKY_HEIGHT = RENDER_H // 2

ENEMY_RADIUS = 0.35       # world-space hit radius used by the hitscan
ENEMY_HEIGHT_SCALE = 0.85 # enemy sprite height relative to a full wall tile
ENEMY_MAX_HP = 100
ENEMY_SPEED = 1.1         # tiles / second, slower than the player
ENEMY_STOP_DIST = 0.6     # stops this close to the player instead of overlapping
ENEMY_SPAWN_INTERVAL = 15.0  # seconds between waves; keeps spawning regardless of survivors
ENEMY_SPAWN_MIN_DIST = 3.0   # don't spawn right on top of the player
ENEMY_SPAWN_MIN_INTERVAL = 5.0     # spawn rate never gets faster than this
KILLS_PER_SPEEDUP = 5              # every N kills...
SPAWN_INTERVAL_STEP = 5.0          # ...shaves this many seconds off the spawn timer
GUN_DAMAGE = 20
RECOIL_DURATION = 0.15
FLASH_DURATION = 0.06
HIT_FLASH_DURATION = 0.15

PLAYER_MAX_HP = 100
ENEMY_CONTACT_DAMAGE = 15
ENEMY_CONTACT_RANGE = 0.65   # must reach roughly ENEMY_STOP_DIST to land a hit
PLAYER_HIT_COOLDOWN = 0.8    # seconds of grace between contact-damage ticks
PLAYER_DAMAGE_FLASH_DURATION = 0.25

KILLS_TO_BOSS = 20           # regular spawning halts and the boss appears here
BOSS_NAME = "THE REVENANT"
BOSS_MAX_HP = 500
BOSS_CONTACT_DAMAGE = 25
BOSS_SPEED = 0.9              # slower, more menacing than regular enemies
BOSS_RADIUS = 0.6             # bigger hitbox to match its bigger silhouette
BOSS_HEIGHT_SCALE = 1.9       # towers over a regular enemy (0.85) and a wall tile
BOSS_SPAWN_MIN_DIST = 4.0

# 0 = empty. Any other number = wall "color id".
MAP = [
    "1111111111111111111111111111111111111111",
    "1...................1..................1",
    "1..222222...........1..1111............1",
    "1..222222..111......1..1111...333333...1",
    "1..222222..111.........1111...333333...1",
    "1..........111..1111..........333333...1",
    "1...............1111...................1",
    "1..11111..................1111111......1",
    "1..11111...44444..........1111111......1",
    "1..11111...44444...111....1111111...11.1",
    "1..........44444...111..............11.1",
    "1..................111........1111.....1",
    "1......1111111................1111.....1",
    "1......1111111.......11111.............1",
    "1......1111111.......11111...1111111...1",
    "1....................11111...1111111...1",
    "1..111.........111...........1111111...1",
    "1..111.........111.....................1",
    "1..111...11....111..1111111............1",
    "1........11.........1111111...11111....1",
    "1...................1111111...11111....1",
    "1...111111....................11111....1",
    "1...111111...11111.....................1",
    "1...111111...11111...5555555...........1",
    "1............11111...5555555...111.....1",
    "1....................5555555...111.....1",
    "1..1111........................111.....1",
    "1..1111...11111111.....................1",
    "1..1111...11111111..........11111111...1",
    "1.........11111111...666....11111111...1",
    "1....................666....11111111...1",
    "1.....1111...........666...............1",
    "1.....1111...1111......................1",
    "1.....1111...1111.......11111111.......1",
    "1............1111.......11111111.......1",
    "1.......................11111111.......1",
    "1..1111111.............................1",
    "1..1111111.........111111111...........1",
    "1..................111111111...........1",
    "1111111111111111111111111111111111111111",
]
# normalize row lengths
MAP_W = max(len(r) for r in MAP)
MAP = [r.ljust(MAP_W, "1") for r in MAP]
MAP_H = len(MAP)

WALL_COLORS = {
    "1": (150, 150, 160),
    "2": (200, 70, 70),
    "3": (70, 130, 200),
    "4": (70, 200, 110),
    "5": (200, 190, 70),
    "6": (170, 90, 200),
}

FLOOR_COLOR = (40, 40, 46)


# --------------------------------------------------------------------------- #
# ENEMIES
# --------------------------------------------------------------------------- #

class Enemy:
    def __init__(self, x, y, max_hp=ENEMY_MAX_HP, contact_damage=ENEMY_CONTACT_DAMAGE,
                 speed=ENEMY_SPEED, radius=ENEMY_RADIUS, height_scale=ENEMY_HEIGHT_SCALE,
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
        self.hit_flash = 0.0  # seconds remaining of white "just hit" flash

    def update(self, dt, player):
        if not self.alive:
            return
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy)
        if dist <= ENEMY_STOP_DIST or dist < 1e-4:
            return

        dx /= dist
        dy /= dist
        step_x = dx * self.speed * dt
        step_y = dy * self.speed * dt

        # simple axis-separated collision so enemies slide along walls too
        if not is_wall(self.x + step_x, self.y):
            self.x += step_x
        if not is_wall(self.x, self.y + step_y):
            self.y += step_y


def spawn_enemies():
    # a handful of fixed positions on open ('.') floor tiles
    candidates = [(4.5, 3.5), (13.5, 3.5), (10.5, 7.5), (6.5, 11.5), (12.5, 11.5)]
    enemies = []
    for x, y in candidates:
        if not is_wall(x, y):
            enemies.append(Enemy(x, y))
    return enemies


OPEN_TILES = [(x + 0.5, y + 0.5) for y in range(MAP_H) for x in range(MAP_W) if MAP[y][x] == "."]


def spawn_random_enemy(player, min_dist=ENEMY_SPAWN_MIN_DIST, attempts=30):
    """Picks a random open floor tile, preferring ones away from the player."""
    for _ in range(attempts):
        x, y = random.choice(OPEN_TILES)
        if math.hypot(x - player.x, y - player.y) >= min_dist:
            return Enemy(x, y)
    x, y = random.choice(OPEN_TILES)  # fallback if the level is small/crowded
    return Enemy(x, y)


def spawn_boss(player, min_dist=BOSS_SPAWN_MIN_DIST, attempts=30):
    """Spawns The Revenant on an open tile, well away from the player for drama."""
    for _ in range(attempts):
        x, y = random.choice(OPEN_TILES)
        if math.hypot(x - player.x, y - player.y) >= min_dist:
            break
    else:
        x, y = random.choice(OPEN_TILES)
    return Enemy(
        x, y,
        max_hp=BOSS_MAX_HP,
        contact_damage=BOSS_CONTACT_DAMAGE,
        speed=BOSS_SPEED,
        radius=BOSS_RADIUS,
        height_scale=BOSS_HEIGHT_SCALE,
        is_boss=True,
        name=BOSS_NAME,
    )


# --------------------------------------------------------------------------- #
# PROCEDURAL STONE TEXTURE
# --------------------------------------------------------------------------- #

def generate_stone_texture(size=TEX_SIZE, seed=1337):
    """Builds a tileable-ish grayscale stone-block texture, no image files needed."""
    rng = __import__("random").Random(seed)
    tex = pygame.Surface((size, size))

    base = 175
    for y in range(size):
        for x in range(size):
            n = rng.randint(-22, 22)
            v = max(0, min(255, base + n))
            tex.set_at((x, y), (v, v, v))

    # carve a brick/stone-block grid: darker mortar lines, slight bevel highlight
    block_w, block_h = size // 4, size // 4
    mortar = (60, 60, 60)
    highlight = (170, 170, 170)
    for by in range(0, size, block_h):
        row_offset = (block_w // 2) if (by // block_h) % 2 else 0
        for bx in range(-block_w, size + block_w, block_w):
            x0 = bx + row_offset
            # mortar border around each block
            pygame.draw.rect(tex, mortar, (x0, by, block_w, block_h), width=2)
            # a soft highlight on the top-left inner edge for a beveled look
            pygame.draw.line(tex, highlight, (x0 + 2, by + 2), (x0 + block_w - 3, by + 2))
            pygame.draw.line(tex, highlight, (x0 + 2, by + 2), (x0 + 2, by + block_h - 3))

    # scatter a few darker "cracks" / pits for grit
    for _ in range(size * 2):
        x, y = rng.randrange(size), rng.randrange(size)
        c = tex.get_at((x, y))
        d = max(0, c.r - rng.randint(10, 40))
        tex.set_at((x, y), (d, d, d))

    return tex


def build_wall_textures():
    """Returns {wall_id: (lit_surface, shaded_surface)} tinted per wall color."""
    stone = generate_stone_texture()
    textures = {}
    for wall_id, color in WALL_COLORS.items():
        lit = stone.copy()
        lit.fill(color, special_flags=pygame.BLEND_RGB_MULT)

        shaded = lit.copy()
        dark = tuple(int(c * SIDE_SHADE) for c in (255, 255, 255))
        shaded.fill(dark, special_flags=pygame.BLEND_RGB_MULT)

        textures[wall_id] = (lit, shaded)
    return textures


# --------------------------------------------------------------------------- #
# PROCEDURAL SKYBOX (night sky + glowing moon)
# --------------------------------------------------------------------------- #

def generate_sky_texture(width=SKY_WIDTH, height=SKY_HEIGHT, seed=99):
    """A horizontally-wrapping night sky strip: gradient, stars, and a glowing moon.
    Sampled by yaw angle so it pans as you turn but stays fixed in the world."""
    rng = __import__("random").Random(seed)
    sky = pygame.Surface((width, height))

    # vertical gradient: deep space near the top, a faint indigo glow near the horizon
    top_color = (6, 8, 22)
    horizon_color = (28, 24, 48)
    for y in range(height):
        t = y / max(1, height - 1)
        color = tuple(int(top_color[i] + (horizon_color[i] - top_color[i]) * t) for i in range(3))
        pygame.draw.line(sky, color, (0, y), (width, y))

    # scattered stars, denser and brighter near the top
    star_count = int(width * height * 0.03)
    for _ in range(star_count):
        x = rng.randrange(width)
        y = rng.randrange(height)
        if rng.random() < (1.0 - y / height) * 0.5 + 0.15:
            b = rng.choice([110, 140, 170, 210, 255])
            color = (b, b, min(255, b + 20))
            sky.set_at((x, y), color)
            if rng.random() < 0.08:  # occasional slightly bigger twinkling star
                pygame.draw.rect(sky, color, (x, y, 2, 2))

    # a soft wispy cloud band or two (subtle, low alpha, doesn't hide stars much)
    cloud_layer = pygame.Surface((width, height), pygame.SRCALPHA)
    for _ in range(6):
        cx = rng.randrange(width)
        cy = rng.randrange(int(height * 0.2), int(height * 0.85))
        cw = rng.randrange(width // 8, width // 4)
        ch = rng.randrange(4, 10)
        pygame.draw.ellipse(cloud_layer, (60, 60, 80, 26), (cx, cy, cw, ch))
    sky.blit(cloud_layer, (0, 0))

    # glowing moon: soft additive halo layers behind a bright disc + a couple craters
    moon_x, moon_y = int(width * 0.22), int(height * 0.30)
    moon_r = max(4, height // 9)
    glow_color = (200, 215, 255)
    for radius, alpha in ((moon_r * 3.2, 18), (moon_r * 2.2, 35), (moon_r * 1.5, 65)):
        glow = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*glow_color, alpha), (moon_x, moon_y), int(radius))
        sky.blit(glow, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

    moon_color = (238, 236, 218)
    pygame.draw.circle(sky, moon_color, (moon_x, moon_y), moon_r)
    crater_color = tuple(max(0, c - 28) for c in moon_color)
    pygame.draw.circle(sky, crater_color, (moon_x - moon_r // 3, moon_y - moon_r // 4), max(1, moon_r // 5))
    pygame.draw.circle(sky, crater_color, (moon_x + moon_r // 4, moon_y + moon_r // 3), max(1, moon_r // 6))
    pygame.draw.circle(sky, crater_color, (moon_x + moon_r // 6, moon_y - moon_r // 3), max(1, moon_r // 7))

    return sky


# --------------------------------------------------------------------------- #
# PROCEDURAL SPRITES (enemy + gun viewmodel)
# --------------------------------------------------------------------------- #

def generate_enemy_sprite():
    """A small blocky ghoul billboard sprite, transparent background."""
    w, h = 16, 26
    img = pygame.Surface((w, h), pygame.SRCALPHA)

    body_color = (70, 40, 90)
    body_dark = (45, 25, 60)
    eye_color = (255, 60, 40)

    # robed/hunched body silhouette (tapered torso)
    pygame.draw.polygon(img, body_color, [
        (3, 25), (2, 14), (4, 8), (12, 8), (14, 14), (13, 25)
    ])
    # head
    pygame.draw.ellipse(img, body_color, (4, 2, 8, 8))
    # shading on one side for a bit of volume
    pygame.draw.polygon(img, body_dark, [(9, 8), (12, 8), (14, 14), (13, 25), (9, 25)])
    # glowing eyes
    pygame.draw.rect(img, eye_color, (5, 5, 2, 2))
    pygame.draw.rect(img, eye_color, (9, 5, 2, 2))
    # skinny arms
    pygame.draw.line(img, body_dark, (3, 15), (0, 21), 2)
    pygame.draw.line(img, body_dark, (13, 15), (16, 21), 2)

    return img


def generate_boss_sprite():
    """The Revenant: a larger, broader-shouldered, horned silhouette in
    blood-red and black, with a wider glowing gaze than a regular enemy."""
    w, h = 22, 30
    img = pygame.Surface((w, h), pygame.SRCALPHA)

    body_color = (110, 20, 20)
    body_dark = (60, 10, 10)
    robe_color = (25, 10, 12)
    eye_color = (255, 150, 30)

    # broad hooded robe silhouette
    pygame.draw.polygon(img, robe_color, [
        (2, 29), (1, 16), (4, 9), (18, 9), (21, 16), (20, 29)
    ])
    # chest/torso highlight
    pygame.draw.polygon(img, body_color, [
        (6, 29), (5, 16), (7, 11), (15, 11), (17, 16), (16, 29)
    ])
    # shading on one side for volume
    pygame.draw.polygon(img, body_dark, [(11, 11), (15, 11), (17, 16), (16, 29), (11, 29)])
    # head
    pygame.draw.ellipse(img, body_color, (6, 2, 10, 9))
    # horns
    pygame.draw.polygon(img, (30, 30, 30), [(6, 5), (2, 0), (7, 3)])
    pygame.draw.polygon(img, (30, 30, 30), [(16, 5), (20, 0), (15, 3)])
    # wide glowing eyes
    pygame.draw.rect(img, eye_color, (7, 6, 3, 2))
    pygame.draw.rect(img, eye_color, (12, 6, 3, 2))
    # heavy arms
    pygame.draw.line(img, body_dark, (4, 17), (0, 25), 3)
    pygame.draw.line(img, body_dark, (18, 17), (22, 25), 3)

    return img


def generate_gun_sprite():
    """A small pixel-art pistol viewmodel, transparent background."""
    w, h = 40, 34
    img = pygame.Surface((w, h), pygame.SRCALPHA)

    metal = (70, 72, 80)
    metal_dark = (40, 42, 48)
    grip = (60, 42, 30)
    grip_dark = (40, 28, 20)
    sight = (200, 200, 210)

    # slide / barrel
    pygame.draw.rect(img, metal, (10, 4, 22, 8))
    pygame.draw.rect(img, metal_dark, (10, 4, 22, 8), width=1)
    pygame.draw.rect(img, sight, (28, 2, 3, 3))
    # frame beneath the slide
    pygame.draw.rect(img, metal_dark, (12, 12, 16, 5))
    # trigger guard
    pygame.draw.arc(img, metal_dark, (14, 14, 10, 10), 3.4, 6.2, 2)
    # grip (angled down-right, held from bottom of screen)
    pygame.draw.polygon(img, grip, [(16, 16), (26, 16), (30, 33), (18, 33)])
    pygame.draw.polygon(img, grip_dark, [(24, 16), (26, 16), (30, 33), (26, 33)])
    # hammer
    pygame.draw.rect(img, metal_dark, (8, 6, 3, 5))

    return img


def tile_at(x, y):
    ix, iy = int(x), int(y)
    if 0 <= iy < MAP_H and 0 <= ix < MAP_W:
        ch = MAP[iy][ix]
        return ch if ch != "." else None
    return "1"


def is_wall(x, y):
    return tile_at(x, y) is not None


# --------------------------------------------------------------------------- #
# PLAYER
# --------------------------------------------------------------------------- #

class Player:
    def __init__(self, x, y, angle):
        self.x = x
        self.y = y
        self.angle = angle
        self.radius = 0.2
        self.hp = PLAYER_MAX_HP
        self.invuln_timer = 0.0
        self.damage_flash = 0.0

    def take_damage(self, amount):
        if self.invuln_timer > 0:
            return False
        self.hp = max(0, self.hp - amount)
        self.invuln_timer = PLAYER_HIT_COOLDOWN
        self.damage_flash = PLAYER_DAMAGE_FLASH_DURATION
        return True

    def try_move(self, dx, dy):
        # simple axis-separated collision so you can slide along walls
        if not is_wall(self.x + dx, self.y):
            self.x += dx
        if not is_wall(self.x, self.y + dy):
            self.y += dy

    def update(self, dt, keys, mouse_dx):
        self.angle += mouse_dx * MOUSE_SENS

        if keys[pygame.K_LEFT]:
            self.angle -= ROT_SPEED * dt
        if keys[pygame.K_RIGHT]:
            self.angle += ROT_SPEED * dt

        speed = MOVE_SPEED
        if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
            speed *= RUN_MULT

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


# --------------------------------------------------------------------------- #
# RAYCASTING (DDA algorithm)
# --------------------------------------------------------------------------- #

def cast_ray(px, py, angle):
    """Returns (distance, wall_id, side, wall_x) using a DDA grid march.

    wall_x is the fractional (0..1) position along the hit wall face,
    used as the horizontal texture coordinate.
    """
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
    for _ in range(256):
        if side_dist_x < side_dist_y:
            side_dist_x += delta_dist_x
            map_x += step_x
            side = 0
        else:
            side_dist_y += delta_dist_y
            map_y += step_y
            side = 1

        if 0 <= map_y < MAP_H and 0 <= map_x < MAP_W:
            ch = MAP[map_y][map_x]
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


def render_scene(surface, player, textures, sky_tex, zbuffer):
    surface.fill(FLOOR_COLOR, (0, RENDER_H // 2, RENDER_W, RENDER_H // 2))

    start_angle = player.angle - HALF_FOV
    sky_w = sky_tex.get_width()
    two_pi = 2 * math.pi

    for col in range(NUM_RAYS):
        ray_angle = start_angle + col * STEP_ANGLE

        # skybox: sample by absolute yaw so it wraps around the world, not the screen
        normalized = ray_angle % two_pi
        sx = int((normalized / two_pi) * sky_w) % sky_w
        sky_col = sky_tex.subsurface((sx, 0, 1, SKY_HEIGHT))
        sky_col = pygame.transform.scale(sky_col, (1, RENDER_H // 2))
        surface.blit(sky_col, (col, 0))

        dist, wall_id, side, wall_x = cast_ray(player.x, player.y, ray_angle)

        # fix fish-eye distortion
        dist *= math.cos(ray_angle - player.angle)
        dist = max(dist, 0.0001)
        zbuffer[col] = dist

        wall_h = int((RENDER_H / dist) * WALL_HEIGHT_SCALE)
        wall_h = min(wall_h, RENDER_H * 4)

        y0 = max(0, RENDER_H // 2 - wall_h // 2)
        y1 = min(RENDER_H, RENDER_H // 2 + wall_h // 2)
        draw_h = max(1, y1 - y0)

        lit_tex, shaded_tex = textures.get(wall_id, textures["1"])
        tex = shaded_tex if side == 1 else lit_tex

        tex_x = min(TEX_SIZE - 1, int(wall_x * TEX_SIZE))
        column = tex.subsurface((tex_x, 0, 1, TEX_SIZE))
        column = pygame.transform.scale(column, (1, draw_h))

        # distance fog: darken the sampled strip based on depth
        shade = max(0.25, 1.0 - dist / MAX_DEPTH)
        fog = int(255 * shade)
        column.fill((fog, fog, fog), special_flags=pygame.BLEND_RGB_MULT)

        surface.blit(column, (col, y0))


def render_enemies(surface, player, enemies, zbuffer, sprite_img, boss_sprite_img):
    """Billboard sprite rendering: enemies always face the camera, sorted
    back-to-front, and occluded per-column against the wall z-buffer."""
    visible = []
    for e in enemies:
        if not e.alive and e.hit_flash <= 0:
            continue  # fully gone, no longer rendered
        dx = e.x - player.x
        dy = e.y - player.y
        dist = math.hypot(dx, dy)
        if dist < 1e-4:
            continue
        angle_to = math.atan2(dy, dx)
        rel = (angle_to - player.angle + math.pi) % (2 * math.pi) - math.pi
        if abs(rel) > HALF_FOV + 0.4:
            continue  # well outside the view frustum, skip
        visible.append((dist, rel, e))

    visible.sort(key=lambda t: -t[0])  # farthest first (painter's algorithm)

    for dist, rel, e in visible:
        perp_dist = dist * math.cos(rel)
        if perp_dist < 0.1:
            continue

        img = boss_sprite_img if e.is_boss else sprite_img
        unit_h = (RENDER_H / perp_dist) * WALL_HEIGHT_SCALE  # height of one full tile
        sprite_h = unit_h * e.height_scale
        aspect = img.get_width() / img.get_height()
        sprite_w = sprite_h * aspect

        screen_x_center = ((rel + HALF_FOV) / FOV) * RENDER_W
        x0 = screen_x_center - sprite_w / 2
        y_bottom = RENDER_H / 2 + unit_h / 2
        y_top = y_bottom - sprite_h

        sw = max(1, int(sprite_w))
        sh = max(1, int(sprite_h))
        scaled_sprite = pygame.transform.scale(img, (sw, sh))

        # tint: white hit-flash overrides normal distance fog
        if e.hit_flash > 0:
            tint = (255, 255, 255)
        else:
            shade = max(0.35, 1.0 - perp_dist / MAX_DEPTH)
            g = int(255 * shade)
            tint = (g, g, g)
        tinted = scaled_sprite.copy()
        tinted.fill(tint, special_flags=pygame.BLEND_RGB_MULT)

        any_visible = False
        for i in range(sw):
            col = int(x0) + i
            if 0 <= col < RENDER_W and perp_dist < zbuffer[col]:
                strip = tinted.subsurface((i, 0, 1, sh))
                surface.blit(strip, (col, int(y_top)))
                any_visible = True

        # regular enemies get a small floating bar; the boss uses a HUD bar instead
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


def draw_weapon(surface, gun_img, gun_state, dt):
    """Fires a muzzle flash on shooting; the gun body itself is invisible."""
    if gun_state["recoil_timer"] > 0:
        gun_state["recoil_timer"] = max(0.0, gun_state["recoil_timer"] - dt)
    if gun_state["flash_timer"] > 0:
        gun_state["flash_timer"] = max(0.0, gun_state["flash_timer"] - dt)

    if gun_state["flash_timer"] > 0:
        flash_x = RENDER_W // 2
        flash_y = RENDER_H - 40
        pygame.draw.circle(surface, (255, 235, 160), (flash_x, flash_y), 9)
        pygame.draw.circle(surface, (255, 255, 255), (flash_x, flash_y), 4)


def draw_crosshair(surface):
    cx, cy = RENDER_W // 2, RENDER_H // 2
    color = (230, 230, 230)
    pygame.draw.line(surface, color, (cx - 6, cy), (cx - 2, cy))
    pygame.draw.line(surface, color, (cx + 2, cy), (cx + 6, cy))
    pygame.draw.line(surface, color, (cx, cy - 6), (cx, cy - 2))
    pygame.draw.line(surface, color, (cx, cy + 2), (cx, cy + 6))


def hitscan(player, enemies):
    """Fires a single ray straight down the player's view direction. If it
    lines up with an alive enemy (within the enemy's hit radius) before
    hitting a wall, that enemy dies. Returns the enemy killed, or None."""
    wall_dist, _, _, _ = cast_ray(player.x, player.y, player.angle)

    best_enemy = None
    best_dist = None
    for e in enemies:
        if not e.alive:
            continue
        dx = e.x - player.x
        dy = e.y - player.y
        dist = math.hypot(dx, dy)
        if dist < 1e-4 or dist >= wall_dist:
            continue  # blocked by (or beyond) a wall

        angle_to = math.atan2(dy, dx)
        rel = (angle_to - player.angle + math.pi) % (2 * math.pi) - math.pi
        half_width_angle = math.atan2(e.radius, dist)

        if abs(rel) <= half_width_angle:
            if best_dist is None or dist < best_dist:
                best_dist = dist
                best_enemy = e

    if best_enemy is not None:
        best_enemy.hp = max(0, best_enemy.hp - GUN_DAMAGE)
        best_enemy.hit_flash = HIT_FLASH_DURATION
        if best_enemy.hp <= 0:
            best_enemy.alive = False

    return best_enemy


def shoot(player, enemies, gun_state):
    gun_state["recoil_timer"] = RECOIL_DURATION
    gun_state["flash_timer"] = FLASH_DURATION
    return hitscan(player, enemies)


def render_minimap(screen, player, enemies, scale=6, ox=10, oy=10):
    for y in range(MAP_H):
        for x in range(MAP_W):
            ch = MAP[y][x]
            rect = pygame.Rect(ox + x * scale, oy + y * scale, scale, scale)
            if ch == ".":
                pygame.draw.rect(screen, (25, 25, 30), rect)
            else:
                pygame.draw.rect(screen, WALL_COLORS.get(ch, (255, 0, 255)), rect)

    for e in enemies:
        if e.alive:
            ex = ox + int(e.x * scale)
            ey = oy + int(e.y * scale)
            pygame.draw.circle(screen, (255, 60, 40), (ex, ey), max(2, scale // 3))

    px = ox + int(player.x * scale)
    py = oy + int(player.y * scale)
    pygame.draw.circle(screen, (255, 255, 0), (px, py), max(2, scale // 3))
    end_x = px + math.cos(player.angle) * scale
    end_y = py + math.sin(player.angle) * scale
    pygame.draw.line(screen, (255, 255, 0), (px, py), (end_x, end_y), 2)


def draw_player_hp_bar(screen, player, font):
    """Player health bar, fixed in the top-right corner of the actual window."""
    bar_w, bar_h = 220, 22
    margin = 14
    x = WINDOW_W - bar_w - margin
    y = margin

    hp_frac = max(0.0, min(1.0, player.hp / PLAYER_MAX_HP))
    fill_color = (60, 200, 70) if hp_frac > 0.3 else (210, 60, 50)

    pygame.draw.rect(screen, (20, 20, 20), (x, y, bar_w, bar_h))
    pygame.draw.rect(screen, fill_color, (x, y, int(bar_w * hp_frac), bar_h))
    pygame.draw.rect(screen, (230, 230, 230), (x, y, bar_w, bar_h), width=2)

    label = font.render(f"HP {player.hp}/{PLAYER_MAX_HP}", True, (255, 255, 255))
    label_rect = label.get_rect(center=(x + bar_w // 2, y + bar_h // 2))
    screen.blit(label, label_rect)


def draw_boss_hp_bar(screen, boss, font):
    """The Revenant's health bar: a wide bar with its name, fixed top-center."""
    bar_w, bar_h = 480, 26
    margin_top = 14
    x = WINDOW_W // 2 - bar_w // 2
    y = margin_top

    hp_frac = max(0.0, min(1.0, boss.hp / boss.max_hp))

    name_label = font.render(boss.name, True, (255, 140, 60))
    name_rect = name_label.get_rect(center=(WINDOW_W // 2, y - 12))
    screen.blit(name_label, name_rect)

    pygame.draw.rect(screen, (20, 20, 20), (x, y, bar_w, bar_h))
    pygame.draw.rect(screen, (170, 30, 30), (x, y, int(bar_w * hp_frac), bar_h))
    pygame.draw.rect(screen, (230, 230, 230), (x, y, bar_w, bar_h), width=2)

    hp_label = font.render(f"{boss.hp}/{boss.max_hp}", True, (255, 255, 255))
    hp_rect = hp_label.get_rect(center=(x + bar_w // 2, y + bar_h // 2))
    screen.blit(hp_label, hp_rect)


def draw_damage_flash(screen, flash_overlay, player):
    if player.damage_flash <= 0:
        return
    alpha = int(140 * (player.damage_flash / PLAYER_DAMAGE_FLASH_DURATION))
    flash_overlay.set_alpha(max(0, min(255, alpha)))
    screen.blit(flash_overlay, (0, 0))


def get_respawn_button_rect():
    btn_w, btn_h = 240, 60
    x = WINDOW_W // 2 - btn_w // 2
    y = WINDOW_H // 2 + 40
    return pygame.Rect(x, y, btn_w, btn_h)


def draw_end_screen(screen, big_font, font, won):
    overlay = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
    overlay.fill((0, 10, 0, 190) if won else (10, 0, 0, 190))
    screen.blit(overlay, (0, 0))

    if won:
        title = big_font.render("YOU WIN", True, (240, 200, 60))
        subtitle = font.render(f"{BOSS_NAME} has fallen.", True, (220, 220, 220))
    else:
        title = big_font.render("GAME OVER", True, (220, 40, 40))
        subtitle = None

    title_rect = title.get_rect(center=(WINDOW_W // 2, WINDOW_H // 2 - 40))
    screen.blit(title, title_rect)
    if subtitle is not None:
        sub_rect = subtitle.get_rect(center=(WINDOW_W // 2, WINDOW_H // 2))
        screen.blit(subtitle, sub_rect)

    btn_rect = get_respawn_button_rect()
    mouse_pos = pygame.mouse.get_pos()
    hovered = btn_rect.collidepoint(mouse_pos)
    btn_color = (90, 160, 90) if hovered else (70, 70, 70)
    pygame.draw.rect(screen, btn_color, btn_rect, border_radius=6)
    pygame.draw.rect(screen, (230, 230, 230), btn_rect, width=2, border_radius=6)

    label = font.render("PLAY AGAIN" if won else "RESPAWN", True, (255, 255, 255))
    label_rect = label.get_rect(center=btn_rect.center)
    screen.blit(label, label_rect)



# --------------------------------------------------------------------------- #
# MAIN LOOP
# --------------------------------------------------------------------------- #

def find_spawn():
    for y in range(MAP_H):
        for x in range(MAP_W):
            if MAP[y][x] == ".":
                return x + 0.5, y + 0.5
    return 1.5, 1.5


def main():
    pygame.init()
    pygame.display.set_caption("Retro Raycaster")
    flags = pygame.DOUBLEBUF
    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H), flags)
    render_surface = pygame.Surface((RENDER_W, RENDER_H))
    clock = pygame.time.Clock()

    font = pygame.font.SysFont("couriernew", 16, bold=True)
    big_font = pygame.font.SysFont("couriernew", 48, bold=True)
    textures = build_wall_textures()
    sky_tex = generate_sky_texture()
    enemy_sprite = generate_enemy_sprite()
    boss_sprite = generate_boss_sprite()
    gun_sprite = generate_gun_sprite()
    zbuffer = [MAX_DEPTH] * NUM_RAYS
    flash_overlay = pygame.Surface((WINDOW_W, WINDOW_H))
    flash_overlay.fill((200, 20, 20))

    spawn_x, spawn_y = find_spawn()
    player = Player(spawn_x, spawn_y, angle=0.0)
    enemies = spawn_enemies()
    boss = None
    gun_state = {"recoil_timer": 0.0, "flash_timer": 0.0}
    game_state = "playing"  # "playing" | "game_over" | "won"
    spawn_timer = 0.0
    kill_count = 0
    spawn_interval = ENEMY_SPAWN_INTERVAL

    show_minimap = True
    fullscreen = False
    mouse_captured = True
    pygame.mouse.set_visible(False)
    pygame.event.set_grab(True)

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        mouse_dx = 0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEMOTION and mouse_captured:
                mouse_dx = event.rel[0]
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_m:
                    show_minimap = not show_minimap
                elif event.key == pygame.K_f:
                    fullscreen = not fullscreen
                    if fullscreen:
                        screen = pygame.display.set_mode((WINDOW_W, WINDOW_H), flags | pygame.FULLSCREEN)
                    else:
                        screen = pygame.display.set_mode((WINDOW_W, WINDOW_H), flags)
                elif event.key == pygame.K_TAB:
                    mouse_captured = not mouse_captured
                    pygame.mouse.set_visible(not mouse_captured)
                    pygame.event.set_grab(mouse_captured)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # left click
                    if game_state == "playing":
                        hit_enemy = shoot(player, enemies, gun_state)
                        if hit_enemy is not None and not hit_enemy.alive:
                            if hit_enemy.is_boss:
                                game_state = "won"
                                mouse_captured = False
                                pygame.mouse.set_visible(True)
                                pygame.event.set_grab(False)
                            else:
                                kill_count += 1
                                if kill_count % KILLS_PER_SPEEDUP == 0:
                                    spawn_interval = max(
                                        ENEMY_SPAWN_MIN_INTERVAL,
                                        spawn_interval - SPAWN_INTERVAL_STEP,
                                    )
                                if kill_count >= KILLS_TO_BOSS and boss is None:
                                    boss = spawn_boss(player)
                                    enemies.append(boss)
                    elif game_state in ("game_over", "won"):
                        if get_respawn_button_rect().collidepoint(event.pos):
                            spawn_x, spawn_y = find_spawn()
                            player.x, player.y, player.angle = spawn_x, spawn_y, 0.0
                            player.hp = PLAYER_MAX_HP
                            player.invuln_timer = 0.0
                            player.damage_flash = 0.0
                            enemies = spawn_enemies()
                            boss = None
                            game_state = "playing"
                            spawn_timer = 0.0
                            kill_count = 0
                            spawn_interval = ENEMY_SPAWN_INTERVAL
                            mouse_captured = True
                            pygame.mouse.set_visible(False)
                            pygame.event.set_grab(True)

        keys = pygame.key.get_pressed()

        if game_state == "playing":
            player.update(dt, keys, mouse_dx)

            if player.invuln_timer > 0:
                player.invuln_timer = max(0.0, player.invuln_timer - dt)
            if player.damage_flash > 0:
                player.damage_flash = max(0.0, player.damage_flash - dt)

            for e in enemies:
                if e.hit_flash > 0:
                    e.hit_flash = max(0.0, e.hit_flash - dt)
                e.update(dt, player)

                if e.alive:
                    dist = math.hypot(e.x - player.x, e.y - player.y)
                    if dist < ENEMY_CONTACT_RANGE:
                        player.take_damage(e.contact_damage)

            if player.hp <= 0:
                game_state = "game_over"
                mouse_captured = False
                pygame.mouse.set_visible(True)
                pygame.event.set_grab(False)

            # regular spawning halts for good once the boss threshold is reached
            if kill_count < KILLS_TO_BOSS:
                spawn_timer += dt
                if spawn_timer >= spawn_interval:
                    spawn_timer -= spawn_interval
                    enemies.append(spawn_random_enemy(player))

        render_scene(render_surface, player, textures, sky_tex, zbuffer)
        render_enemies(render_surface, player, enemies, zbuffer, enemy_sprite, boss_sprite)
        draw_weapon(render_surface, gun_sprite, gun_state, dt)
        draw_crosshair(render_surface)

        scaled = pygame.transform.scale(render_surface, (WINDOW_W, WINDOW_H))
        screen.blit(scaled, (0, 0))

        if show_minimap:
            render_minimap(screen, player, enemies)

        draw_player_hp_bar(screen, player, font)
        if boss is not None and boss.alive:
            draw_boss_hp_bar(screen, boss, font)
        draw_damage_flash(screen, flash_overlay, player)

        remaining = sum(1 for e in enemies if e.alive)
        if boss is not None:
            status = f"{BOSS_NAME} has appeared!" if boss.alive else f"{BOSS_NAME} defeated!"
        else:
            status = f"Spawn every {spawn_interval:.0f}s"
        hud_text = font.render(
            f"{clock.get_fps():.0f} FPS  |  Enemies left: {remaining}  |  Kills: {kill_count}  |  "
            f"{status}  |  "
            f"(Left-click: shoot  M: map  F: fullscreen  TAB: mouse  ESC: quit)",
            True, (255, 255, 0))
        screen.blit(hud_text, (10, WINDOW_H - 26))

        if game_state in ("game_over", "won"):
            draw_end_screen(screen, big_font, font, won=(game_state == "won"))

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()