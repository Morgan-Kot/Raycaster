import os
import random
import pygame
import config

class SoundManager:
    def __init__(self):
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        self.volume = config.SFX_VOLUME
        self.music_volume = config.MUSIC_VOLUME
        self.sfx = {}
        self.step_timer = 0.0
        self.load_all_sounds()
        self.start_music()

    def load_all_sounds(self):
        sound_files = {
            "gunshot": ["gunshot.wav", "gunshot.ogg", "gunshot.mp3"],
            "hitsound": ["hitsound.wav", "hitsound.ogg", "hitsound.mp3"],
            "boss_killed": ["boss_killed.wav", "win.wav", "win.ogg", "win.mp3"],
            "win": ["win.wav", "win.ogg", "win.mp3"],
            "lose": ["lose.wav", "lose.ogg", "lose.mp3"],
            "player_hit": ["player_hit.wav", "player_hit.ogg", "player_hit.mp3"],
            "footstep": ["footstep.wav", "footstep.ogg", "footstep.mp3"],
            "grunt": ["grunt.wav", "grunt.ogg", "grunt.mp3"]
        }
        for key, filenames in sound_files.items():
            self.sfx[key] = None
            for filename in filenames:
                path = os.path.join(config.SFX_DIR, filename)
                if os.path.exists(path):
                    try:
                        sound = pygame.mixer.Sound(path)
                        sound.set_volume(self.volume)
                        self.sfx[key] = sound
                        break
                    except Exception:
                        pass

    def start_music(self):
        if not os.path.exists(config.MUSIC_DIR):
            return
        for ext in [".mp3", ".ogg", ".wav"]:
            path = os.path.join(config.MUSIC_DIR, "ambient" + ext)
            if os.path.exists(path):
                try:
                    pygame.mixer.music.load(path)
                    pygame.mixer.music.set_volume(self.music_volume)
                    pygame.mixer.music.play(-1)
                    break
                except Exception:
                    pass

    def set_volume(self, vol):
        self.volume = max(0.0, min(1.0, vol))
        for sound in self.sfx.values():
            if sound:
                sound.set_volume(self.volume)

    def play(self, key):
        if self.sfx.get(key):
            self.sfx[key].play()

    def Gunshot(self):
        self.play("gunshot")

    def Enemy_Hit(self):
        self.play("hitsound")

    def Player_Hit(self):
        self.play("player_hit")

    def Boss_Killed(self):
        self.play("boss_killed")

    def Win(self):
        self.play("win")

    def Lose(self):
        self.play("lose")

    def Footstep(self, dt, is_moving):
        if not is_moving:
            self.step_timer = 0.0
            return
        self.step_timer += dt
        if self.step_timer >= config.FOOTSTEP_INTERVAL:
            self.step_timer -= config.FOOTSTEP_INTERVAL
            self.play("footstep")

    def Monster_Grunt(self):
        if random.random() < config.MONSTER_GRUNT_CHANCE:
            self.play("grunt")