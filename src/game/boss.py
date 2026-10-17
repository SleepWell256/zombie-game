"""Final Boss Titan: Multi-phase heavyweight boss with telegraphs, shockwaves, charge, and minion summons."""

from __future__ import annotations
import math
import random
from typing import TYPE_CHECKING, Callable
import pygame

from src.game.boss_renderer import BossAppearance

if TYPE_CHECKING:
    from src.game.camera import Camera
    from src.game.effects import EffectManager
    from src.game.player import Player


class BossShockwave:
    """A shockwave surging along the ground following a heavy Boss ground slam."""

    def __init__(self, position: tuple[float, float], direction: int, speed: float = 380.0, max_dist: float = 400.0) -> None:
        self.x: float = position[0]
        self.y: float = position[1]
        self.direction: int = direction  # -1 for left, 1 for right
        self.speed: float = speed
        self.traveled: float = 0.0
        self.max_dist: float = max_dist
        self.width: int = 32
        self.height: int = 36
        self.damage: float = 10.0  # Sets player back by 10 time points!
        self.expired: bool = False
        self.hit_players: set[int] = set()

    def bounds(self) -> pygame.Rect:
        return pygame.Rect(int(self.x - self.width / 2), int(self.y - self.height), self.width, self.height)

    def update(self, dt: float, players: list[Player], effects: EffectManager) -> None:
        if self.expired:
            return

        dist = self.speed * dt
        self.x += self.direction * dist
        self.traveled += dist

        if self.traveled >= self.max_dist:
            self.expired = True
            return

        # Particle trail
        if random.random() < 0.4:
            palette = [(220, 50, 60), (255, 120, 80)] if self.damage >= 10 else [(40, 180, 80)]
            effects.burst((self.x, self.y - 10), count=2, palette=palette, strength=0.3)

        # Check player collision
        box = self.bounds()
        for p in players:
            if not p.alive() or p.player_id in self.hit_players:
                continue
            if box.colliderect(p.bounds()):
                self.hit_players.add(p.player_id)
                kb_x = self.direction * 380.0
                p.take_damage(self.damage, knockback=(kb_x, -200.0))
                effects.burst((p.position.x, p.position.y - 25), count=14, palette=[(255, 40, 40), (255, 200, 50)])
                effects.request_shake(intensity=8.0, duration=0.2)

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        if self.expired:
            return
        sx, sy = camera.apply((self.x, self.y))
        z = camera.zoom

        # Draw jagged energy wave / earth spikes
        w = int(self.width * z)
        h = int(self.height * z * (1.0 - (self.traveled / self.max_dist) * 0.4))
        if h <= 2 or w <= 2:
            return

        wave_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        # Jagged triangular wave
        pts = [(0, h), (w // 2, 0), (w, h)]
        pygame.draw.polygon(wave_surf, (220, 40, 50, 200), pts)
        pygame.draw.polygon(wave_surf, (255, 220, 100, 240), pts, width=max(1, int(2 * z)))
        surface.blit(wave_surf, (sx - w // 2, sy - h))


class BossAcidMortar:
    """Lobbed toxic acid mortar from the Boss that creates a hazard on contact."""

    def __init__(self, start_pos: tuple[float, float], target_pos: tuple[float, float]) -> None:
        self.x: float = start_pos[0]
        self.y: float = start_pos[1]
        self.radius: int = 10
        self.damage: float = 10.0  # 10 time points!
        self.expired: bool = False

        # Calculate parabolic arc velocity
        dx = target_pos[0] - start_pos[0]
        time_to_target = 1.1  # seconds
        self.vx: float = dx / time_to_target
        self.vy: float = -380.0  # initial upward launch
        self.gravity: float = 700.0
        self.time_alive: float = 0.0

    def bounds(self) -> pygame.Rect:
        r = self.radius
        return pygame.Rect(int(self.x - r), int(self.y - r), r * 2, r * 2)

    def update(self, dt: float, platforms: list[pygame.Rect], players: list[Player], effects: EffectManager) -> None:
        if self.expired:
            return

        self.time_alive += dt
        self.vy += self.gravity * dt
        self.x += self.vx * dt
        self.y += self.vy * dt

        # Green acid trail
        if random.random() < 0.5:
            effects.burst((self.x, self.y), count=2, palette=[(60, 255, 80), (100, 200, 50)], strength=0.2)

        box = self.bounds()

        # Check collision with players
        for p in players:
            if p.alive() and box.colliderect(p.bounds()):
                p.take_damage(self.damage, knockback=(180.0 if self.vx >= 0 else -180.0, -120.0))
                effects.burst((self.x, self.y), count=16, palette=[(50, 255, 60), (255, 220, 50)])
                effects.request_shake(intensity=6.0, duration=0.15)
                self.expired = True
                return

        # Check collision with ground/platforms
        if self.vy > 0:
            for plat in platforms:
                if box.colliderect(plat):
                    # Splat
                    effects.burst((self.x, self.y), count=12, palette=[(40, 220, 60), (80, 255, 120)], strength=0.6)
                    self.expired = True
                    return

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        if self.expired:
            return
        sx, sy = camera.apply((self.x, self.y))
        z = camera.zoom
        r = max(2, int(self.radius * z))
        pygame.draw.circle(surface, (40, 220, 60), (sx, sy), r)
        pygame.draw.circle(surface, (180, 255, 120), (sx, sy), max(1, r // 2))


class FinalBoss:
    """The Final Boss Titan entity (Wave 16 / post-checkpoint 3)."""

    def __init__(self, spawn: tuple[float, float]) -> None:
        # Dimensions: 3x scale of player
        self.width: int = 70
        self.height: int = 160
        self.position: pygame.Vector2 = pygame.Vector2(spawn[0], spawn[1])
        self.velocity: pygame.Vector2 = pygame.Vector2(0.0, 0.0)
        self.facing: int = -1
        self.on_ground: bool = True

        # Health & Phases
        self.max_health: float = 600.0
        self.health: float = self.max_health
        self.is_enraged: bool = False
        self.damage_power: float = 10.0  # Sets player back by 10 time points!

        # Procedural visual controller entity
        self.appearance: BossAppearance = BossAppearance(base_height=self.height, base_width=self.width)

        # AI Behavior State Machine
        self.state: str = "IDLE"  # IDLE, WALK, WINDUP_CHARGE, CHARGING, WINDUP_SLAM, LEAPING, SLAM, ACID_SPIT, ROAR_SUMMON, STUNNED
        self.state_timer: float = 1.0
        self.action_cooldown: float = 2.0
        self.attack_hit_cooldown: float = 0.0

        # Sub-projectiles & hazards
        self.shockwaves: list[BossShockwave] = []
        self.acid_mortars: list[BossAcidMortar] = []

        # Target player
        self.target: Player | None = None

        # Minion summon callback (to spawn fast zombies for player +3s time harvesting)
        self.minion_summon_callback: Callable[[int, tuple[float, float]], None] | None = None
        self.has_summoned_enrage_wave: bool = False

    def alive(self) -> bool:
        return self.health > 0

    def bounds(self) -> pygame.Rect:
        return pygame.Rect(
            int(self.position.x - self.width / 2),
            int(self.position.y - self.height),
            self.width,
            self.height,
        )

    def center(self) -> tuple[float, float]:
        return (self.position.x, self.position.y - self.height / 2)

    def take_damage(self, amount: float, effects: EffectManager) -> float:
        """Process incoming player attack. Returns amount of time gained by player (1.0)."""
        if not self.alive():
            return 0.0

        self.health = max(0.0, self.health - amount)
        self.appearance.trigger_flash(0.12)
        effects.burst(self.center(), count=10, palette=[(255, 60, 60), (255, 220, 100)])

        # Check enrage threshold (50% HP)
        if not self.is_enraged and self.health <= self.max_health * 0.5:
            self.enter_enrage(effects)

        return 1.0  # Rule: hitting a zombie gives 1 unit of time

    def enter_enrage(self, effects: EffectManager) -> None:
        """Trigger Phase 2 Enrage mutation."""
        self.is_enraged = True
        self.state = "ROAR_SUMMON"
        self.state_timer = 1.8
        self.appearance.set_squash_stretch(0.85, 1.35)
        effects.request_shake(intensity=12.0, duration=0.8)
        effects.explosion(self.center(), radius=70.0, palette=[(255, 40, 50), (120, 20, 30)])

        # Summon 2 fast minions for player to farm +3s time
        if self.minion_summon_callback and not self.has_summoned_enrage_wave:
            self.has_summoned_enrage_wave = True
            self.minion_summon_callback(2, (self.position.x, self.position.y))

    def update(
        self,
        dt: float,
        platforms: list[pygame.Rect],
        world_bounds: pygame.Rect,
        players: list[Player],
        effects: EffectManager,
    ) -> None:
        """Update Boss AI, attacks, physics, and state transitions."""
        if not self.alive():
            return

        # Update visuals
        self.appearance.update(dt, self.is_enraged)

        # Select closest alive player
        alive_players = [p for p in players if p.alive()]
        if alive_players:
            self.target = min(alive_players, key=lambda p: math.hypot(p.position.x - self.position.x, p.position.y - self.position.y))
        else:
            self.target = None

        if self.attack_hit_cooldown > 0:
            self.attack_hit_cooldown = max(0.0, self.attack_hit_cooldown - dt)

        # AI Behavior State Machine
        self.update_ai_state(dt, effects)

        # Apply Physics & Gravity
        self.apply_physics(dt, platforms, world_bounds, effects)

        # Check Direct Body/Attack Collisions with Players
        self.check_player_collisions(players, effects)

        # Update active shockwaves and acid mortars
        for sw in self.shockwaves:
            sw.update(dt, players, effects)
        self.shockwaves = [sw for sw in self.shockwaves if not sw.expired]

        for mortar in self.acid_mortars:
            mortar.update(dt, platforms, players, effects)
        self.acid_mortars = [m for m in self.acid_mortars if not m.expired]

    def update_ai_state(self, dt: float, effects: EffectManager) -> None:
        """Execute action based on current state."""
        self.state_timer -= dt

        # Face target
        if self.target and self.state in ("IDLE", "WALK", "WINDUP_CHARGE", "WINDUP_SLAM"):
            self.facing = 1 if self.target.position.x > self.position.x else -1

        speed_multiplier = 1.35 if self.is_enraged else 1.0

        if self.state == "IDLE":
            self.velocity.x = 0.0
            self.appearance.telegraph_glow = 0.0
            if self.state_timer <= 0:
                self.decide_next_action()

        elif self.state == "WALK":
            walk_speed = 140.0 * speed_multiplier
            self.velocity.x = self.facing * walk_speed
            # Heavy footstep screenshake
            if math.sin(self.appearance.anim_time * 5.0) > 0.95:
                effects.request_shake(intensity=2.0, duration=0.08)

            if self.state_timer <= 0:
                self.decide_next_action()

        elif self.state == "WINDUP_CHARGE":
            # Squats and flashes warning aura
            self.velocity.x = 0.0
            self.appearance.telegraph_glow = 1.0 - (self.state_timer / 0.8)
            self.appearance.set_squash_stretch(1.25, 0.8)
            if self.state_timer <= 0:
                # Launch charge!
                self.state = "CHARGING"
                self.state_timer = 1.2
                self.appearance.set_squash_stretch(0.75, 1.25)
                self.velocity.x = self.facing * (620.0 * speed_multiplier)
                effects.request_shake(intensity=6.0, duration=0.3)

        elif self.state == "CHARGING":
            self.appearance.telegraph_glow = 0.8
            # Dust and speed trail
            if random.random() < 0.6:
                palette = [(240, 80, 80), (120, 30, 30)] if self.is_enraged else [(180, 180, 180)]
                effects.burst((self.position.x - self.facing * 30, self.position.y - 10), count=2, palette=palette, strength=0.3)

            if self.state_timer <= 0:
                self.state = "IDLE"
                self.state_timer = 0.6

        elif self.state == "WINDUP_SLAM":
            # Deep crouch before leap
            self.velocity.x = 0.0
            self.appearance.set_squash_stretch(1.35, 0.7)
            self.appearance.telegraph_glow = 1.0 - (self.state_timer / 0.7)
            if self.state_timer <= 0:
                # Leap toward player
                self.state = "LEAPING"
                self.state_timer = 2.0
                self.on_ground = False
                leap_vx = self.facing * (280.0 * speed_multiplier)
                leap_vy = -680.0
                if self.target:
                    dx = self.target.position.x - self.position.x
                    leap_vx = max(-400.0, min(400.0, dx * 1.5))
                self.velocity = pygame.Vector2(leap_vx, leap_vy)
                self.appearance.set_squash_stretch(0.75, 1.35)

        elif self.state == "LEAPING":
            # Airborne peak transition into plummet
            if self.velocity.y > 100.0:
                self.state = "SLAM"
                self.velocity.y = 850.0  # Heavy crash downward
                self.velocity.x = 0.0

        elif self.state == "SLAM":
            self.appearance.telegraph_glow = 1.0
            # Falling fast until on_ground is triggered in apply_physics

        elif self.state == "ACID_SPIT":
            self.velocity.x = 0.0
            if self.state_timer <= 0:
                self.state = "IDLE"
                self.state_timer = 0.5

        elif self.state == "ROAR_SUMMON":
            self.velocity.x = 0.0
            self.appearance.telegraph_glow = 1.0
            if self.state_timer <= 0:
                self.state = "IDLE"
                self.state_timer = 0.8

        elif self.state == "STUNNED":
            self.velocity.x = 0.0
            self.appearance.telegraph_glow = 0.0
            if self.state_timer <= 0:
                self.state = "IDLE"
                self.state_timer = 0.4

    def decide_next_action(self) -> None:
        """Choose intelligent attack based on distance to player and phase."""
        if not self.target:
            self.state = "IDLE"
            self.state_timer = 1.0
            return

        dist_x = abs(self.target.position.x - self.position.x)
        dist_y = self.target.position.y - self.position.y

        # Distance evaluations
        if dist_x > 500.0:
            # Far away: Either Bull Charge or Acid Spit
            action = random.choice(["CHARGE", "ACID", "WALK"])
        elif dist_x < 180.0:
            # Close quarters: Ground Slam or Melee Rush
            action = random.choice(["SLAM", "CHARGE", "WALK"])
        else:
            # Mid-range: Any action
            action = random.choice(["SLAM", "CHARGE", "ACID", "WALK"])

        if action == "CHARGE":
            self.state = "WINDUP_CHARGE"
            self.state_timer = 0.6 if self.is_enraged else 0.8
        elif action == "SLAM":
            self.state = "WINDUP_SLAM"
            self.state_timer = 0.5 if self.is_enraged else 0.7
        elif action == "ACID":
            self.state = "ACID_SPIT"
            self.state_timer = 0.6
            self.fire_acid_mortars()
        else:
            self.state = "WALK"
            self.state_timer = random.uniform(1.0, 2.0)

    def fire_acid_mortars(self) -> None:
        """Lob acid projectiles toward player's area."""
        target_pt = self.target.position if self.target else pygame.Vector2(self.position.x + self.facing * 300, self.position.y)
        # Primary mortar
        self.acid_mortars.append(BossAcidMortar((self.position.x, self.position.y - 120), (target_pt.x, target_pt.y)))
        # Flanking mortar
        spread = 90.0
        self.acid_mortars.append(BossAcidMortar((self.position.x, self.position.y - 120), (target_pt.x + spread, target_pt.y)))
        if self.is_enraged:
            self.acid_mortars.append(BossAcidMortar((self.position.x, self.position.y - 120), (target_pt.x - spread, target_pt.y)))

    def apply_physics(self, dt: float, platforms: list[pygame.Rect], world_bounds: pygame.Rect, effects: EffectManager) -> None:
        """Update platform collision, gravity, wall bounce, and slam triggers."""
        # Gravity
        if not self.on_ground:
            self.velocity.y += 1200.0 * dt

        # Move X
        self.position.x += self.velocity.x * dt

        # Arena wall collision
        box = self.bounds()
        if box.left <= world_bounds.left + 20:
            self.position.x = world_bounds.left + 20 + self.width / 2
            if self.state == "CHARGING":
                self.wall_crash(effects)
        elif box.right >= world_bounds.right - 20:
            self.position.x = world_bounds.right - 20 - self.width / 2
            if self.state == "CHARGING":
                self.wall_crash(effects)

        # Move Y
        prev_y = self.position.y
        self.position.y += self.velocity.y * dt
        box = self.bounds()

        # Platform / Floor landing
        was_on_ground = self.on_ground
        self.on_ground = False

        for plat in platforms:
            # Landing on top of platform
            if self.velocity.y > 0 and box.colliderect(plat):
                if prev_y <= plat.top + 20 and self.position.y >= plat.top:
                    self.position.y = plat.top
                    self.velocity.y = 0.0
                    self.on_ground = True

                    # Did we land a SLAM?
                    if self.state == "SLAM":
                        self.trigger_ground_slam(effects)
                    elif not was_on_ground:
                        self.appearance.set_squash_stretch(1.28, 0.75)
                    break

    def wall_crash(self, effects: EffectManager) -> None:
        """Boss crashes into wall during charge: screenshake and brief stun."""
        self.velocity.x = 0.0
        self.state = "STUNNED"
        self.state_timer = 0.7  # Vulnerability window for player!
        self.appearance.set_squash_stretch(1.3, 0.7)
        effects.request_shake(intensity=14.0, duration=0.35)
        effects.burst(self.center(), count=20, palette=[(255, 200, 80), (180, 180, 180)])

    def trigger_ground_slam(self, effects: EffectManager) -> None:
        """Impact of slam: creates dual shockwaves and massive shake."""
        self.state = "IDLE"
        self.state_timer = 0.8
        self.appearance.set_squash_stretch(1.45, 0.6)
        effects.request_shake(intensity=16.0, duration=0.45)
        effects.explosion((self.position.x, self.position.y - 10), radius=90.0, palette=[(240, 50, 50), (255, 180, 40), (80, 20, 20)])

        # Spawn Left and Right shockwaves
        sw_speed = 420.0 if self.is_enraged else 350.0
        self.shockwaves.append(BossShockwave((self.position.x - 30, self.position.y), direction=-1, speed=sw_speed))
        self.shockwaves.append(BossShockwave((self.position.x + 30, self.position.y), direction=1, speed=sw_speed))

    def check_player_collisions(self, players: list[Player], effects: EffectManager) -> None:
        """Check collision with player for body damage / charge hit."""
        if self.attack_hit_cooldown > 0:
            return

        boss_box = self.bounds()
        for p in players:
            if not p.alive():
                continue
            if boss_box.colliderect(p.bounds()):
                # Player takes 10 time points damage!
                kb_x = self.facing * 500.0 if self.state == "CHARGING" else (350.0 if p.position.x > self.position.x else -350.0)
                kb_y = -260.0
                p.take_damage(self.damage_power, knockback=(kb_x, kb_y))
                self.attack_hit_cooldown = 0.6  # Prevent spam collision in 1 tick
                effects.burst((p.position.x, p.position.y - 25), count=18, palette=[(255, 30, 30), (255, 200, 60)])
                effects.request_shake(intensity=10.0, duration=0.25)

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        """Render the Boss, its active shockwaves, and acid mortars."""
        if not self.alive():
            return

        # Draw Boss stickman entity via BossAppearance
        self.appearance.draw(
            surface=surface,
            camera=camera,
            position=self.position,
            facing=self.facing,
            state_name=self.state,
            is_grounded=self.on_ground,
        )

        # Draw shockwaves
        for sw in self.shockwaves:
            sw.draw(surface, camera)

        # Draw acid mortars
        for mortar in self.acid_mortars:
            mortar.draw(surface, camera)
