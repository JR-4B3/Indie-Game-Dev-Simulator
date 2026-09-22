"""Stdlib witness of the frozen M1-K1 K2 RNG golden vectors (WP-KV)."""

import hashlib
import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VECTORS_PATH = REPO_ROOT / "docs" / "rewrite" / "fixtures" / "m1-random-vectors.json"


def _canonical_digest(args, protocol):
    payload = json.dumps(
        [protocol] + list(args),
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(payload).digest()


class M1ContractVectorsTest(unittest.TestCase):
    def test_frozen_vectors(self):
        data = json.loads(VECTORS_PATH.read_text(encoding="utf-8"))
        self.assertEqual(data["protocol"], "studio-rng-v1")
        vectors = data["vectors"]
        self.assertEqual(len(vectors), 3)
        for vector in vectors:
            with self.subTest(args=vector["args"]):
                digest = _canonical_digest(vector["args"], data["protocol"])
                self.assertEqual(
                    digest.hex(), vector["sha256"])
                self.assertEqual(
                    int.from_bytes(digest[:8], "big"), vector["u64"])


if __name__ == "__main__":
    unittest.main()
