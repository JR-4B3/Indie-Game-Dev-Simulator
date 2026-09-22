"""WP-03 save codec and store safety tests (M1-K1 K4/K5).

Runs real temp files under ``$TMPDIR`` (``/tmp/opencode``) and injects precise
low-level stdlib faults (write/fsync/replace/read) at each commit stage. No test
touches a real game save, a non-temporary user path, or another WP's files.
"""

import copy
import datetime
import errno
import fcntl
import hashlib
import json
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from studio_sim.infrastructure import saves  # noqa: E402
from studio_sim.infrastructure.saves import SaveError, SaveStore, decode, encode  # noqa: E402

_FIXTURE_PATH = pathlib.Path(__file__).resolve().parent / "fixtures" / "rewrite_v1.json"
_TEMP_ROOT = pathlib.Path(os.environ.get("TMPDIR") or "/tmp/opencode")

PRIMARY = saves.PRIMARY_NAME
BACKUP = saves.BACKUP_NAME
RECOVERY = saves.RECOVERY_NAME
LOCK = saves.LOCK_NAME
MARKER = saves.FAILURE_MARKER_NAME
FOUR_MIB = 4 * 1024 * 1024


def k5_payload():
    """The exact K5 witness payload, independent of any WP-01 import."""
    return {
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


def canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def digest_of(payload):
    return hashlib.sha256(canonical(payload)).hexdigest()


def envelope_for(payload, *, digest=None, format_id="studio-rewrite", version=1, drop=(), extra=None):
    document = {}
    if "format_id" not in drop:
        document["format_id"] = format_id
    if "schema_version" not in drop:
        document["schema_version"] = version
    if "payload" not in drop:
        document["payload"] = payload
    if "sha256" not in drop:
        document["sha256"] = digest_of(payload) if digest is None else digest
    if extra:
        document.update(extra)
    return canonical(document)


def patched(payload, path, value):
    out = copy.deepcopy(payload)
    node = out
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    return out


def without(payload, path):
    out = copy.deepcopy(payload)
    node = out
    for key in path[:-1]:
        node = node[key]
    del node[path[-1]]
    return out


def posting_list(*specs):
    out = []
    for index, spec in enumerate(specs, 1):
        posting = dict(spec)
        posting["id"] = f"p-{index}"
        out.append(posting)
    return out


def event_list(*specs):
    out = []
    for index, spec in enumerate(specs, 1):
        event = dict(spec)
        event["id"] = f"e-{index}"
        out.append(event)
    return out


def build(
    *,
    campaign_id="camp-1",
    start_date="2031-01-31",
    seed=42,
    mode="normal",
    day=0,
    revision=0,
    status="running",
    closed_reason=None,
    manual_paused=False,
    events=None,
    decisions=None,
    receipts=None,
    opening=10000,
    monthly_draw=0,
    negative_since=None,
    postings=None,
    obligations=None,
    labor=None,
):
    postings = list(postings or [])
    events = list(events or [])
    cash = opening + sum(posting["amount_minor"] for posting in postings)
    return {
        "campaign_id": campaign_id,
        "start_date": start_date,
        "seed": seed,
        "simulation_version": 1,
        "ruleset_id": "m1-kernel-1",
        "mode": mode,
        "day": day,
        "revision": revision,
        "status": status,
        "closed_reason": closed_reason,
        "manual_paused": manual_paused,
        "next_event_id": len(events) + 1,
        "events": events,
        "decisions": list(decisions or []),
        "receipts": list(receipts or []),
        "finance": {
            "opening_cash_minor": opening,
            "cash_minor": cash,
            "monthly_draw_minor": monthly_draw,
            "negative_since_day": negative_since,
            "next_posting_id": len(postings) + 1,
            "postings": postings,
            "obligations": list(obligations or []),
            "labor": list(labor or []),
        },
    }


def rich_payload():
    """One valid snapshot exercising postings, decisions, receipts and a draw."""
    postings = posting_list(
        {"day": 1, "category": "expense", "amount_minor": -1200, "source": "cmd:c-1", "product_id": None},
        {"day": 2, "category": "income", "amount_minor": 500, "source": "cmd:c-2", "product_id": "prod-a"},
        {"day": 3, "category": "draw", "amount_minor": -2143, "source": "draw:2031-02-03", "product_id": None},
    )
    events = event_list(
        {"day": 1, "kind": "cash_posted", "source": "cmd:c-1", "subject_id": None, "facts": {"posting_id": "p-1"}},
        {"day": 1, "kind": "decision_resolved", "source": "cmd:c-3", "subject_id": "dec-a", "facts": {}},
        {"day": 2, "kind": "cash_posted", "source": "cmd:c-2", "subject_id": None, "facts": {"posting_id": "p-2"}},
        {"day": 3, "kind": "cash_posted", "source": "draw:2031-02-03", "subject_id": None, "facts": {"posting_id": "p-3"}},
    )
    decisions = [
        {"id": "dec-a", "due_day": 1, "reason": "technical review", "resolved": True},
        {"id": "dec-b", "due_day": 9, "reason": "later review", "resolved": False},
    ]
    receipts = [
        {"command_id": "c-1", "fingerprint": "ab" * 32, "applied_revision": 1, "event_ids": ["e-1"]},
        {"command_id": "c-2", "fingerprint": "cd" * 32, "applied_revision": 2, "event_ids": ["e-3"]},
    ]
    return build(
        campaign_id="rich-1",
        day=3,
        revision=2,
        monthly_draw=60000,
        postings=postings,
        events=events,
        decisions=decisions,
        receipts=receipts,
    )


def negative_payload(day, *, negative_since=1, status="running", revision=0):
    postings = posting_list(
        {"day": 1, "category": "expense", "amount_minor": -1800, "source": "cmd:c-1", "product_id": None}
    )
    specs = [
        {"day": 1, "kind": "cash_posted", "source": "cmd:c-1", "subject_id": None, "facts": {"posting_id": "p-1"}},
        {
            "day": negative_since,
            "kind": "liquidity_warning",
            "source": "tick",
            "subject_id": None,
            "facts": {"negative_since_day": negative_since},
        },
    ]
    if status == "failed":
        specs.append(
            {"day": day, "kind": "campaign_closed", "source": "tick", "subject_id": None, "facts": {"reason": "insolvent"}}
        )
    if status == "retired":
        specs.append(
            {"day": day, "kind": "campaign_closed", "source": "cmd:c-9", "subject_id": None, "facts": {"reason": "retired"}}
        )
    reasons = {"running": None, "retired": "retired", "failed": "insolvent"}
    return build(
        campaign_id="neg-1",
        day=day,
        revision=revision,
        status=status,
        closed_reason=reasons[status],
        opening=1000,
        negative_since=negative_since,
        postings=postings,
        events=event_list(*specs),
    )


def keep_events(payload, kinds):
    out = copy.deepcopy(payload)
    kept = [event for event in out["events"] if event["kind"] in kinds]
    for index, event in enumerate(kept, 1):
        event["id"] = f"e-{index}"
    out["events"] = kept
    out["next_event_id"] = len(kept) + 1
    return out


class RewriteTestCase(unittest.TestCase):
    def assert_code(self, expected, callable_, *args, **kwargs):
        with self.assertRaises(SaveError) as ctx:
            callable_(*args, **kwargs)
        self.assertEqual(ctx.exception.code, expected, msg=str(ctx.exception))
        return ctx.exception

    def assert_snapshot_rejected(self, payload, code="invalid_payload", digest=None):
        self.assert_code(code, decode, envelope_for(payload, digest=digest))

    def assert_accepts(self, payload):
        data = envelope_for(payload)
        self.assertEqual(decode(data), payload)


class TestGoldenFixture(RewriteTestCase):
    def setUp(self):
        self.raw = _FIXTURE_PATH.read_bytes()

    def test_fixture_bytes_are_the_exact_canonical_envelope(self):
        document = json.loads(self.raw)
        self.assertEqual(
            set(document),
            {"format_id", "schema_version", "payload", "sha256"},
        )
        self.assertEqual(document["format_id"], "studio-rewrite")
        self.assertEqual(document["schema_version"], 1)
        self.assertEqual(document["sha256"], digest_of(document["payload"]))
        self.assertEqual(document["payload"], k5_payload())
        self.assertEqual(self.raw, canonical(document))
        self.assertNotIn(b"\n", self.raw)

    def test_fixture_payload_matches_k5_values(self):
        payload = decode(self.raw)
        self.assertEqual(payload["campaign_id"], "kernel-test")
        self.assertEqual(payload["start_date"], "2031-01-31")
        self.assertEqual(payload["seed"], 42)
        self.assertEqual(payload["mode"], "normal")
        self.assertEqual(payload["day"], 0)
        self.assertEqual(payload["revision"], 0)
        self.assertEqual(payload["status"], "running")
        self.assertIsNone(payload["closed_reason"])
        self.assertFalse(payload["manual_paused"])
        self.assertEqual(payload["next_event_id"], 1)
        self.assertEqual(payload["events"], [])
        self.assertEqual(payload["decisions"], [])
        self.assertEqual(payload["receipts"], [])
        finance = payload["finance"]
        self.assertEqual(finance["opening_cash_minor"], 10000)
        self.assertEqual(finance["cash_minor"], 10000)
        self.assertEqual(finance["monthly_draw_minor"], 0)
        self.assertIsNone(finance["negative_since_day"])
        self.assertEqual(finance["next_posting_id"], 1)
        self.assertEqual(finance["postings"], [])
        self.assertEqual(finance["obligations"], [])
        self.assertEqual(finance["labor"], [])
        self.assertEqual(set(payload), set(k5_payload()))

    def test_empty_lists_stay_empty(self):
        payload = decode(self.raw)
        self.assertIsInstance(payload["events"], list)
        self.assertEqual(payload["events"], [])
        self.assertEqual(payload["finance"]["postings"], [])

    def test_encode_reproduces_fixture_bytes(self):
        self.assertEqual(encode(k5_payload()), self.raw)

    def test_decode_detaches_payload(self):
        first = decode(self.raw)
        first["finance"]["cash_minor"] = 0
        first["events"].append("junk")
        second = decode(self.raw)
        self.assertEqual(second, k5_payload())

    def test_encode_does_not_mutate_input(self):
        payload = k5_payload()
        before = copy.deepcopy(payload)
        encode(payload)
        self.assertEqual(payload, before)

    def test_whitespace_and_key_order_are_accepted(self):
        document = json.loads(self.raw)
        loose = json.dumps(document, indent=2, sort_keys=False).encode("utf-8")
        self.assertEqual(decode(loose), k5_payload())


class TestDecodeEnvelope(RewriteTestCase):
    def test_non_dict_roots(self):
        for raw in (b"[]", b'"text"', b"5", b"null", b"true", b"[]\n"):
            with self.subTest(raw=raw):
                self.assert_code("invalid_payload", decode, raw)

    def test_malformed_json_is_invalid_json(self):
        for raw in (b"", b" ", b"{", b"not json", b'{"a":}', b"\x00", b"\xff\xfe", b"[1,]", b"{,}"):
            with self.subTest(raw=raw):
                self.assert_code("invalid_json", decode, raw)

    def test_deep_nesting_does_not_crash(self):
        self.assert_code("invalid_json", decode, b"[" * 200000 + b"]" * 200000)
        deep_object = b'{"a":' * 100000 + b"1" + b"}" * 100000
        with self.assertRaises(SaveError) as ctx:
            decode(deep_object)
        self.assertIn(ctx.exception.code, ("invalid_json", "invalid_payload"))

    def test_size_limits(self):
        self.assert_code("too_large", decode, b" " * (FOUR_MIB + 1))
        self.assert_code("invalid_json", decode, b" " * FOUR_MIB)

    def test_bytes_like_inputs(self):
        raw = _FIXTURE_PATH.read_bytes()
        self.assertEqual(decode(bytearray(raw)), k5_payload())
        self.assertEqual(decode(memoryview(raw)), k5_payload())

    def test_non_bytes_input(self):
        self.assert_code("invalid_json", decode, "not bytes")
        self.assert_code("invalid_json", decode, 5)
        self.assert_code("invalid_json", decode, None)

    def test_envelope_shape(self):
        payload = k5_payload()
        self.assert_code("invalid_payload", decode, envelope_for(payload, extra={"saved_at": "now"}))
        for key in ("format_id", "schema_version", "payload", "sha256"):
            with self.subTest(drop=key):
                self.assert_code("invalid_payload", decode, envelope_for(payload, drop=(key,)))

    def test_format_id(self):
        payload = k5_payload()
        self.assert_code("unsupported_format", decode, envelope_for(payload, format_id="legacy-save"))
        self.assert_code("unsupported_format", decode, envelope_for(payload, format_id="studio-rewrite-v2"))
        self.assert_code("invalid_payload", decode, envelope_for(payload, format_id=1))
        self.assert_code("invalid_payload", decode, envelope_for(payload, format_id=None))

    def test_schema_version(self):
        payload = k5_payload()
        self.assert_code("unsupported_version", decode, envelope_for(payload, version=2))
        self.assert_code("unsupported_version", decode, envelope_for(payload, version=0))
        self.assert_code("invalid_payload", decode, envelope_for(payload, version="1"))
        self.assert_code("invalid_payload", decode, envelope_for(payload, version=1.0))
        self.assert_code("invalid_payload", decode, envelope_for(payload, version=True))
        self.assert_code("invalid_payload", decode, envelope_for(payload, version=None))

    def test_digest(self):
        payload = k5_payload()
        self.assert_code("integrity", decode, envelope_for(payload, digest="0" * 64))
        self.assert_code("integrity", decode, envelope_for(payload, digest=digest_of(k5_payload())[::-1]))
        self.assert_code("invalid_payload", decode, envelope_for(payload, digest="zz" * 32))
        self.assert_code("invalid_payload", decode, envelope_for(payload, digest="AB" * 32))
        self.assert_code("invalid_payload", decode, envelope_for(payload, digest=42))
        self.assert_code("invalid_payload", decode, envelope_for(payload, extra={"sha256": None}))

    def test_payload_is_validated_before_digest(self):
        bad = patched(k5_payload(), ("seed",), True)
        self.assert_snapshot_rejected(bad)
        self.assert_snapshot_rejected(bad, digest="0" * 64)

    def test_duplicate_keys_at_any_nesting(self):
        text = _FIXTURE_PATH.read_text()
        duplicated = [
            text[:-1] + ',"format_id":"studio-rewrite"}',
            text.replace('"payload":{"campaign_id"', '"payload":{"campaign_id":"kernel-test","campaign_id"', 1),
            text.replace('"finance":{"cash_minor"', '"finance":{"cash_minor":1,"cash_minor"', 1),
        ]
        rich = canonical(rich_payload()).decode()
        duplicated.append(
            rich.replace('"facts":{"posting_id":"p-1"}', '"facts":{"posting_id":"p-X","posting_id":"p-1"}', 1)
        )
        for raw in duplicated:
            with self.subTest(fragment=raw[:60]):
                self.assert_code("invalid_json", decode, raw.encode())

    def test_nan_and_infinity_literals(self):
        text = _FIXTURE_PATH.read_text()
        for literal in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(literal=literal):
                raw = text.replace('"seed":42', f'"seed":{literal}').encode()
                self.assert_code("invalid_json", decode, raw)

    def test_overflowing_numeric_literals_are_floats(self):
        text = _FIXTURE_PATH.read_text()
        raw = text.replace('"seed":42', '"seed":1e400').encode()
        self.assert_code("invalid_payload", decode, raw)


class TestSnapshotSchema(RewriteTestCase):
    def test_unknown_keys_at_every_level(self):
        rich = rich_payload()
        cases = {
            "snapshot": patched(rich, ("extra",), 1),
            "decision": patched(rich, ("decisions", 0, "extra"), 1),
            "event": patched(rich, ("events", 0, "extra"), 1),
            "facts": patched(rich, ("events", 0, "facts", "extra"), 1),
            "receipt": patched(rich, ("receipts", 0, "extra"), 1),
            "finance": patched(rich, ("finance", "extra"), 1),
            "posting": patched(rich, ("finance", "postings", 0, "extra"), 1),
        }
        for label, payload in cases.items():
            with self.subTest(level=label):
                self.assert_snapshot_rejected(payload)

    def test_missing_keys_at_every_level(self):
        rich = rich_payload()
        cases = {
            "snapshot": without(rich, ("revision",)),
            "decision": without(rich, ("decisions", 0, "resolved")),
            "event": without(rich, ("events", 0, "subject_id")),
            "facts": without(rich, ("events", 1, "facts")),
            "receipt": without(rich, ("receipts", 0, "fingerprint")),
            "finance": without(rich, ("finance", "cash_minor")),
            "posting": without(rich, ("finance", "postings", 0, "product_id")),
        }
        for label, payload in cases.items():
            with self.subTest(level=label):
                self.assert_snapshot_rejected(payload)

    def test_top_level_field_types(self):
        rich = rich_payload()
        wrong = {
            "campaign_id": 1,
            "start_date": 20310131,
            "seed": "42",
            "simulation_version": "1",
            "ruleset_id": 1,
            "mode": 1,
            "day": "0",
            "revision": 1.5,
            "status": True,
            "closed_reason": 0,
            "manual_paused": "false",
            "next_event_id": "1",
            "events": {},
            "decisions": {},
            "receipts": {},
            "finance": [],
        }
        for field, value in wrong.items():
            with self.subTest(field=field):
                self.assert_snapshot_rejected(patched(rich, (field,), value))

    def test_booleans_are_not_integers(self):
        rich = rich_payload()
        cases = {
            "seed": patched(rich, ("seed",), True),
            "day": patched(rich, ("day",), False),
            "revision": patched(rich, ("revision",), True),
            "next_event_id": patched(rich, ("next_event_id",), True),
            "opening_cash_minor": patched(rich, ("finance", "opening_cash_minor"), True),
            "monthly_draw_minor": patched(rich, ("finance", "monthly_draw_minor"), True),
            "next_posting_id": patched(rich, ("finance", "next_posting_id"), True),
            "posting_amount": patched(rich, ("finance", "postings", 0, "amount_minor"), True),
            "posting_day": patched(rich, ("finance", "postings", 0, "day"), True),
            "receipt_revision": patched(rich, ("receipts", 0, "applied_revision"), True),
            "decision_due_day": patched(rich, ("decisions", 0, "due_day"), True),
            "decision_resolved": patched(rich, ("decisions", 0, "resolved"), 1),
        }
        for label, payload in cases.items():
            with self.subTest(field=label):
                self.assert_snapshot_rejected(payload)

    def test_float_values_are_rejected(self):
        rich = rich_payload()
        cases = {
            "seed": patched(rich, ("seed",), 42.0),
            "day": patched(rich, ("day",), 3.0),
            "opening": patched(rich, ("finance", "opening_cash_minor"), 10000.0),
            "amount": patched(rich, ("finance", "postings", 0, "amount_minor"), -1200.0),
        }
        for label, payload in cases.items():
            with self.subTest(field=label):
                self.assert_snapshot_rejected(payload)
                self.assert_snapshot_rejected(payload, digest="0" * 64)

    def test_identifier_rules(self):
        rich = rich_payload()
        for bad in (
            "Kernel-Test",
            "9kernel",
            "kernel.test",
            "kernel test",
            "kernel/test",
            "..",
            ".",
            "",
            "a" * 49,
            "caf\u00e9",
            "kernel\x00test",
        ):
            with self.subTest(campaign_id=bad):
                self.assert_snapshot_rejected(patched(rich, ("campaign_id",), bad))
        self.assert_accepts(patched(rich, ("campaign_id",), "a" * 48))
        self.assert_accepts(patched(rich, ("campaign_id",), "a-0_b"))

    def test_reference_identifier_rules(self):
        rich = rich_payload()
        self.assert_snapshot_rejected(patched(rich, ("events", 0, "id"), "e-0"))
        self.assert_snapshot_rejected(patched(rich, ("events", 0, "id"), "e-01"))
        self.assert_snapshot_rejected(patched(rich, ("events", 0, "id"), "E-1"))
        self.assert_snapshot_rejected(patched(rich, ("finance", "postings", 0, "id"), "p-0"))
        self.assert_snapshot_rejected(patched(rich, ("finance", "postings", 0, "id"), "p-01"))
        self.assert_snapshot_rejected(patched(rich, ("finance", "postings", 0, "product_id"), "Prod A"))
        self.assert_snapshot_rejected(patched(rich, ("events", 0, "source"), "cmd:"))
        self.assert_snapshot_rejected(patched(rich, ("events", 0, "source"), "cmd:Upper"))
        self.assert_snapshot_rejected(patched(rich, ("events", 0, "source"), "nonsense"))
        self.assert_snapshot_rejected(patched(rich, ("events", 0, "source"), "obligation:"))
        self.assert_snapshot_rejected(patched(rich, ("events", 0, "source"), "draw:2031-2-3"))

    def test_date_rules(self):
        rich = rich_payload()
        for bad in ("2031-02-30", "20310131", "2031-1-31", "1999-12-31", "2200-01-01", "", "x"):
            with self.subTest(start_date=bad):
                self.assert_snapshot_rejected(patched(rich, ("start_date",), bad))
        for ok in ("2000-01-01", "2199-12-31", "2032-02-29"):
            with self.subTest(start_date=ok):
                self.assert_accepts(patched(k5_payload(), ("start_date",), ok))

    def test_numeric_ranges(self):
        rich = rich_payload()
        cases = {
            "seed_high": patched(rich, ("seed",), 2 ** 64),
            "seed_negative": patched(rich, ("seed",), -1),
            "day_high": patched(rich, ("day",), 36501),
            "revision_high": patched(rich, ("revision",), 10 ** 9 + 1),
            "revision_negative": patched(rich, ("revision",), -1),
            "opening_high": patched(rich, ("finance", "opening_cash_minor"), 10 ** 12 + 1),
            "monthly_high": patched(rich, ("finance", "monthly_draw_minor"), 10 ** 9 + 1),
            "cash_high": patched(rich, ("finance", "cash_minor"), 10 ** 12 + 1),
            "amount_high": patched(rich, ("finance", "postings", 0, "amount_minor"), -(10 ** 12) - 1),
        }
        for label, payload in cases.items():
            with self.subTest(field=label):
                self.assert_snapshot_rejected(payload)

    def test_simulation_version_and_ruleset_are_frozen(self):
        rich = rich_payload()
        self.assert_snapshot_rejected(patched(rich, ("simulation_version",), 2))
        self.assert_snapshot_rejected(patched(rich, ("simulation_version",), 0))
        self.assert_snapshot_rejected(patched(rich, ("ruleset_id",), "m1-kernel-2"))
        self.assert_snapshot_rejected(patched(rich, ("mode",), "hardcore"))
        self.assert_snapshot_rejected(patched(rich, ("status",), "paused"))
        self.assert_snapshot_rejected(patched(rich, ("closed_reason",), "bankrupt"))

    def test_reason_text_bounds(self):
        rich = rich_payload()
        self.assert_snapshot_rejected(patched(rich, ("decisions", 0, "reason"), ""))
        self.assert_snapshot_rejected(patched(rich, ("decisions", 0, "reason"), "a" * 161))
        self.assert_snapshot_rejected(patched(rich, ("decisions", 0, "reason"), "bad\x00reason"))
        self.assert_snapshot_rejected(patched(rich, ("decisions", 0, "reason"), 5))
        self.assert_accepts(patched(rich, ("decisions", 0, "reason"), "a" * 160))
        self.assert_accepts(patched(rich, ("decisions", 0, "reason"), "caf\u00e9 review"))


class TestSnapshotReferences(RewriteTestCase):
    def test_event_ids_must_be_contiguous(self):
        rich = rich_payload()
        self.assert_snapshot_rejected(patched(rich, ("events", 0, "id"), "e-2"))
        self.assert_snapshot_rejected(patched(rich, ("events", 1, "id"), "e-5"))

    def test_posting_ids_must_be_contiguous(self):
        rich = rich_payload()
        self.assert_snapshot_rejected(patched(rich, ("finance", "postings", 0, "id"), "p-2"))
        self.assert_snapshot_rejected(patched(rich, ("finance", "postings", 2, "id"), "p-9"))

    def test_next_counters(self):
        rich = rich_payload()
        self.assert_snapshot_rejected(patched(rich, ("next_event_id",), 4))
        self.assert_snapshot_rejected(patched(rich, ("next_event_id",), 6))
        self.assert_snapshot_rejected(patched(rich, ("finance", "next_posting_id"), 3))
        self.assert_snapshot_rejected(patched(rich, ("finance", "next_posting_id"), 9))
        empty = k5_payload()
        self.assert_snapshot_rejected(patched(empty, ("next_event_id",), 2))
        self.assert_snapshot_rejected(patched(empty, ("finance", "next_posting_id"), 2))
        self.assert_accepts(empty)

    def test_days_must_be_ordered_and_bounded(self):
        rich = rich_payload()
        self.assert_snapshot_rejected(patched(rich, ("events", 2, "day"), 0))
        self.assert_snapshot_rejected(patched(rich, ("finance", "postings", 2, "day"), 1))
        self.assert_snapshot_rejected(patched(rich, ("events", 2, "day"), 4))
        self.assert_snapshot_rejected(patched(rich, ("finance", "postings", 2, "day"), 4))

    def test_decisions_unique_sorted_and_due(self):
        rich = rich_payload()
        self.assert_snapshot_rejected(patched(rich, ("decisions", 1, "id"), "dec-a"))
        swapped = patched(rich, ("decisions",), list(reversed(rich["decisions"])))
        self.assert_snapshot_rejected(swapped)
        self.assert_snapshot_rejected(patched(rich, ("decisions", 0, "due_day"), 4))
        self.assert_accepts(patched(rich, ("decisions", 0, "due_day"), 3))

    def test_receipts_strictly_increasing_revisions(self):
        rich = rich_payload()
        self.assert_snapshot_rejected(patched(rich, ("receipts", 1, "applied_revision"), 1))
        self.assert_snapshot_rejected(patched(rich, ("receipts", 0, "applied_revision"), 3))
        self.assert_snapshot_rejected(patched(rich, ("receipts", 0, "applied_revision"), 0))
        self.assert_snapshot_rejected(patched(rich, ("receipts", 1, "applied_revision"), 5))
        self.assert_snapshot_rejected(
            patched(rich, ("receipts", 1, "command_id"), "c-1")
        )

    def test_receipt_fingerprints(self):
        rich = rich_payload()
        self.assert_snapshot_rejected(patched(rich, ("receipts", 0, "fingerprint"), "ab" * 31))
        self.assert_snapshot_rejected(patched(rich, ("receipts", 0, "fingerprint"), "AB" * 32))
        self.assert_snapshot_rejected(patched(rich, ("receipts", 0, "fingerprint"), "zz" * 32))
        self.assert_snapshot_rejected(patched(rich, ("receipts", 0, "fingerprint"), 5))

    def test_receipt_event_references_must_exist(self):
        rich = rich_payload()
        self.assert_snapshot_rejected(patched(rich, ("receipts", 0, "event_ids"), ["e-9"]))
        self.assert_snapshot_rejected(patched(rich, ("receipts", 0, "event_ids"), ["not-an-id"]))

    def test_events_may_reference_aged_out_receipts(self):
        rich = rich_payload()
        payload = patched(rich, ("receipts",), [])
        payload = patched(payload, ("revision",), 0)
        self.assert_accepts(payload)

    def test_receipts_may_carry_empty_event_lists(self):
        rich = rich_payload()
        payload = patched(
            rich,
            ("receipts",),
            [
                {"command_id": "c-7", "fingerprint": "ab" * 32, "applied_revision": 1, "event_ids": []},
                {"command_id": "c-8", "fingerprint": "cd" * 32, "applied_revision": 2, "event_ids": []},
            ],
        )
        self.assert_accepts(payload)


class TestSnapshotFinance(RewriteTestCase):
    def one_posting(self, category, amount, *, day=0, monthly_draw=0, start_date="2031-01-31"):
        postings = posting_list(
            {"day": day, "category": category, "amount_minor": amount, "source": "cmd:c-1", "product_id": None}
        )
        events = event_list(
            {"day": day, "kind": "cash_posted", "source": "cmd:c-1", "subject_id": None, "facts": {"posting_id": "p-1"}}
        )
        return build(
            day=day,
            start_date=start_date,
            monthly_draw=monthly_draw,
            opening=10000,
            postings=postings,
            events=events,
        )

    def obligation_payload(self, *, paid=True):
        postings = posting_list(
            {"day": 3, "category": "expense", "amount_minor": -500, "source": "obligation:ob-1", "product_id": None}
        )
        events = event_list(
            {
                "day": 3,
                "kind": "cash_posted",
                "source": "obligation:ob-1",
                "subject_id": None,
                "facts": {"posting_id": "p-1"},
            }
        )
        obligations = [
            {
                "id": "ob-1",
                "due_day": 3,
                "category": "expense",
                "amount_minor": -500,
                "product_id": None,
                "paid": paid,
            }
        ]
        return build(
            day=3,
            revision=1,
            opening=10000,
            postings=postings,
            events=events,
            obligations=obligations,
        )

    def test_cash_identity(self):
        rich = rich_payload()
        self.assertEqual(rich["finance"]["cash_minor"], 7157)
        self.assert_accepts(rich)
        self.assert_snapshot_rejected(patched(rich, ("finance", "cash_minor"), 7158))
        self.assert_snapshot_rejected(patched(rich, ("finance", "cash_minor"), -7157))

    def test_amount_sign_rules(self):
        self.assert_accepts(self.one_posting("income", 1))
        self.assert_accepts(self.one_posting("expense", -1))
        self.assert_accepts(self.one_posting("financing", 5))
        self.assert_accepts(self.one_posting("financing", -5))
        self.assert_snapshot_rejected(self.one_posting("income", -5))
        self.assert_snapshot_rejected(self.one_posting("income", 0))
        self.assert_snapshot_rejected(self.one_posting("expense", 5))
        self.assert_snapshot_rejected(self.one_posting("expense", 0))
        self.assert_snapshot_rejected(self.one_posting("financing", 0))
        # immediate postings may not use the draw category
        self.assert_snapshot_rejected(self.one_posting("draw", -5))

    def test_founder_draw_formula(self):
        feb1 = self.one_posting("draw", -2142, day=1, monthly_draw=60000)
        feb1 = patched(feb1, ("finance", "postings", 0, "source"), "draw:2031-02-01")
        feb1 = patched(feb1, ("events", 0, "source"), "draw:2031-02-01")
        self.assert_accepts(feb1)
        self.assert_snapshot_rejected(patched(feb1, ("finance", "postings", 0, "amount_minor"), -2143))
        self.assert_snapshot_rejected(patched(feb1, ("finance", "postings", 0, "amount_minor"), -2141))
        self.assert_snapshot_rejected(patched(feb1, ("finance", "postings", 0, "source"), "draw:2031-02-02"))
        self.assert_snapshot_rejected(patched(feb1, ("finance", "postings", 0, "product_id"), "prod-a"))

        feb2 = self.one_posting("draw", -2143, day=2, monthly_draw=60000)
        feb2 = patched(feb2, ("finance", "postings", 0, "source"), "draw:2031-02-02")
        feb2 = patched(feb2, ("events", 0, "source"), "draw:2031-02-02")
        self.assert_accepts(feb2)

        leap = self.one_posting("draw", -2068, day=1, monthly_draw=60000, start_date="2032-01-31")
        leap = patched(leap, ("finance", "postings", 0, "source"), "draw:2032-02-01")
        leap = patched(leap, ("events", 0, "source"), "draw:2032-02-01")
        self.assert_accepts(leap)

        # no founder draw posting on the initial day
        day0 = self.one_posting("draw", -1936, day=0, monthly_draw=60000)
        day0 = patched(day0, ("finance", "postings", 0, "source"), "draw:2031-01-31")
        day0 = patched(day0, ("events", 0, "source"), "draw:2031-01-31")
        self.assert_snapshot_rejected(day0)

        # monthly draw zero can never produce a nonzero draw posting
        zero = self.one_posting("draw", -1, day=1, monthly_draw=0)
        zero = patched(zero, ("finance", "postings", 0, "source"), "draw:2031-02-01")
        zero = patched(zero, ("events", 0, "source"), "draw:2031-02-01")
        self.assert_snapshot_rejected(zero)

    def test_at_most_one_draw_posting_per_date(self):
        postings = posting_list(
            {"day": 1, "category": "draw", "amount_minor": -2142, "source": "draw:2031-02-01", "product_id": None},
            {"day": 1, "category": "draw", "amount_minor": -2142, "source": "draw:2031-02-01", "product_id": None},
        )
        events = event_list(
            {"day": 1, "kind": "cash_posted", "source": "draw:2031-02-01", "subject_id": None, "facts": {"posting_id": "p-1"}},
            {"day": 1, "kind": "cash_posted", "source": "draw:2031-02-01", "subject_id": None, "facts": {"posting_id": "p-2"}},
        )
        payload = build(day=1, monthly_draw=60000, postings=postings, events=events)
        self.assert_snapshot_rejected(payload)

    def test_paid_obligation_requires_one_matching_posting(self):
        base = self.obligation_payload()
        self.assert_accepts(base)
        self.assert_snapshot_rejected(patched(base, ("finance", "postings", 0, "amount_minor"), -499))
        self.assert_snapshot_rejected(patched(base, ("finance", "postings", 0, "source"), "cmd:c-9"))
        self.assert_snapshot_rejected(patched(base, ("finance", "postings", 0, "category"), "financing"))
        self.assert_snapshot_rejected(patched(base, ("finance", "postings", 0, "product_id"), "prod-a"))
        self.assert_snapshot_rejected(patched(base, ("finance", "postings", 0, "day"), 2))
        self.assert_snapshot_rejected(without(base, ("finance", "postings", 0)))
        self.assert_snapshot_rejected(
            patched(
                base,
                ("finance", "obligations", 0, "category"),
                "income",
            )
        )
        self.assert_snapshot_rejected(patched(base, ("finance", "obligations", 0, "paid"), False))

    def test_unpaid_obligations_have_no_posting_and_hold_future_due_days(self):
        payload = build(
            day=3,
            obligations=[
                {
                    "id": "ob-1",
                    "due_day": 9,
                    "category": "income",
                    "amount_minor": 500,
                    "product_id": None,
                    "paid": False,
                }
            ],
        )
        self.assert_accepts(payload)
        self.assert_snapshot_rejected(patched(payload, ("finance", "obligations", 0, "due_day"), 3))
        self.assert_snapshot_rejected(patched(payload, ("finance", "obligations", 0, "due_day"), 0))
        self.assert_snapshot_rejected(patched(payload, ("finance", "obligations", 0, "paid"), True))
        self.assert_snapshot_rejected(patched(payload, ("finance", "obligations", 0, "category"), "draw"))
        self.assert_snapshot_rejected(patched(payload, ("finance", "obligations", 0, "amount_minor"), 0))
        self.assert_snapshot_rejected(patched(payload, ("finance", "obligations", 0, "amount_minor"), -500))

    def test_paid_obligation_cannot_be_due_after_today(self):
        base = self.obligation_payload()
        self.assert_snapshot_rejected(patched(base, ("finance", "obligations", 0, "due_day"), 9))

    def test_obligation_order_and_duplicates(self):
        obligations = [
            {"id": "ob-b", "due_day": 9, "category": "income", "amount_minor": 1, "product_id": None, "paid": False},
            {"id": "ob-a", "due_day": 9, "category": "income", "amount_minor": 1, "product_id": None, "paid": False},
        ]
        self.assert_snapshot_rejected(build(obligations=obligations))
        self.assert_accepts(build(obligations=list(reversed(obligations))))
        duplicated = [dict(obligations[0]), dict(obligations[0])]
        self.assert_snapshot_rejected(build(obligations=duplicated))
        self.assert_snapshot_rejected(patched(build(obligations=list(reversed(obligations))), ("finance", "obligations", 0, "extra"), 1))
        self.assert_snapshot_rejected(without(build(obligations=list(reversed(obligations))), ("finance", "obligations", 0, "paid")))

    def test_labor_attribution_rules(self):
        postings = posting_list(
            {"day": 0, "category": "expense", "amount_minor": -1200, "source": "cmd:c-1", "product_id": None}
        )
        events = event_list(
            {"day": 0, "kind": "cash_posted", "source": "cmd:c-1", "subject_id": None, "facts": {"posting_id": "p-1"}}
        )
        labor = [
            {"posting_id": "p-1", "product_id": "prod-a", "amount_minor": 700},
            {"posting_id": "p-1", "product_id": "prod-b", "amount_minor": 500},
        ]
        payload = build(postings=postings, events=events, labor=labor)
        self.assert_accepts(payload)
        self.assert_snapshot_rejected(patched(payload, ("finance", "labor", 0, "amount_minor"), 701))
        self.assert_snapshot_rejected(patched(payload, ("finance", "labor", 0, "amount_minor"), 0))
        self.assert_snapshot_rejected(patched(payload, ("finance", "labor", 1, "product_id"), "prod-a"))
        self.assert_snapshot_rejected(patched(payload, ("finance", "labor", 0, "posting_id"), "p-9"))
        self.assert_snapshot_rejected(patched(payload, ("finance", "labor", 0, "extra"), 1))
        self.assert_snapshot_rejected(without(payload, ("finance", "labor", 0, "amount_minor")))

    def test_labor_requires_expense_posting(self):
        postings = posting_list(
            {"day": 0, "category": "income", "amount_minor": 1000, "source": "cmd:c-1", "product_id": None}
        )
        events = event_list(
            {"day": 0, "kind": "cash_posted", "source": "cmd:c-1", "subject_id": None, "facts": {"posting_id": "p-1"}}
        )
        labor = [{"posting_id": "p-1", "product_id": "prod-a", "amount_minor": 100}]
        self.assert_snapshot_rejected(build(postings=postings, events=events, labor=labor))

    def test_labor_event_must_match_allocation(self):
        postings = posting_list(
            {"day": 0, "category": "expense", "amount_minor": -1200, "source": "cmd:c-1", "product_id": None}
        )
        labor = [{"posting_id": "p-1", "product_id": "prod-a", "amount_minor": 700}]
        events = event_list(
            {"day": 0, "kind": "cash_posted", "source": "cmd:c-1", "subject_id": None, "facts": {"posting_id": "p-1"}},
            {
                "day": 0,
                "kind": "labor_attributed",
                "source": "cmd:c-2",
                "subject_id": "prod-a",
                "facts": {"posting_id": "p-1", "amount_minor": 700},
            },
        )
        payload = build(postings=postings, events=events, labor=labor)
        self.assert_accepts(payload)
        self.assert_snapshot_rejected(patched(payload, ("events", 1, "facts", "amount_minor"), 500))
        self.assert_snapshot_rejected(patched(payload, ("events", 1, "facts", "amount_minor"), 0))
        self.assert_snapshot_rejected(patched(payload, ("events", 1, "subject_id"), "prod-z"))
        self.assert_snapshot_rejected(patched(payload, ("events", 1, "source"), "tick"))
        self.assert_snapshot_rejected(patched(payload, ("events", 1, "facts", "posting_id"), "p-9"))


class TestSnapshotStatus(RewriteTestCase):
    def test_negative_cash_requires_episode(self):
        payload = negative_payload(6)
        self.assert_accepts(payload)
        self.assert_snapshot_rejected(patched(payload, ("finance", "negative_since_day"), None))
        self.assert_snapshot_rejected(patched(payload, ("finance", "negative_since_day"), 0))
        self.assert_snapshot_rejected(patched(payload, ("finance", "negative_since_day"), 7))
        positive = build(
            opening=1000,
            negative_since=1,
            events=event_list(
                {
                    "day": 1,
                    "kind": "liquidity_warning",
                    "source": "tick",
                    "subject_id": None,
                    "facts": {"negative_since_day": 1},
                }
            ),
        )
        self.assert_snapshot_rejected(positive)

    def test_seven_day_insolvency_boundary(self):
        self.assert_accepts(negative_payload(6))
        self.assert_snapshot_rejected(negative_payload(7))
        self.assert_accepts(negative_payload(7, status="failed"))
        self.assert_snapshot_rejected(negative_payload(6, status="failed"))
        self.assert_snapshot_rejected(negative_payload(7, negative_since=2, status="failed"))
        self.assert_accepts(negative_payload(8, negative_since=2, status="failed"))
        self.assert_accepts(negative_payload(2, status="retired"))
        self.assert_accepts(negative_payload(6, status="retired"))
        failed = negative_payload(7, status="failed")
        self.assert_snapshot_rejected(patched(failed, ("finance", "negative_since_day"), None))

    def test_liquidity_warning_shape(self):
        payload = negative_payload(6)
        self.assert_snapshot_rejected(patched(payload, ("events", 1, "facts", "negative_since_day"), 2))
        self.assert_snapshot_rejected(patched(payload, ("events", 1, "source"), "cmd:c-9"))
        self.assert_snapshot_rejected(patched(payload, ("events", 1, "subject_id"), "prod-a"))
        self.assert_snapshot_rejected(patched(payload, ("events", 1, "facts"), {"extra": 1}))
        self.assert_snapshot_rejected(patched(payload, ("events", 1, "facts", "negative_since_day"), True))
        self.assert_snapshot_rejected(keep_events(payload, {"cash_posted"}))
        stale = patched(payload, ("events", 1, "day"), 5)
        stale = patched(stale, ("events", 1, "facts", "negative_since_day"), 5)
        self.assert_snapshot_rejected(stale)
        duplicate_warnings = copy.deepcopy(payload)
        duplicate_warnings["events"] = event_list(
            {"day": 1, "kind": "cash_posted", "source": "cmd:c-1", "subject_id": None, "facts": {"posting_id": "p-1"}},
            {
                "day": 1,
                "kind": "liquidity_warning",
                "source": "tick",
                "subject_id": None,
                "facts": {"negative_since_day": 1},
            },
            {
                "day": 1,
                "kind": "liquidity_warning",
                "source": "tick",
                "subject_id": None,
                "facts": {"negative_since_day": 1},
            },
        )
        duplicate_warnings["next_event_id"] = 4
        self.assert_snapshot_rejected(duplicate_warnings)

    def test_campaign_closed_rules(self):
        failed = negative_payload(7, status="failed")
        self.assert_accepts(failed)
        retired = negative_payload(3, status="retired")
        self.assert_accepts(retired)
        self.assert_snapshot_rejected(keep_events(retired, {"cash_posted", "liquidity_warning"}))
        self.assert_snapshot_rejected(keep_events(failed, {"cash_posted", "liquidity_warning"}))
        running = negative_payload(6)
        with_closure = copy.deepcopy(running)
        with_closure["events"] = event_list(
            {"day": 1, "kind": "cash_posted", "source": "cmd:c-1", "subject_id": None, "facts": {"posting_id": "p-1"}},
            {
                "day": 1,
                "kind": "liquidity_warning",
                "source": "tick",
                "subject_id": None,
                "facts": {"negative_since_day": 1},
            },
            {"day": 3, "kind": "campaign_closed", "source": "cmd:c-9", "subject_id": None, "facts": {"reason": "retired"}},
        )
        with_closure["next_event_id"] = 4
        self.assert_snapshot_rejected(with_closure)
        mismatched = patched(failed, ("events", 2, "facts", "reason"), "retired")
        mismatched = patched(mismatched, ("events", 2, "source"), "cmd:c-9")
        self.assert_snapshot_rejected(mismatched)
        twice = copy.deepcopy(failed)
        twice["events"] = event_list(
            {"day": 1, "kind": "cash_posted", "source": "cmd:c-1", "subject_id": None, "facts": {"posting_id": "p-1"}},
            {
                "day": 1,
                "kind": "liquidity_warning",
                "source": "tick",
                "subject_id": None,
                "facts": {"negative_since_day": 1},
            },
            {"day": 7, "kind": "campaign_closed", "source": "tick", "subject_id": None, "facts": {"reason": "insolvent"}},
            {"day": 7, "kind": "campaign_closed", "source": "tick", "subject_id": None, "facts": {"reason": "insolvent"}},
        )
        twice["next_event_id"] = 5
        self.assert_snapshot_rejected(twice)

    def test_status_and_closed_reason_consistency(self):
        rich = rich_payload()
        self.assert_snapshot_rejected(patched(rich, ("status",), "retired"))
        self.assert_snapshot_rejected(patched(rich, ("status",), "failed"))
        self.assert_snapshot_rejected(patched(rich, ("closed_reason",), "retired"))
        self.assert_snapshot_rejected(patched(rich, ("closed_reason",), "insolvent"))
        retired = negative_payload(3, status="retired")
        self.assert_snapshot_rejected(patched(retired, ("closed_reason",), None))
        self.assert_snapshot_rejected(patched(retired, ("closed_reason",), "insolvent"))
        failed = negative_payload(7, status="failed")
        self.assert_snapshot_rejected(patched(failed, ("closed_reason",), "retired"))
        self.assert_snapshot_rejected(patched(failed, ("closed_reason",), None))

    def test_manual_paused_tracks_pause_events(self):
        self.assert_snapshot_rejected(build(manual_paused=True))
        pause = event_list(
            {"day": 0, "kind": "pause_changed", "source": "cmd:c-1", "subject_id": None, "facts": {"paused": True}}
        )
        payload = build(manual_paused=True, events=pause)
        self.assert_accepts(payload)
        self.assert_snapshot_rejected(patched(payload, ("manual_paused",), False))
        self.assert_snapshot_rejected(patched(payload, ("events", 0, "facts", "paused"), False))
        self.assert_snapshot_rejected(patched(payload, ("events", 0, "source"), "tick"))
        self.assert_snapshot_rejected(patched(payload, ("events", 0, "subject_id"), "prod-a"))
        self.assert_snapshot_rejected(patched(payload, ("events", 0, "facts"), {"paused": 1}))

    def test_event_reference_semantics(self):
        rich = rich_payload()
        self.assert_snapshot_rejected(patched(rich, ("events", 1, "subject_id"), "dec-z"))
        self.assert_snapshot_rejected(patched(rich, ("events", 1, "facts"), {"extra": 1}))
        self.assert_snapshot_rejected(patched(rich, ("events", 1, "source"), "tick"))
        self.assert_snapshot_rejected(patched(rich, ("events", 0, "facts", "posting_id"), "p-9"))
        self.assert_snapshot_rejected(patched(rich, ("events", 0, "source"), "cmd:c-9"))
        self.assert_snapshot_rejected(patched(rich, ("events", 0, "day"), 2))
        self.assert_snapshot_rejected(patched(rich, ("events", 0, "kind"), "unknown_kind"))
        self.assert_snapshot_rejected(patched(rich, ("events", 3, "kind"), "obligation_added"))
        orphan_posting = build(
            postings=posting_list(
                {"day": 0, "category": "income", "amount_minor": 5, "source": "cmd:c-1", "product_id": None}
            )
        )
        self.assert_snapshot_rejected(orphan_posting)

    def test_obligation_added_event_references(self):
        payload = build(
            day=3,
            obligations=[
                {
                    "id": "ob-1",
                    "due_day": 9,
                    "category": "income",
                    "amount_minor": 500,
                    "product_id": None,
                    "paid": False,
                }
            ],
            events=event_list(
                {"day": 0, "kind": "obligation_added", "source": "cmd:c-1", "subject_id": "ob-1", "facts": {}}
            ),
        )
        self.assert_accepts(payload)
        self.assert_snapshot_rejected(patched(payload, ("events", 0, "subject_id"), "ob-9"))
        self.assert_snapshot_rejected(patched(payload, ("events", 0, "source"), "tick"))

    def test_decision_resolved_event_references(self):
        rich = rich_payload()
        self.assert_accepts(rich)
        self.assert_snapshot_rejected(patched(rich, ("decisions", 0, "resolved"), False))
        self.assert_snapshot_rejected(patched(rich, ("decisions", 1, "resolved"), True))
        self.assert_snapshot_rejected(patched(rich, ("decisions", 0, "due_day"), 4))

    def test_collection_caps(self):
        decisions = [
            {"id": f"d-{index:03d}", "due_day": 0, "reason": "review", "resolved": False}
            for index in range(65)
        ]
        self.assert_snapshot_rejected(build(decisions=decisions))
        self.assert_accepts(build(decisions=decisions[:64]))

        receipts = [
            {
                "command_id": f"c-{index}",
                "fingerprint": "ab" * 32,
                "applied_revision": index + 1,
                "event_ids": [],
            }
            for index in range(65)
        ]
        self.assert_snapshot_rejected(build(revision=65, receipts=receipts))
        self.assert_accepts(build(revision=64, receipts=receipts[:64]))

        obligations = [
            {
                "id": f"o-{index:04d}",
                "due_day": 1,
                "category": "income",
                "amount_minor": 1,
                "product_id": None,
                "paid": False,
            }
            for index in range(1, 514)
        ]
        self.assert_snapshot_rejected(build(obligations=obligations))
        self.assert_accepts(build(obligations=obligations[:512]))

        expense_postings = posting_list(
            {"day": 0, "category": "expense", "amount_minor": -5000, "source": "cmd:c-1", "product_id": None}
        )
        expense_events = event_list(
            {
                "day": 0,
                "kind": "cash_posted",
                "source": "cmd:c-1",
                "subject_id": None,
                "facts": {"posting_id": "p-1"},
            }
        )
        labor = [
            {"posting_id": "p-1", "product_id": f"prod-{index:04d}", "amount_minor": 1}
            for index in range(4097)
        ]
        self.assert_snapshot_rejected(build(postings=expense_postings, events=expense_events, labor=labor))
        self.assert_accepts(build(postings=expense_postings, events=expense_events, labor=labor[:4096]))

        pause_events = [
            {
                "id": f"e-{index + 1}",
                "day": 0,
                "kind": "pause_changed",
                "source": "cmd:c-1",
                "subject_id": None,
                "facts": {"paused": bool(index % 2)},
            }
            for index in range(8193)
        ]
        self.assert_snapshot_rejected(build(events=pause_events))
        self.assert_accepts(build(events=pause_events[:8192], manual_paused=True))

        many_postings = posting_list(
            *[
                {"day": 0, "category": "income", "amount_minor": 1, "source": "cmd:c-1", "product_id": None}
                for _ in range(8193)
            ]
        )
        many_events = event_list(
            *[
                {
                    "day": 0,
                    "kind": "cash_posted",
                    "source": "cmd:c-1",
                    "subject_id": None,
                    "facts": {"posting_id": f"p-{index}"},
                }
                for index in range(1, 8193)
            ]
        )
        self.assert_snapshot_rejected(build(postings=many_postings, events=many_events))

    def test_receipt_revision_cap_and_ordering(self):
        receipts = [
            {
                "command_id": f"c-{index}",
                "fingerprint": "ab" * 32,
                "applied_revision": index,
                "event_ids": [],
            }
            for index in range(1, 65)
        ]
        self.assert_accepts(build(revision=64, receipts=receipts))
        shuffled = copy.deepcopy(receipts)
        shuffled[10], shuffled[11] = shuffled[11], shuffled[10]
        self.assert_snapshot_rejected(build(revision=64, receipts=shuffled))


# ---------------------------------------------------------------------------
# SaveStore: real temp files under $TMPDIR
# ---------------------------------------------------------------------------


def failed_ironman_payload(*, campaign_id="iron-1", revision=7, day=7, negative_since=1, opening=1000):
    postings = posting_list(
        {"day": 1, "category": "expense", "amount_minor": -1800, "source": "cmd:c-1", "product_id": None}
    )
    events = event_list(
        {"day": 1, "kind": "cash_posted", "source": "cmd:c-1", "subject_id": None, "facts": {"posting_id": "p-1"}},
        {
            "day": negative_since,
            "kind": "liquidity_warning",
            "source": "tick",
            "subject_id": None,
            "facts": {"negative_since_day": negative_since},
        },
        {"day": day, "kind": "campaign_closed", "source": "tick", "subject_id": None, "facts": {"reason": "insolvent"}},
    )
    return build(
        campaign_id=campaign_id,
        mode="ironman",
        day=day,
        revision=revision,
        status="failed",
        closed_reason="insolvent",
        opening=opening,
        negative_since=negative_since,
        postings=postings,
        events=events,
    )


def failed_normal_payload(*, campaign_id="normal-fail", revision=7, day=7):
    payload = failed_ironman_payload(campaign_id=campaign_id, revision=revision, day=day)
    payload["mode"] = "normal"
    return payload


class StoreTestCase(RewriteTestCase):
    def setUp(self):
        _TEMP_ROOT.mkdir(parents=True, exist_ok=True)
        self._tmp = tempfile.TemporaryDirectory(dir=str(_TEMP_ROOT))
        self.addCleanup(self._tmp.cleanup)
        self.base = pathlib.Path(self._tmp.name)
        self.root = self.base / "saves"

    def new_store(self, root=None):
        return SaveStore(self.root if root is None else root)

    def campaign_dir(self, campaign_id="kernel-test", root=None):
        base = self.root if root is None else root
        return base / campaign_id

    def listing(self, directory):
        return sorted(entry.name for entry in directory.iterdir())

    def assert_no_temps(self, directory):
        leftovers = [
            name
            for name in self.listing(directory)
            if name.startswith(".") and name.endswith(".part")
        ]
        self.assertEqual(leftovers, [], msg=f"temporary files left behind: {leftovers}")

    def two_save_state(self, campaign_id="kernel-test"):
        store = self.new_store()
        p0 = k5_payload()
        p1 = patched(p0, ("revision",), 1)
        store.save(p0)
        store.save(p1)
        directory = self.campaign_dir(campaign_id)
        self.assertEqual(store.load(campaign_id), p1)
        self.assertEqual(store.load(campaign_id, "backup"), p0)
        return store, directory, p0, p1

    def snapshot(self, directory):
        return {path.name: path.read_bytes() for path in directory.iterdir()}

    def assert_state(self, store, expected_primary, expected_backup, campaign_id="kernel-test"):
        self.assertEqual(store.load(campaign_id), expected_primary)
        self.assertEqual(store.load(campaign_id, "backup"), expected_backup)

    def patch_write(self, *, fail_on=None, mutate_first=False):
        real = os.write
        calls = []

        def wrapper(fd, data):
            calls.append(bytes(data))
            index = len(calls)
            if mutate_first and index == 1:
                return real(fd, b"[" + bytes(data)[1:])
            if fail_on is not None and index == fail_on:
                raise OSError(errno.ENOSPC, "injected write failure")
            return real(fd, data)

        return wrapper, calls

    def patch_fsync(self, fail_on):
        real = os.fsync
        calls = []

        def wrapper(fd):
            calls.append(fd)
            if len(calls) == fail_on:
                raise OSError(errno.EIO, "injected fsync failure")
            return real(fd)

        return wrapper, calls

    def patch_replace(self, fail_suffix):
        real = os.replace
        calls = []

        def wrapper(src, dst):
            calls.append(str(dst))
            if str(dst).endswith(fail_suffix):
                raise OSError(errno.EIO, "injected replace failure")
            return real(src, dst)

        return wrapper, calls

    def patch_read(self, fail_on):
        real = os.read
        calls = []

        def wrapper(fd, size):
            calls.append(fd)
            if len(calls) == fail_on:
                raise OSError(errno.EIO, "injected read failure")
            return real(fd, size)

        return wrapper, calls


class TestSaveStoreBasics(StoreTestCase):
    def test_root_created_and_first_save_layout(self):
        store = self.new_store()
        self.assertTrue(self.root.is_dir())
        store.save(k5_payload())
        directory = self.campaign_dir()
        self.assertEqual(self.listing(directory), [LOCK, PRIMARY])
        self.assertEqual(self.listing(self.root), ["kernel-test"])
        self.assertEqual(store.load("kernel-test"), k5_payload())
        self.assert_code("not_found", store.load, "kernel-test", "backup")
        self.assert_code("not_found", store.load, "kernel-test", "recovery")
        self.assert_no_temps(directory)

    def test_second_save_creates_backup_of_previous_primary(self):
        store, directory, p0, p1 = self.two_save_state()
        self.assertEqual(self.listing(directory), sorted([LOCK, BACKUP, PRIMARY]))
        self.assertEqual((directory / BACKUP).read_bytes(), encode(p0))
        self.assertEqual((directory / PRIMARY).read_bytes(), encode(p1))
        self.assert_no_temps(directory)

    def test_revision_conflict_matrix(self):
        store, _, p0, p1 = self.two_save_state()
        p0_late = patched(p0, ("revision",), 0)
        self.assert_code("conflict", store.save, p0_late)
        same_rev_other = patched(p1, ("day",), 1)
        self.assert_code("conflict", store.save, same_rev_other)
        p2 = patched(p0, ("revision",), 2)
        store.save(p2)
        self.assertEqual(store.load("kernel-test"), p2)
        self.assertEqual(store.load("kernel-test", "backup"), p1)

    def test_identical_revision_and_payload_is_idempotent_noop(self):
        store, directory, _, p1 = self.two_save_state()
        before = {path.name: path.read_bytes() for path in directory.iterdir()}
        store.save(copy.deepcopy(p1))
        after = {path.name: path.read_bytes() for path in directory.iterdir()}
        self.assertEqual(before, after)
        self.assert_no_temps(directory)

    def test_invalid_payload_touches_nothing(self):
        store, directory, _, p1 = self.two_save_state()
        before = {path.name: path.read_bytes() for path in directory.iterdir()}
        bad = patched(k5_payload(), ("extra",), 1)
        self.assert_code("invalid_payload", store.save, bad)
        bad_id = patched(k5_payload(), ("campaign_id",), "../escape")
        self.assert_code("invalid_payload", store.save, bad_id)
        after = {path.name: path.read_bytes() for path in directory.iterdir()}
        self.assertEqual(before, after)
        self.assertEqual(store.load("kernel-test"), p1)
        self.assert_no_temps(directory)

    def test_load_missing_campaign_does_not_create_it(self):
        store = self.new_store()
        self.assert_code("not_found", store.load, "kernel-test")
        self.assert_code("not_found", store.load, "kernel-test", "backup")
        self.assert_code("not_found", store.recover_backup, "kernel-test")
        self.assertEqual(self.listing(self.root), [])

    def test_load_source_allowlist(self):
        store = self.new_store()
        store.save(k5_payload())
        for source in ("other", "PRIMARY", "", "autosave.studio.json", None, 5, "../primary"):
            with self.subTest(source=source):
                self.assert_code("unsafe_path", store.load, "kernel-test", source)

    def test_corrupt_primary_blocks_save_and_preserves_backup(self):
        store, directory, p0, _ = self.two_save_state()
        (directory / PRIMARY).write_bytes(b"{not valid json")
        backup_bytes = (directory / BACKUP).read_bytes()
        p2 = patched(k5_payload(), ("revision",), 2)
        self.assert_code("corrupt_primary", store.save, p2)
        self.assertEqual((directory / PRIMARY).read_bytes(), b"{not valid json")
        self.assertEqual((directory / BACKUP).read_bytes(), backup_bytes)
        self.assert_code("invalid_json", store.load, "kernel-test")
        self.assertEqual(store.load("kernel-test", "backup"), p0)
        self.assert_no_temps(directory)

    def test_corrupt_primary_never_overwrites_known_good_backup(self):
        store, directory, p0, _ = self.two_save_state()
        good_backup = (directory / BACKUP).read_bytes()
        tampered = encode(patched(k5_payload(), ("seed",), 7)).replace(b'"seed":7', b'"seed":8')
        (directory / PRIMARY).write_bytes(tampered)
        self.assert_code("corrupt_primary", store.save, patched(k5_payload(), ("revision",), 3))
        self.assertEqual((directory / BACKUP).read_bytes(), good_backup)
        self.assertEqual(store.load("kernel-test", "backup"), p0)

    def test_normal_failed_campaign_is_saved_and_inspectable(self):
        store = self.new_store()
        failed = failed_normal_payload()
        store.save(failed)
        directory = self.campaign_dir("normal-fail")
        self.assertFalse((directory / MARKER).exists())
        self.assertEqual(store.load("normal-fail"), failed)
        self.assertEqual(store.load("normal-fail", "primary")["status"], "failed")
        self.assert_no_temps(directory)

    def test_load_primary_without_fallback_when_primary_missing(self):
        store = self.new_store()
        p0 = k5_payload()
        p1 = patched(p0, ("revision",), 1)
        store.save(p0)
        store.save(p1)
        directory = self.campaign_dir()
        (directory / PRIMARY).unlink()
        self.assert_code("not_found", store.load, "kernel-test")
        self.assertEqual(store.load("kernel-test", "backup"), p0)

    def test_backup_load_never_mutates_files(self):
        store, directory, p0, _ = self.two_save_state()
        before = {path.name: path.read_bytes() for path in directory.iterdir()}
        self.assertEqual(store.load("kernel-test", "backup"), p0)
        after = {path.name: path.read_bytes() for path in directory.iterdir()}
        self.assertEqual(before, after)

    def test_save_without_primary_uses_backup_as_revision_floor(self):
        store = self.new_store()
        p0 = k5_payload()
        p1 = patched(p0, ("revision",), 1)
        p2 = patched(p0, ("revision",), 2)
        store.save(p0)
        store.save(p1)
        store.save(p2)
        directory = self.campaign_dir()
        self.assertEqual(store.load("kernel-test", "backup"), p1)
        (directory / PRIMARY).unlink()
        self.assert_code("conflict", store.save, p0)
        store.save(p2)
        self.assertEqual((directory / PRIMARY).read_bytes(), encode(p2))
        self.assertEqual((directory / BACKUP).read_bytes(), encode(p1))
        self.assert_no_temps(directory)


class TestRecoveryAndBackup(StoreTestCase):
    def test_recover_backup_creates_fixed_recovery_file(self):
        store, directory, p0, p1 = self.two_save_state()
        primary_bytes = (directory / PRIMARY).read_bytes()
        backup_bytes = (directory / BACKUP).read_bytes()
        target = store.recover_backup("kernel-test")
        self.assertEqual(target, directory / RECOVERY)
        self.assertEqual(target.read_bytes(), encode(p0))
        self.assertEqual(store.load("kernel-test", "recovery"), p0)
        self.assertEqual((directory / PRIMARY).read_bytes(), primary_bytes)
        self.assertEqual((directory / BACKUP).read_bytes(), backup_bytes)
        self.assert_no_temps(directory)

    def test_existing_recovery_conflicts(self):
        store, directory, p0, _ = self.two_save_state()
        target = store.recover_backup("kernel-test")
        original = target.read_bytes()
        self.assert_code("conflict", store.recover_backup, "kernel-test")
        self.assertEqual(target.read_bytes(), original)
        self.assertEqual(store.load("kernel-test", "recovery"), p0)

    def test_recover_requires_a_backup(self):
        store = self.new_store()
        store.save(k5_payload())
        self.assert_code("not_found", store.recover_backup, "kernel-test")
        self.assertFalse((self.campaign_dir() / RECOVERY).exists())

    def test_recover_corrupt_backup_fails_without_creating_recovery(self):
        store, directory, _, p1 = self.two_save_state()
        (directory / BACKUP).write_bytes(b"garbage backup")
        primary_bytes = (directory / PRIMARY).read_bytes()
        self.assert_code("invalid_json", store.recover_backup, "kernel-test")
        self.assertFalse((directory / RECOVERY).exists())
        self.assertEqual((directory / PRIMARY).read_bytes(), primary_bytes)
        self.assertEqual(store.load("kernel-test"), p1)
        self.assert_no_temps(directory)

    def test_recovery_content_is_canonical_envelope(self):
        store, directory, p0, _ = self.two_save_state()
        target = store.recover_backup("kernel-test")
        self.assertEqual(target.read_bytes(), encode(p0))
        self.assertEqual(decode(target.read_bytes()), p0)


class TestOwnershipAndPaths(StoreTestCase):
    def test_invalid_campaign_ids_are_unsafe_paths(self):
        store = self.new_store()
        store.save(k5_payload())
        for bad in (
            "../escape",
            "a/b",
            "/abs",
            "C:\\x",
            "",
            ".",
            "..",
            "A",
            "1a",
            "a" * 49,
            "a b",
            "caf\u00e9",
            "a\x00b",
            "kernel-test/",
        ):
            with self.subTest(campaign_id=bad):
                self.assert_code("unsafe_path", store.load, bad)
                self.assert_code("unsafe_path", store.recover_backup, bad)

    def test_invalid_campaign_id_in_payload_is_invalid_payload(self):
        store = self.new_store()
        for bad in ("../escape", "a/b", "A"):
            with self.subTest(campaign_id=bad):
                self.assert_code(
                    "invalid_payload", store.save, patched(k5_payload(), ("campaign_id",), bad)
                )

    def test_campaign_directory_symlink_rejected(self):
        store = self.new_store()
        elsewhere = self.base / "elsewhere"
        elsewhere.mkdir()
        (self.root / "kernel-test").symlink_to(elsewhere, target_is_directory=True)
        self.assert_code("unsafe_path", store.load, "kernel-test")
        self.assert_code("unsafe_path", store.save, k5_payload())
        self.assert_code("unsafe_path", store.recover_backup, "kernel-test")
        self.assert_code("unsafe_path", store.invalidate_failed, failed_ironman_payload(campaign_id="kernel-test"))
        self.assertEqual(list(elsewhere.iterdir()), [])

    def test_named_primary_symlink_rejected(self):
        store, directory, _, p1 = self.two_save_state()
        elsewhere = self.base / "elsewhere.json"
        elsewhere.write_bytes((directory / PRIMARY).read_bytes())
        (directory / PRIMARY).unlink()
        (directory / PRIMARY).symlink_to(elsewhere)
        self.assert_code("unsafe_path", store.load, "kernel-test")
        self.assert_code("unsafe_path", store.save, patched(k5_payload(), ("revision",), 2))
        self.assertEqual(elsewhere.read_bytes(), encode(p1))

    def test_lock_file_symlink_rejected(self):
        store = self.new_store()
        store.save(k5_payload())
        directory = self.campaign_dir()
        target = self.base / "lock-target"
        target.write_bytes(b"")
        (directory / LOCK).unlink()
        (directory / LOCK).symlink_to(target)
        self.assert_code("unsafe_path", store.save, patched(k5_payload(), ("revision",), 1))
        self.assert_code("unsafe_path", store.load, "kernel-test")

    def test_marker_symlink_rejected(self):
        store = self.new_store()
        store.save(failed_ironman_payload())
        directory = self.campaign_dir("iron-1")
        target = self.base / "marker-target"
        target.write_bytes(b"{}")
        (directory / MARKER).unlink()
        (directory / MARKER).symlink_to(target)
        self.assert_code("unsafe_path", store.load, "iron-1")
        self.assert_code("unsafe_path", store.save, failed_ironman_payload())
        self.assertEqual(target.read_bytes(), b"{}")

    def test_root_symlink_rejected(self):
        real = self.base / "real-root"
        real.mkdir()
        link = self.base / "link-root"
        link.symlink_to(real, target_is_directory=True)
        self.assert_code("unsafe_path", SaveStore, link)
        self.assertEqual(list(real.iterdir()), [])

    def test_root_ancestor_symlink_rejected(self):
        real = self.base / "real-parent"
        real.mkdir()
        link = self.base / "link-parent"
        link.symlink_to(real, target_is_directory=True)
        self.assert_code("unsafe_path", SaveStore, link / "saves")
        self.assertEqual(list(real.iterdir()), [])

    def test_root_is_a_file(self):
        self.root.write_bytes(b"not a directory")
        self.assert_code("unsafe_path", SaveStore, self.root)

    def test_wrong_campaign_content_is_ownership_error(self):
        store = self.new_store()
        store.save(k5_payload())
        alpha_bytes = (self.campaign_dir("kernel-test") / PRIMARY).read_bytes()
        beta_dir = self.root / "beta"
        beta_dir.mkdir()
        (beta_dir / PRIMARY).write_bytes(alpha_bytes)
        (beta_dir / BACKUP).write_bytes(alpha_bytes)
        self.assert_code("ownership", store.load, "beta")
        self.assert_code("ownership", store.load, "beta", "backup")
        self.assert_code("ownership", store.recover_backup, "beta")
        beta_payload = patched(k5_payload(), ("campaign_id",), "beta")
        self.assert_code("ownership", store.save, beta_payload)

    def test_mode_is_immutable(self):
        store = self.new_store()
        store.save(k5_payload())
        iron = patched(k5_payload(), ("revision",), 1)
        iron = patched(iron, ("mode",), "ironman")
        self.assert_code("ownership", store.save, iron)

        second_root = self.base / "saves2"
        store2 = SaveStore(second_root)
        store2.save(patched(k5_payload(), ("mode",), "ironman"))
        normal = patched(k5_payload(), ("revision",), 1)
        self.assert_code("ownership", store2.save, normal)

    def test_backup_only_ownership_guard(self):
        store = self.new_store()
        store.save(k5_payload())
        gamma_dir = self.root / "gamma"
        gamma_dir.mkdir()
        (gamma_dir / BACKUP).write_bytes(encode(k5_payload()))
        gamma_payload = patched(k5_payload(), ("campaign_id",), "gamma")
        gamma_payload = patched(gamma_payload, ("revision",), 5)
        self.assert_code("ownership", store.save, gamma_payload)
        self.assertEqual(self.listing(gamma_dir), sorted([LOCK, BACKUP]))


class TestLocking(StoreTestCase):
    def hold_lock(self, directory, operation):
        fd = os.open(str(directory / LOCK), os.O_RDWR | os.O_CREAT, 0o600)
        fcntl.flock(fd, operation | fcntl.LOCK_NB)
        return fd

    def test_shared_lock_allows_load_and_blocks_writers(self):
        store, directory, _, p1 = self.two_save_state()
        fd = self.hold_lock(directory, fcntl.LOCK_SH)
        try:
            self.assertEqual(store.load("kernel-test"), p1)
            self.assert_code("conflict", store.save, patched(k5_payload(), ("revision",), 2))
            self.assert_code("conflict", store.recover_backup, "kernel-test")
        finally:
            os.close(fd)
        p2 = patched(k5_payload(), ("revision",), 2)
        store.save(p2)
        self.assertEqual(store.load("kernel-test"), p2)

    def test_exclusive_lock_blocks_readers_and_writers(self):
        store, directory, _, _ = self.two_save_state()
        fd = self.hold_lock(directory, fcntl.LOCK_EX)
        try:
            self.assert_code("conflict", store.load, "kernel-test")
            self.assert_code("conflict", store.load, "kernel-test", "backup")
            self.assert_code("conflict", store.save, patched(k5_payload(), ("revision",), 2))
        finally:
            os.close(fd)
        self.assertEqual(store.load("kernel-test")["revision"], 1)

    def test_invalidate_respects_lock(self):
        store = self.new_store()
        store.save(patched(k5_payload(), ("mode",), "ironman"))
        directory = self.campaign_dir()
        fd = self.hold_lock(directory, fcntl.LOCK_EX)
        try:
            self.assert_code(
                "conflict",
                store.invalidate_failed,
                failed_ironman_payload(campaign_id="kernel-test", revision=1),
            )
        finally:
            os.close(fd)
        self.assertFalse((directory / MARKER).exists())

    def test_lock_file_is_permanent(self):
        store, directory, _, _ = self.two_save_state()
        lock_path = directory / LOCK
        inode = lock_path.stat().st_ino
        store.save(patched(k5_payload(), ("revision",), 2))
        store.load("kernel-test")
        store.recover_backup("kernel-test")
        self.assertTrue(lock_path.exists())
        self.assertEqual(lock_path.stat().st_ino, inode)

    def test_two_store_instances_share_one_lock_file(self):
        store, directory, _, _ = self.two_save_state()
        other = SaveStore(self.root)
        other.save(patched(k5_payload(), ("revision",), 2))
        self.assertEqual(store.load("kernel-test")["revision"], 2)
        self.assertEqual((directory / LOCK).stat().st_ino, (directory / LOCK).stat().st_ino)


class TestFaultInjection(StoreTestCase):
    """Precise stdlib faults at each commit stage, over real temp files."""

    def prepare(self):
        store, directory, p0, p1 = self.two_save_state()
        p2 = patched(k5_payload(), ("revision",), 2)
        self.assertEqual(self.listing(directory), sorted([LOCK, BACKUP, PRIMARY]))
        self.assert_no_temps(directory)
        return store, directory, p0, p1, p2

    def test_write_failure_leaves_old_copies(self):
        store, directory, p0, p1, p2 = self.prepare()
        before = self.snapshot(directory)
        wrapper, calls = self.patch_write(fail_on=1)
        with mock.patch.object(saves.os, "write", wrapper):
            self.assert_code("io", store.save, p2)
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.snapshot(directory), before)
        self.assert_state(store, p1, p0)
        self.assert_no_temps(directory)

    def test_short_writes_are_completed(self):
        store, directory, p0, p1, p2 = self.prepare()
        real = os.write
        calls = []

        def wrapper(fd, data):
            calls.append(len(data))
            return real(fd, bytes(data)[:3])

        with mock.patch.object(saves.os, "write", wrapper):
            store.save(p2)
        self.assertGreater(len(calls), 1)
        self.assert_state(store, p2, p1)
        self.assert_no_temps(directory)

    def test_primary_temp_fsync_failure(self):
        store, directory, p0, p1, p2 = self.prepare()
        before = self.snapshot(directory)
        wrapper, calls = self.patch_fsync(1)
        with mock.patch.object(saves.os, "fsync", wrapper):
            self.assert_code("io", store.save, p2)
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.snapshot(directory), before)
        self.assert_no_temps(directory)

    def test_backup_temp_fsync_failure(self):
        store, directory, p0, p1, p2 = self.prepare()
        before = self.snapshot(directory)
        wrapper, calls = self.patch_fsync(2)
        with mock.patch.object(saves.os, "fsync", wrapper):
            self.assert_code("io", store.save, p2)
        self.assertEqual(len(calls), 2)
        self.assertEqual(self.snapshot(directory), before)
        self.assert_no_temps(directory)

    def test_directory_fsync_failure_after_backup_replace(self):
        store, directory, p0, p1, p2 = self.prepare()
        wrapper, calls = self.patch_fsync(3)
        with mock.patch.object(saves.os, "fsync", wrapper):
            self.assert_code("io", store.save, p2)
        self.assertEqual(len(calls), 3)
        self.assert_state(store, p1, p1)
        self.assert_no_temps(directory)

    def test_final_directory_fsync_is_durability_uncertain(self):
        store, directory, p0, p1, p2 = self.prepare()
        wrapper, calls = self.patch_fsync(4)
        with mock.patch.object(saves.os, "fsync", wrapper):
            self.assert_code("durability_uncertain", store.save, p2)
        self.assertEqual(len(calls), 4)
        self.assert_state(store, p2, p1)
        self.assert_no_temps(directory)
        store.save(copy.deepcopy(p2))

    def test_backup_replace_failure(self):
        store, directory, p0, p1, p2 = self.prepare()
        before = self.snapshot(directory)
        wrapper, calls = self.patch_replace(BACKUP)
        with mock.patch.object(saves.os, "replace", wrapper):
            self.assert_code("io", store.save, p2)
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.snapshot(directory), before)
        self.assert_state(store, p1, p0)
        self.assert_no_temps(directory)

    def test_primary_replace_failure(self):
        store, directory, p0, p1, p2 = self.prepare()
        wrapper, calls = self.patch_replace(PRIMARY)
        with mock.patch.object(saves.os, "replace", wrapper):
            self.assert_code("io", store.save, p2)
        self.assertEqual(len(calls), 2)
        self.assert_state(store, p1, p1)
        self.assert_no_temps(directory)

    def test_temp_verify_mismatch(self):
        store, directory, p0, p1, p2 = self.prepare()
        before = self.snapshot(directory)
        wrapper, calls = self.patch_write(mutate_first=True)
        with mock.patch.object(saves.os, "write", wrapper):
            self.assert_code("io", store.save, p2)
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.snapshot(directory), before)
        self.assert_no_temps(directory)

    def test_temp_verify_read_failure(self):
        store, directory, p0, p1, p2 = self.prepare()
        before = self.snapshot(directory)
        wrapper, calls = self.patch_read(1)
        with mock.patch.object(saves.os, "read", wrapper):
            self.assert_code("io", store.save, p2)
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.snapshot(directory), before)
        self.assert_no_temps(directory)

    def test_first_save_primary_replace_failure_leaves_no_files(self):
        store = self.new_store()
        wrapper, calls = self.patch_replace(PRIMARY)
        with mock.patch.object(saves.os, "replace", wrapper):
            self.assert_code("io", store.save, k5_payload())
        self.assertEqual(len(calls), 1)
        directory = self.campaign_dir()
        self.assertEqual(self.listing(directory), [LOCK])
        self.assert_code("not_found", store.load, "kernel-test")
        self.assert_no_temps(directory)

    def test_first_save_write_failure_leaves_no_files(self):
        store = self.new_store()
        wrapper, calls = self.patch_write(fail_on=1)
        with mock.patch.object(saves.os, "write", wrapper):
            self.assert_code("io", store.save, k5_payload())
        self.assertEqual(len(calls), 1)
        directory = self.campaign_dir()
        self.assertEqual(self.listing(directory), [LOCK])
        self.assert_no_temps(directory)

    def test_save_succeeds_after_injected_fault(self):
        store, directory, p0, p1, p2 = self.prepare()
        wrapper, _ = self.patch_write(fail_on=1)
        with mock.patch.object(saves.os, "write", wrapper):
            self.assert_code("io", store.save, p2)
        store.save(p2)
        self.assert_state(store, p2, p1)
        self.assert_no_temps(directory)


def marker_document(**overrides):
    document = {
        "format_id": "studio-rewrite-failure",
        "schema_version": 1,
        "campaign_id": "kernel-test",
        "mode": "ironman",
        "revision": 1,
        "day": 7,
        "reason": "insolvent",
    }
    document.update(overrides)
    return canonical(document)


class TestIronmanInvalidation(StoreTestCase):
    def test_failed_ironman_save_writes_marker_only(self):
        store = self.new_store()
        store.save(failed_ironman_payload())
        directory = self.campaign_dir("iron-1")
        self.assertEqual(self.listing(directory), sorted([LOCK, MARKER]))
        marker = json.loads((directory / MARKER).read_bytes())
        self.assertEqual(
            marker,
            {
                "format_id": "studio-rewrite-failure",
                "schema_version": 1,
                "campaign_id": "iron-1",
                "mode": "ironman",
                "revision": 7,
                "day": 7,
                "reason": "insolvent",
            },
        )
        self.assertEqual((directory / MARKER).read_bytes(), canonical(marker))
        self.assertFalse((directory / PRIMARY).exists())
        self.assert_no_temps(directory)

    def test_marker_blocks_every_source_and_write(self):
        store = self.new_store()
        running = patched(k5_payload(), ("mode",), "ironman")
        store.save(running)
        directory = self.campaign_dir()
        store.save(failed_ironman_payload(campaign_id="kernel-test", revision=1))
        self.assertTrue((directory / MARKER).exists())
        self.assertTrue((directory / PRIMARY).exists())
        for source in ("primary", "backup", "recovery"):
            with self.subTest(source=source):
                self.assert_code("ironman_failed", store.load, "kernel-test", source)
        self.assert_code("ironman_failed", store.save, patched(running, ("revision",), 9))
        self.assert_code("ironman_failed", store.recover_backup, "kernel-test")

    def test_marker_idempotent_and_conflicting(self):
        store = self.new_store()
        failed = failed_ironman_payload()
        store.save(failed)
        directory = self.campaign_dir("iron-1")
        before = self.snapshot(directory)
        store.save(copy.deepcopy(failed))
        self.assertEqual(self.snapshot(directory), before)
        later = failed_ironman_payload(revision=8, day=8, negative_since=2)
        self.assert_code("conflict", store.save, later)
        self.assert_code("conflict", store.invalidate_failed, later)
        same_day_later = failed_ironman_payload(revision=8, day=7, negative_since=1)
        self.assert_code("conflict", store.invalidate_failed, same_day_later)
        self.assertEqual(self.snapshot(directory), before)

    def test_marker_revision_floor(self):
        store = self.new_store()
        running = patched(k5_payload(), ("mode",), "ironman")
        running = patched(running, ("revision",), 5)
        store.save(running)
        directory = self.campaign_dir()
        self.assert_code(
            "conflict",
            store.invalidate_failed,
            failed_ironman_payload(campaign_id="kernel-test", revision=0),
        )
        self.assert_code(
            "conflict",
            store.invalidate_failed,
            failed_ironman_payload(campaign_id="kernel-test", revision=4),
        )
        self.assertFalse((directory / MARKER).exists())
        store.invalidate_failed(failed_ironman_payload(campaign_id="kernel-test", revision=5))
        self.assertTrue((directory / MARKER).exists())
        self.assertEqual(json.loads((directory / MARKER).read_bytes())["revision"], 5)
        self.assert_code("ironman_failed", store.load, "kernel-test")

    def test_invalidate_requires_valid_failed_ironman(self):
        store = self.new_store()
        retired = build(
            campaign_id="iron-1",
            mode="ironman",
            day=3,
            status="retired",
            closed_reason="retired",
            events=event_list(
                {
                    "day": 3,
                    "kind": "campaign_closed",
                    "source": "cmd:c-1",
                    "subject_id": None,
                    "facts": {"reason": "retired"},
                }
            ),
        )
        cases = {
            "normal failed": failed_normal_payload(),
            "ironman running": patched(k5_payload(), ("mode",), "ironman"),
            "ironman retired": retired,
            "invalid schema": patched(k5_payload(), ("extra",), 1),
            "failed without insolvency": patched(k5_payload(), ("status",), "failed"),
        }
        for label, payload in cases.items():
            with self.subTest(case=label):
                self.assert_code("invalid_payload", store.invalidate_failed, payload)
        self.assertEqual(self.listing(self.root), [])

    def test_marker_does_not_delete_owned_copies(self):
        store = self.new_store()
        running = patched(k5_payload(), ("mode",), "ironman")
        store.save(running)
        store.save(patched(running, ("revision",), 1))
        directory = self.campaign_dir()
        primary = (directory / PRIMARY).read_bytes()
        backup = (directory / BACKUP).read_bytes()
        store.invalidate_failed(failed_ironman_payload(campaign_id="kernel-test", revision=2))
        self.assertEqual((directory / PRIMARY).read_bytes(), primary)
        self.assertEqual((directory / BACKUP).read_bytes(), backup)
        self.assertEqual(self.listing(directory), sorted([LOCK, BACKUP, PRIMARY, MARKER]))

    def test_corrupt_marker_fails_closed(self):
        store = self.new_store()
        running = patched(k5_payload(), ("mode",), "ironman")
        store.save(running)
        directory = self.campaign_dir()
        primary = (directory / PRIMARY).read_bytes()
        missing_day = {
            key: value
            for key, value in json.loads(marker_document()).items()
            if key != "day"
        }
        variants = {
            "garbage": b"{not json",
            "empty object": b"{}",
            "wrong format": marker_document(format_id="other"),
            "wrong version": marker_document(schema_version=2),
            "missing day": canonical(missing_day),
            "wrong campaign": marker_document(campaign_id="other"),
            "wrong mode": marker_document(mode="normal"),
            "wrong reason": marker_document(reason="retired"),
            "float revision": marker_document(revision=1.5),
            "extra key": marker_document(extra=1),
        }
        for label, raw in variants.items():
            with self.subTest(marker=label):
                (directory / MARKER).write_bytes(raw)
                self.assert_code("integrity", store.load, "kernel-test")
                self.assert_code("integrity", store.save, patched(running, ("revision",), 1))
                self.assert_code("integrity", store.recover_backup, "kernel-test")
                self.assertEqual((directory / MARKER).read_bytes(), raw)
                self.assertEqual((directory / PRIMARY).read_bytes(), primary)

    def test_normal_failed_payload_never_invalidates(self):
        store = self.new_store()
        store.save(failed_normal_payload())
        directory = self.campaign_dir("normal-fail")
        self.assertFalse((directory / MARKER).exists())
        self.assertEqual(store.load("normal-fail")["status"], "failed")
        self.assert_code("invalid_payload", store.invalidate_failed, failed_normal_payload())

    def test_io_error_alone_never_infers_failure(self):
        store = self.new_store()
        running = patched(k5_payload(), ("mode",), "ironman")
        store.save(running)
        directory = self.campaign_dir()
        primary = (directory / PRIMARY).read_bytes()
        wrapper, calls = self.patch_read(1)
        with mock.patch.object(saves.os, "read", wrapper):
            self.assert_code("io", store.save, patched(running, ("revision",), 1))
        self.assertEqual(len(calls), 1)
        self.assertFalse((directory / MARKER).exists())
        self.assertEqual((directory / PRIMARY).read_bytes(), primary)

    def test_io_error_reading_marker_is_not_treated_as_malformed_or_failure(self):
        store = self.new_store()
        running = patched(k5_payload(), ("mode",), "ironman")
        store.save(running)
        directory = self.campaign_dir()
        corrupt = b"{not json"
        (directory / MARKER).write_bytes(corrupt)
        wrapper, calls = self.patch_read(1)
        with mock.patch.object(saves.os, "read", wrapper):
            self.assert_code("io", store.load, "kernel-test")
        self.assertEqual(len(calls), 1)
        self.assertEqual((directory / MARKER).read_bytes(), corrupt)

    def test_invalidation_with_corrupt_owned_files_still_needs_validated_payload(self):
        store = self.new_store()
        running = patched(k5_payload(), ("mode",), "ironman")
        store.save(running)
        directory = self.campaign_dir()
        (directory / PRIMARY).write_bytes(b"corrupt")
        self.assert_code("invalid_payload", store.invalidate_failed, patched(running, ("revision",), 3))
        self.assertFalse((directory / MARKER).exists())
        store.invalidate_failed(failed_ironman_payload(campaign_id="kernel-test", revision=1))
        self.assertTrue((directory / MARKER).exists())
        self.assertEqual((directory / PRIMARY).read_bytes(), b"corrupt")


class TestPreservation(StoreTestCase):
    def test_unrelated_files_are_never_touched(self):
        store = self.new_store()
        store.save(k5_payload())
        directory = self.campaign_dir()
        sentinels = {
            self.root / "legacy.sav": b"legacy save bytes",
            self.root / "README.txt": b"notes",
            directory / "user-notes.txt": b"do not delete",
            directory / "autosave.old.json": b"user copy",
        }
        for path, data in sentinels.items():
            path.write_bytes(data)
        store.save(patched(k5_payload(), ("revision",), 1))
        store.load("kernel-test")
        store.load("kernel-test", "backup")
        store.recover_backup("kernel-test")
        store.load("kernel-test", "recovery")
        for path, data in sentinels.items():
            with self.subTest(path=str(path)):
                self.assertTrue(path.exists())
                self.assertEqual(path.read_bytes(), data)
        self.assert_no_temps(directory)

    def test_invalidation_is_campaign_scoped(self):
        store = self.new_store()
        store.save(k5_payload())
        store.save(failed_ironman_payload(campaign_id="iron-1"))
        kernel_dir = self.campaign_dir("kernel-test")
        iron_dir = self.campaign_dir("iron-1")
        primary = (kernel_dir / PRIMARY).read_bytes()
        marker = (iron_dir / MARKER).read_bytes()
        self.assertEqual(store.load("kernel-test")["campaign_id"], "kernel-test")
        self.assertEqual((kernel_dir / PRIMARY).read_bytes(), primary)
        self.assertEqual((iron_dir / MARKER).read_bytes(), marker)

    def test_no_stray_files_created(self):
        store = self.new_store()
        store.save(k5_payload())
        store.save(patched(k5_payload(), ("revision",), 1))
        store.recover_backup("kernel-test")
        store.load("kernel-test", "recovery")
        directory = self.campaign_dir()
        self.assertEqual(self.listing(directory), sorted([LOCK, BACKUP, PRIMARY, RECOVERY]))
        self.assertEqual(self.listing(self.root), ["kernel-test"])
        self.assert_no_temps(directory)

    def test_save_after_marker_never_writes_resumable_autosave(self):
        store = self.new_store()
        store.save(failed_ironman_payload())
        directory = self.campaign_dir("iron-1")
        before = self.snapshot(directory)
        running = patched(k5_payload(), ("mode",), "ironman")
        running = patched(running, ("campaign_id",), "iron-1")
        self.assert_code("ironman_failed", store.save, running)
        self.assertEqual(self.snapshot(directory), before)
        self.assertFalse((directory / PRIMARY).exists())


class TestAdditionalStoreSafety(StoreTestCase):
    def test_oversized_primary_is_too_large(self):
        store = self.new_store()
        store.save(k5_payload())
        directory = self.campaign_dir()
        (directory / PRIMARY).write_bytes(b" " * (FOUR_MIB + 1))
        self.assert_code("too_large", store.load, "kernel-test")
        self.assert_code("corrupt_primary", store.save, patched(k5_payload(), ("revision",), 1))
        self.assertFalse((directory / BACKUP).exists())

    def test_non_ascii_reason_round_trips_canonically(self):
        store = self.new_store()
        payload = patched(k5_payload(), ("decisions",), [])
        payload["decisions"] = [
            {"id": "dec-a", "due_day": 0, "reason": "caf\u00e9 review", "resolved": False}
        ]
        store.save(payload)
        directory = self.campaign_dir()
        self.assertIn(b"caf\\u00e9", (directory / PRIMARY).read_bytes())
        self.assertEqual(store.load("kernel-test"), payload)

    def test_campaign_path_that_is_a_file(self):
        store = self.new_store()
        (self.root / "kernel-test").write_bytes(b"not a directory")
        self.assert_code("unsafe_path", store.load, "kernel-test")
        self.assert_code("unsafe_path", store.save, k5_payload())

    def test_recovery_write_fault_removes_partial_file(self):
        store, directory, p0, _ = self.two_save_state()
        wrapper, calls = self.patch_fsync(1)
        with mock.patch.object(saves.os, "fsync", wrapper):
            self.assert_code("io", store.recover_backup, "kernel-test")
        self.assertEqual(len(calls), 1)
        self.assertFalse((directory / RECOVERY).exists())
        self.assertEqual(store.load("kernel-test", "backup"), p0)

    def test_recovery_final_directory_fsync_is_durability_uncertain(self):
        store, directory, p0, _ = self.two_save_state()
        wrapper, calls = self.patch_fsync(2)
        with mock.patch.object(saves.os, "fsync", wrapper):
            self.assert_code("durability_uncertain", store.recover_backup, "kernel-test")
        self.assertEqual(len(calls), 2)
        self.assertTrue((directory / RECOVERY).exists())
        self.assertEqual(store.load("kernel-test", "recovery"), p0)

    def test_marker_write_fault_leaves_no_marker(self):
        store = self.new_store()
        wrapper, calls = self.patch_write(fail_on=1)
        with mock.patch.object(saves.os, "write", wrapper):
            self.assert_code("io", store.save, failed_ironman_payload())
        self.assertEqual(len(calls), 1)
        directory = self.campaign_dir("iron-1")
        self.assertEqual(self.listing(directory), [LOCK])
        self.assert_no_temps(directory)

    def test_primary_write_is_a_sibling_temp_file_then_replaced(self):
        store = self.new_store()
        wrapper, calls = self.patch_replace(PRIMARY)
        with mock.patch.object(saves.os, "replace", wrapper):
            self.assert_code("io", store.save, k5_payload())
        self.assertEqual(len(calls), 1)
        source, target = calls[0], None
        self.assertNotEqual(source, target)
        self.assertNotEqual(pathlib.Path(source).name, PRIMARY)
        self.assertTrue(pathlib.Path(source).name.startswith("."))
        self.assertTrue(pathlib.Path(source).name.endswith(".part"))
