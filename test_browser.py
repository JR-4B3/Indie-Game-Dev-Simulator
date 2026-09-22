import json
import tempfile
import unittest
from pathlib import Path

from browser import BrowserGame


class BrowserTests(unittest.TestCase):
    def test_release_management_and_sales_view(self):
        import simulation as sim
        game = BrowserGame('unused.json')
        game.action({'action': 'new'})
        studio = game.state.studio
        studio.cash = 1_000_000
        studio.completed_research = [node['key'] for node in sim.RESEARCH_NODES]
        released = sim.ReleasedGame(1, 'Test release', 'Adventure', 'Space', 'Steam', 75, '2026-09-06', net_revenue=20000, production_cost=10000)
        studio.catalog.append(released)
        studio.active_sales.append(sim.ActiveSale(released.title, 'Steam', 75, 9.99, .3, .05, 400, 30, game_id=1, week_units=125))
        view = game.view()['studio']['catalog'][0]
        self.assertEqual(view['weekly_units'], 400)
        self.assertEqual(view['week_to_date'], 125)
        self.assertEqual(view['profit'], sim.game_profit(released))
        game.action({'action': 'release_update', 'index': 0, 'size': 'Hotfix', 'focus': 'Bug fixes'})
        self.assertIsNotNone(studio.active_update)
        self.assertEqual(studio.active_update.size, 'Hotfix')
        self.assertEqual(studio.active_update.game_id, 1)
        game.action({'action': 'marketing', 'index': 0, 'game_id': 1})
        self.assertEqual(studio.active_promotions[0].game_id, 1)
        game.action({'action': 'community', 'index': 0, 'game_id': 1})
        self.assertEqual(studio.active_community_actions[0]['game_id'], 1)
        before = released.support_level
        game.action({'action': 'support', 'index': 0})
        self.assertNotEqual(before, released.support_level)
        before = released.price
        game.action({'action': 'price', 'index': 0, 'delta': -1})
        self.assertNotEqual(before, released.price)
        for payload in ({'action': 'marketing', 'game_id': 999}, {'action': 'marketing', 'game_id': 1, 'index': 999}, {'action': 'release_update', 'size': 'bad', 'focus': 'Bug fixes'}, {'action': 'price', 'delta': 4}):
            with self.assertRaises(ValueError):
                game.action(payload)

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
            project_view = game.view()['studio']['current_project']
            self.assertEqual(project_view['phase'], game.state.studio.current_project.phase)
            self.assertEqual(project_view['progress'], game.state.studio.current_project.progress)
            self.assertGreater(project_view['weekly_output'], 0)
            self.assertGreater(project_view['remaining_work'], 0)
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
