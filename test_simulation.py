import curses
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

from main import draw_header, handle_key, handle_mouse, handle_new_game_key, open_new_game, parse_args
from simulation import (
    START_DATE,
    GameState,
    accept_contract,
    accept_contract_offer,
    advance_game,
    buy_promotion,
    contract_weekly_output,
    cycle_game_update_size,
    estimated_update_weeks,
    game_profit,
    game_total_cost,
    hire_candidate,
    load_game,
    monthly_fixed_cost,
    recommended_team_size,
    refresh_applicants,
    save_game,
    start_project,
    toggle_auto_contracts,
    toggle_game_updates,
)


def advance(state: GameState, weeks: int) -> None:
    for _ in range(weeks):
        state.clock.current_date += timedelta(days=7)
        state.clock.week += 1
        advance_game(state, 1)


class SimulationTests(unittest.TestCase):
    def test_new_studio_starts_today_with_real_overhead(self) -> None:
        state = GameState()

        self.assertEqual(state.clock.current_date, START_DATE)
        self.assertEqual(len(state.studio.team), 1)
        self.assertEqual(len(state.studio.applicants), 6)
        self.assertGreater(monthly_fixed_cost(state.studio), 3_000)

    def test_project_uses_variable_work_and_releases_to_store(self) -> None:
        state = GameState()

        self.assertTrue(start_project(state))
        setup_cash = state.studio.cash
        self.assertGreater(state.studio.current_project.planned_weeks, 8)
        advance(state, 40)

        self.assertIsNone(state.studio.current_project)
        self.assertEqual(state.studio.released_games, 1)
        self.assertGreaterEqual(state.studio.followers, 40)
        self.assertLess(state.studio.cash, setup_cash)

    def test_legacy_campaign_name_can_finish_saved_project(self) -> None:
        state = GameState()
        state.selected_marketing = 4
        self.assertTrue(start_project(state))
        state.studio.current_project.marketing_name = "Campaign"
        state.studio.current_project.work_done = state.studio.current_project.total_work - 1

        advance(state, 1)

        self.assertIsNone(state.studio.current_project)
        self.assertEqual(state.studio.released_games, 1)

    def test_game_profit_includes_development_staff_marketing_and_live_costs(self) -> None:
        state = GameState()
        state.selected_marketing = 2
        self.assertTrue(start_project(state))
        advance(state, 40)
        game = state.studio.catalog[0]

        self.assertTrue(game.cost_history_complete)
        self.assertGreater(game.production_cost, 0)
        self.assertGreater(game.labor_cost, 0)
        self.assertEqual(game.marketing_cost, 4_000)
        self.assertGreater(game.post_launch_cost, 0)
        self.assertEqual(
            game_total_cost(game),
            game.production_cost + game.labor_cost + game.marketing_cost + game.post_launch_cost,
        )
        self.assertEqual(game_profit(game), game.net_revenue - game_total_cost(game))

    def test_released_game_keeps_selling_at_evergreen_floor(self) -> None:
        state = GameState()
        self.assertTrue(start_project(state))
        advance(state, 40)
        game = state.studio.catalog[0]
        sale = next(item for item in state.studio.active_sales if item.game_id == game.game_id)

        advance(state, 30)

        self.assertIn(sale, state.studio.active_sales)
        self.assertGreaterEqual(sale.weekly_units, sale.evergreen_units)
        self.assertGreater(game.units_sold, 0)

    def test_continuous_updates_ship_and_raise_live_game_activity(self) -> None:
        state = GameState()
        self.assertTrue(start_project(state))
        advance(state, 40)
        game = state.studio.catalog[0]
        self.assertTrue(toggle_game_updates(state, game.game_id))

        advance(state, 30)

        self.assertGreaterEqual(game.updates_released, 1)
        self.assertTrue(game.auto_updates)

    def test_update_size_changes_estimated_development_length(self) -> None:
        state = GameState()
        start_project(state)
        advance(state, 40)
        game = state.studio.catalog[0]
        patch_weeks = estimated_update_weeks(state.studio, game)

        cycle_game_update_size(state, game.game_id)
        cycle_game_update_size(state, game.game_id)
        expansion_weeks = estimated_update_weeks(state.studio, game)

        self.assertEqual(game.update_size, "Expansion")
        self.assertGreater(expansion_weeks, patch_weeks * 4)

    def test_rating_controls_hype_decay_and_player_retention(self) -> None:
        low = GameState()
        high = GameState()
        for state in (low, high):
            start_project(state)
            state.studio.current_project.work_done = state.studio.current_project.total_work - 1
            advance(state, 1)
            game = state.studio.catalog[0]
            sale = state.studio.active_sales[0]
            game.hype = 120
            sale.weekly_units = 500
        low.studio.catalog[0].score = low.studio.active_sales[0].score = 25
        high.studio.catalog[0].score = high.studio.active_sales[0].score = 90

        advance(low, 8)
        advance(high, 8)

        self.assertGreater(high.studio.active_sales[0].weekly_units, low.studio.active_sales[0].weekly_units * 3)
        self.assertGreater(high.studio.catalog[0].monthly_players, low.studio.catalog[0].monthly_players * 2)

    def test_pre_release_hype_creates_a_larger_launch_spike(self) -> None:
        organic = GameState()
        hyped = GameState()
        for state, hype in ((organic, 5), (hyped, 180)):
            start_project(state)
            state.studio.current_project.hype = hype
            state.studio.current_project.work_done = state.studio.current_project.total_work - 1
            advance(state, 1)

        self.assertGreater(hyped.studio.active_sales[0].weekly_units, organic.studio.active_sales[0].weekly_units * 3)

    def test_promotion_costs_money_and_builds_project_hype(self) -> None:
        state = GameState()
        state.studio.reputation = 20
        self.assertTrue(start_project(state))
        before_cash = state.studio.cash
        before_hype = state.studio.current_project.hype

        self.assertTrue(buy_promotion(state, 0, 3))
        advance(state, 2)

        self.assertLess(state.studio.cash, before_cash)
        self.assertGreater(state.studio.current_project.hype, before_hype)

    def test_mouse_controls_live_updates_and_promotion(self) -> None:
        state = GameState()
        start_project(state)
        advance(state, 40)
        state.modal = "games"
        game_row = (0, 2, 5, 0, curses.BUTTON1_DOUBLE_CLICKED)
        with patch("main.curses.getmouse", return_value=game_row):
            handle_mouse(state, (38, 120))
        self.assertTrue(state.studio.catalog[0].auto_updates)

        handle_key(state, ord("m"))
        promotion_row = (0, 42, 4, 0, curses.BUTTON1_DOUBLE_CLICKED)
        with patch("main.curses.getmouse", return_value=promotion_row):
            handle_mouse(state, (38, 120))
        self.assertEqual(len(state.studio.active_promotions), 1)

    def test_hiring_changes_team_and_monthly_burn(self) -> None:
        state = GameState()
        old_burn = monthly_fixed_cost(state.studio)
        candidate = state.studio.applicants[0]

        self.assertTrue(hire_candidate(state))
        self.assertIn(candidate, state.studio.team)
        self.assertGreater(monthly_fixed_cost(state.studio), old_burn + candidate.monthly_salary)

    def test_contract_diverts_capacity_then_pays(self) -> None:
        state = GameState()
        self.assertTrue(start_project(state))
        self.assertTrue(accept_contract(state))
        payout = state.studio.contract.payout
        deadline = state.studio.contract.weeks_left
        revenue_before = state.studio.lifetime_revenue

        advance(state, deadline)

        self.assertIsNone(state.studio.contract)
        self.assertGreaterEqual(state.studio.lifetime_revenue, revenue_before + payout)
        self.assertGreater(state.studio.contractor_reputation, 0)

    def test_contract_speed_uses_relevant_team_skill(self) -> None:
        state = GameState()
        state.studio.team[0].code = 20
        low_output = contract_weekly_output(state.studio, "Code")
        state.studio.team[0].code = 95
        high_output = contract_weekly_output(state.studio, "Code")

        self.assertGreater(high_output, low_output * 4)

    def test_auto_contract_toggle_queues_every_eligible_offer(self) -> None:
        state = GameState()
        eligible = sum(job.reputation_required <= state.studio.contractor_reputation for job in state.studio.contract_offers)

        self.assertTrue(toggle_auto_contracts(state))

        self.assertIsNotNone(state.studio.contract)
        self.assertEqual(1 + len(state.studio.contract_queue), eligible)
        self.assertEqual(len(state.studio.contract_offers), 6 - eligible)
        self.assertFalse(toggle_auto_contracts(state))
        self.assertEqual(len(state.studio.contract_queue), 0)
        self.assertIsNotNone(state.studio.contract)

    def test_disabling_auto_preserves_manually_queued_job(self) -> None:
        state = GameState()
        self.assertTrue(accept_contract(state))
        eligible_index = next(index for index, job in enumerate(state.studio.contract_offers) if job.reputation_required <= state.studio.contractor_reputation)
        self.assertTrue(accept_contract_offer(state, eligible_index))
        manual_id = state.studio.contract_queue[0].contract_id

        toggle_auto_contracts(state)
        toggle_auto_contracts(state)

        self.assertEqual([job.contract_id for job in state.studio.contract_queue], [manual_id])

    def test_auto_off_save_clears_untagged_legacy_queue(self) -> None:
        state = GameState()
        toggle_auto_contracts(state)
        state.studio.auto_contracts = False
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy-auto-queue.json"
            state.save_path = str(path)
            save_game(state)
            data = json.loads(path.read_text(encoding="utf-8"))
            for contract in data["studio"]["contract_queue"]:
                contract.pop("auto_accepted", None)
            path.write_text(json.dumps(data), encoding="utf-8")
            loaded = load_game(str(path))

        self.assertFalse(loaded.studio.auto_contracts)
        self.assertEqual(loaded.studio.contract_queue, [])
        self.assertIn("Removed", loaded.logs[0])

    def test_active_contract_does_not_replace_week_progress_bar(self) -> None:
        state = GameState()
        self.assertTrue(accept_contract(state))
        state.studio.contract.work_done = state.studio.contract.required_work * 0.4
        screen = MagicMock()
        screen.getmaxyx.return_value = (36, 120)

        with patch("main.curses.color_pair", return_value=0):
            draw_header(screen, state, 120)

        status_line = screen.addstr.call_args_list[1].args[2]
        self.assertIn("Next week [", status_line)
        self.assertIn("░", status_line)
        self.assertIn("JOB", status_line)

    def test_version_two_save_round_trip(self) -> None:
        state = GameState()
        start_project(state)
        advance(state, 3)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "save.json"
            state.save_path = str(path)
            save_game(state)
            loaded = load_game(str(path))

        self.assertEqual(loaded.clock.current_date, state.clock.current_date)
        self.assertEqual(loaded.studio.cash, state.studio.cash)
        self.assertEqual(loaded.studio.current_project.work_done, state.studio.current_project.work_done)
        self.assertEqual(len(loaded.studio.applicants), 6)
        self.assertEqual(len(loaded.studio.contract_offers), len(state.studio.contract_offers))

    def test_accounting_preserves_expense_categories(self) -> None:
        state = GameState()
        self.assertTrue(start_project(state))

        advance(state, 4)

        self.assertTrue(state.studio.ledger)
        self.assertIn("Development", state.studio.ledger[0].categories)
        self.assertIn("Payroll", state.studio.period_expense_categories)

    def test_reach_expands_staffing_target_and_applicant_pool(self) -> None:
        state = GameState()
        state.studio.followers = 1_250
        state.studio.released_games = 6
        state.studio.reputation = 18

        refresh_applicants(state)

        self.assertGreater(recommended_team_size(state.studio), 1)
        self.assertGreater(len(state.studio.applicants), 6)

    def test_positional_save_path_implies_loading(self) -> None:
        direct = parse_args(["studio.json"])
        after_load = parse_args(["--load", "studio.json"])
        explicit = parse_args(["--load", "--save-file", "studio.json"])

        self.assertTrue(direct.load)
        self.assertTrue(after_load.load)
        self.assertTrue(explicit.load)
        self.assertEqual(direct.save_path, "studio.json")
        self.assertEqual(after_load.save_path, "studio.json")
        self.assertEqual(explicit.save_path, "studio.json")

    def test_mouse_opens_and_switches_analysis(self) -> None:
        state = GameState()
        click = (0, 2, 4, 0, curses.BUTTON1_CLICKED)
        with patch("main.curses.getmouse", return_value=click):
            handle_mouse(state, (36, 120))
        self.assertEqual(state.modal, "analysis")

        second_tab = (0, 40, 4, 0, curses.BUTTON1_CLICKED)
        with patch("main.curses.getmouse", return_value=second_tab):
            handle_mouse(state, (36, 120))
        self.assertEqual(state.analysis_view, 1)

    def test_footer_mouse_can_start_and_choose_a_new_game(self) -> None:
        state = GameState()
        new_button = (0, 2, 35, 0, curses.BUTTON1_CLICKED)
        with patch("main.curses.getmouse", return_value=new_button):
            handle_mouse(state, (36, 120))
        self.assertEqual(state.modal, "new_game")
        self.assertEqual(state.new_game_step, -1)

        choose_button = (0, 9, 35, 0, curses.BUTTON1_CLICKED)
        with patch("main.curses.getmouse", return_value=choose_button):
            handle_mouse(state, (36, 120))
        self.assertEqual(state.new_game_step, 0)

    def test_mouse_can_open_board_and_accept_a_single_contract(self) -> None:
        state = GameState()
        jobs_button = (0, 8, 35, 0, curses.BUTTON1_CLICKED)
        with patch("main.curses.getmouse", return_value=jobs_button):
            handle_mouse(state, (36, 120))
        self.assertEqual(state.modal, "contracts")

        first_job = (0, 2, 4, 0, curses.BUTTON1_DOUBLE_CLICKED)
        with patch("main.curses.getmouse", return_value=first_job):
            handle_mouse(state, (36, 120))
        self.assertIsNotNone(state.studio.contract)
        self.assertEqual(len(state.studio.contract_offers), 5)

    def test_custom_title_and_sequel_lineage_are_persistent(self) -> None:
        state = GameState()
        state.modal = "new_game"
        handle_new_game_key(state, ord("t"))
        for character in "My First Commercial Game":
            handle_key(state, ord(character))
        handle_key(state, 10)
        self.assertTrue(start_project(state))
        advance(state, 40)

        original = state.studio.catalog[0]
        self.assertEqual(original.title, "My First Commercial Game")
        self.assertGreater(state.studio.genre_fans[original.genre], 0)

        open_new_game(state)
        self.assertEqual(state.new_game_step, -1)
        handle_new_game_key(state, curses.KEY_DOWN)
        handle_new_game_key(state, 10)
        self.assertIn("II", state.draft_title)
        self.assertTrue(start_project(state))
        self.assertEqual(state.studio.current_project.sequel_of, original.game_id)
        self.assertEqual(state.studio.current_project.generation, 2)
        with tempfile.TemporaryDirectory() as directory:
            state.save_path = str(Path(directory) / "franchise.json")
            save_game(state)
            loaded = load_game(state.save_path)
        self.assertEqual(loaded.studio.catalog[0].title, "My First Commercial Game")
        self.assertEqual(loaded.studio.current_project.sequel_of, original.game_id)

    def test_old_settled_release_is_recovered_for_sequels(self) -> None:
        state = GameState()
        state.studio.released_games = 1
        state.logs = [
            "Music: Visual Novel settled at 1,573 units and $14,403 studio net.",
            "Delivered the prototype for a local agency; client paid $10,000.",
            "Delivered the UI implementation contract; client paid $12,000.",
        ]
        with tempfile.TemporaryDirectory() as directory:
            state.save_path = str(Path(directory) / "old-v2.json")
            save_game(state)
            loaded = load_game(state.save_path)

        self.assertEqual(len(loaded.studio.catalog), 1)
        self.assertEqual(loaded.studio.catalog[0].title, "Music: Visual Novel")
        self.assertEqual(loaded.studio.catalog[0].units_sold, 1_573)
        self.assertEqual(loaded.studio.contracts_completed, 2)
        self.assertEqual(loaded.studio.contractor_reputation, 3.0)

    def test_legacy_save_migrates_to_current_date(self) -> None:
        legacy = {
            "clock": {"current_date": "1976-01-08", "week": 2},
            "studio": {"cash": 10_000, "fans": 12, "reputation": 3, "released_games": 1},
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy.json"
            path.write_text(json.dumps(legacy), encoding="utf-8")
            loaded = load_game(str(path))

        self.assertEqual(loaded.clock.current_date, date.today())
        self.assertEqual(loaded.studio.cash, 30_000)
        self.assertEqual(loaded.studio.followers, 52)
        self.assertIn("Migrated", loaded.logs[0])


if __name__ == "__main__":
    unittest.main()
