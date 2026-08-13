import json
import os
import math
import sys
import pygame

import config
from sound import SoundManager
from engine import (
    Player,
    spawn_enemies,
    spawn_random_enemy,
    spawn_boss,
    build_wall_textures,
    generate_enemy_sprite,
    generate_boss_sprite,
    generate_gun_sprite,
    render_scene,
    render_enemies_and_bullets,
    draw_weapon,
    draw_crosshair,
    shoot,
    render_minimap,
    draw_player_hp_bar,
    draw_boss_hp_bar,
    draw_damage_flash,
    draw_tab_overlay,
    draw_main_menu,
    draw_settings_menu,
    get_respawn_button_rect,
    draw_end_screen,
)

def load_level_data(level_key="LEVEL_01"):
    default_map = [
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
        "1......7777777................1111.....1",
        "1......7777777.......11111.............1",
        "1......7777777.......11111...1111111...1",
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
        "1111111111111111111111111111111111111111"
    ]
    default_data = {
        "name": "Castle Dungeons",
        "map": default_map,
        "enemy_config": {
            "max_hp": config.ENEMY_MAX_HP,
            "speed": config.ENEMY_SPEED,
            "contact_damage": config.ENEMY_CONTACT_DAMAGE,
            "spawn_interval": config.ENEMY_SPAWN_INTERVAL,
            "spawn_min_dist": config.ENEMY_SPAWN_MIN_DIST
        },
        "boss_config": {
            "name": config.BOSS_NAME,
            "max_hp": config.BOSS_MAX_HP,
            "speed": config.BOSS_SPEED,
            "contact_damage": config.BOSS_CONTACT_DAMAGE,
            "radius": config.BOSS_RADIUS,
            "height_scale": config.BOSS_HEIGHT_SCALE,
            "spawn_min_dist": config.BOSS_SPAWN_MIN_DIST
        }
    }

    if os.path.exists(config.LEVELS_FILE):
        try:
            with open(config.LEVELS_FILE, "r") as f:
                data = json.load(f)
                if level_key in data:
                    lvl = data[level_key]
                    raw_map = lvl.get("map", default_map)
                    map_w = max(len(r) for r in raw_map)
                    norm_map = [r.ljust(map_w, "1") for r in raw_map]
                    return {
                        "name": lvl.get("name", "Castle Dungeon"),
                        "map": norm_map,
                        "enemy_config": lvl.get("enemy_config", default_data["enemy_config"]),
                        "boss_config": lvl.get("boss_config", default_data["boss_config"])
                    }
        except Exception:
            pass

    map_w = max(len(r) for r in default_map)
    default_data["map"] = [r.ljust(map_w, "1") for r in default_data["map"]]
    return default_data

def find_spawn(level_map):
    map_h = len(level_map)
    map_w = len(level_map[0])
    for y in range(map_h):
        for x in range(map_w):
            if level_map[y][x] == ".":
                return x + 0.5, y + 0.5
    return 1.5, 1.5

def get_render_mouse_pos():
    raw_x, raw_y = pygame.mouse.get_pos()
    rx = int(raw_x * (config.RENDER_W / config.WINDOW_W))
    ry = int(raw_y * (config.RENDER_H / config.WINDOW_H))
    return rx, ry

def main():
    pygame.init()
    pygame.display.set_caption("Retro Raycaster")
    flags = pygame.DOUBLEBUF
    screen = pygame.display.set_mode((config.WINDOW_W, config.WINDOW_H), flags)
    render_surface = pygame.Surface((config.RENDER_W, config.RENDER_H))
    clock = pygame.time.Clock()

    sounds = SoundManager()

    selected_level_key = "LEVEL_01"
    level_data = load_level_data(selected_level_key)
    level_map = level_data["map"]
    level_name = level_data["name"]
    e_cfg = level_data["enemy_config"]
    b_cfg = level_data["boss_config"]

    font = pygame.font.SysFont("couriernew", 8, bold=True)
    big_font = pygame.font.SysFont("couriernew", 18, bold=True)
    textures = build_wall_textures()
    enemy_sprite = generate_enemy_sprite()
    boss_sprite = generate_boss_sprite()
    gun_sprite = generate_gun_sprite()
    zbuffer = [config.MAX_DEPTH] * config.NUM_RAYS
    flash_overlay = pygame.Surface((config.RENDER_W, config.RENDER_H))
    flash_overlay.fill((200, 20, 20))

    spawn_x, spawn_y = find_spawn(level_map)
    player = Player(spawn_x, spawn_y, angle=0.0)
    enemies = spawn_enemies(level_map, e_cfg)
    bullets = []
    boss = None
    gun_state = {"recoil_timer": 0.0, "flash_timer": 0.0, "cooldown_timer": 0.0}
    game_state = "main_menu"
    spawn_timer = 0.0
    kill_count = 0
    spawn_interval = e_cfg.get("spawn_interval", config.ENEMY_SPAWN_INTERVAL)

    fullscreen = False
    mouse_captured = False

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        mouse_dx = 0
        mouse_dy = 0
        m_pos = get_render_mouse_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEMOTION and mouse_captured and game_state == "playing":
                mouse_dx = event.rel[0]
                mouse_dy = event.rel[1]

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if game_state == "playing":
                        game_state = "main_menu"
                        mouse_captured = False
                        pygame.mouse.set_visible(True)
                        pygame.event.set_grab(False)
                    elif game_state in ("main_menu", "settings"):
                        running = False
                elif game_state == "playing":
                    if event.key == pygame.K_f:
                        fullscreen = not fullscreen
                        if fullscreen:
                            screen = pygame.display.set_mode((config.WINDOW_W, config.WINDOW_H), flags | pygame.FULLSCREEN)
                        else:
                            screen = pygame.display.set_mode((config.WINDOW_W, config.WINDOW_H), flags)

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if game_state == "main_menu":
                    play_r, lvl_r, set_r, exit_r = draw_main_menu(render_surface, big_font, font, level_name, m_pos)
                    if play_r.collidepoint(m_pos):
                        level_data = load_level_data(selected_level_key)
                        level_map = level_data["map"]
                        level_name = level_data["name"]
                        e_cfg = level_data["enemy_config"]
                        b_cfg = level_data["boss_config"]
                        spawn_x, spawn_y = find_spawn(level_map)
                        player = Player(spawn_x, spawn_y, angle=0.0)
                        enemies = spawn_enemies(level_map, e_cfg)
                        bullets = []
                        boss = None
                        kill_count = 0
                        spawn_timer = 0.0
                        spawn_interval = e_cfg.get("spawn_interval", config.ENEMY_SPAWN_INTERVAL)
                        gun_state["cooldown_timer"] = 0.0
                        game_state = "playing"
                        mouse_captured = True
                        pygame.mouse.set_visible(False)
                        pygame.event.set_grab(True)
                    elif lvl_r.collidepoint(m_pos):
                        selected_level_key = "LEVEL_02" if selected_level_key == "LEVEL_01" else "LEVEL_01"
                        level_data = load_level_data(selected_level_key)
                        level_name = level_data["name"]
                    elif set_r.collidepoint(m_pos):
                        game_state = "settings"
                    elif exit_r.collidepoint(m_pos):
                        running = False

                elif game_state == "settings":
                    vd_r, vu_r, back_r = draw_settings_menu(render_surface, big_font, font, sounds, m_pos)
                    if vd_r.collidepoint(m_pos):
                        sounds.set_volume(sounds.volume - 0.1)
                    elif vu_r.collidepoint(m_pos):
                        sounds.set_volume(sounds.volume + 0.1)
                    elif back_r.collidepoint(m_pos):
                        game_state = "main_menu"

                elif game_state == "playing":
                    bullet = shoot(player, gun_state)
                    if bullet is not None:
                        bullets.append(bullet)
                        sounds.Gunshot()

                elif game_state in ("game_over", "won"):
                    if get_respawn_button_rect().collidepoint(m_pos):
                        level_data = load_level_data(selected_level_key)
                        level_map = level_data["map"]
                        level_name = level_data["name"]
                        e_cfg = level_data["enemy_config"]
                        b_cfg = level_data["boss_config"]
                        spawn_x, spawn_y = find_spawn(level_map)
                        player = Player(spawn_x, spawn_y, angle=0.0)
                        enemies = spawn_enemies(level_map, e_cfg)
                        bullets = []
                        boss = None
                        game_state = "playing"
                        spawn_timer = 0.0
                        kill_count = 0
                        spawn_interval = e_cfg.get("spawn_interval", config.ENEMY_SPAWN_INTERVAL)
                        gun_state["cooldown_timer"] = 0.0
                        mouse_captured = True
                        pygame.mouse.set_visible(False)
                        pygame.event.set_grab(True)

        keys = pygame.key.get_pressed()

        if game_state == "main_menu":
            draw_main_menu(render_surface, big_font, font, level_name, m_pos)

        elif game_state == "settings":
            draw_settings_menu(render_surface, big_font, font, sounds, m_pos)

        elif game_state == "playing":
            is_moving = player.update(dt, keys, mouse_dx, mouse_dy, level_map)
            sounds.Footstep(dt, is_moving)
            sounds.Monster_Grunt()

            if player.invuln_timer > 0:
                player.invuln_timer = max(0.0, player.invuln_timer - dt)
            if player.damage_flash > 0:
                player.damage_flash = max(0.0, player.damage_flash - dt)

            for b in bullets:
                hit_e = b.update(dt, level_map, enemies)
                if hit_e is not None:
                    sounds.Enemy_Hit()
                    if not hit_e.alive:
                        if hit_e.is_boss:
                            game_state = "won"
                            sounds.Boss_Killed()
                            sounds.Win()
                            mouse_captured = False
                            pygame.mouse.set_visible(True)
                            pygame.event.set_grab(False)
                        else:
                            kill_count += 1
                            if kill_count % config.KILLS_PER_SPEEDUP == 0:
                                spawn_interval = max(
                                    config.ENEMY_SPAWN_MIN_INTERVAL,
                                    spawn_interval - config.SPAWN_INTERVAL_STEP,
                                )
                            if kill_count >= config.KILLS_TO_BOSS and boss is None:
                                boss = spawn_boss(player, level_map, b_cfg)
                                enemies.append(boss)

            bullets = [b for b in bullets if b.alive]

            for e in enemies:
                if e.hit_flash > 0:
                    e.hit_flash = max(0.0, e.hit_flash - dt)
                e.update(dt, player, level_map)

                if e.alive:
                    dist = math.hypot(e.x - player.x, e.y - player.y)
                    if dist < config.ENEMY_CONTACT_RANGE:
                        took_damage = player.take_damage(e.contact_damage)
                        if took_damage:
                            sounds.Player_Hit()

            if player.hp <= 0:
                game_state = "game_over"
                sounds.Lose()
                mouse_captured = False
                pygame.mouse.set_visible(True)
                pygame.event.set_grab(False)

            if kill_count < config.KILLS_TO_BOSS:
                spawn_timer += dt
                if spawn_timer >= spawn_interval:
                    spawn_timer -= spawn_interval
                    enemies.append(spawn_random_enemy(player, level_map, e_cfg))

            render_scene(render_surface, player, textures, zbuffer, level_map)
            render_enemies_and_bullets(render_surface, player, enemies, bullets, zbuffer, enemy_sprite, boss_sprite)
            draw_weapon(render_surface, gun_sprite, gun_state, dt)
            draw_crosshair(render_surface)

            if keys[pygame.K_m]:
                render_minimap(render_surface, player, enemies, level_map)

            draw_player_hp_bar(render_surface, player, font)
            if boss is not None and boss.alive:
                draw_boss_hp_bar(render_surface, boss, font)
            draw_damage_flash(render_surface, flash_overlay, player)

            boss_name = b_cfg.get("name", config.BOSS_NAME)
            remaining = sum(1 for e in enemies if e.alive)
            if boss is not None:
                status = f"{boss_name} active!" if boss.alive else f"{boss_name} dead!"
            else:
                status = f"Spawn {spawn_interval:.0f}s"

            if keys[pygame.K_TAB]:
                draw_tab_overlay(render_surface, font, clock.get_fps(), remaining, kill_count, status, level_name)

        elif game_state in ("game_over", "won"):
            boss_name = b_cfg.get("name", config.BOSS_NAME)
            draw_end_screen(render_surface, big_font, font, won=(game_state == "won"), mouse_pos=m_pos, boss_name=boss_name)

        scaled = pygame.transform.scale(render_surface, (config.WINDOW_W, config.WINDOW_H))
        screen.blit(scaled, (0, 0))

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()