import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from sim_core.market import COHORTS, MacroSnapshot, ProductOffer, allocate_weekly_demand
from simulation import (
    MONETIZATION_MODELS,
    PRICE_POINTS,
    GameState,
    advance_game,
    cycle_game_price,
    launch_early_access,
    load_game,
    process_sales,
    release_ready_project,
    save_game,
    start_project,
    state_from_data,
    state_to_data,
    take_community_action,
)


def advance(state: GameState, weeks: int = 1) -> None:
    for _ in range(weeks):
        state.clock.current_date += timedelta(days=7)
        state.clock.week += 1
        advance_game(state, 1)


def release_game(state: GameState):
    assert start_project(state)
    state.studio.current_project.work_done = state.studio.current_project.total_work - 1
    advance(state)
    return state.studio.catalog[-1]


class Version10Tests(unittest.TestCase):
    def test_finite_market_conserves_shoppers_and_ownership(self) -> None:
        awareness = {cohort.key: 0.8 for cohort in COHORTS}
        common = {
            "genre": "Action",
            "quality": 80,
            "user_rating": 80,
            "awareness_by_cohort": awareness,
            "store_reach": 1.0,
        }
        low = ProductOffer(product_id="low", price=29.99, **common)
        high = ProductOffer(product_id="high", price=69.99, **common)
        results = allocate_weekly_demand([low, high], MacroSnapshot(), 123)

        self.assertGreater(results[0].units, results[1].units)
        for cohort in COHORTS:
            allocated = sum(result.units_by_cohort[cohort.key] for result in results)
            shopper_pool = int(cohort.population * cohort.weekly_purchase_propensity)
            self.assertLessEqual(allocated, shopper_pool)

        owned = ProductOffer(
            product_id="owned",
            price=29.99,
            owners_by_cohort={cohort.key: cohort.population for cohort in COHORTS},
            **common,
        )
        self.assertEqual(allocate_weekly_demand([owned], MacroSnapshot(), 123)[0].units, 0)

    def test_campaigns_have_unique_seeds_and_legacy_saves_are_rejected(self) -> None:
        first = GameState.new_campaign()
        second = GameState.new_campaign()
        self.assertNotEqual(first.studio.seed, second.studio.seed)
        self.assertEqual(GameState().studio.seed, GameState().studio.seed)

        legacy = state_to_data(first)
        legacy["version"] = 9
        with self.assertRaisesRegex(ValueError, "Legacy save version"):
            state_from_data(legacy, "legacy.json")

    def test_atomic_save_round_trip_preserves_version_10_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "campaign.json"
            state = GameState.new_campaign(save_path=str(path))
            state.selected_monetization = 2
            state.selected_price = 6
            save_game(state)
            state.studio.cash = 12_345
            save_game(state)
            loaded = load_game(str(path))

            self.assertEqual(loaded.studio.seed, state.studio.seed)
            self.assertEqual(loaded.studio.cash, 12_345)
            self.assertEqual(loaded.selected_monetization, 2)
            self.assertEqual(loaded.selected_price, 6)
            self.assertTrue(path.with_suffix(".json.bak").exists())

    def test_greenlight_captures_commercial_and_release_strategy(self) -> None:
        state = GameState()
        state.studio.cash = 1_000_000
        state.studio.completed_research.append("paid_dlc")
        state.selected_monetization = next(index for index, model in enumerate(MONETIZATION_MODELS) if model["key"] == "premium_dlc")
        state.selected_price = next(index for index, point in enumerate(PRICE_POINTS) if point["price"] == 39.99)
        state.selected_announcement = 2
        state.selected_release_policy = 1

        self.assertTrue(start_project(state))
        project = state.studio.current_project
        self.assertEqual(project.monetization, "premium_dlc")
        self.assertEqual(project.price, 39.99)
        self.assertEqual(project.announcement_strategy, "open_development")
        self.assertEqual(project.release_policy, "manual_window")
        self.assertGreaterEqual(project.production_cost, 125_000)

    def test_manual_release_holds_gold_build_until_player_launches(self) -> None:
        state = GameState(selected_release_policy=1)
        self.assertTrue(start_project(state))
        project = state.studio.current_project
        project.work_done = project.total_work
        project.defects = project.known_defects = 0
        advance(state)

        self.assertTrue(state.studio.current_project.ready_for_release)
        self.assertEqual(state.studio.catalog, [])
        self.assertTrue(release_ready_project(state))
        self.assertIsNone(state.studio.current_project)
        self.assertEqual(len(state.studio.catalog), 1)

    def test_paid_early_access_has_owners_revenue_and_public_rating(self) -> None:
        state = GameState()
        state.studio.cash = 1_000_000
        state.studio.completed_research.append("content_updates")
        state.selected_monetization = next(index for index, model in enumerate(MONETIZATION_MODELS) if model["key"] == "paid_early_access")
        self.assertTrue(start_project(state))
        project = state.studio.current_project
        project.work_done = project.total_work * 0.5

        self.assertTrue(launch_early_access(state))
        advance(state)
        self.assertGreater(project.early_access_units, 0)
        self.assertGreater(project.early_access_revenue, 0)
        self.assertGreater(project.early_access_rating, 0)
        self.assertEqual(sum(project.early_access_owners_by_cohort.values()), project.early_access_units)

    def test_price_hikes_create_controversy_and_community_actions_consume_capacity(self) -> None:
        state = GameState()
        state.studio.cash = 1_000_000
        game = release_game(state)
        trust = game.trust

        self.assertIsNotNone(cycle_game_price(state, game.game_id, 1))
        self.assertLess(game.trust, trust)
        self.assertTrue(any(issue["kind"] == "pricing" for issue in game.issues))

        trust = game.trust
        self.assertTrue(take_community_action(state, game.game_id, 0))
        self.assertGreater(game.trust, trust)
        self.assertEqual(state.studio.active_community_actions[-1]["action"], "dev_diary")

    def test_publisher_recoup_crossing_uses_post_recoup_share_only_on_excess(self) -> None:
        state = GameState()
        state.studio.cash = 1_000_000
        game = release_game(state)
        sale = state.studio.active_sales[-1]
        sale.publisher = "Test Publisher"
        sale.publisher_recoupable = 100
        sale.publisher_recouped = 90
        sale.publisher_recoup_share = 0.8
        sale.publisher_post_recoup_share = 0.2
        sale.price = game.price = 10
        sale.platform_cut = sale.refund_rate = 0
        sale.weekly_units = 1_000
        transaction_start = len(state.studio.transactions)

        process_sales(state, week_end=False, day_number=state.clock.current_date.toordinal())
        transactions = state.studio.transactions[transaction_start:]
        receipts = next(item["amount"] for item in transactions if item["category"] == "Game sales")
        royalty = next(item["amount"] for item in transactions if item["category"] == "Publisher royalties")
        expected = 10 + (receipts - 12.5) * 0.2

        self.assertAlmostEqual(sale.publisher_recouped, 100)
        self.assertAlmostEqual(royalty, expected)


if __name__ == "__main__":
    unittest.main()
