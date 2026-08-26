import tempfile
import unittest
from copy import deepcopy
from datetime import timedelta
from pathlib import Path

from sim_core.market import COHORTS, MacroSnapshot, ProductOffer, allocate_weekly_demand
from simulation import (
    CHANNELS,
    GAME_FORMATS,
    MONETIZATION_MODELS,
    PRICE_POINTS,
    RESEARCH_NODES,
    GameState,
    accept_contract_offer,
    advance_game,
    blended_platform_cut,
    channel_lock_reason,
    cycle_game_price,
    cycle_game_support,
    launch_early_access,
    load_game,
    process_sales,
    refresh_contract_offers,
    release_ready_project,
    save_game,
    selected_monetization_model,
    selected_platform_indexes,
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


def unlock_everything(state: GameState) -> None:
    for node in RESEARCH_NODES:
        if node["key"] not in state.studio.completed_research:
            state.studio.completed_research.append(node["key"])


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

    def test_new_campaign_starts_on_itchio_with_donationware(self) -> None:
        state = GameState.new_campaign()
        self.assertEqual(CHANNELS[state.selected_channel]["name"], "itch.io")
        self.assertEqual(selected_monetization_model(state)["key"], "donationware")
        self.assertEqual(selected_platform_indexes(state), [state.selected_channel])
        # Storefronts are never career-gated - only platform technology is.
        self.assertIsNone(channel_lock_reason(state.studio, 0))
        self.assertIsNotNone(channel_lock_reason(state.studio, 3))  # App Store

    def test_storefronts_are_tech_gated_not_career_gated(self) -> None:
        state = GameState()
        # A nobody can greenlight a Steam release from day one.
        state.selected_platforms = [0]
        self.assertTrue(start_project(state))
        self.assertEqual(state.studio.current_project.platforms, ["Steam"])
        # But a phone release waits for the mobile SDK technology.
        lock = channel_lock_reason(state.studio, 3)
        self.assertIsNotNone(lock)
        self.assertIn("research", lock)

    def test_multi_platform_release_sums_fees_and_reach(self) -> None:
        state = GameState()
        state.studio.cash = 1_000_000
        state.studio.completed_research.append("mobile_distribution")
        state.selected_platforms = [0, 3]  # Steam + App Store
        state.selected_price = next(index for index, point in enumerate(PRICE_POINTS) if point["price"] == 7.99)
        self.assertTrue(start_project(state))
        project = state.studio.current_project
        self.assertEqual(project.platforms, ["Steam", "App Store"])
        self.assertEqual(project.platform_cut, blended_platform_cut([0, 3]))
        self.assertGreater(project.production_cost, 100)  # both store fees included
        project.work_done = project.total_work - 1
        project.defects = project.known_defects = 0
        advance(state)
        game = state.studio.catalog[-1]
        sale = state.studio.active_sales[-1]
        self.assertEqual(sale.platforms, ["Steam", "App Store"])
        self.assertEqual(game.platforms, ["Steam", "App Store"])

    def test_tiny_games_get_no_press_reviews_until_they_have_buzz(self) -> None:
        state = GameState.new_campaign()
        state.studio.cash = 1_000_000
        game = release_game(state)
        self.assertEqual(game.press_rating, 0)
        self.assertFalse(game.press_reviewed)

        hyped = GameState()
        hyped.studio.cash = 1_000_000
        hyped.studio.followers = 30_000
        hyped_game = release_game(hyped)
        self.assertGreater(hyped_game.press_rating, 0)
        self.assertTrue(hyped_game.press_reviewed)

    def test_first_contracts_are_unpaid_portfolio_work(self) -> None:
        state = GameState()
        self.assertTrue(state.studio.contract_offers)
        self.assertTrue(all(offer.payout == 0 for offer in state.studio.contract_offers))
        revenue_before = state.studio.lifetime_revenue
        reputation_before = state.studio.contractor_reputation
        self.assertTrue(accept_contract_offer(state))
        contract = state.studio.contract
        self.assertEqual(contract.payout, 0)
        contract.quality_target = 0
        contract.work_done = contract.required_work
        advance(state)
        self.assertIsNone(state.studio.contract)
        self.assertEqual(state.studio.lifetime_revenue, revenue_before)
        self.assertGreater(state.studio.contractor_reputation, reputation_before)

        state.studio.contractor_reputation = 20
        state.studio.contracts_completed = 5
        refresh_contract_offers(state, announce=False)
        self.assertTrue(any(offer.payout > 0 for offer in state.studio.contract_offers))

    def test_online_games_pay_server_rent_until_sunset(self) -> None:
        state = GameState.new_campaign()
        state.studio.seed = 424242
        state.studio.cash = 3_000_000
        state.studio.followers = 300_000
        unlock_everything(state)
        state.selected_format = next(
            index for index, item in enumerate(GAME_FORMATS) if item["name"] == "Online co-op"
        )
        while len(state.studio.team) < 4:
            member = deepcopy(state.studio.team[0])
            member.employee_id = 10 + len(state.studio.team)
            state.studio.team.append(member)
        game = release_game(state)
        self.assertNotEqual(game.game_format, "Offline solo")

        advance(state, 2)
        rent = [item for item in state.studio.transactions if item["category"] == "Server rent"]
        self.assertTrue(rent, "an online game must pay infrastructure rent even with few players")

        cycle_game_support(state, game.game_id)  # Active -> Maintenance
        cycle_game_support(state, game.game_id)  # Maintenance -> Sunset
        mark = len(state.studio.transactions)
        players_before = game.active_players
        advance(state)
        self.assertEqual(
            [item for item in state.studio.transactions[mark:] if item["category"] == "Server rent"],
            [],
            "sunsetting an online game shuts its servers down",
        )
        self.assertLess(game.active_players, players_before * 0.9)

    def test_free_games_trickle_donations_and_never_charge_players(self) -> None:
        state = GameState.new_campaign()
        state.studio.seed = 424242
        state.studio.cash = 1_000_000
        state.studio.followers = 120_000
        unlock_everything(state)
        game = release_game(state)
        sale = state.studio.active_sales[-1]
        self.assertEqual(sale.price, 0.0)
        self.assertEqual(game.price, 0.0)
        advance(state, 3)
        self.assertGreater(game.recurring_revenue, 0)
        self.assertTrue(any(item["category"] == "Donations" for item in state.studio.transactions))

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
