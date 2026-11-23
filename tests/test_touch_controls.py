import json
import os
import unittest
from collections import defaultdict
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
from player import Player
from settings import SCREEN_WIDTH, SCREEN_HEIGHT
from touch_controls import TouchControls, pointer_click
from weapon import WeaponManager, GUN_MAX_AMMO


class TouchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.controls = TouchControls()
        self.controls.set_active(True)
        self.keyboard = defaultdict(bool)

    def finger(self, kind, key, finger=1, touch=1, pos=None):
        x, y = pos or self.controls.rects[key].center
        return pygame.event.Event(kind, touch_id=touch, finger_id=finger,
                                  x=x / SCREEN_WIDTH, y=y / SCREEN_HEIGHT)

    def press(self, key, finger=1):
        return self.controls.handle_event(self.finger(pygame.FINGERDOWN, key, finger))

    def release(self, key, finger=1):
        return self.controls.handle_event(self.finger(pygame.FINGERUP, key, finger))

    def keys(self):
        return self.controls.keys(self.keyboard)

    def test_three_simultaneous_inputs_release_independently(self):
        for finger, key in enumerate((pygame.K_RIGHT, pygame.K_SPACE, pygame.K_f)):
            self.assertEqual(self.press(key, finger), (True, key))
        self.assertTrue(self.keys()[pygame.K_RIGHT])
        self.assertTrue(self.keys()[pygame.K_SPACE])
        self.assertTrue(self.keys()[pygame.K_f])
        self.release(pygame.K_f, 2)
        self.assertFalse(self.keys()[pygame.K_f])
        self.assertTrue(self.keys()[pygame.K_RIGHT])
        self.release(pygame.K_RIGHT, 0)
        self.assertFalse(self.keys()[pygame.K_RIGHT])

    def test_two_fingers_on_one_button(self):
        self.press(pygame.K_LEFT, 1)
        self.press(pygame.K_LEFT, 2)
        self.release(pygame.K_LEFT, 1)
        self.assertTrue(self.keys()[pygame.K_LEFT])
        self.release(pygame.K_LEFT, 2)
        self.assertFalse(self.keys()[pygame.K_LEFT])

    def test_short_jump_tap_is_consumed_once(self):
        self.press(pygame.K_SPACE)
        self.release(pygame.K_SPACE)
        self.assertTrue(self.keys()[pygame.K_SPACE])
        self.assertFalse(self.keys()[pygame.K_SPACE])

    def test_release_does_not_cancel_physical_key(self):
        self.keyboard[pygame.K_RIGHT] = True
        self.press(pygame.K_RIGHT)
        self.release(pygame.K_RIGHT)
        self.assertTrue(self.keys()[pygame.K_RIGHT])

    def test_drag_out_and_release_outside(self):
        self.press(pygame.K_RIGHT)
        self.controls.handle_event(self.finger(pygame.FINGERMOTION, pygame.K_RIGHT, pos=(500, 200)))
        self.assertFalse(self.keys()[pygame.K_RIGHT])
        self.press(pygame.K_f)
        self.controls.handle_event(self.finger(pygame.FINGERUP, pygame.K_f, pos=(1200, 600)))
        self.assertFalse(self.keys()[pygame.K_f])

    def test_pause_focus_resize_and_disable_clear_holds(self):
        for kind in (pygame.WINDOWFOCUSLOST, pygame.WINDOWMINIMIZED, pygame.WINDOWRESIZED):
            self.press(pygame.K_f)
            self.controls.handle_event(pygame.event.Event(kind))
            self.assertFalse(self.keys()[pygame.K_f])
        self.press(pygame.K_RIGHT)
        self.controls.set_active(False)
        self.controls.set_active(True)
        self.assertFalse(self.keys()[pygame.K_RIGHT])
        self.press(pygame.K_RIGHT)
        self.controls.toggle()
        self.assertFalse(self.keys()[pygame.K_RIGHT])
        self.press(pygame.K_RIGHT)
        self.assertFalse(self.controls.enabled)

    def test_touch_click_deduplicates_synthetic_mouse(self):
        event = self.finger(pygame.FINGERDOWN, pygame.K_f)
        self.assertEqual(pointer_click(event), self.controls.rects[pygame.K_f].center)
        mouse = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(10, 20), touch=True)
        self.assertIsNone(pointer_click(mouse))
        self.assertEqual(self.controls.handle_event(mouse), (False, None))
        mouse.touch = False
        self.assertEqual(pointer_click(mouse), (10, 20))

    def test_mouse_controller_and_release(self):
        self.controls.toggle()
        pos = self.controls.rects[pygame.K_f].center
        self.controls.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))
        self.assertTrue(self.keys()[pygame.K_f])
        self.controls.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=pos))
        self.assertFalse(self.keys()[pygame.K_f])

    def test_mobile_layout_has_large_nonoverlapping_targets(self):
        for width, height in ((320, 180), (390, 219), (640, 360), (693, 390), (1024, 576)):
            self.controls.resize(width, height)
            scale = width / SCREEN_WIDTH
            for key, rect in self.controls.rects.items():
                self.assertGreaterEqual(rect.width * scale, 44)
                self.assertTrue(pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT).contains(rect))
                for other, other_rect in self.controls.rects.items():
                    if key != other:
                        self.assertFalse(rect.colliderect(other_rect))
            ammo = pygame.Rect((SCREEN_WIDTH - 256) // 2, SCREEN_HEIGHT - 62, 256, 52)
            self.assertFalse(any(ammo.colliderect(r) for r in self.controls.rects.values()))

    def test_browser_detects_touch_and_cancels_without_changing_manual_choice(self):
        data = dict(touch=True, reset=0, width=693, height=390, left=0, right=0, bottom=0)
        bridge = SimpleNamespace(snapshot=json.dumps(data))
        with patch("touch_controls.IS_WEB", True), patch("platform.window", SimpleNamespace(coinstrikeTouch=bridge), create=True):
            self.controls.sync_browser()
            self.assertTrue(self.controls.enabled)
            self.press(pygame.K_RIGHT)
            data["reset"] = 1
            bridge.snapshot = json.dumps(data)
            self.controls.sync_browser()
            self.assertFalse(self.keys()[pygame.K_RIGHT])
            self.controls.toggle()
            data["reset"] = 2
            bridge.snapshot = json.dumps(data)
            self.controls.sync_browser()
            self.assertFalse(self.controls.enabled)

    def test_safe_area_insets_keep_controls_and_ammo_above_home_indicator(self):
        self.controls.resize(693, 390, safe_left=20, safe_right=20, safe_bottom=21)
        scale = 693 / SCREEN_WIDTH
        self.assertGreaterEqual(self.controls.rects[pygame.K_LEFT].left * scale, 28)
        self.assertGreaterEqual((SCREEN_WIDTH - self.controls.rects[pygame.K_t].right) * scale, 28)
        self.assertGreaterEqual(self.controls.bottom_margin * scale, 29)

    def player(self):
        player = Player.__new__(Player)
        player.rect = pygame.Rect(100, 100, 70, 80)
        player.world_x, player.speed, player.speed_multiplier = 100.0, 5, 1.0
        player.facing_right, player.on_ground = True, True
        player.vel_y, player.gravity, player.jump_power = 0, 0.8, -15
        player.idle_right = player.idle_left = pygame.Surface((1, 1))
        player.run_right = player.run_left = pygame.Surface((1, 1))
        return player

    def test_player_reuses_physics_for_touch_and_keyboard(self):
        player = self.player()
        self.press(pygame.K_RIGHT)
        self.press(pygame.K_SPACE, 2)
        player.update([], [], controls=self.keys())
        self.assertEqual(player.world_x, 105)
        self.assertAlmostEqual(player.vel_y, -14.2)
        self.release(pygame.K_RIGHT)
        player.update([], [], controls=self.keys())
        self.assertEqual(player.world_x, 105)
        self.keyboard[pygame.K_a] = True
        with patch("pygame.key.get_pressed", return_value=self.keyboard):
            player.update([], [])
        self.assertEqual(player.world_x, 100)

    def test_held_attack_uses_existing_cooldown_and_stops_on_release(self):
        manager, player = WeaponManager(), self.player()
        manager.grant("gun")
        _, initial = self.press(pygame.K_f)
        manager.handle_keydown(initial, player)
        self.release(pygame.K_f)
        # A down/up tap before the next update still fires once.
        self.assertEqual(manager.ammo["gun"], GUN_MAX_AMMO - 1)
        self.press(pygame.K_f)
        for _ in range(46):
            if self.keys()[pygame.K_f]:
                manager.handle_keydown(pygame.K_f, player)
            manager.update([], [])
        self.assertEqual(manager.ammo["gun"], GUN_MAX_AMMO - 4)
        self.release(pygame.K_f)
        remaining = manager.ammo["gun"]
        for _ in range(30):
            if self.keys()[pygame.K_f]:
                manager.handle_keydown(pygame.K_f, player)
            manager.update([], [])
        self.assertEqual(manager.ammo["gun"], remaining)

    def test_throw_priority_cooldown_and_ammo_depletion(self):
        manager, player = WeaponManager(), self.player()
        manager.grant("spear")
        manager.grant("grenade")
        manager.ammo["grenade"] = 1
        manager.handle_keydown(pygame.K_t, player)
        self.assertEqual(len(manager.grenades), 1)
        self.assertNotIn("grenade", manager.owned)
        manager.handle_keydown(pygame.K_t, player)
        self.assertEqual(len(manager.spears), 0)
        manager._throw_cooldown = 0
        manager.handle_keydown(pygame.K_t, player)
        self.assertEqual(len(manager.spears), 1)
        manager.grant("gun")
        manager.ammo["gun"] = 1
        manager.handle_keydown(pygame.K_f, player)
        manager._gun_cooldown = 0
        manager.handle_keydown(pygame.K_f, player)
        self.assertEqual(manager.ammo["gun"], 0)
        self.assertEqual(len(manager.bullets), 1)


if __name__ == "__main__":
    unittest.main()
