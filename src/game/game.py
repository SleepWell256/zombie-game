"""Top-level game state machine and application execution loop."""

from __future__ import annotations
import sys
import pygame

from src.game.assets import AssetManager
from src.game.settings import GameConfig
from src.game.ui import UI
from src.game.world import World


class Game:
    """State machine coordinator and application loop."""

    def __init__(self) -> None:
        pygame.init()
        pygame.font.init()
        try:
            pygame.mixer.init()
        except Exception:
            pass

        self.config: GameConfig = GameConfig()
        self.screen: pygame.Surface = pygame.display.set_mode(self.config.screen_size)
        pygame.display.set_caption(self.config.title)

        self.clock: pygame.time.Clock = pygame.time.Clock()
        self.assets: AssetManager = AssetManager(self.config.asset_dir)
        self.world: World = World(self.config, self.assets)
        self.ui: UI = UI(self.config)

        # States: "menu", "intro", "playing", "game_over", "quit"
        self.state: str = "playing"
        self.running: bool = True
        self._last_dt: float = 0.016
        self.world.camera.skip_intro()

    def change_state(self, state: str) -> None:
        """Transition application state."""
        self.state = state
        if state == "intro":
            self.world.camera.skip_intro()
            self.state = "playing"
        elif state == "quit":
            self.quit()

    def quit(self) -> None:
        """Cleanly terminate the application."""
        self.running = False
        self.state = "quit"

    def handle_event(self, event: pygame.event.Event) -> None:
        """Route incoming user events depending on active state."""
        if event.type == pygame.QUIT:
            self.quit()
            return

        if self.state == "menu":
            action = self.ui.handle_event(event)
            if action == "start":
                self.world.reset()
                self.change_state("intro")

        elif self.state == "intro":
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    # Skip intro cinematic directly into arena action
                    self.world.camera.skip_intro()
                    self.change_state("playing")
                elif event.key == pygame.K_ESCAPE:
                    self.change_state("menu")

        elif self.state == "playing":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.change_state("menu")
                return
            self.world.handle_event(event)

        elif self.state == "game_over":
            action = self.ui.handle_event(event)
            if action == "restart":
                self.world.reset()
                self.world.camera.skip_intro()
                self.change_state("playing")
            elif action == "menu":
                self.change_state("menu")

    def update(self, dt: float) -> None:
        """Advance game simulation by dt seconds according to active state."""
        self._last_dt = dt

        if self.state == "intro":
            # Update camera pan, zoom, ambient particles, and player idle animations
            self.world.camera.update(dt)
            self.world.effects.update(dt)
            for p in self.world.players:
                p.anim_time += dt
            if self.world.camera.intro_finished():
                self.change_state("playing")

        elif self.state == "playing":
            self.world.update(dt)
            if self.world.finished():
                self.change_state("game_over")

        elif self.state == "game_over":
            # Settle world effects and screen shake
            self.world.effects.update(dt)
            self.world.camera.set_shake(self.world.effects.shake_offset())

    def draw(self) -> None:
        """Render frame according to active state and flip display buffer."""
        if self.state == "menu":
            self.ui.draw_menu(self.screen, self._last_dt)

        elif self.state in ("intro", "playing"):
            self.world.draw(self.screen)
            self.ui.draw_hud(self.screen, self.world.left_player, self.world.right_player)
            if self.world.boss and self.world.boss.alive():
                self.ui.draw_boss_health_bar(self.screen, self.world.boss, self._last_dt)

        elif self.state == "game_over":
            self.world.draw(self.screen)
            self.ui.draw_hud(self.screen, self.world.left_player, self.world.right_player)
            if self.world.boss:
                self.ui.draw_boss_health_bar(self.screen, self.world.boss, self._last_dt)
            winner = self.world.winner()
            if winner:
                self.ui.draw_result(self.screen, winner)

        pygame.display.flip()

    def run(self) -> None:
        """Primary application loop."""
        while self.running:
            raw_dt = self.clock.tick(self.config.fps) / 1000.0
            dt = min(0.05, max(0.001, raw_dt))

            for event in pygame.event.get():
                self.handle_event(event)

            if not self.running:
                break

            self.update(dt)
            self.draw()

        pygame.quit()
