import unittest

from location_enrichment.confirm_hifld_candidates import confirm, haversine_miles


class HifldConfirmationTests(unittest.TestCase):
    def test_same_point_distance(self):
        self.assertEqual(haversine_miles(33.0, -81.0, 33.0, -81.0), 0.0)

    def test_exact_nearby_sources_confirm(self):
        osm = {
            "terminals": [
                {
                    "terminal": "Hooks",
                    "status": "exact_candidate",
                    "candidates": [
                        {
                            "name": "Hooks Substation",
                            "latitude": 33.0,
                            "longitude": -81.0,
                            "source": "https://www.openstreetmap.org/node/1",
                        }
                    ],
                }
            ]
        }
        hifld = {
            "features": [
                {"attributes": {"NAME": "Hooks", "LATITUDE": 33.001, "LONGITUDE": -81.001}}
            ]
        }
        result = confirm(osm, hifld, 2.0)[0]
        self.assertEqual(result["status"], "confirmed")
        self.assertEqual(result["location_quality"], "verified")

    def test_far_source_does_not_confirm(self):
        osm = {
            "terminals": [
                {
                    "terminal": "Hooks",
                    "status": "exact_candidate",
                    "candidates": [
                        {
                            "name": "Hooks Substation",
                            "latitude": 33.0,
                            "longitude": -81.0,
                            "source": "https://www.openstreetmap.org/node/1",
                        }
                    ],
                }
            ]
        }
        hifld = {
            "features": [
                {"attributes": {"NAME": "Hooks", "LATITUDE": 34.0, "LONGITUDE": -82.0}}
            ]
        }
        self.assertEqual(confirm(osm, hifld, 2.0)[0]["status"], "needs_review")

    def test_colocated_unnamed_hifld_feature_confirms_osm_name(self):
        osm = {
            "terminals": [
                {
                    "terminal": "Hooks",
                    "status": "exact_candidate",
                    "candidates": [
                        {
                            "name": "Hooks Substation",
                            "latitude": 33.0,
                            "longitude": -81.0,
                            "source": "https://www.openstreetmap.org/node/1",
                        }
                    ],
                }
            ]
        }
        hifld = {
            "features": [
                {"attributes": {"NAME": "UNKNOWN123", "LATITUDE": 33.0001, "LONGITUDE": -81.0001}}
            ]
        }
        result = confirm(osm, hifld, 2.0, 0.1)[0]
        self.assertEqual(result["status"], "confirmed")
        self.assertIn("colocated", result["notes"])


if __name__ == "__main__":
    unittest.main()
