import json
import tempfile
import unittest
from pathlib import Path

from browser import BrowserGame


class BrowserTests(unittest.TestCase):
    def test_analysis_uses_simulation_figures(self):
        import simulation as sim
        from dataclasses import asdict
        game = BrowserGame('unused.json')
        game.action({'action': 'new'})
        for _ in range(12):
            game.action({'action': 'advance', 'week': True})
        view = game.view()
        self.assertEqual(view['market_chart'], [asdict(x) for x in sim.market_chart(game.state, 30)])
        self.assertTrue(view['market_chart'])
        self.assertEqual(sum(view['cost_breakdown'].values()), view['monthly_cost'])
        self.assertTrue(view['studio']['ledger'])

    def test_design_commit_preserves_manual_pause(self):
        game = BrowserGame('unused.json')
        game.action({'action': 'new'})
        game.action({'action': 'idea', 'index': 0})
        game.action({'action': 'design'})
        game.action({'action': 'pause'})
        game.action({'action': 'commit'})
        self.assertEqual(game.state.studio.current_project.stage, 'development')
        self.assertEqual(game.state.time_speed_index, 0)

    def test_continuous_clock_and_popup_pause(self):
        game = BrowserGame('unused.json')
        game.action({'action': 'new'})
        start = game.last_tick
        game.tick(start + .5)
        progress = game.state.clock.elapsed_seconds
        self.assertGreater(progress, 0)
        game.action({'action': 'overlay', 'open': True})
        game.tick(start + 1)
        self.assertEqual(progress, game.state.clock.elapsed_seconds)
        self.assertEqual(game.state.time_speed_index, 1)
        game.action({'action': 'overlay', 'open': False})
        game.tick(start + 1.5)
        self.assertGreater(game.state.clock.elapsed_seconds, progress)
        game.action({'action': 'pause'})
        progress = game.state.clock.elapsed_seconds
        game.action({'action': 'overlay', 'open': True})
        game.action({'action': 'overlay', 'open': False})
        game.tick(start + 2)
        self.assertEqual(game.state.time_speed_index, 0)
        self.assertEqual(progress, game.state.clock.elapsed_seconds)

    def test_clock_holds_without_browser_but_runs_during_design(self):
        game = BrowserGame('unused.json')
        game.action({'action': 'new'})
        game.last_contact -= 10
        game.tick(game.last_tick + .5)
        self.assertEqual(game.state.clock.elapsed_seconds, 0)
        self.assertEqual(game.hold_reason(), 'Browser disconnected')
        game.last_contact = game.last_tick
        game.action({'action': 'idea', 'index': 0})
        game.action({'action': 'design'})
        self.assertEqual(game.state.time_speed_index, 1)
        for speed in (1, 2, 3):
            game.action({'action': 'speed', 'index': speed})
            before = (game.state.clock.day, game.state.clock.elapsed_seconds)
            game.tick(game.last_tick + .5)
            self.assertNotEqual(before, (game.state.clock.day, game.state.clock.elapsed_seconds))
            self.assertEqual(game.hold_reason(), '')
            self.assertEqual(game.state.studio.current_project.stage, 'design')

    def test_browser_pipeline_and_save(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'studio.json'
            game = BrowserGame(path)
            self.assertFalse(game.view()['started'])
            game.action({'action': 'new'})
            game.action({'action': 'idea', 'index': 0})
            game.action({'action': 'experiment', 'index': 0})
            for _ in range(3):
                game.action({'action': 'advance', 'week': True})
            self.assertTrue(game.state.studio.current_project.gdd['findings'])
            game.action({'action': 'design'})
            before = game.state.clock.current_date
            game.action({'action': 'advance'})
            self.assertGreater(game.state.clock.current_date, before)
            game.action({'action': 'commit'})
            self.assertEqual(game.state.studio.current_project.stage, 'development')
            game.action({'action': 'save'})
            loaded = BrowserGame(path)
            loaded.action({'action': 'load'})
            self.assertEqual(loaded.state.studio.current_project.title, game.state.studio.current_project.title)
            json.dumps(loaded.view())

    def test_invalid_actions(self):
        game = BrowserGame('unused.json')
        with self.assertRaises(ValueError):
            game.action({'action': 'commit'})
        game.action({'action': 'new'})
        with self.assertRaises(ValueError):
            game.action({'action': 'hire', 'index': -1})
        with self.assertRaises(ValueError):
            game.action({'action': 'unknown'})


if __name__ == '__main__':
    unittest.main()
