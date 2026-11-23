"""Exercise the real game loop with SDL events and a headless display."""

import ast
import asyncio
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from collections import defaultdict
from unittest.mock import patch

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
        exec(compile(tree, "main.py", "exec"), game)
        game["clock"] = SimpleNamespace(tick=lambda *args: None)
        game["save_high_score"] = lambda *args: False
        controls = game["touch_controls"]
        game["menu_button_rects"] = game["draw_menu"](game["screen"], 0)
        screenshots = Path("build/touch-qa")
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
            yield [touch(game["shop"].rect.center)]
            self.assertTrue(game["show_shop_modal"])
            pos = game["_shop_buy_rects"][1][0].center
            yield [touch(pos), duplicate(pos)]
            self.assertFalse(game["show_shop_modal"])
            self.assertIn("gun", game["weapon_manager"].owned)
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
            yield [pygame.event.Event(pygame.QUIT)]

        steps = script()
        with patch("pygame.event.get", side_effect=lambda: next(steps)), patch(
                "pygame.key.get_pressed", return_value=defaultdict(bool)):
            asyncio.run(game["main"]())
        pygame.quit()


if __name__ == "__main__":
    unittest.main()
