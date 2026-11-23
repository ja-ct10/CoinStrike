"""Exercise the real game loop with SDL events and a headless display."""

import ast
import asyncio
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
import time
from collections import defaultdict
from unittest.mock import patch, Mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame


class GameTouchFlowTests(unittest.TestCase):
    def test_menus_purchase_gameplay_restart_and_keyboard(self):
        # Load the real module without its unconditional asyncio.run(main()).
        tree = ast.parse(Path("main.py").read_text(encoding="utf-8"), "main.py")
        self.assertIsInstance(tree.body[-1], ast.Expr)
        self.assertEqual(ast.unparse(tree.body[-1]), "asyncio.run(main())")
        tree.body.pop()
        game = {"__name__": "coinstrike_test", "__file__": str(Path("main.py").resolve())}
        calls = []
        pre_init, init = pygame.mixer.pre_init, pygame.init

        def mixer_defaults(*args):
            calls.append(("pre_init", args))
            return pre_init(*args)

        def initialize():
            calls.append(("init", ()))
            return init()

        with patch("pygame.mixer.pre_init", side_effect=mixer_defaults), patch("pygame.init", side_effect=initialize):
            exec(compile(tree, "main.py", "exec"), game)
        self.assertEqual(calls[:2], [("pre_init", (44100, -16, 2, 2048)), ("init", ())])
        game["music_channel"] = Mock()
        with patch("pygame.image.load") as load, patch("pygame.transform.scale") as scale:
            first = game["Player"](20, 200)
            second = game["Player"](40, 200)
        load.assert_not_called()
        scale.assert_not_called()
        self.assertIs(first.idle_right, second.idle_right)
        self.assertIs(first.hold_run_left["gun"], second.hold_run_left["gun"])
        first.rect.x = 99
        first.vel_y = -15
        self.assertEqual(second.rect.x, 40)
        self.assertEqual(second.vel_y, 0)
        started = time.perf_counter()
        game["reset_game"]()
        print(f"Warm reset: {(time.perf_counter() - started) * 1000:.1f} ms")
        game["clock"] = SimpleNamespace(tick=lambda *args: None)
        game["save_high_score"] = lambda *args: False
        controls = game["touch_controls"]
        game["menu_button_rects"] = game["draw_menu"](game["screen"], 0)
        screenshots = Path("build/touch-qa/compact")
        screenshots.mkdir(parents=True, exist_ok=True)

        def touch(pos, kind=pygame.FINGERDOWN, finger=100):
            return pygame.event.Event(kind, touch_id=1, finger_id=finger,
                                      x=pos[0] / 1024, y=pos[1] / 576)

        def duplicate(pos):
            return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, touch=True, pos=pos)

        def key(value):
            return pygame.event.Event(pygame.KEYDOWN, key=value)

        def script():
            yield []
            yield [touch(game["menu_button_rects"][1].center)]
            self.assertTrue(game["show_options_modal"])
            self.assertTrue(controls.enabled)
            pos = game["_options_toggle_rect"].center
            yield [touch(pos), duplicate(pos)]
            self.assertFalse(controls.enabled)
            yield [touch(pos)]
            self.assertTrue(controls.enabled)
            pygame.image.save(game["screen"], screenshots / "options.png")
            yield [touch(game["_options_close_rect"].center)]
            yield [touch(game["menu_button_rects"][0].center)]
            self.assertEqual(game["game_state"], game["PLAYING"])
            self.assertEqual(set(controls.rects), {pygame.K_LEFT, pygame.K_RIGHT, pygame.K_SPACE})
            pygame.image.save(game["screen"], screenshots / "no-weapons.png")
            yield [touch(game["shop"].rect.center)]
            self.assertTrue(game["show_shop_modal"])
            pos = game["_shop_buy_rects"][1][0].center
            yield [touch(pos), duplicate(pos)]
            self.assertFalse(game["show_shop_modal"])
            self.assertIn("gun", game["weapon_manager"].owned)
            self.assertIn(pygame.K_f, controls.rects)
            self.assertNotIn(pygame.K_t, controls.rects)
            pygame.image.save(game["screen"], screenshots / "gun.png")
            self.assertEqual(game["player"].coins_collected, 0)
            game["player"].on_ground = True
            start_x = game["player"].world_x
            yield [touch(controls.rects[pygame.K_RIGHT].center, finger=1),
                   touch(controls.rects[pygame.K_SPACE].center, finger=2),
                   touch(controls.rects[pygame.K_f].center, finger=3)]
            self.assertEqual(game["player"].world_x, start_x + 5)
            self.assertLess(game["player"].vel_y, 0)
            ammo = game["weapon_manager"].ammo["gun"]
            yield [touch(controls.rects[pygame.K_f].center, pygame.FINGERUP, 3)]
            self.assertEqual(game["player"].world_x, start_x + 10)
            self.assertEqual(game["weapon_manager"].ammo["gun"], ammo)
            controls.resize(693, 390)
            pygame.image.save(game["screen"], screenshots / "gameplay.png")
            frames, position = game["game_frames"], game["player"].world_x
            controls.portrait_blocked = True
            yield [key(pygame.K_f), touch(controls.rects[pygame.K_RIGHT].center, finger=90)]
            self.assertEqual(game["game_frames"], frames)
            self.assertEqual(game["player"].world_x, position)
            self.assertEqual(game["weapon_manager"].ammo["gun"], ammo)
            self.assertFalse(controls.pointers)
            game["game_state"], game["boss_intro_timer"] = game["BOSS_INTRO"], 7
            yield []
            self.assertEqual(game["boss_intro_timer"], 7)
            game["game_state"] = game["PLAYING"]
            game["show_shop_modal"] = True
            controls.portrait_blocked = False
            yield []
            self.assertTrue(game["show_shop_modal"])
            self.assertEqual(game["game_frames"], frames)
            game["show_shop_modal"] = False
            yield [touch(game["settings_icon"].rect.center)]
            self.assertTrue(game["show_settings_modal"])
            self.assertFalse(controls.pointers)
            yield [touch(game["_settings_btn_rects"][2].center)]
            self.assertTrue(game["show_options_modal"])
            yield [touch(game["_options_close_rect"].center)]
            yield [touch(game["_settings_btn_rects"][0].center)]
            self.assertFalse(game["show_settings_modal"])
            game["game_state"] = game["GAME_OVER"]
            game["health"].game_over = True
            yield []
            pos = game["_game_over_yes_rect"].center
            yield [touch(pos), duplicate(pos)]
            self.assertEqual(game["game_state"], game["PLAYING"])
            self.assertFalse(game["health"].game_over)
            self.assertFalse(controls.pointers)
            self.assertTrue(controls.enabled)
            self.assertNotIn(pygame.K_f, controls.rects)
            self.assertNotIn(pygame.K_t, controls.rects)
            game["game_state"] = game["MISSION_COMPLETE"]
            yield []
            yield [touch(game["_mission_complete_restart_rect"].center)]
            self.assertEqual(game["game_state"], game["PLAYING"])
            game["game_state"] = game["MENU"]
            yield []
            yield [key(pygame.K_RETURN)]
            self.assertEqual(game["game_state"], game["PLAYING"])
            yield [key(pygame.K_ESCAPE)]
            self.assertTrue(game["show_settings_modal"])
            yield [key(pygame.K_ESCAPE)]
            self.assertFalse(game["show_settings_modal"])
            yield [key(pygame.K_b)]
            self.assertTrue(game["show_shop_modal"])
            yield [key(pygame.K_ESCAPE)]
            self.assertFalse(game["show_shop_modal"])
            controls.resize(320, 180)
            yield []
            pygame.image.save(game["screen"], screenshots / "small-phone.png")
            for name, weapons in (("spear", ["spear"]), ("grenade", ["grenade"]),
                                  ("gun-spear", ["gun", "spear"]),
                                  ("all-weapons", ["gun", "spear", "grenade"])):
                game["weapon_manager"].owned.clear()
                game["weapon_manager"].ammo.clear()
                for weapon in weapons:
                    game["weapon_manager"].grant(weapon)
                yield []
                pygame.image.save(game["screen"], screenshots / (name + ".png"))
            yield [pygame.event.Event(pygame.QUIT)]

        steps = script()
        with patch("pygame.event.get", side_effect=lambda: next(steps)), patch(
                "pygame.key.get_pressed", return_value=defaultdict(bool)):
            asyncio.run(game["main"]())
        channel = game["music_channel"]
        channel.play.assert_called_once_with(game["bg_music"], loops=-1)
        channel.stop.assert_not_called()
        channel.unpause.assert_not_called()
        game["_pause_music"]()
        game["_pause_music"]()
        game["_resume_music"]()
        game["_resume_music"]()
        channel.pause.assert_called_once()
        channel.unpause.assert_called_once()
        self.assertEqual(channel.play.call_count, 1)
        pygame.quit()


if __name__ == "__main__":
    unittest.main()
