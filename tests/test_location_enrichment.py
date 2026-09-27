import unittest

from location_enrichment.fetch_osm_candidates import normalized, rank_candidates


class LocationEnrichmentTests(unittest.TestCase):
    def test_normalizes_substation_suffix(self):
        self.assertEqual(normalized("Hooks Substation"), normalized("Hooks"))

    def test_exact_candidate_requires_one_exact_match(self):
        osm = {
            "elements": [
                {
                    "type": "node",
                    "id": 1,
                    "lat": 33.1,
                    "lon": -81.9,
                    "tags": {"power": "substation", "name": "Hooks Substation"},
                }
            ]
        }
        result = rank_candidates(["Hooks"], osm)[0]
        self.assertEqual(result["status"], "exact_candidate")
        self.assertEqual(result["candidates"][0]["source"], "https://www.openstreetmap.org/node/1")

    def test_missing_match_stays_unknown(self):
        self.assertEqual(rank_candidates(["Hooks"], {"elements": []})[0]["status"], "unknown")


if __name__ == "__main__":
    unittest.main()
