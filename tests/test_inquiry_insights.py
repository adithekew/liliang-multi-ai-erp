import unittest
from research.inquiry_insights import candidate_insight, inquiry_insight

def p(pid,sku,name,application="Beverage, Bakery",description="Type: Powder; Applications: Bakery"):
    return dict(product_id=pid,sku=sku,name=name,description=description,
                application=application,profile="",source_ref="CATALOG-PDF-UNVERIFIED")

class InquiryInsightTest(unittest.TestCase):
    def test_strawberry_typo_legacy_wasabi_is_explicitly_rejected(self):
        inquiry="Butuh Rasa Susu Strowbery"
        saved=p(17,"LEGACY-017","WASABI FLAVOR")
        report=inquiry_insight(inquiry,[saved],"bm25-expert-review-demo-v0.2","MATCHED")
        self.assertEqual(report["interpreted_requirement"]["flavors"],["strawberry"])
        self.assertEqual(report["stage"],"CONFLICT_REVIEW_REQUIRED")
        self.assertEqual(report["candidates"][0]["decision_support"],"DO_NOT_RECOMMEND")
        self.assertEqual(report["candidates"][0]["flags"][0]["status"],"MISMATCH")
        self.assertFalse(report["model_accuracy_evidence"])
    def test_lemon_powder_inquiry_has_explicit_evidence_and_unknowns(self):
        inquiry="Perlu flavor lemon dalam bentuk serbuk untuk produksi roti"
        sku=p(5,"15100187","LEMON POWDER FLAVOR")
        report=inquiry_insight(inquiry,[sku],"bm25-catalog-constraint-v0.3","MATCHED")
        self.assertEqual(report["interpreted_requirement"]["forms"],["powder"])
        flags={x["aspect"]:x["status"] for x in report["candidates"][0]["flags"]}
        self.assertEqual(flags["Rasa utama"],"NAME_MATCH")
        self.assertEqual(flags["Bentuk produk"],"CATALOG_MATCH")
        self.assertEqual(flags["Aplikasi"],"CATALOG_MATCH")
        self.assertEqual(flags["Kesesuaian teknis, halal, regulatory"],"UNKNOWN")
        self.assertEqual(report["candidates"][0]["decision_support"],"TECHNICAL_VALIDATION_REQUIRED")
        self.assertTrue(report["technical_review_required"])
    def test_no_match_requests_clarification_instead_of_fabricating(self):
        r=inquiry_insight("Butuh rasa kiwi serbuk untuk roti",[],"bm25-catalog-constraint-v0.3","NO_MATCH")
        self.assertEqual(r["stage"],"CLARIFICATION_REQUIRED")
        self.assertEqual(r["candidate_count"],0)
        self.assertIn("Tidak ada kandidat",r["summary"])
    def test_form_mismatch_and_non_food_are_rejected(self):
        q="rasa strawberry bubuk untuk minuman"
        wrong=p(1,"TEST-LIQ","STRAWBERRY FLAVOR",description="Type: Liquid; Applications: Beverage")
        out=candidate_insight(wrong,q)
        self.assertEqual(out["decision_support"],"DO_NOT_RECOMMEND")
        self.assertEqual({x["aspect"]:x["status"] for x in out["flags"]}["Bentuk produk"],"MISMATCH")
        vape=p(2,"TEST-VAPE","STRAWBERRY VAPE","E-Cigarettes",description="Type: Liquid")
        self.assertEqual(candidate_insight(vape,"strawberry untuk minuman")["decision_support"],"DO_NOT_RECOMMEND")
    def test_individual_explanation_never_mutates_legacy_ranking(self):
        bad=p(1,"WASABI","WASABI FLAVOR")
        right=p(2,"STRAW","STRAWBERRY FLAVOR")
        ordered=[bad,right]
        summary=inquiry_insight("Strowbery susu",ordered,"legacy-v0.2","MATCHED")
        self.assertEqual([x["sku"] for x in ordered],["WASABI","STRAW"])
        self.assertEqual([x["sku"] for x in summary["candidates"]],["WASABI","STRAW"])
        self.assertEqual(summary["candidates"][0]["risk"],"HIGH")
        self.assertEqual(summary["candidates"][1]["risk"],"REVIEW")
if __name__=="__main__":unittest.main()
