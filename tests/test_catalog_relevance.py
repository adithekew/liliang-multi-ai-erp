"""Developer-designed hard-constraint checks, NOT independent expert accuracy evidence."""
import unittest
from research.catalog_matcher import query_intent, score_products

def item(i,name,kind,app):
    return dict(id=i,sku=f"TST-{i:02d}",name=name,
      description=f"Type: {kind}; Applications: {app}; Catalog percentage text: UNKNOWN",
      profile="",application=app,source_ref="SYNTHETIC_CATALOG_FIXTURE")

PRODUCTS=[
 item(1,"Wasabi Seasoning","Powder","Snack, Savory"),
 item(2,"Strawberry Flavor","Liquid","Beverage, Bakery"),
 item(3,"Strawberry Powder Flavor","Powder","Beverage, Bakery"),
 item(4,"Avocado Flavor","Liquid","Beverage, Dairy"),
 item(5,"Lemon Powder Flavor","Powder","Bakery, Beverage"),
 item(6,"Lemongrass Powder Flavor","Powder","Bakery, Beverage"),
 item(7,"Lemon Flavor","Liquid","Beverage, Bakery"),
 item(8,"Mango Flavor","Liquid","Beverage"),
 item(9,"Mango Powder Flavor","Powder","Bakery"),
 item(10,"Strawberry Vape","Liquid","E-Cigarettes"),
 item(11,"Coconut Flavor","Liquid","Beverage"),
 item(12,"Durian Powder Flavor","Powder","Bakery"),
 item(13,"Coffee Flavor","Liquid","Beverage"),
]

class CatalogMatchingGuardrailsTest(unittest.TestCase):
    def test_spelling_variants_and_bilingual_flavors(self):
        for query,expected in [
          ("Butuh Rasa Susu Strowbery","Strawberry"),
          ("rasa stroberi untuk minuman susu","Strawberry"),
          ("perisa mangga untuk minuman","Mango"),
          ("kelapa untuk minuman","Coconut"),
          ("kopi cair untuk minuman","Coffee"),
          ("durian bubuk untuk roti","Durian Powder"),
        ]:
            with self.subTest(query=query):
                result=score_products(query,PRODUCTS)
                self.assertTrue(result,query)
                self.assertIn(expected.lower(),result[0]["name"].lower())
                self.assertTrue(all(expected.split()[0].lower() in x["name"].lower() for x in result),
                                "Flavor substitutions found: "+query)
    def test_flavor_and_form_are_hard_constraints(self):
        candidates=score_products("perlu flavor rasa lemon dalam bentuk serbuk untuk produksi roti",PRODUCTS)
        self.assertTrue(candidates)
        self.assertTrue(all("Lemon Powder" in x["name"] for x in candidates))
        self.assertTrue(all(x["explanation"]["form_match"] for x in candidates))
        self.assertEqual(candidates[0]["sku"],"TST-05")
        self.assertNotIn("Lemongrass",str(candidates))
        strawberry=score_products("Butuh Strowbery powder untuk beverage",PRODUCTS)
        self.assertTrue(strawberry)
        self.assertTrue(all("Strawberry Powder" in x["name"] for x in strawberry))
    def test_no_unrelated_fallback_for_unknown_flavor(self):
        self.assertEqual(score_products("Butuh flavor kiwi untuk bakery",PRODUCTS),[])
        self.assertEqual(score_products("Need flavour for drink",PRODUCTS),[])
        self.assertEqual(score_products("Butuh vanilla rasa untuk roti",PRODUCTS),[])
    def test_vape_rejected_for_food_application(self):
        ranked=score_products("strawberry flavour untuk minuman",PRODUCTS)
        self.assertTrue(ranked)
        self.assertTrue(all("Vape" not in x["name"] for x in ranked))
    def test_status_and_suitability_are_never_fabricated(self):
        matched=score_products("rasa strawberry minuman susu dairy",PRODUCTS)
        self.assertTrue(matched)
        for row in matched:
            self.assertFalse(row["evidence_verified"])
            self.assertIn("product_suitability",row["unknown_attributes"])
            self.assertEqual(row["explanation"]["retrieval_status"],"LEXICAL_CANDIDATE_UNVERIFIED")
    def test_interpreter_preserves_form(self):
        parsed=query_intent("Butuh rasa lemon dalam bentuk serbuk untuk produksi roti")
        self.assertEqual(parsed["flavors"],["lemon"])
        self.assertEqual(parsed["forms"],["powder"])
        self.assertIn("bakery",parsed["applications"])
        self.assertEqual(query_intent("Butuh Rasa Susu Strowbery")["flavors"],["strawberry"])
if __name__=="__main__":unittest.main()
