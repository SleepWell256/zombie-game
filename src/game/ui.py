"""User interface: atmospheric title menu, screen-space HUD, and result screen."""

from __future__ import annotations
import math
import random
from typing import TYPE_CHECKING
import pygame

if TYPE_CHECKING:
    from src.game.boss import FinalBoss
    from src.game.player import Player
    from src.game.settings import GameConfig


class UI:
    """Screen-space UI manager for menus, HUD bars, and round victory results."""

    def __init__(self, config: GameConfig) -> None:
        self.config: GameConfig = config
        self.sw: int = config.screen_width
        self.sh: int = config.screen_height

        # Initialize fonts safely
        pygame.font.init()
        font_name = "georgia" if "georgia" in pygame.font.get_fonts() else None
        self.title_font = pygame.font.SysFont(font_name, 56, bold=True)
        self.header_font = pygame.font.SysFont(font_name, 32, bold=True)
        self.button_font = pygame.font.SysFont(font_name, 24, bold=True)
        self.hud_font = pygame.font.SysFont(font_name, 18, bold=True)
        self.small_font = pygame.font.SysFont(font_name, 14)

        # Button rects
        btn_w, btn_h = 240, 54
        self.start_btn: pygame.Rect = pygame.Rect((self.sw - btn_w) // 2, self.sh - 140, btn_w, btn_h)
        self.restart_btn: pygame.Rect = pygame.Rect(self.sw // 2 - 220, self.sh // 2 + 70, 200, 50)
        self.menu_btn: pygame.Rect = pygame.Rect(self.sw // 2 + 20, self.sh // 2 + 70, 200, 50)

        # Menu procedural starfield / floating dust
        self._menu_time: float = 0.0
        self.boss_lag_health: float = 600.0
        self.boss_pulse_time: float = 0.0
        self._stars: list[dict[str, float]] = [
            {
                "x": random.uniform(0, self.sw),
                "y": random.uniform(0, self.sh),
                "speed": random.uniform(15.0, 45.0),
                "size": random.uniform(1.5, 3.5),
                "phase": random.uniform(0, 6.28),
            }
            for _ in range(65)
        ]

    def handle_event(self, event: pygame.event.Event) -> str | None:
        """Process UI interactions and return action string or None."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if self.start_btn.collidepoint(mx, my):
                return "start"
            if self.restart_btn.collidepoint(mx, my):
                return "restart"
            if self.menu_btn.collidepoint(mx, my):
                return "menu"

        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                return "start"
            elif event.key == pygame.K_r:
                return "restart"
            elif event.key == pygame.K_ESCAPE:
                return "menu"

        return None

    def draw_button(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        text: str,
        hovered: bool = False,
    ) -> None:
        """Render a button using procedural gold bevels and magical corners."""
        # Colors
        if hovered:
            bg_color = (48, 38, 70)
            border_color = (255, 230, 90)
            text_color = (255, 255, 220)
        else:
            bg_color = (26, 22, 38)
            border_color = (210, 175, 60)
            text_color = (240, 230, 200)

        # Base button rect
        pygame.draw.rect(surface, bg_color, rect, border_radius=6)
        pygame.draw.rect(surface, border_color, rect, width=2, border_radius=6)

        # Four decorative gold squares in corners
        sq = 4
        pygame.draw.rect(surface, border_color, (rect.left + 3, rect.top + 3, sq, sq))
        pygame.draw.rect(surface, border_color, (rect.right - 3 - sq, rect.top + 3, sq, sq))
        pygame.draw.rect(surface, border_color, (rect.left + 3, rect.bottom - 3 - sq, sq, sq))
        pygame.draw.rect(surface, border_color, (rect.right - 3 - sq, rect.bottom - 3 - sq, sq, sq))

        # Centered text
        txt_surf = self.button_font.render(text, True, text_color)
        t_rect = txt_surf.get_rect(center=rect.center)
        surface.blit(txt_surf, t_rect)

    def draw_menu(self, surface: pygame.Surface, dt: float) -> None:
        """Render atmospheric title menu with animated floating particles and control cards."""
        self._menu_time += dt

        # Deep magical gradient background
        surface.fill((11, 14, 25))

        # Floating procedural stars
        for st in self._stars:
            st["y"] -= st["speed"] * dt
            if st["y"] < 0:
                st["y"] = self.sh
                st["x"] = random.uniform(0, self.sw)

            alpha_sin = math.sin(self._menu_time * 2.0 + st["phase"]) * 0.4 + 0.6
            star_color = (
                int(220 * alpha_sin),
                int(210 * alpha_sin),
                int(255 * alpha_sin),
            )
            pygame.draw.circle(surface, star_color, (int(st["x"]), int(st["y"])), max(1, int(st["size"])))

        # Title banner
        title_y = 110 + int(math.sin(self._menu_time * 1.5) * 6.0)
        # Shadow
        shadow_surf = self.title_font.render(self.config.title, True, (20, 10, 30))
        surface.blit(shadow_surf, shadow_surf.get_rect(center=(self.sw // 2 + 3, title_y + 3)))

        # Glowing gold title text
        glow_color = (255, 215, 60)
        title_surf = self.title_font.render(self.config.title, True, glow_color)
        surface.blit(title_surf, title_surf.get_rect(center=(self.sw // 2, title_y)))

        # Subtitle
        sub_surf = self.hud_font.render("Fast-Paced Local 2-Player Stickman Arena", True, (180, 195, 225))
        surface.blit(sub_surf, sub_surf.get_rect(center=(self.sw // 2, title_y + 55)))

        # Controls Cards (Player 1 left, Player 2 right)
        card_w, card_h = 320, 220
        card_y = self.sh // 2 - 50

        # --- Left Player Card (Gryffindor) ---
        p1_rect = pygame.Rect(self.sw // 2 - card_w - 40, card_y, card_w, card_h)
        pygame.draw.rect(surface, (30, 20, 28, 220), p1_rect, border_radius=8)
        pygame.draw.rect(surface, (196, 30, 58), p1_rect, width=2, border_radius=8)

        p1_title = self.header_font.render("PLAYER 1 (Crimson)", True, (255, 215, 80))
        surface.blit(p1_title, (p1_rect.x + 20, p1_rect.y + 18))

        lines_p1 = [
            "Move:  A  /  D",
            "Jump / Wall-Jump:  W",
            "Attack / Use Item:  S or F",
            "Hold attack for Auto Weapons",
        ]
        for i, line in enumerate(lines_p1):
            txt = self.hud_font.render(line, True, (230, 230, 235))
            surface.blit(txt, (p1_rect.x + 20, p1_rect.y + 70 + i * 32))

        # --- Right Player Card (Slytherin) ---
        p2_rect = pygame.Rect(self.sw // 2 + 40, card_y, card_w, card_h)
        pygame.draw.rect(surface, (18, 30, 26, 220), p2_rect, border_radius=8)
        pygame.draw.rect(surface, (27, 100, 75), p2_rect, width=2, border_radius=8)

        p2_title = self.header_font.render("PLAYER 2 (Emerald)", True, (160, 240, 200))
        surface.blit(p2_title, (p2_rect.x + 20, p2_rect.y + 18))

        lines_p2 = [
            "Move:  LEFT  /  RIGHT",
            "Jump / Wall-Jump:  UP",
            "Attack / Use Item:  DOWN or RSHIFT",
            "Hold attack for Auto Weapons",
        ]
        for i, line in enumerate(lines_p2):
            txt = self.hud_font.render(line, True, (230, 230, 235))
            surface.blit(txt, (p2_rect.x + 20, p2_rect.y + 70 + i * 32))

        # Start Button
        mx, my = pygame.mouse.get_pos()
        hovered = self.start_btn.collidepoint(mx, my)
        self.draw_button(surface, self.start_btn, "START DUEL (Enter)", hovered=hovered)

    def draw_hud(self, surface: pygame.Surface, left: Player, right: Player | None = None) -> None:
        """Render screen-space HUD bars and held weapon indicators."""
        bar_w = 340
        bar_h = 24
        margin = 32

        # ================= LEFT PLAYER (P1) =================
        # Name
        p1_name = self.hud_font.render("PLAYER 1", True, (255, 215, 80))
        surface.blit(p1_name, (margin, margin - 22))

        # Health Bar Background
        p1_bg_rect = pygame.Rect(margin, margin, bar_w, bar_h)
        pygame.draw.rect(surface, (25, 20, 25), p1_bg_rect, border_radius=4)

        # Health Bar Fill
        p1_ratio = max(0.0, min(1.0, left.health / float(self.config.player_health)))
        if p1_ratio > 0:
            p1_fill_rect = pygame.Rect(margin, margin, int(bar_w * p1_ratio), bar_h)
            fill_color = (196, 30, 58) if p1_ratio > 0.25 else (220, 40, 20)
            pygame.draw.rect(surface, fill_color, p1_fill_rect, border_radius=4)

        # Health Bar Border
        pygame.draw.rect(surface, (220, 190, 80), p1_bg_rect, width=2, border_radius=4)

        # Health Numbers
        hp_str = f"{int(left.health)} / {self.config.player_health}"
        hp_surf = self.small_font.render(hp_str, True, (255, 255, 255))
        surface.blit(hp_surf, (margin + 8, margin + 4))

        # Held Item Indicator Box
        box_rect = pygame.Rect(margin, margin + bar_h + 8, 140, 32)
        pygame.draw.rect(surface, (20, 24, 34), box_rect, border_radius=4)
        pygame.draw.rect(surface, (100, 110, 130), box_rect, width=1, border_radius=4)

        item_str = "Unarmed"
        if left.held_item:
            item_str = f"{left.held_item.item_type.value.upper()} ({left.held_item.ammo})"
        elif left.shield_timer > 0:
            item_str = f"SHIELD ({int(left.shield_timer)}s)"
        it_surf = self.small_font.render(item_str, True, (230, 220, 180))
        surface.blit(it_surf, (box_rect.x + 8, box_rect.y + 8))

        # ================= RIGHT PLAYER (P2) =================
        if right is not None:
            p2_bg_rect = pygame.Rect(self.sw - margin - bar_w, margin, bar_w, bar_h)

            # Name
            p2_name = self.hud_font.render("PLAYER 2", True, (160, 240, 200))
            surface.blit(p2_name, (self.sw - margin - bar_w, margin - 22))

            # Health Bar Background
            pygame.draw.rect(surface, (20, 25, 22), p2_bg_rect, border_radius=4)

            # Health Bar Fill (anchored to right)
            p2_ratio = max(0.0, min(1.0, right.health / float(self.config.player_health)))
            if p2_ratio > 0:
                fill_w = int(bar_w * p2_ratio)
                p2_fill_rect = pygame.Rect(self.sw - margin - fill_w, margin, fill_w, bar_h)
                fill_color = (27, 120, 80) if p2_ratio > 0.25 else (220, 40, 20)
                pygame.draw.rect(surface, fill_color, p2_fill_rect, border_radius=4)

            # Health Bar Border
            pygame.draw.rect(surface, (180, 210, 200), p2_bg_rect, width=2, border_radius=4)

            # Health Numbers
            hp2_str = f"{int(right.health)} / {self.config.player_health}"
            hp2_surf = self.small_font.render(hp2_str, True, (255, 255, 255))
            surface.blit(hp2_surf, (self.sw - margin - bar_w + 8, margin + 4))

            # Held Item Indicator Box (Right)
            box2_rect = pygame.Rect(self.sw - margin - 140, margin + bar_h + 8, 140, 32)
            pygame.draw.rect(surface, (20, 24, 34), box2_rect, border_radius=4)
            pygame.draw.rect(surface, (100, 110, 130), box2_rect, width=1, border_radius=4)

            item2_str = "Unarmed"
            if right.held_item:
                item2_str = f"{right.held_item.item_type.value.upper()} ({right.held_item.ammo})"
            elif right.shield_timer > 0:
                item2_str = f"SHIELD ({int(right.shield_timer)}s)"
            it2_surf = self.small_font.render(item2_str, True, (190, 230, 210))
            surface.blit(it2_surf, (box2_rect.x + 8, box2_rect.y + 8))

            # Center Arena Title
            vs_surf = self.header_font.render("VS", True, (200, 180, 120))
            surface.blit(vs_surf, vs_surf.get_rect(center=(self.sw // 2, margin + bar_h // 2)))

    def draw_result(self, surface: pygame.Surface, winner: Player) -> None:
        """Render victory result screen overlay."""
        # Dim backdrop
        dim_surf = pygame.Surface((self.sw, self.sh), pygame.SRCALPHA)
        dim_surf.fill((10, 12, 18, 200))
        surface.blit(dim_surf, (0, 0))

        # Result card
        card_w, card_h = 560, 300
        card_rect = pygame.Rect((self.sw - card_w) // 2, (self.sh - card_h) // 2 - 30, card_w, card_h)
        pygame.draw.rect(surface, (24, 26, 38), card_rect, border_radius=10)
        border_col = (255, 215, 60) if winner.player_id == 1 else (160, 240, 200)
        pygame.draw.rect(surface, border_col, card_rect, width=3, border_radius=10)

        # Victory title
        vic_surf = self.title_font.render("DUEL DECIDED!", True, (255, 230, 120))
        surface.blit(vic_surf, vic_surf.get_rect(center=(self.sw // 2, card_rect.y + 55)))

        # Winner text
        win_label = f"Player {winner.player_id} is Victorious!"
        sub_col = (255, 180, 80) if winner.player_id == 1 else (140, 240, 190)
        win_surf = self.header_font.render(win_label, True, sub_col)
        surface.blit(win_surf, win_surf.get_rect(center=(self.sw // 2, card_rect.y + 120)))

        # Buttons
        mx, my = pygame.mouse.get_pos()
        r_hover = self.restart_btn.collidepoint(mx, my)
        m_hover = self.menu_btn.collidepoint(mx, my)

        self.draw_button(surface, self.restart_btn, "RESTART (R)", hovered=r_hover)
        self.draw_button(surface, self.menu_btn, "MAIN MENU (Esc)", hovered=m_hover)

    def draw_boss_health_bar(self, surface: pygame.Surface, boss: FinalBoss, dt: float = 0.016) -> None:
        """Render the epic screen-top Boss health bar with damage lag, phase glow, and gothic borders."""
        if not boss or not boss.alive():
            return

        self.boss_pulse_time += dt

        # Smooth damage lag catching up to actual health
        if self.boss_lag_health > boss.health:
            self.boss_lag_health = max(boss.health, self.boss_lag_health - (boss.max_health * 0.45) * dt)
        elif self.boss_lag_health < boss.health:
            self.boss_lag_health = boss.health

        bar_w = 680
        bar_h = 24
        x = (self.sw - bar_w) // 2
        y = 36

        # --- BOSS TITLE & PHASE TAG ---
        name_str = "💀 THE ZOMBIE TITAN: PATIENT ZERO 💀"
        name_col = (255, 60, 70) if boss.is_enraged else (255, 215, 90)
        name_surf = self.hud_font.render(name_str, True, name_col)
        surface.blit(name_surf, name_surf.get_rect(center=(self.sw // 2, y - 16)))

        if boss.is_enraged:
            enrage_txt = self.small_font.render("⚡ PHASE 2: ENRAGED MUTATION ⚡", True, (255, 50, 60))
            surface.blit(enrage_txt, enrage_txt.get_rect(center=(self.sw // 2, y + bar_h + 16)))

        # Background bar
        bg_rect = pygame.Rect(x, y, bar_w, bar_h)
        pygame.draw.rect(surface, (18, 12, 16), bg_rect, border_radius=6)

        # Lagging damage bar (Dark Souls / Elden Ring style orange/red trailing bar)
        lag_ratio = max(0.0, min(1.0, self.boss_lag_health / boss.max_health))
        if lag_ratio > 0:
            lag_rect = pygame.Rect(x, y, int(bar_w * lag_ratio), bar_h)
            pygame.draw.rect(surface, (180, 50, 40), lag_rect, border_radius=6)

        # Active current health fill
        hp_ratio = max(0.0, min(1.0, boss.health / boss.max_health))
        if hp_ratio > 0:
            hp_rect = pygame.Rect(x, y, int(bar_w * hp_ratio), bar_h)
            if boss.is_enraged:
                pulse = (math.sin(self.boss_pulse_time * 8.0) + 1.0) * 0.5
                r = int(220 + pulse * 35)
                g = int(30 + pulse * 20)
                b = int(40)
                fill_color = (r, g, b)
            else:
                fill_color = (40, 180, 70) if hp_ratio > 0.3 else (210, 140, 30)
            pygame.draw.rect(surface, fill_color, hp_rect, border_radius=6)

            # Highlighting top gloss sheen
            gloss_rect = pygame.Rect(x, y, int(bar_w * hp_ratio), bar_h // 2)
            gloss_surf = pygame.Surface((gloss_rect.width, gloss_rect.height), pygame.SRCALPHA)
            gloss_surf.fill((255, 255, 255, 45))
            surface.blit(gloss_surf, (x, y))

        # Heavy Gothic Metallic / Gold border
        border_col = (255, 60, 70) if boss.is_enraged else (220, 185, 70)
        pygame.draw.rect(surface, border_col, bg_rect, width=2, border_radius=6)

        # 4 Corner Diamond Accents
        sq = 5
        pygame.draw.rect(surface, border_col, (x - sq // 2, y + bar_h // 2 - sq // 2, sq, sq))
        pygame.draw.rect(surface, border_col, (x + bar_w - sq // 2, y + bar_h // 2 - sq // 2, sq, sq))

        # Health Numbers
        hp_str = f"{int(boss.health)} / {int(boss.max_health)}"
        hp_num_surf = self.small_font.render(hp_str, True, (255, 255, 255))
        surface.blit(hp_num_surf, hp_num_surf.get_rect(center=(self.sw // 2, y + bar_h // 2)))
