import unittest
from app.schemas import Jurisdiction, ProductCategory, LabelInspectionPayload, Severity
from app.auditor import ComplianceAuditor

class TestRegulatoryComplianceAuditor(unittest.TestCase):
    def setUp(self):
        self.auditor = ComplianceAuditor()

    def test_fully_compliant_fda_supplement(self):
        payload = LabelInspectionPayload(
            label_id="LBL-001",
            product_name="Zenith Pure Omega-3",
            product_category=ProductCategory.DIETARY_SUPPLEMENT,
            jurisdiction=Jurisdiction.FDA_US,
            raw_text=(
                "Zenith Pure Omega-3 Fish Oil. Dietary Supplement. "
                "Supports cardiovascular and cognitive health. "
                "Net Wt. 8 oz (227 g). 60 Softgels. "
                "Suggested Use: Take 2 softgels daily with water. "
                "Ingredients: Purified Deep Sea Fish Oil, Gelatin, Glycerin, Purified Water. "
                "Contains: Fish (Anchovy, Sardine). "
                "These statements have not been evaluated by the Food and Drug Administration. "
                "This product is not intended to diagnose, treat, cure, or prevent any disease. "
                "Manufactured for Zenith Wellness LLC, Austin, TX 78701."
            )
        )
        result = self.auditor.audit_label(payload)
        self.assertEqual(result.status, "PASSED")
        self.assertGreaterEqual(result.compliance_score, 85.0)
        self.assertEqual(result.critical_count, 0)
        self.assertTrue(len(result.cryptographic_audit_hash) == 64)

    def test_unauthorized_disease_claim_triggers_rejection(self):
        payload = LabelInspectionPayload(
            label_id="LBL-002",
            product_name="Miracle Herb Elixir",
            product_category=ProductCategory.DIETARY_SUPPLEMENT,
            jurisdiction=Jurisdiction.FDA_US,
            raw_text=(
                "Miracle Herb Elixir. Cures diabetes and prevents cancer naturally! "
                "Net Wt. 4 oz (113 g). "
                "These statements have not been evaluated by the Food and Drug Administration."
            )
        )
        result = self.auditor.audit_label(payload)
        self.assertEqual(result.status, "REJECTED")
        self.assertGreaterEqual(result.critical_count, 1)
        violation_rules = [v.rule_id for v in result.violations]
        self.assertIn("FDA-DIS-001", violation_rules)

    def test_missing_dshea_disclaimer_for_supplement(self):
        payload = LabelInspectionPayload(
            label_id="LBL-003",
            product_name="BioVitality Vitamin C",
            product_category=ProductCategory.DIETARY_SUPPLEMENT,
            jurisdiction=Jurisdiction.FDA_US,
            raw_text=(
                "BioVitality Vitamin C 1000mg. Supports immune resilience. "
                "Net Wt. 6 oz (170 g). Contains no allergens."
            )
        )
        result = self.auditor.audit_label(payload)
        self.assertEqual(result.status, "REJECTED")
        violation_rules = [v.rule_id for v in result.violations]
        self.assertIn("FDA-DSH-002", violation_rules)

    def test_uae_moiat_missing_arabic_fails(self):
        payload = LabelInspectionPayload(
            label_id="LBL-004",
            product_name="Desert Oasis Protein Shake",
            product_category=ProductCategory.FOOD_AND_BEVERAGE,
            jurisdiction=Jurisdiction.MOIAT_UAE,
            raw_text=(
                "Desert Oasis Protein Shake. Product of UAE. "
                "Net Weight: 330 ml. EXP: 20/12/2026."
            )
        )
        result = self.auditor.audit_label(payload)
        self.assertEqual(result.status, "REJECTED")
        violation_rules = [v.rule_id for v in result.violations]
        self.assertIn("UAE-LANG-001", violation_rules)

    def test_uae_moiat_compliant_bilingual_label(self):
        payload = LabelInspectionPayload(
            label_id="LBL-005",
            product_name="Al Ain Natural Honey",
            product_category=ProductCategory.FOOD_AND_BEVERAGE,
            jurisdiction=Jurisdiction.MOIAT_UAE,
            raw_text=(
                "Al Ain Natural Honey. عسل طبيعي نقي. "
                "Made in UAE. صنع في الإمارات. "
                "Net Weight: 500g. الوزن الصافي: 500 جم. "
                "PROD: 10/01/2026. EXP: 09/01/2028."
            )
        )
        result = self.auditor.audit_label(payload)
        self.assertEqual(result.status, "PASSED")
        self.assertEqual(result.critical_count, 0)
        self.assertGreaterEqual(result.compliance_score, 85.0)

if __name__ == "__main__":
    unittest.main()
