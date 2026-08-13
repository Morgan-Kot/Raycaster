import math

WINDOW_W, WINDOW_H = 1024, 640
RENDER_W, RENDER_H = 320, 200           # Low-res pixel render buffer[cite: 1]
FOV = math.pi / 3.0                     # 60-degree FOV in radians[cite: 1]
HALF_FOV = FOV / 2.0
MAX_DEPTH = 20.0                        # Max raycast rendering distance[cite: 1]
NUM_RAYS = RENDER_W
STEP_ANGLE = FOV / NUM_RAYS             # Radians per ray column[cite: 1]

MOVE_SPEED = 3.2
RUN_MULT = 1.8
ROT_SPEED = 2.6
MOUSE_SENS = 0.0075
PITCH_SENS = 0.0012                     # Vertical look camera sensitivity[cite: 1]
MAX_PITCH = 80                          # Max vertical camera pitch shift in pixels[cite: 1]

WALL_HEIGHT_SCALE = 0.9                 # Projected wall scale factor[cite: 1]

TEX_SIZE = 64
SIDE_SHADE = 0.7                        # Darkening multiplier for N/S wall faces[cite: 1]

ENEMY_RADIUS = 0.35
ENEMY_HEIGHT_SCALE = 0.85
ENEMY_MAX_HP = 100
ENEMY_SPEED = 1.1
ENEMY_STOP_DIST = 0.6
ENEMY_SPAWN_INTERVAL = 15.0
ENEMY_SPAWN_MIN_DIST = 3.0
ENEMY_SPAWN_MIN_INTERVAL = 5.0
KILLS_PER_SPEEDUP = 5
SPAWN_INTERVAL_STEP = 5.0

GUN_DAMAGE = 25
BULLET_SPEED = 14.0                     # Flying bullet velocity in world units / sec[cite: 1]
FIRE_RATE_COOLDOWN = 0.30               # Delay required between shots in seconds[cite: 1]
RECOIL_DURATION = 0.15
FLASH_DURATION = 0.06
HIT_FLASH_DURATION = 0.15

PLAYER_MAX_HP = 100
ENEMY_CONTACT_DAMAGE = 15
ENEMY_CONTACT_RANGE = 0.65
PLAYER_HIT_COOLDOWN = 0.8               # Player invulnerability window after damage[cite: 1]
PLAYER_DAMAGE_FLASH_DURATION = 0.25

FOOTSTEP_INTERVAL = 0.4                 # Cadence delay between footstep audio ticks[cite: 1]
MONSTER_GRUNT_CHANCE = 0.003            # Random per-frame chance of monster grunt[cite: 1]

KILLS_TO_BOSS = 20
BOSS_NAME = "THE REVENANT"
BOSS_MAX_HP = 500
BOSS_CONTACT_DAMAGE = 25
BOSS_SPEED = 0.9
BOSS_RADIUS = 0.6
BOSS_HEIGHT_SCALE = 1.9
BOSS_SPAWN_MIN_DIST = 4.0

SFX_DIR = "assets/sfx"                  # Directory path for audio FX[cite: 1]
MUSIC_DIR = "assets/music"              # Directory path for music[cite: 1]
WEAPONS_DIR = "assets/weapons"          # Directory path for custom gun textures[cite: 1]
LEVELS_FILE = "level.json"              # JSON level database path[cite: 1]
SFX_VOLUME = 0.5                        # Default SFX volume level[cite: 1]
MUSIC_VOLUME = 0.3                      # Default Music volume level[cite: 1]

WALL_COLORS = {
    "1": (140, 140, 150),
    "2": (180, 60, 60),
    "3": (60, 110, 180),
    "4": (60, 180, 90),
    "5": (180, 170, 60),
    "6": (150, 80, 180),
    "7": (110, 110, 120),               # Stair / Elevated step color[cite: 1]
}

FLOOR_COLOR = (32, 32, 38)
CEILING_COLOR = (22, 22, 28)