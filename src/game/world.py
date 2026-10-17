"""Game world simulation: orchestrates players, arena, spawner, projectiles, effects, and camera."""

from __future__ import annotations
import math
from typing import TYPE_CHECKING
import pygame

from src.game.boss import FinalBoss
from src.game.camera import Camera
from src.game.effects import EffectManager
from src.game.items import Item, ItemSpawner
from src.game.platforms import create_arena, platform_rects, Platform
from src.game.player import Player
from src.game.projectiles import ProjectileManager

if TYPE_CHECKING:
    from src.game.assets import AssetManager
    from src.game.settings import GameConfig


class World:
    """Orchestrates all game entities, physics simulation, collisions, and world rendering."""

    def __init__(self, config: GameConfig, assets: AssetManager) -> None:
        self.config: GameConfig = config
        self.assets: AssetManager = assets

        # Arena world bounds (spacious arena for cinematic panning)
        self.world_bounds: pygame.Rect = pygame.Rect(0, 0, 1600, 860)

        self.camera: Camera = Camera(config.screen_size, self.world_bounds)
        self.effects: EffectManager = EffectManager()
        self.projectile_manager: ProjectileManager = ProjectileManager()
        self.platforms: list[Platform] = create_arena(self.world_bounds)
        self.spawner: ItemSpawner = ItemSpawner(config)
        self.items: list[Item] = []
        self.boss: FinalBoss | None = None

        self.players: list[Player] = []
        self.left_player: Player
        self.right_player: Player

        self.reset()

    def spawn_boss(self, spawn_pos: tuple[float, float] | None = None) -> FinalBoss:
        """Spawn the 3x mutated Final Boss Titan."""
        if spawn_pos is None:
            floor_y = float(self.world_bounds.bottom - 90)
            spawn_pos = (float(self.world_bounds.centerx), floor_y)
        boss = FinalBoss(spawn=spawn_pos)
        self.boss = boss
        # Dramatic entrance screen shake & ground explosion
        self.effects.request_shake(intensity=14.0, duration=0.6)
        self.effects.explosion((spawn_pos[0], spawn_pos[1] - 80), radius=100.0, palette=[(255, 50, 60), (255, 200, 60), (40, 20, 20)])
        return boss

    def reset(self) -> None:
        """Reset match state, spawn fresh players, and initiate cinematic intro camera."""
        self.effects.clear()
        self.projectile_manager = ProjectileManager()
        self.items.clear()
        self.boss = None
        self.platforms = create_arena(self.world_bounds)
        self.spawner = ItemSpawner(self.config)

        # Spawn Left player (Player 1) on arena ground
        floor_y = float(self.world_bounds.bottom - 90)
        spawn_left = (240.0, floor_y)
        p1 = Player(
            player_id=1,
            spawn=spawn_left,
            controls=self.config.controls.left,
            assets=self.assets,
            config=self.config,
        )
        p1.on_ground = True

        # Spawn Right player (Player 2) on arena ground
        spawn_right = (float(self.world_bounds.right - 240), floor_y)
        p2 = Player(
            player_id=2,
            spawn=spawn_right,
            controls=self.config.controls.right,
            assets=self.assets,
            config=self.config,
        )
        p2.on_ground = True

        self.players = [p1, p2]
        self.left_player = p1
        self.right_player = p2

        # Start non-blocking intro pan sequence
        self.camera.start_intro(p1.center(), p2.center())

    def handle_event(self, event: pygame.event.Event) -> None:
        """Route input events to players."""
        for p in self.players:
            p.handle_event(event)

    def update(self, dt: float) -> None:
        """Advance world simulation adhering to integration collision order."""
        plat_boxes = platform_rects(self.platforms)
        keys = pygame.key.get_pressed()

        # Input handling for players
        for p in self.players:
            p.handle_input(keys, dt)

            # Check continuous attack hold
            att_key = p.controls.get("attack", -1)
            att_alt = p.controls.get("attack_alt", -1)
            is_attacking = p._attack_held or (att_key != -1 and keys[att_key]) or (att_alt != -1 and keys[att_alt])
            if is_attacking:
                p.attack(self.projectile_manager.projectiles, self.effects)

        # 1. Update players and platform collisions (passing platforms to detect one-way platforms)
        for p in self.players:
            p.update(dt, self.platforms, self.world_bounds)

        # 2. Update pickups and collect
        newly_spawned = self.spawner.update(dt, self.world_bounds)
        self.items.extend(newly_spawned)

        for item in self.items:
            item.update(dt, plat_boxes, self.world_bounds)
            if item.active:
                item_box = item.bounds
                for p in self.players:
                    if p.alive() and p.bounds().colliderect(item_box):
                        item.collect(p)
                        self.effects.burst(
                            (item.position.x, item.position.y),
                            count=12,
                            palette=[(255, 230, 80), (100, 240, 255)],
                        )
                        break

        self.items = [it for it in self.items if it.active]

        # Update Boss if active
        if self.boss:
            if self.boss.alive():
                self.boss.update(dt, plat_boxes, self.world_bounds, self.players, self.effects)
            else:
                if not getattr(self, "_boss_victory_triggered", False):
                    self._boss_victory_triggered = True
                    self.effects.explosion(self.boss.center(), radius=140.0, palette=[(255, 240, 100), (255, 120, 30), (255, 50, 50)])
                    self.effects.request_shake(intensity=18.0, duration=0.8)

        # 3. Update projectiles and apply damage (including boss hits)
        self.projectile_manager.update(dt, plat_boxes, self.world_bounds, self.players, self.effects, boss=self.boss)

        # 4. Update effects and camera
        self.effects.update(dt)
        self.camera.set_shake(self.effects.shake_offset())
        self.camera.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        """Render world objects adhering to integration rendering order."""
        # 1. Background (Atmospheric magical starry sky & distant battlements)
        self._draw_background(surface)

        # 2. Platforms
        for plat in self.platforms:
            plat.draw(surface, self.camera)

        # 3. Pickups
        for it in self.items:
            it.draw(surface, self.camera)

        # 4. Projectiles
        self.projectile_manager.draw(surface, self.camera)

        # 4.5. Final Boss Titan
        if self.boss and self.boss.alive():
            self.boss.draw(surface, self.camera)

        # 5. Players
        for p in self.players:
            p.draw(surface, self.camera)

        # 6. World visual effects
        self.effects.draw(surface, self.camera)

    def _draw_background(self, surface: pygame.Surface) -> None:
        """Render procedural background with layered battlements and stars."""
        # Deep night gradient fill
        surface.fill((12, 16, 26))

        # Distant stars (parallax)
        cam_tl = self.camera.top_left
        for i in range(50):
            star_wx = (i * 97) % self.world_bounds.width
            star_wy = (i * 53) % (self.world_bounds.height - 200)
            sx = int((star_wx - self.camera.center.x) * 0.4 + self.config.screen_width / 2) % self.config.screen_width
            sy = int((star_wy - self.camera.center.y) * 0.4 + self.config.screen_height / 2) % self.config.screen_height
            brightness = 140 + (i * 17) % 115
            pygame.draw.circle(surface, (brightness, brightness, min(255, brightness + 20)), (sx, sy), 2)

        # Distant silhouette towers / battlements
        tower_color = (20, 24, 38)
        tower_spacing = 280
        z = self.camera.zoom
        for x in range(0, self.world_bounds.width + 100, tower_spacing):
            tw_rect = pygame.Rect(x, self.world_bounds.bottom - 420, 150, 420)
            s_rect = self.camera.apply_rect(tw_rect)
            if s_rect.colliderect(surface.get_rect()):
                pygame.draw.rect(surface, tower_color, s_rect)
                emb_w = max(8, int(20 * z))
                emb_h = max(5, int(14 * z))
                step = max(14, int(35 * z))
                for bx in range(s_rect.left, s_rect.right, step):
                    pygame.draw.rect(surface, (14, 18, 28), (bx, s_rect.top - emb_h, emb_w, emb_h))

    def finished(self) -> bool:
        """Check if round has concluded due to a player's health reaching zero."""
        return not (self.left_player.alive() and self.right_player.alive())

    def winner(self) -> Player | None:
        """Retrieve the winning player entity or None if ongoing."""
        if not self.finished():
            return None
        if self.left_player.alive() and not self.right_player.alive():
            return self.left_player
        if self.right_player.alive() and not self.left_player.alive():
            return self.right_player
        return self.left_player  # tie fallback
