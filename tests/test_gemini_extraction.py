import unittest

from gemini_extraction.extract_projects import (
    build_prompt,
    normalize_result,
    parse_pages,
    ssl_context,
    validate_result,
)


class GeminiExtractionTests(unittest.TestCase):
    def test_ssl_context_has_certificate_verification(self):
        context = ssl_context()
        self.assertTrue(context.check_hostname)
        self.assertNotEqual(context.verify_mode, 0)

    def test_page_parser(self):
        self.assertEqual(parse_pages("31,189-190,410"), [31, 189, 190, 410])

    def test_prompt_keeps_need_date_separate(self):
        prompt = build_prompt("source.pdf", [410])
        self.assertIn("Never copy a Need Date into in_service_date", prompt)
        self.assertIn("physical PDF pages: 410", prompt)

    def test_date_normalization(self):
        result = {
            "projects": [
                {
                    "in_service_date": "12/31/2024",
                    "construction_start": None,
                    "construction_end": None,
                    "need_date": "06/01/33",
                }
            ]
        }
        normalized = normalize_result(result)["projects"][0]
        self.assertEqual(normalized["in_service_date"], "2024-12-31")
        self.assertEqual(normalized["need_date"], "2033-06-01")

    def test_multiple_phase_dates_are_preserved_as_uncertainty(self):
        result = {
            "projects": [
                {
                    "in_service_date": "10/1/2025 (phase 1) and 10/1/2026 (phase 2)",
                    "construction_start": None,
                    "construction_end": None,
                    "need_date": None,
                    "schedule_text": None,
                    "uncertainties": [],
                }
            ]
        }
        normalized = normalize_result(result)["projects"][0]
        self.assertIsNone(normalized["in_service_date"])
        self.assertIn("phase 1", normalized["schedule_text"])
        self.assertTrue(normalized["uncertainties"])

    def test_validation_rejects_need_date_as_in_service(self):
        result = {
            "projects": [
                {
                    "source_project_id": "20793",
                    "project_name": "Example",
                    "schedule_text": "Need Date: 06/01/2033",
                    "in_service_date": "2033-06-01",
                    "evidence": [
                        {"pdf_page": 410, "printed_page": "240", "supports": ["need_date"], "text": "Need Date"}
                    ],
                }
            ]
        }
        errors = validate_result(result, [410])
        self.assertTrue(any("Need Date cannot populate" in error for error in errors))

    def test_validation_rejects_evidence_outside_scope(self):
        result = {
            "projects": [
                {
                    "source_project_id": "6810 A",
                    "project_name": "Example",
                    "schedule_text": "Planned In-Service Date: 12/31/2024",
                    "in_service_date": "2024-12-31",
                    "evidence": [
                        {"pdf_page": 30, "printed_page": "30", "supports": ["project_name"], "text": "Example"}
                    ],
                }
            ]
        }
        errors = validate_result(result, [31])
        self.assertTrue(any("outside the requested pages" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
