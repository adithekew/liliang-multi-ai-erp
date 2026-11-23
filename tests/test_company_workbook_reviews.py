import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from scripts.validate_company_workbook import REQUIRED, validate


class WorkbookReviewTests(unittest.TestCase):
    def review_report(self, reviews=(), catalog=(), evidence=()):
        workbook = Workbook()
        workbook.remove(workbook.active)
        for name, columns in REQUIRED.items():
            sheet = workbook.create_sheet(name)
            headers = sorted(columns)
            if name == "05_AI02_RELEVANCE_LABELS":
                headers.append("review_round")
            if name == "01_SUPPLIER_CATALOG":
                headers.append("tds_evidence_id")
            if name == "02_TECHNICAL_EVIDENCE":
                headers.extend(["page_or_section", "expiry_date"])
            sheet.append(headers)
            if name == "03_CUSTOMER_INQUIRIES":
                rows = [{"inquiry_id": "Q", "processing_authorization_ref": "TEST"}]
            elif name == "05_AI02_RELEVANCE_LABELS":
                rows = [dict(inquiry_id="Q", internal_sku="A", review_rationale="test",
                             adjudication_status="AGREED", **review) for review in reviews]
            elif name == "01_SUPPLIER_CATALOG":
                rows = catalog
            elif name == "02_TECHNICAL_EVIDENCE":
                rows = evidence
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

    def test_verified_product_requires_matching_current_reviewed_evidence(self):
        product = dict(supplier_id="SUP", supplier_sku="SKU", tds_evidence_id="DOC",
                       technical_verification_status="VERIFIED")
        proof = dict(supplier_id="SUP", supplier_sku="SKU", evidence_id="DOC", evidence_type="TDS",
                     review_status="VERIFIED", page_or_section="2", field_supported="physical_form",
                     verbatim_value="powder", private_storage_uri="private/test")
        self.assertEqual(self.review_report(catalog=[product], evidence=[proof])["errors"], [])
        for change in ({"supplier_sku": "OTHER"}, {"supplier_id": "OTHER"}, {"evidence_type": "COA"},
                       {"review_status": "PENDING"}, {"expiry_date": "2000-01-01"}, {"page_or_section": ""}):
            with self.subTest(change=change):
                report = self.review_report(catalog=[product], evidence=[{**proof, **change}])
                self.assertIn("INVALID_VERIFIED_EVIDENCE_LINK", [error["issue"] for error in report["errors"]])
