import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from scripts.validate_company_workbook import REQUIRED, validate


class WorkbookReviewTests(unittest.TestCase):
    def review_report(self, reviews):
        workbook = Workbook()
        workbook.remove(workbook.active)
        for name, columns in REQUIRED.items():
            sheet = workbook.create_sheet(name)
            headers = sorted(columns)
            if name == "05_AI02_RELEVANCE_LABELS":
                headers.append("review_round")
            sheet.append(headers)
            if name == "03_CUSTOMER_INQUIRIES":
                rows = [{"inquiry_id": "Q", "processing_authorization_ref": "TEST"}]
            elif name == "05_AI02_RELEVANCE_LABELS":
                rows = [dict(inquiry_id="Q", internal_sku="A", review_rationale="test",
                             adjudication_status="AGREED", **review) for review in reviews]
            else:
                rows = []
            for row in rows:
                sheet.append([row.get(header) for header in headers])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.xlsx"
            workbook.save(path)
            return validate(path)

    def test_unknown_is_ungraded_and_does_not_count_as_adjudicated(self):
        reviews = [{"technical_decision": "UNKNOWN", "reviewer_id": reviewer} for reviewer in ("A", "B")]
        report = self.review_report(reviews)
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["readiness"]["ai02_pairs_dual_reviewed_and_adjudicated"], 0)

    def test_two_distinct_reviewers_must_judge_the_same_version_and_round(self):
        first = dict(reviewer_id="A", technical_decision="ACCEPT", relevance_grade_0_3=3,
                     label_set_version="v1", review_round=1)
        for override, count in [({}, 1), ({"label_set_version": "v2"}, 0), ({"review_round": 2}, 0),
                                ({"reviewer_id": ""}, 0), ({"relevance_grade_0_3": 2.8}, 0)]:
            with self.subTest(override=override):
                report = self.review_report([first, {**first, "reviewer_id": "B", **override}])
                self.assertEqual(report["readiness"]["ai02_pairs_dual_reviewed_and_adjudicated"], count)
