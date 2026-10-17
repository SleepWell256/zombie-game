"""Dedicated procedural renderer and appearance controller for the Final Boss Titan."""

from __future__ import annotations
import math
import random
from typing import TYPE_CHECKING
import pygame

if TYPE_CHECKING:
    from src.game.camera import Camera


class BossAppearance:
    """Controls the visual aesthetic, procedural animations, and phase transitions for the Final Boss."""

    def __init__(self, base_height: int = 160, base_width: int = 70) -> None:
        self.height: int = base_height
        self.width: int = base_width
        self.anim_time: float = 0.0

        # Dynamic visual states
        self.squash_stretch: pygame.Vector2 = pygame.Vector2(1.0, 1.0)
        self.damage_flash: float = 0.0
        self.telegraph_glow: float = 0.0  # 0.0 to 1.0 (for charge/slam windups)
        self.is_enraged: bool = False     # Phase 2 trigger
        self.eye_pulse: float = 0.0
        self.vein_pulse: float = 0.0

    def update(self, dt: float, is_enraged: bool) -> None:
        """Update animation timers and pulses."""
        self.anim_time += dt
        self.is_enraged = is_enraged

        if self.damage_flash > 0:
            self.damage_flash = max(0.0, self.damage_flash - dt)

        # Smooth recovery from squash & stretch
        self.squash_stretch.x += (1.0 - self.squash_stretch.x) * min(1.0, dt * 12.0)
        self.squash_stretch.y += (1.0 - self.squash_stretch.y) * min(1.0, dt * 12.0)

        # Pulses
        pulse_speed = 8.0 if is_enraged else 4.0
        self.eye_pulse = (math.sin(self.anim_time * pulse_speed) + 1.0) * 0.5
        self.vein_pulse = (math.sin(self.anim_time * (pulse_speed * 1.5)) + 1.0) * 0.5

    def trigger_flash(self, duration: float = 0.12) -> None:
        """Trigger white damage flash on hit."""
        self.damage_flash = duration

    def set_squash_stretch(self, sx: float, sy: float) -> None:
        """Apply squash & stretch deformation."""
        self.squash_stretch = pygame.Vector2(sx, sy)

    def draw(
        self,
        surface: pygame.Surface,
        camera: Camera,
        position: pygame.Vector2,
        facing: int,
        state_name: str,
        is_grounded: bool,
    ) -> None:
        """Draw the 3x mutated Titan Boss stickman with bulky shoulders, claws, spikes, and glowing eyes."""
        screen_pos = camera.apply((position.x, position.y))
        sx, sy = screen_pos
        z = camera.zoom

        # Base scales (3x player scale)
        sq_x = self.squash_stretch.x
        sq_y = self.squash_stretch.y
        scale_w = z * sq_x
        scale_h = z * sq_y

        # Colors
        if self.damage_flash > 0:
            body_color = (255, 255, 255)
            muscle_color = (240, 240, 240)
            eye_color = (255, 255, 255)
            vein_color = (255, 255, 255)
        elif self.is_enraged:
            # Enraged Phase 2: Corrupted Crimson / Blood Ash
            body_color = (45, 15, 20)
            muscle_color = (80, 25, 30)
            eye_color = (255, 30, 40)
            vein_color = (220, 50, 60)
        else:
            # Phase 1: Necrotic Moss / Corrupted Titan Dark Green
            body_color = (20, 35, 25)
            muscle_color = (35, 55, 40)
            eye_color = (60, 255, 120)
            vein_color = (40, 180, 80)

        # Telegraph Aura (flashes bright warning when charging or winding up slam)
        if self.telegraph_glow > 0.05:
            glow_radius = int(80 * z * (1.0 + self.telegraph_glow * 0.3))
            glow_surf = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
            alpha = int(120 * self.telegraph_glow)
            glow_col = (255, 50, 50, alpha) if self.is_enraged else (255, 180, 40, alpha)
            pygame.draw.circle(glow_surf, glow_col, (glow_radius, glow_radius), glow_radius)
            surface.blit(glow_surf, (sx - glow_radius, sy - int(80 * scale_h) - glow_radius))

        # Core anchor positions (relative to feet at sx, sy)
        pelvis_y = sy - int(55 * scale_h)
        chest_y = sy - int(110 * scale_h)
        head_y = sy - int(145 * scale_h)
        head_radius = max(6, int(18 * z))

        # Dynamic idle / run sway
        sway = math.sin(self.anim_time * 5.0) * (6.0 * z) if state_name == "WALK" else 0.0
        breath_bob = math.sin(self.anim_time * 3.0) * (3.0 * z) if is_grounded and state_name == "IDLE" else 0.0
        chest_y += int(breath_bob)
        head_y += int(breath_bob)

        # 1. LEGS (Thick, jagged mutated limbs)
        leg_width = max(3, int(8 * z))
        # Left leg
        left_foot_x = sx - int(24 * scale_w) + (int(sway) if facing > 0 else -int(sway))
        left_knee_x = sx - int(18 * scale_w)
        left_knee_y = sy - int(28 * scale_h)
        pygame.draw.line(surface, body_color, (sx - int(10 * scale_w), pelvis_y), (left_knee_x, left_knee_y), leg_width)
        pygame.draw.line(surface, body_color, (left_knee_x, left_knee_y), (left_foot_x, sy), leg_width)

        # Right leg
        right_foot_x = sx + int(24 * scale_w) - (int(sway) if facing > 0 else -int(sway))
        right_knee_x = sx + int(18 * scale_w)
        right_knee_y = sy - int(28 * scale_h)
        pygame.draw.line(surface, body_color, (sx + int(10 * scale_w), pelvis_y), (right_knee_x, right_knee_y), leg_width)
        pygame.draw.line(surface, body_color, (right_knee_x, right_knee_y), (right_foot_x, sy), leg_width)

        # 2. TORSO (Broad muscular V-taper)
        torso_width = max(6, int(18 * scale_w))
        pygame.draw.line(surface, body_color, (sx, pelvis_y), (sx, chest_y), torso_width)

        # Torso veins / muscle detailing
        vein_w = max(1, int(2 * z))
        v_offset = int(self.vein_pulse * 3 * z)
        pygame.draw.line(surface, vein_color, (sx - 6 * z, chest_y + 10 * z), (sx + 4 * z, pelvis_y - 10 * z), vein_w)
        pygame.draw.line(surface, vein_color, (sx + 6 * z, chest_y + 15 * z + v_offset), (sx - 4 * z, pelvis_y - 5 * z), vein_w)

        # 3. BULKY SHOULDERS (Massive mutated shoulder pads / pauldrons)
        shoulder_span = int(42 * scale_w)
        left_shoulder = (sx - shoulder_span, chest_y - int(6 * z))
        right_shoulder = (sx + shoulder_span, chest_y - int(6 * z))

        # Main shoulder bar
        pygame.draw.line(surface, muscle_color, left_shoulder, right_shoulder, max(4, int(16 * z)))

        # Mutated shoulder spikes
        spike_len = int(18 * z)
        pygame.draw.line(surface, body_color, left_shoulder, (left_shoulder[0] - spike_len, left_shoulder[1] - spike_len), max(2, int(5 * z)))
        pygame.draw.line(surface, body_color, right_shoulder, (right_shoulder[0] + spike_len, right_shoulder[1] - spike_len), max(2, int(5 * z)))

        # 4. MUTATED CLAW ARMS
        arm_width = max(3, int(7 * z))
        reach = int(48 * scale_w)
        
        # Attack arm posing based on state
        if state_name == "CHARGING":
            # Forward charging tackle posture
            arm_front_x = sx + facing * (reach + 20 * z)
            arm_front_y = chest_y + int(10 * z)
            arm_back_x = sx - facing * (reach - 10 * z)
            arm_back_y = chest_y - int(20 * z)
        elif state_name == "SLAM":
            # Arms raised overhead or crashing down
            arm_front_x = sx + facing * (reach * 0.7)
            arm_front_y = sy - int(20 * scale_h)
            arm_back_x = sx - facing * (reach * 0.3)
            arm_back_y = sy - int(20 * scale_h)
        elif state_name == "WINDUP_SLAM":
            # Raised high overhead preparing to slam
            arm_front_x = sx + int(10 * facing * z)
            arm_front_y = head_y - int(35 * z)
            arm_back_x = sx - int(15 * facing * z)
            arm_back_y = head_y - int(40 * z)
        else:
            # Default heavy idle / swinging walk
            arm_front_x = sx + facing * (reach * 0.8) + (int(sway * 1.5) if facing > 0 else -int(sway * 1.5))
            arm_front_y = chest_y + int(35 * scale_h)
            arm_back_x = sx - facing * (reach * 0.8) - (int(sway * 1.5) if facing > 0 else -int(sway * 1.5))
            arm_back_y = chest_y + int(30 * scale_h)

        # Draw arms
        pygame.draw.line(surface, body_color, (left_shoulder[0], left_shoulder[1]), (arm_back_x, arm_back_y), arm_width)
        pygame.draw.line(surface, body_color, (right_shoulder[0], right_shoulder[1]), (arm_front_x, arm_front_y), arm_width)

        # Claw hands (3 jagged claw lines per hand)
        claw_len = int(12 * z)
        for offset in (-5, 0, 5):
            pygame.draw.line(surface, vein_color, (arm_front_x, arm_front_y), (arm_front_x + facing * claw_len, arm_front_y + offset * z), max(1, int(2 * z)))
            pygame.draw.line(surface, vein_color, (arm_back_x, arm_back_y), (arm_back_x - facing * claw_len, arm_back_y + offset * z), max(1, int(2 * z)))

        # 5. HEAD & GLOWING EYES
        head_center = (sx + int(facing * 4 * z), head_y)
        pygame.draw.circle(surface, body_color, head_center, head_radius)
        pygame.draw.circle(surface, muscle_color, head_center, head_radius, width=max(1, int(2 * z)))

        # Glowing Menacing Eyes
        eye_offset_x = int(facing * (head_radius * 0.45))
        eye_y = head_y - int(head_radius * 0.1)
        eye_size = max(2, int((4.0 + self.eye_pulse * 2.0) * z))
        
        # Primary eye
        pygame.draw.circle(surface, eye_color, (head_center[0] + eye_offset_x, eye_y), eye_size)
        # Secondary inner eye for eerie monstrosity
        pygame.draw.circle(surface, (255, 255, 255), (head_center[0] + eye_offset_x + int(facing * z), eye_y), max(1, eye_size // 2))
