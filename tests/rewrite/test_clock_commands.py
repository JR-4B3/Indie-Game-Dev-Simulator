"""WP-01 acceptance tests: frozen clock, command transactions, named randomness.

Covers M1-K1/K2 exactly: canonical snapshot shape, config/snapshot ownership,
receipt/idempotency semantics, hold precedence, capacity bounds, the three
named SHA-256 goldens and no wall-clock/global-RNG/draw consumption.
"""

import copy
import hashlib
import json
import unittest

from studio_sim.application.commands import Command
from studio_sim.application.service import execute
from studio_sim.application.tick import AdvanceGate, advance
from studio_sim.domain.campaign import (
    CampaignConfig,
    calendar_date,
    from_validated_payload,
    new_campaign,
    to_payload,
)
from studio_sim.infrastructure.randomness import draw_u64

K5_PAYLOAD = {
    "campaign_id": "kernel-test",
    "start_date": "2031-01-31",
    "seed": 42,
    "simulation_version": 1,
    "ruleset_id": "m1-kernel-1",
    "mode": "normal",
    "day": 0,
    "revision": 0,
    "status": "running",
    "closed_reason": None,
    "manual_paused": False,
    "next_event_id": 1,
    "events": [],
    "decisions": [],
    "receipts": [],
    "finance": {
        "opening_cash_minor": 10000,
        "cash_minor": 10000,
        "monthly_draw_minor": 0,
        "negative_since_day": None,
        "next_posting_id": 1,
        "postings": [],
        "obligations": [],
        "labor": [],
    },
}

ACTIVE = AdvanceGate(active_play=True)


def campaign_config(**overrides):
    values = {
        "campaign_id": "kernel-test",
        "start_date": "2031-01-31",
        "seed": 42,
        "mode": "normal",
        "opening_cash_minor": 10000,
        "monthly_draw_minor": 0,
    }
    values.update(overrides)
    return CampaignConfig(**values)


def expected_fingerprint(expected_revision, kind, payload):
    material = {"expected_revision": expected_revision, "kind": kind, "payload": payload}
    return hashlib.sha256(
        json.dumps(
            material,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    ).hexdigest()


def seeded_events(count):
    return [
        {
            "id": "e-{}".format(index),
            "day": 0,
            "kind": "pause_changed",
            "source": "cmd:seed",
            "subject_id": None,
            "facts": {"paused": True},
        }
        for index in range(1, count + 1)
    ]


class NewCampaignTests(unittest.TestCase):
    def test_k5_witness_payload_is_exact(self):
        campaign = new_campaign(campaign_config())
        self.assertEqual(to_payload(campaign), K5_PAYLOAD)
        self.assertEqual(calendar_date(campaign), "2031-01-31")
        self.assertEqual(len(campaign.finance), 8)
        self.assertEqual(campaign.finance.keys(), set(K5_PAYLOAD["finance"]))

    def test_config_decisions_sorted_copied_and_unresolved(self):
        decisions = [
            {"id": "d-b", "due_day": 3, "reason": "later review"},
            {"id": "d-a", "due_day": 0, "reason": "immediate review"},
        ]
        config = campaign_config(decisions=decisions)
        campaign = new_campaign(config)
        self.assertEqual([decision["id"] for decision in campaign.decisions], ["d-a", "d-b"])
        self.assertEqual(
            campaign.decisions[0],
            {"id": "d-a", "due_day": 0, "reason": "immediate review", "resolved": False},
        )
        decisions[0]["reason"] = "mutated after creation"
        decisions.append({"id": "d-c", "due_day": 9, "reason": "late addition"})
        self.assertEqual(campaign.decisions[1]["reason"], "later review")
        self.assertEqual(len(campaign.decisions), 2)

    def test_valid_extreme_config_accepted(self):
        campaign = new_campaign(
            campaign_config(
                campaign_id="a",
                start_date="2000-01-01",
                seed=0,
                mode="ironman",
                opening_cash_minor=0,
                monthly_draw_minor=10**9,
            )
        )
        self.assertEqual(campaign.seed, 0)
        self.assertEqual(campaign.mode, "ironman")
        self.assertEqual(campaign.finance["cash_minor"], 0)
        self.assertEqual(campaign.finance["monthly_draw_minor"], 10**9)
        largest = new_campaign(
            campaign_config(
                campaign_id="z" * 48,
                start_date="2199-12-31",
                seed=2**64 - 1,
                opening_cash_minor=10**12,
            )
        )
        self.assertEqual(largest.seed, 2**64 - 1)
        self.assertEqual(largest.finance["opening_cash_minor"], 10**12)

    def test_monthly_draw_amount_is_carried_but_not_settled(self):
        campaign = new_campaign(campaign_config(monthly_draw_minor=60000))
        payload = to_payload(campaign)
        self.assertEqual(payload["finance"]["monthly_draw_minor"], 60000)
        self.assertEqual(payload["finance"]["cash_minor"], 10000)
        self.assertEqual(payload["finance"]["postings"], [])

    def test_invalid_config_rejected(self):
        invalid = [
            dict(campaign_id="Kernel-test"),
            dict(campaign_id=""),
            dict(campaign_id="a" * 49),
            dict(campaign_id="1abc"),
            dict(campaign_id="abc.def"),
            dict(campaign_id=True),
            dict(start_date="2031-1-1"),
            dict(start_date="2031-02-30"),
            dict(start_date="1999-12-31"),
            dict(start_date="2200-01-01"),
            dict(start_date=20310131),
            dict(seed=True),
            dict(seed=-1),
            dict(seed=2**64),
            dict(seed=1.0),
            dict(seed=float("nan")),
            dict(seed=float("inf")),
            dict(mode="easy"),
            dict(mode=True),
            dict(opening_cash_minor=-1),
            dict(opening_cash_minor=10**12 + 1),
            dict(opening_cash_minor=True),
            dict(opening_cash_minor=1.0),
            dict(monthly_draw_minor=-1),
            dict(monthly_draw_minor=10**9 + 1),
            dict(monthly_draw_minor=True),
            dict(decisions="x"),
            dict(decisions={"id": "d-a"}),
            dict(decisions=[{"id": "d-a", "due_day": 0, "reason": "r", "resolved": False}]),
            dict(decisions=[{"id": "d-a", "due_day": 0}]),
            dict(decisions=[{"id": "d-a", "due_day": 0, "reason": "r", "extra": 1}]),
            dict(
                decisions=[
                    {"id": "d-a", "due_day": 0, "reason": "r"},
                    {"id": "d-a", "due_day": 1, "reason": "r"},
                ]
            ),
            dict(decisions=[{"id": "D-a", "due_day": 0, "reason": "r"}]),
            dict(decisions=[{"id": "d-a", "due_day": -1, "reason": "r"}]),
            dict(decisions=[{"id": "d-a", "due_day": 36501, "reason": "r"}]),
            dict(decisions=[{"id": "d-a", "due_day": True, "reason": "r"}]),
            dict(decisions=[{"id": "d-a", "due_day": 0, "reason": ""}]),
            dict(decisions=[{"id": "d-a", "due_day": 0, "reason": "x" * 161}]),
            dict(decisions=[{"id": "d-a", "due_day": 0, "reason": "a\x00b"}]),
            dict(decisions=[{"id": "d-a", "due_day": 0, "reason": 7}]),
            dict(decisions=[("not", "a", "mapping")]),
            dict(
                decisions=[
                    {"id": "d-{}".format(index), "due_day": 0, "reason": "r"}
                    for index in range(65)
                ]
            ),
        ]
        for overrides in invalid:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    new_campaign(campaign_config(**overrides))
        with self.assertRaises(ValueError):
            new_campaign("not-a-config")

    def test_to_payload_detached_and_round_trips(self):
        campaign = new_campaign(campaign_config(decisions=[{"id": "d-a", "due_day": 0, "reason": "note"}]))
        first = to_payload(campaign)
        second = to_payload(campaign)
        self.assertEqual(first, second)
        self.assertIsNot(first, second)
        self.assertIsNot(first["finance"], second["finance"])
        self.assertIsNot(first["decisions"][0], second["decisions"][0])
        first["finance"]["cash_minor"] = 7
        first["decisions"][0]["resolved"] = True
        first["events"].append({"bogus": True})
        self.assertEqual(campaign.finance["cash_minor"], 10000)
        self.assertFalse(campaign.decisions[0]["resolved"])
        self.assertEqual(campaign.events, ())

        round_trip = from_validated_payload(second)
        self.assertEqual(round_trip, campaign)
        self.assertIsNot(round_trip.finance, campaign.finance)
        self.assertIsNot(round_trip.finance["postings"], campaign.finance["postings"])
        self.assertIsNot(round_trip.decisions[0], campaign.decisions[0])
        round_trip.finance["cash_minor"] = -1
        self.assertEqual(campaign.finance["cash_minor"], 10000)

    def test_from_validated_payload_does_not_mutate_input(self):
        payload = copy.deepcopy(K5_PAYLOAD)
        payload["decisions"] = [{"id": "d-a", "due_day": 0, "reason": "r", "resolved": False}]
        snapshot = copy.deepcopy(payload)
        campaign = from_validated_payload(payload)
        self.assertEqual(payload, snapshot)
        campaign.decisions[0]["resolved"] = True
        campaign.finance["cash_minor"] = 1
        self.assertEqual(payload, snapshot)


class RandomnessTests(unittest.TestCase):
    GOLDENS = (
        ([0, "clock", 0, "campaign", "witness", 0], "235fc7ebcd986a6d8321e25bf8b4e0f8ddebf02b48195eaecc08cc314a16474e", 2548975729695550061),
        ([42, "market", 7, "project-a", "demand", 0], "efd9c714aee6be7066db918f8beacfd24bb38259cbe7e471171cba574812ef90", 17283063936658620016),
        ([42, "market", 7, "project-a", "demand", 1], "f8537aa4ba9526ae8514e3a12583bc12c5ce2f2ff5dabd2973e29641ecc70842", 17893780592396674734),
    )

    def test_three_frozen_goldens(self):
        for args, digest, u64 in self.GOLDENS:
            with self.subTest(args=args):
                material = json.dumps(
                    ["studio-rng-v1"] + args,
                    separators=(",", ":"),
                    ensure_ascii=True,
                    allow_nan=False,
                ).encode("ascii")
                self.assertEqual(hashlib.sha256(material).hexdigest(), digest)
                self.assertEqual(int.from_bytes(hashlib.sha256(material).digest()[:8], "big"), u64)
                self.assertEqual(draw_u64(*args), u64)

    def test_repeatable_and_ordinal_sensitive(self):
        self.assertEqual(
            draw_u64(42, "market", 7, "project-a", "demand", 0),
            draw_u64(42, "market", 7, "project-a", "demand", 0),
        )
        self.assertNotEqual(
            draw_u64(42, "market", 7, "project-a", "demand", 0),
            draw_u64(42, "market", 7, "project-a", "demand", 1),
        )

    def test_invalid_arguments_rejected(self):
        invalid = [
            dict(seed=True),
            dict(seed=-1),
            dict(seed=2**64),
            dict(seed=1.5),
            dict(system="Clock"),
            dict(system=""),
            dict(day=-1),
            dict(day=36501),
            dict(day=True),
            dict(entity="Project-A"),
            dict(purpose=""),
            dict(ordinal=-1),
            dict(ordinal=2**32),
            dict(ordinal=True),
        ]
        base = dict(seed=0, system="clock", day=0, entity="campaign", purpose="witness", ordinal=0)
        for override in invalid:
            values = dict(base)
            values.update(override)
            with self.subTest(override=override):
                with self.assertRaises(ValueError):
                    draw_u64(**values)


class CommandEnvelopeTests(unittest.TestCase):
    def test_envelope_rejections_leave_state_untouched(self):
        campaign = new_campaign(campaign_config())
        before = to_payload(campaign)
        cases = [
            ("not-a-command", "invalid_command"),
            (Command("Bad", 0, "set_pause", {"paused": True}), "invalid_command"),
            (Command("", 0, "set_pause", {"paused": True}), "invalid_command"),
            (Command("cmd", True, "set_pause", {"paused": True}), "invalid_command"),
            (Command("cmd", -1, "set_pause", {"paused": True}), "invalid_command"),
            (Command("cmd", 10**9 + 1, "set_pause", {"paused": True}), "invalid_command"),
            (Command("cmd", 1.0, "set_pause", {"paused": True}), "invalid_command"),
            (Command("cmd", 0, 7, {}), "invalid_command"),
            (Command("cmd", 0, "set_pause", []), "invalid_command"),
            (Command("cmd", 0, "set_pause", {"paused": 1}), "invalid_command"),
            (Command("cmd", 0, "set_pause", {"paused": 0}), "invalid_command"),
            (Command("cmd", 0, "set_pause", {}), "invalid_command"),
            (Command("cmd", 0, "set_pause", {"paused": True, "extra": 1}), "invalid_command"),
            (Command("cmd", 0, "set_pause", {"paused": float("nan")}), "invalid_command"),
            (Command("cmd", 0, "set_pause", {"paused": float("inf")}), "invalid_command"),
            (Command("cmd", 0, "set_pause", {"paused": b"x"}), "invalid_command"),
            (Command("cmd", 0, "set_pause", {1: True}), "invalid_command"),
            (Command("cmd", 0, "resolve_decision", {"decision_id": "D-a"}), "invalid_command"),
            (Command("cmd", 0, "resolve_decision", {"decision_id": 5}), "invalid_command"),
            (Command("cmd", 0, "resolve_decision", {}), "invalid_command"),
            (Command("cmd", 0, "retire", {"reason": "x"}), "invalid_command"),
            (Command("cmd", 0, "unknown_kind", {}), "unknown_command"),
            (Command("cmd", 0, "post_cash", {"category": "income", "amount_minor": 2500, "product_id": None}), "unknown_command"),
            (Command("cmd", 0, "add_obligation", {}), "unknown_command"),
            (Command("cmd", 0, "attribute_labor", {}), "unknown_command"),
            (Command("cmd", 0, "cancel_obligation", {}), "unknown_command"),
        ]
        for command, code in cases:
            with self.subTest(code=code, command=command):
                result = execute(campaign, command)
                self.assertFalse(result.accepted)
                self.assertEqual(result.code, code)
                self.assertIsNone(result.applied_revision)
                self.assertEqual(result.event_ids, ())
                self.assertFalse(result.duplicate)
                self.assertEqual(result.campaign, campaign)
                self.assertIsNot(result.campaign, campaign)
                self.assertEqual(to_payload(campaign), before)

    def test_payload_rejects_nonexact_json_types(self):
        class EvilDict(dict):
            pass

        class EvilList(list):
            pass

        class EvilInt(int):
            pass

        class EvilStr(str):
            pass

        campaign = new_campaign(campaign_config())
        before = to_payload(campaign)
        cases = [
            Command("cmd-tuple", 0, "unknown_kind", {"x": (1, 2)}),
            Command("cmd-tuple-bool", 0, "unknown_kind", {"x": (True,)}),
            Command("cmd-set", 0, "unknown_kind", {"x": {1, 2}}),
            Command("cmd-float", 0, "unknown_kind", {"x": 1.5}),
            Command("cmd-float-nested", 0, "unknown_kind", {"x": [1, [2.5]]}),
            Command("cmd-bytes", 0, "unknown_kind", {"x": b"raw"}),
            Command("cmd-evil-dict", 0, "unknown_kind", EvilDict()),
            Command("cmd-evil-dict-nested", 0, "unknown_kind", {"x": EvilDict({"k": 1})}),
            Command("cmd-evil-list", 0, "unknown_kind", {"x": EvilList([1])}),
            Command("cmd-evil-int", 0, "unknown_kind", {"x": EvilInt(1)}),
            Command("cmd-evil-str", 0, "unknown_kind", {"x": EvilStr("a")}),
            Command("cmd-int-key", 0, "unknown_kind", {"x": [{1: True}]}),
            Command("cmd-bool-key", 0, "unknown_kind", {"x": [{True: 1}]}),
        ]
        for command in cases:
            with self.subTest(command_id=command.command_id):
                payload_before = copy.deepcopy(command.payload)
                result = execute(campaign, command)
                self.assertFalse(result.accepted)
                self.assertEqual(result.code, "invalid_command")
                self.assertIsNone(result.applied_revision)
                self.assertEqual(result.event_ids, ())
                self.assertFalse(result.duplicate)
                self.assertEqual(result.campaign, campaign)
                self.assertEqual(to_payload(campaign), before)
                self.assertEqual(command.payload, payload_before)

    def test_payload_rejects_ancestor_cycles(self):
        campaign = new_campaign(campaign_config())
        before = to_payload(campaign)

        self_cycle = {}
        self_cycle["self"] = self_cycle

        list_cycle = []
        list_cycle.append(list_cycle)

        deep_cycle = {"a": {"b": {}}}
        deep_cycle["a"]["b"]["back"] = deep_cycle

        list_in_dict_cycle = {"x": list_cycle}
        cases = [self_cycle, deep_cycle, list_in_dict_cycle]
        for payload in cases:
            with self.subTest(payload_id=id(payload)):
                result = execute(campaign, Command("cmd-cycle", 0, "unknown_kind", payload))
                self.assertFalse(result.accepted)
                self.assertEqual(result.code, "invalid_command")
                self.assertIsNone(result.applied_revision)
                self.assertEqual(result.event_ids, ())
                self.assertEqual(result.campaign, campaign)
                self.assertEqual(to_payload(campaign), before)
        self.assertIs(self_cycle["self"], self_cycle)
        self.assertIs(deep_cycle["a"]["b"]["back"], deep_cycle)
        self.assertIs(list_cycle[0], list_cycle)

    def test_payload_depth_bound_is_32_containers(self):
        campaign = new_campaign(campaign_config())
        before = to_payload(campaign)

        for depth in (32, 33):
            dict_payload = {}
            node = dict_payload
            for _ in range(depth - 1):
                child = {}
                node["n"] = child
                node = child
            node["leaf"] = 0
            list_payload = {}
            node = 0
            for _ in range(depth - 1):
                node = [node]
            list_payload["x"] = node
            expected = "unknown_command" if depth == 32 else "invalid_command"
            for label, payload in (("dict", dict_payload), ("list", list_payload)):
                with self.subTest(depth=depth, label=label):
                    result = execute(campaign, Command("cmd-depth", 0, "unknown_kind", payload))
                    self.assertEqual(result.code, expected)
                    self.assertEqual(result.campaign, campaign)
                    self.assertIsNot(result.campaign, campaign)
                    self.assertEqual(to_payload(campaign), before)

    def test_payload_allows_shared_noncyclic_references(self):
        campaign = new_campaign(campaign_config())
        before = to_payload(campaign)
        shared = {"k": [1, 2]}
        payload = {"a": shared, "b": shared, "c": [shared, shared]}
        result = execute(campaign, Command("cmd-shared", 0, "unknown_kind", payload))
        self.assertFalse(result.accepted)
        self.assertEqual(result.code, "unknown_command")
        self.assertEqual(result.campaign, campaign)
        self.assertEqual(to_payload(campaign), before)
        self.assertIs(payload["a"], payload["b"])
        self.assertEqual(payload["c"][0], shared)

    def test_receipt_fingerprint_matches_frozen_canonical_json(self):
        campaign = new_campaign(campaign_config())
        result = execute(campaign, Command("cmd-pause", 0, "set_pause", {"paused": False}))
        self.assertTrue(result.accepted)
        receipt = result.campaign.receipts[0]
        self.assertEqual(receipt["command_id"], "cmd-pause")
        self.assertEqual(receipt["applied_revision"], 1)
        self.assertEqual(receipt["event_ids"], [])
        self.assertEqual(
            receipt["fingerprint"],
            expected_fingerprint(0, "set_pause", {"paused": False}),
        )
        self.assertRegex(receipt["fingerprint"], r"^[0-9a-f]{64}$")


class ClockCommandTests(unittest.TestCase):
    def test_set_pause_noop_and_change(self):
        campaign = new_campaign(campaign_config())
        before = to_payload(campaign)

        noop = execute(campaign, Command("cmd-pause", 0, "set_pause", {"paused": False}))
        self.assertTrue(noop.accepted)
        self.assertEqual(noop.code, "ok")
        self.assertFalse(noop.duplicate)
        self.assertEqual(noop.applied_revision, 1)
        self.assertEqual(noop.event_ids, ())
        self.assertEqual(noop.campaign.manual_paused, False)
        self.assertEqual(noop.campaign.events, ())
        self.assertEqual(noop.campaign.next_event_id, 1)
        self.assertEqual(len(noop.campaign.receipts), 1)
        noop_receipt = noop.campaign.receipts[0]
        self.assertEqual(noop_receipt["event_ids"], [])
        self.assertEqual(noop_receipt["fingerprint"], expected_fingerprint(0, "set_pause", {"paused": False}))

        changed = execute(noop.campaign, Command("cmd-pause-2", 1, "set_pause", {"paused": True}))
        self.assertTrue(changed.accepted)
        self.assertEqual(changed.code, "ok")
        self.assertEqual(changed.applied_revision, 2)
        self.assertEqual(changed.event_ids, ("e-1",))
        self.assertEqual(
            changed.campaign.events,
            (
                {
                    "id": "e-1",
                    "day": 0,
                    "kind": "pause_changed",
                    "source": "cmd:cmd-pause-2",
                    "subject_id": None,
                    "facts": {"paused": True},
                },
            ),
        )
        self.assertEqual(changed.campaign.manual_paused, True)
        self.assertEqual(changed.campaign.next_event_id, 2)

        replay = execute(changed.campaign, Command("cmd-pause-2", 1, "set_pause", {"paused": True}))
        self.assertTrue(replay.duplicate)
        self.assertEqual(replay.code, "duplicate")
        self.assertEqual(replay.event_ids, ("e-1",))
        self.assertEqual(to_payload(campaign), before)

    def test_resolve_decision_codes_events_and_progress(self):
        campaign = new_campaign(
            campaign_config(
                decisions=[
                    {"id": "d-due", "due_day": 0, "reason": "due now"},
                    {"id": "d-late", "due_day": 5, "reason": "later"},
                ]
            )
        )
        unknown = execute(campaign, Command("cmd-u", 0, "resolve_decision", {"decision_id": "d-missing"}))
        self.assertEqual((unknown.accepted, unknown.code), (False, "unknown_target"))
        not_due = execute(campaign, Command("cmd-l", 0, "resolve_decision", {"decision_id": "d-late"}))
        self.assertEqual((not_due.accepted, not_due.code), (False, "not_due"))

        resolved = execute(campaign, Command("cmd-d", 0, "resolve_decision", {"decision_id": "d-due"}))
        self.assertTrue(resolved.accepted)
        self.assertEqual(resolved.event_ids, ("e-1",))
        self.assertEqual(
            resolved.campaign.events[0],
            {
                "id": "e-1",
                "day": 0,
                "kind": "decision_resolved",
                "source": "cmd:cmd-d",
                "subject_id": "d-due",
                "facts": {},
            },
        )
        self.assertEqual(
            [decision["resolved"] for decision in resolved.campaign.decisions],
            [True, False],
        )
        again = execute(resolved.campaign, Command("cmd-d2", 1, "resolve_decision", {"decision_id": "d-due"}))
        self.assertEqual((again.accepted, again.code), (False, "already_resolved"))

        held = advance(resolved.campaign, 10, ACTIVE)
        self.assertEqual((held.stop_reason, held.consumed_days, held.campaign.day), ("decision", 5, 5))
        self.assertEqual(held.pending_decision_ids, ("d-late",))
        late = execute(held.campaign, Command("cmd-l2", held.campaign.revision, "resolve_decision", {"decision_id": "d-late"}))
        self.assertTrue(late.accepted)
        self.assertEqual(late.event_ids, ("e-2",))
        self.assertEqual(late.campaign.events[1]["day"], 5)
        freed = advance(late.campaign, 2, ACTIVE)
        self.assertEqual((freed.stop_reason, freed.consumed_days, freed.campaign.day), ("complete", 2, 7))

    def test_retire_event_closed_behavior_and_ended_rejections(self):
        campaign = new_campaign(campaign_config(decisions=[{"id": "d-a", "due_day": 0, "reason": "r"}]))
        retired = execute(campaign, Command("cmd-retire", 0, "retire", {}))
        self.assertTrue(retired.accepted)
        self.assertEqual(retired.event_ids, ("e-1",))
        self.assertEqual(
            retired.campaign.events[0],
            {
                "id": "e-1",
                "day": 0,
                "kind": "campaign_closed",
                "source": "cmd:cmd-retire",
                "subject_id": None,
                "facts": {"reason": "retired"},
            },
        )
        self.assertEqual(retired.campaign.status, "retired")
        self.assertEqual(retired.campaign.closed_reason, "retired")
        self.assertEqual(retired.campaign.manual_paused, False)
        self.assertEqual(retired.campaign.decisions[0]["resolved"], False)

        stop = advance(retired.campaign, 3, ACTIVE)
        self.assertEqual((stop.stop_reason, stop.consumed_days), ("ended", 0))
        self.assertEqual(stop.pending_decision_ids, ("d-a",))
        self.assertEqual(stop.campaign, retired.campaign)

        for command in (
            Command("cmd-p", 1, "set_pause", {"paused": True}),
            Command("cmd-r", 1, "resolve_decision", {"decision_id": "d-a"}),
            Command("cmd-retire-2", 1, "retire", {}),
        ):
            rejected = execute(retired.campaign, command)
            self.assertEqual((rejected.accepted, rejected.code), (False, "ended"))
            self.assertEqual(rejected.campaign, retired.campaign)

    def test_duplicate_after_advance_returns_original_receipt(self):
        campaign = new_campaign(campaign_config())
        first = execute(campaign, Command("cmd-hold", 0, "set_pause", {"paused": True}))
        second = execute(first.campaign, Command("cmd-resume", 1, "set_pause", {"paused": False}))
        advanced = advance(second.campaign, 5, ACTIVE).campaign
        self.assertEqual(advanced.revision, 7)
        self.assertEqual(advanced.day, 5)

        duplicate = execute(advanced, Command("cmd-hold", 0, "set_pause", {"paused": True}))
        self.assertTrue(duplicate.accepted)
        self.assertEqual(duplicate.code, "duplicate")
        self.assertTrue(duplicate.duplicate)
        self.assertEqual(duplicate.applied_revision, 1)
        self.assertEqual(duplicate.event_ids, ("e-1",))
        self.assertEqual(duplicate.campaign, advanced)

        later = advance(duplicate.campaign, 1, ACTIVE).campaign
        still_cached = execute(later, Command("cmd-hold", 0, "set_pause", {"paused": True}))
        self.assertEqual((still_cached.code, still_cached.applied_revision), ("duplicate", 1))
        self.assertEqual(still_cached.campaign, later)

    def test_duplicate_after_retirement(self):
        campaign = new_campaign(campaign_config())
        retired = execute(campaign, Command("cmd-retire", 0, "retire", {})).campaign
        duplicate = execute(retired, Command("cmd-retire", 0, "retire", {}))
        self.assertTrue(duplicate.accepted)
        self.assertEqual(duplicate.code, "duplicate")
        self.assertTrue(duplicate.duplicate)
        self.assertEqual(duplicate.applied_revision, 1)
        self.assertEqual(duplicate.event_ids, ("e-1",))
        self.assertEqual(duplicate.campaign, retired)

    def test_id_conflict_and_stale_revision(self):
        campaign = new_campaign(campaign_config())
        first = execute(campaign, Command("cmd-1", 0, "set_pause", {"paused": True}))
        second = execute(first.campaign, Command("cmd-2", 1, "set_pause", {"paused": False}))
        advanced = advance(second.campaign, 5, ACTIVE).campaign
        before = to_payload(advanced)

        conflict = execute(advanced, Command("cmd-1", 0, "set_pause", {"paused": False}))
        self.assertEqual((conflict.accepted, conflict.code), (False, "id_conflict"))
        self.assertIsNone(conflict.applied_revision)
        self.assertEqual(conflict.event_ids, ())
        self.assertEqual(conflict.campaign, advanced)

        stale = execute(advanced, Command("cmd-new", 1, "set_pause", {"paused": True}))
        self.assertEqual((stale.accepted, stale.code), (False, "stale_revision"))
        self.assertEqual(stale.campaign, advanced)
        self.assertEqual(to_payload(advanced), before)

    def test_receipt_fifo64_eviction(self):
        campaign = new_campaign(campaign_config())
        for index in range(65):
            paused = (index % 2) == 0
            result = execute(campaign, Command("cmd-{:02d}".format(index), campaign.revision, "set_pause", {"paused": paused}))
            self.assertTrue(result.accepted)
            self.assertEqual(result.applied_revision, index + 1)
            campaign = result.campaign
        self.assertEqual(campaign.revision, 65)
        self.assertEqual(len(campaign.receipts), 64)
        self.assertEqual(campaign.receipts[0]["command_id"], "cmd-01")
        self.assertEqual(campaign.receipts[0]["applied_revision"], 2)
        self.assertEqual(campaign.receipts[-1]["command_id"], "cmd-64")
        self.assertEqual(campaign.receipts[-1]["applied_revision"], 65)

        evicted = execute(campaign, Command("cmd-00", 0, "set_pause", {"paused": True}))
        self.assertEqual((evicted.accepted, evicted.code), (False, "stale_revision"))
        self.assertEqual(evicted.campaign, campaign)

        duplicate = execute(campaign, Command("cmd-64", 64, "set_pause", {"paused": True}))
        self.assertEqual((duplicate.code, duplicate.applied_revision), ("duplicate", 65))
        self.assertEqual(duplicate.event_ids, ("e-65",))
        self.assertEqual(duplicate.campaign, campaign)

        conflict = execute(campaign, Command("cmd-64", 64, "set_pause", {"paused": False}))
        self.assertEqual((conflict.accepted, conflict.code), (False, "id_conflict"))

    def test_command_capacity_at_revision_bound(self):
        campaign = new_campaign(campaign_config(decisions=[{"id": "d-a", "due_day": 0, "reason": "r"}]))
        payload = to_payload(campaign)
        payload["revision"] = 10**9
        bounded = from_validated_payload(payload)
        for command in (
            Command("cmd-p", 10**9, "set_pause", {"paused": True}),
            Command("cmd-r", 10**9, "resolve_decision", {"decision_id": "d-a"}),
            Command("cmd-ret", 10**9, "retire", {}),
        ):
            result = execute(bounded, command)
            self.assertEqual((result.accepted, result.code), (False, "capacity"))
            self.assertEqual(result.campaign, bounded)

    def test_duplicate_still_allowed_at_revision_bound(self):
        campaign = new_campaign(campaign_config())
        first = execute(campaign, Command("cmd-keep", 0, "set_pause", {"paused": True}))
        payload = to_payload(first.campaign)
        payload["revision"] = 10**9
        bounded = from_validated_payload(payload)
        duplicate = execute(bounded, Command("cmd-keep", 0, "set_pause", {"paused": True}))
        self.assertEqual((duplicate.code, duplicate.applied_revision), ("duplicate", 1))
        self.assertEqual(duplicate.campaign, bounded)

    def test_noop_capacity_at_revision_bound(self):
        campaign = new_campaign(campaign_config())
        self.assertFalse(campaign.manual_paused)
        payload = to_payload(campaign)

        at_limit = from_validated_payload(dict(payload, revision=10**9))
        before = to_payload(at_limit)
        rejected = execute(at_limit, Command("cmd-noop", 10**9, "set_pause", {"paused": False}))
        self.assertFalse(rejected.accepted)
        self.assertEqual(rejected.code, "capacity")
        self.assertIsNone(rejected.applied_revision)
        self.assertEqual(rejected.event_ids, ())
        self.assertFalse(rejected.duplicate)
        self.assertEqual(rejected.campaign, at_limit)
        self.assertIsNot(rejected.campaign, at_limit)
        self.assertEqual(to_payload(at_limit), before)

        below_limit = from_validated_payload(dict(payload, revision=10**9 - 1))
        accepted = execute(below_limit, Command("cmd-noop", 10**9 - 1, "set_pause", {"paused": False}))
        self.assertTrue(accepted.accepted)
        self.assertEqual(accepted.code, "ok")
        self.assertEqual(accepted.applied_revision, 10**9)
        self.assertEqual(accepted.event_ids, ())
        self.assertEqual(accepted.campaign.revision, 10**9)
        self.assertEqual(len(accepted.campaign.receipts), 1)

        blocked = execute(accepted.campaign, Command("cmd-after", 10**9, "set_pause", {"paused": False}))
        self.assertEqual((blocked.accepted, blocked.code), (False, "capacity"))

    def test_command_capacity_at_event_bound(self):
        campaign = new_campaign(
            campaign_config(decisions=[{"id": "d-a", "due_day": 0, "reason": "r"}])
        )
        payload = to_payload(campaign)
        payload["events"] = seeded_events(8192)
        payload["next_event_id"] = 8193
        bounded = from_validated_payload(payload)

        for command in (
            Command("cmd-p", 0, "set_pause", {"paused": True}),
            Command("cmd-r", 0, "resolve_decision", {"decision_id": "d-a"}),
            Command("cmd-ret", 0, "retire", {}),
        ):
            result = execute(bounded, command)
            self.assertEqual((result.accepted, result.code), (False, "capacity"))
            self.assertEqual(result.campaign, bounded)

        noop = execute(bounded, Command("cmd-noop", 0, "set_pause", {"paused": False}))
        self.assertTrue(noop.accepted)
        self.assertEqual(noop.event_ids, ())
        self.assertEqual(len(noop.campaign.events), 8192)
        self.assertEqual(noop.campaign.next_event_id, 8193)


class AdvanceClockTests(unittest.TestCase):
    def test_request_validation_raises_value_error(self):
        campaign = new_campaign(campaign_config())
        for bad in (-1, 3661, True, 1.5, "3", None):
            with self.subTest(requested_days=bad):
                with self.assertRaises(ValueError):
                    advance(campaign, bad, ACTIVE)
        with self.assertRaises(ValueError):
            advance(campaign, 1, None)
        with self.assertRaises(ValueError):
            advance(campaign, 1, AdvanceGate(active_play="yes"))
        with self.assertRaises(ValueError):
            advance(campaign, 1, AdvanceGate(True, preview_holds=["d-a"]))
        with self.assertRaises(ValueError):
            advance(campaign, 1, AdvanceGate(True, preview_holds=("d-a", "d-a")))
        with self.assertRaises(ValueError):
            advance(campaign, 1, AdvanceGate(True, preview_holds=("D-a",)))
        with self.assertRaises(ValueError):
            advance(campaign, 1, AdvanceGate(True, preview_holds=("",)))

    def test_zero_request_complete_without_changes(self):
        held = new_campaign(campaign_config(decisions=[{"id": "d-a", "due_day": 0, "reason": "r"}]))
        before = to_payload(held)
        result = advance(held, 0, AdvanceGate(active_play=False, preview_holds=("d-a",)))
        self.assertEqual((result.stop_reason, result.consumed_days), ("complete", 0))
        self.assertEqual(result.campaign, held)
        self.assertEqual(result.pending_decision_ids, ("d-a",))
        self.assertEqual(to_payload(held), before)

        retired = execute(held, Command("cmd-retire", 0, "retire", {})).campaign
        zero = advance(retired, 0, AdvanceGate(active_play=False))
        self.assertEqual((zero.stop_reason, zero.consumed_days), ("complete", 0))
        self.assertEqual(zero.campaign, retired)

    def test_stop_precedence(self):
        retired = execute(new_campaign(campaign_config()), Command("cmd-retire", 0, "retire", {})).campaign
        ended = advance(retired, 5, AdvanceGate(active_play=False, preview_holds=("d-a",)))
        self.assertEqual((ended.stop_reason, ended.consumed_days), ("ended", 0))
        self.assertEqual(ended.campaign, retired)

        paused = execute(new_campaign(campaign_config()), Command("cmd-hold", 0, "set_pause", {"paused": True})).campaign
        inactive = advance(paused, 5, AdvanceGate(active_play=False, preview_holds=("d-a",)))
        self.assertEqual((inactive.stop_reason, inactive.consumed_days), ("inactive", 0))
        manual = advance(paused, 5, AdvanceGate(active_play=True, preview_holds=("d-a",)))
        self.assertEqual((manual.stop_reason, manual.consumed_days), ("manual_pause", 0))
        self.assertEqual(manual.campaign, paused)

        plain = new_campaign(campaign_config())
        held = advance(plain, 5, AdvanceGate(active_play=True, preview_holds=("d-a",)))
        self.assertEqual((held.stop_reason, held.consumed_days), ("preview_hold", 0))
        self.assertEqual(held.campaign, plain)

        review = new_campaign(campaign_config(decisions=[{"id": "d-a", "due_day": 0, "reason": "r"}]))
        decision = advance(review, 5, ACTIVE)
        self.assertEqual((decision.stop_reason, decision.consumed_days), ("decision", 0))
        self.assertEqual(decision.pending_decision_ids, ("d-a",))
        self.assertEqual(decision.campaign, review)

    def test_manual_pause_holds_and_resumes(self):
        campaign = new_campaign(campaign_config())
        paused = execute(campaign, Command("cmd-hold", 0, "set_pause", {"paused": True})).campaign
        held = advance(paused, 3, ACTIVE)
        self.assertEqual((held.stop_reason, held.consumed_days, held.campaign.day), ("manual_pause", 0, 0))
        self.assertEqual(held.campaign, paused)

        resumed = execute(paused, Command("cmd-resume", 1, "set_pause", {"paused": False})).campaign
        progressed = advance(resumed, 3, ACTIVE)
        self.assertEqual((progressed.stop_reason, progressed.consumed_days, progressed.campaign.day), ("complete", 3, 3))
        self.assertEqual(progressed.campaign.revision, 5)
        inactive = advance(progressed.campaign, 2, AdvanceGate(active_play=False))
        self.assertEqual((inactive.stop_reason, inactive.consumed_days), ("inactive", 0))

    def test_due0_and_day3_decisions_stop_exactly(self):
        campaign = new_campaign(
            campaign_config(
                decisions=[
                    {"id": "d-a", "due_day": 0, "reason": "due today"},
                    {"id": "d-b", "due_day": 3, "reason": "due on day three"},
                ]
            )
        )
        first = advance(campaign, 10, ACTIVE)
        self.assertEqual((first.stop_reason, first.consumed_days, first.campaign.day), ("decision", 0, 0))
        self.assertEqual(first.pending_decision_ids, ("d-a",))

        resolved_a = execute(first.campaign, Command("cmd-a", 0, "resolve_decision", {"decision_id": "d-a"}))
        second = advance(resolved_a.campaign, 10, ACTIVE)
        self.assertEqual((second.stop_reason, second.consumed_days, second.campaign.day), ("decision", 3, 3))
        self.assertEqual(second.pending_decision_ids, ("d-b",))
        self.assertEqual(second.campaign.revision, 4)

        resolved_b = execute(second.campaign, Command("cmd-b", 4, "resolve_decision", {"decision_id": "d-b"}))
        third = advance(resolved_b.campaign, 10, ACTIVE)
        self.assertEqual((third.stop_reason, third.consumed_days, third.campaign.day), ("complete", 10, 13))
        self.assertEqual(third.pending_decision_ids, ())
        self.assertEqual(third.campaign.revision, 15)

    def test_day_batch_equality_across_calendar_boundaries(self):
        cases = (
            ("2031-01-31", 28, "2031-02-28"),
            ("2032-01-31", 29, "2032-02-29"),
            ("2031-12-31", 31, "2032-01-31"),
            ("2032-01-31", 60, "2032-03-31"),
            ("2031-11-15", 90, "2032-02-13"),
        )
        for start_date, days, expected_date in cases:
            with self.subTest(start_date=start_date, days=days):
                campaign = new_campaign(campaign_config(start_date=start_date))
                batch = advance(campaign, days, ACTIVE)
                single = campaign
                for _ in range(days):
                    single = advance(single, 1, ACTIVE).campaign
                self.assertEqual(batch.stop_reason, "complete")
                self.assertEqual(batch.consumed_days, days)
                self.assertEqual(batch.campaign, single)
                self.assertEqual(calendar_date(batch.campaign), expected_date)
                self.assertEqual(batch.campaign.revision, days)

    def test_maximum_request_completes(self):
        campaign = new_campaign(campaign_config())
        result = advance(campaign, 3660, ACTIVE)
        self.assertEqual((result.stop_reason, result.consumed_days, result.campaign.day), ("complete", 3660, 3660))
        self.assertEqual(result.campaign.revision, 3660)

    def test_tick_capacity_at_day_bound(self):
        payload = to_payload(new_campaign(campaign_config(start_date="2000-01-01")))
        payload["day"] = 36499
        campaign = from_validated_payload(payload)
        result = advance(campaign, 10, ACTIVE)
        self.assertEqual((result.stop_reason, result.consumed_days, result.campaign.day), ("capacity", 1, 36500))
        self.assertEqual(result.campaign.revision, 1)
        blocked = advance(result.campaign, 10, ACTIVE)
        self.assertEqual((blocked.stop_reason, blocked.consumed_days, blocked.campaign.day), ("capacity", 0, 36500))

    def test_tick_capacity_at_revision_bound(self):
        payload = to_payload(new_campaign(campaign_config()))
        payload["revision"] = 10**9 - 1
        campaign = from_validated_payload(payload)
        result = advance(campaign, 10, ACTIVE)
        self.assertEqual((result.stop_reason, result.consumed_days), ("capacity", 1))
        self.assertEqual(result.campaign.revision, 10**9)
        blocked = advance(result.campaign, 10, ACTIVE)
        self.assertEqual((blocked.stop_reason, blocked.consumed_days), ("capacity", 0))
        self.assertEqual(blocked.campaign.revision, 10**9)


class OwnershipTests(unittest.TestCase):
    def test_results_are_detached_from_callers(self):
        campaign = new_campaign(campaign_config(decisions=[{"id": "d-a", "due_day": 0, "reason": "note"}]))
        before = to_payload(campaign)

        accepted = execute(campaign, Command("cmd-a", 0, "resolve_decision", {"decision_id": "d-a"}))
        self.assertIsNot(accepted.campaign, campaign)
        self.assertIsNot(accepted.campaign.finance, campaign.finance)
        self.assertIsNot(accepted.campaign.decisions[0], campaign.decisions[0])
        accepted.campaign.decisions[0]["resolved"] = False
        accepted.campaign.events[0]["facts"]["x"] = 1
        accepted.campaign.finance["cash_minor"] = -1
        self.assertEqual(to_payload(campaign), before)

        rejected = execute(campaign, Command("cmd-b", 99, "set_pause", {"paused": True}))
        rejected.campaign.finance["cash_minor"] = -5
        rejected.campaign.decisions[0]["reason"] = "tampered"
        self.assertEqual(to_payload(campaign), before)

        plain = new_campaign(campaign_config())
        plain_before = to_payload(plain)
        advanced = advance(plain, 2, ACTIVE)
        self.assertIsNot(advanced.campaign, plain)
        advanced.campaign.finance["cash_minor"] = -9
        advanced.campaign.finance["postings"].append({"bogus": True})
        self.assertEqual(to_payload(plain), plain_before)

    def test_queries_and_draws_consume_nothing(self):
        campaign = new_campaign(campaign_config(decisions=[{"id": "d-a", "due_day": 0, "reason": "r"}]))
        before = to_payload(campaign)
        self.assertEqual(calendar_date(campaign), "2031-01-31")
        self.assertEqual(to_payload(campaign), to_payload(campaign))
        first = draw_u64(0, "clock", 0, "campaign", "witness", 0)
        self.assertEqual(first, draw_u64(0, "clock", 0, "campaign", "witness", 0))
        execute(campaign, Command("cmd-x", 5, "set_pause", {"paused": True}))
        execute(campaign, Command("cmd-y", 0, "unknown_kind", {}))
        execute(campaign, Command("cmd-z", 0, "set_pause", {"paused": True}))
        self.assertEqual(to_payload(campaign), before)

    def test_round_trip_snapshot_resumes_equivalently(self):
        campaign = new_campaign(campaign_config(decisions=[{"id": "d-a", "due_day": 1, "reason": "review"}]))
        paused = execute(campaign, Command("cmd-pause", 0, "set_pause", {"paused": True}))
        resumed = execute(paused.campaign, Command("cmd-resume", 1, "set_pause", {"paused": False}))
        original = resumed.campaign
        copy_of = from_validated_payload(to_payload(original))
        self.assertEqual(copy_of, original)

        first = advance(original, 1, ACTIVE)
        first_copy = advance(copy_of, 1, ACTIVE)
        self.assertEqual(first, first_copy)
        self.assertEqual(first.stop_reason, "decision")

        command = Command("cmd-resolve", first.campaign.revision, "resolve_decision", {"decision_id": "d-a"})
        left = execute(first.campaign, command)
        right = execute(first_copy.campaign, Command("cmd-resolve", first_copy.campaign.revision, "resolve_decision", {"decision_id": "d-a"}))
        self.assertEqual(left.code, right.code)
        self.assertEqual(left.event_ids, right.event_ids)
        self.assertEqual(left.campaign, right.campaign)
        self.assertEqual(left.campaign.receipts, right.campaign.receipts)

        after_left = advance(left.campaign, 5, ACTIVE)
        after_right = advance(right.campaign, 5, ACTIVE)
        self.assertEqual(after_left, after_right)
        self.assertEqual(after_left.campaign.day, 6)


if __name__ == "__main__":
    unittest.main()
