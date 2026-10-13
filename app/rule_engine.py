import re
from typing import List
from app.schemas import (
    Jurisdiction,
    ProductCategory,
    Severity,
    AuditViolation,
    LabelInspectionPayload
)

# Major Food Allergens under FALCPA + FASTER Act (USA)
MAJOR_ALLERGENS_US = [
    "milk", "egg", "eggs", "peanut", "peanuts", "tree nut", "tree nuts",
    "wheat", "fish", "crustacean", "shellfish", "soy", "soybean", "soybeans", "sesame"
]

# High-Risk Unauthorized Disease Terms (Triggers FDA Warning Letter / 21 CFR §101.93 violation)
UNAUTHORIZED_DISEASE_CLAIMS = [
    r"\bcures?\b",
    r"\btreats?\b",
    r"\bprevents?\s+(?:cancer|diabetes|alzheimer|covid|heart disease|hypertension|stroke|parkinson)\b",
    r"\beradicates?\b",
    r"\bheal(?:s|ing)?\s+(?:chronic disease|infection|tumors?)\b",
    r"\bantiviral\s+therapy\b",
    r"\bchemotherapy\s+alternative\b"
]

FDA_MANDATORY_DISCLAIMER_SNIPPET = "these statements have not been evaluated by the food and drug administration"

class RegulatoryRuleEngine:
    """
    Deterministic rule validation engine enforcing FDA and UAE MoIAT standards.
    Zero hallucination risk: all checks are pattern and clause-verified.
    """

    def evaluate_fda(self, payload: LabelInspectionPayload) -> List[AuditViolation]:
        violations: List[AuditViolation] = []
        text_lower = payload.raw_text.lower()

        # 1. Disease Claims Validation (21 CFR §101.93)
        # Exclude mandatory negative disclaimer phrasing so 'not intended to treat, cure' does not false-positive
        claims_search_text = re.sub(
            r"not intended to\s+(?:diagnose,\s*)?(?:treat,\s*)?(?:cure,\s*)?(?:or\s*prevent\s+any\s+disease)?",
            "",
            text_lower
        )
        claims_search_text = claims_search_text.replace(FDA_MANDATORY_DISCLAIMER_SNIPPET, "")

        for pattern in UNAUTHORIZED_DISEASE_CLAIMS:
            match = re.search(pattern, claims_search_text, re.IGNORECASE)
            if match:
                violations.append(
                    AuditViolation(
                        rule_id="FDA-DIS-001",
                        regulatory_clause="21 CFR §101.93(g)",
                        severity=Severity.CRITICAL,
                        detected_issue="Unauthorized disease treatment or prevention claim detected on packaging.",
                        snippet=match.group(0),
                        remediation_recommendation=(
                            "Remove disease claims immediately. Dietary supplements may only make structure/function "
                            "claims (e.g., 'Supports joint health'), NOT disease mitigation claims."
                        )
                    )
                )

        # 2. Mandatory DSHEA Disclaimer for Dietary Supplements (21 CFR §101.93)
        if payload.product_category == ProductCategory.DIETARY_SUPPLEMENT:
            if FDA_MANDATORY_DISCLAIMER_SNIPPET not in text_lower:
                violations.append(
                    AuditViolation(
                        rule_id="FDA-DSH-002",
                        regulatory_clause="21 CFR §101.93(c)",
                        severity=Severity.CRITICAL,
                        detected_issue="Missing mandatory FDA DSHEA disclaimer for dietary supplement.",
                        snippet=None,
                        remediation_recommendation=(
                            "Add verbatim statement: 'These statements have not been evaluated by the Food and Drug Administration. "
                            "This product is not intended to diagnose, treat, cure, or prevent any disease.'"
                        )
                    )
                )

        # 3. Statement of Identity (21 CFR §101.3)
        if payload.product_name.lower() not in text_lower:
            violations.append(
                AuditViolation(
                    rule_id="FDA-ID-003",
                    regulatory_clause="21 CFR §101.3",
                    severity=Severity.WARNING,
                    detected_issue="Prominent Statement of Identity matching official product name was not detected.",
                    snippet=None,
                    remediation_recommendation=(
                        "Ensure the common or usual name of the product appears prominently on the Primary Display Panel."
                    )
                )
            )

        # 4. Net Quantity of Contents (21 CFR §101.105)
        # Check for dual declaration: metric (g/ml/kg/l) and US customary (oz/fl oz/lb)
        has_customary = bool(re.search(r"\b(?:\d+(?:\.\d+)?)\s*(?:fl\s*oz|oz|lbs?)\b", text_lower))
        has_metric = bool(re.search(r"\b(?:\d+(?:\.\d+)?)\s*(?:g|mg|ml|kg|l|liters?)\b", text_lower))
        
        if not (has_customary and has_metric):
            violations.append(
                AuditViolation(
                    rule_id="FDA-NET-004",
                    regulatory_clause="21 CFR §101.105",
                    severity=Severity.WARNING,
                    detected_issue="Net quantity of contents lacks dual unit declaration (US Customary + Metric).",
                    snippet=None,
                    remediation_recommendation=(
                        "Label must declare net contents in both units (e.g., 'Net Wt. 8 oz (227 g)' or '16 fl oz (473 mL)')."
                    )
                )
            )

        # 5. Allergen Declaration (FALCPA / FASTER Act)
        has_contains_statement = "contains:" in text_lower or "contains " in text_lower
        detected_allergens_in_text = [
            allergen for allergen in MAJOR_ALLERGENS_US
            if re.search(r"\b" + allergen + r"\b", text_lower)
        ]
        
        if detected_allergens_in_text and not has_contains_statement:
            # Check if allergen is identified in ingredient list in parentheses
            has_parenthetical = any(f"({a})" in text_lower for a in detected_allergens_in_text)
            if not has_parenthetical:
                violations.append(
                    AuditViolation(
                        rule_id="FDA-ALG-005",
                        regulatory_clause="FALCPA 21 U.S.C. 343(w)",
                        severity=Severity.CRITICAL,
                        detected_issue=f"Major allergens ({', '.join(detected_allergens_in_text)}) mentioned without standard 'Contains:' statement or parenthetical specification.",
                        snippet=", ".join(detected_allergens_in_text),
                        remediation_recommendation=(
                            "Add a dedicated 'Contains: [Allergen]' statement immediately following the ingredients list."
                        )
                    )
                )

        return violations

    def evaluate_moiat_uae(self, payload: LabelInspectionPayload) -> List[AuditViolation]:
        violations: List[AuditViolation] = []
        raw_text = payload.raw_text

        # 1. Mandatory Arabic Language Requirement (UAE GSO 9:2013 §4.1)
        arabic_pattern = re.compile(r"[\u0600-\u06FF]")
        if not arabic_pattern.search(raw_text):
            violations.append(
                AuditViolation(
                    rule_id="UAE-LANG-001",
                    regulatory_clause="UAE MoIAT GSO 9:2013 Clause 4.1",
                    severity=Severity.CRITICAL,
                    detected_issue="Label packaging contains no Arabic translation.",
                    snippet=None,
                    remediation_recommendation=(
                        "MoIAT regulations require Arabic language labelling on the primary or secondary packaging "
                        "for all consumer food, supplement, and wellness goods sold in the UAE."
                    )
                )
            )

        # 2. Date Format Validation (GSO 150-1 / GSO 9:2013 Clause 4.6)
        date_format_valid = bool(
            re.search(r"\b(?:0?[1-9]|[12]\d|3[01])[-/.](?:0?[1-9]|1[0-2])[-/.](?:20\d{2})\b", raw_text) or
            re.search(r"\b(?:prod|exp|mfg|bb)\b.*?\d{2}/\d{2}/\d{4}", raw_text, re.IGNORECASE)
        )
        if not date_format_valid:
            violations.append(
                AuditViolation(
                    rule_id="UAE-DATE-002",
                    regulatory_clause="UAE GSO 150-1 Expiry Standards",
                    severity=Severity.WARNING,
                    detected_issue="Missing or non-standard production/expiry date format (DD/MM/YYYY required).",
                    snippet=None,
                    remediation_recommendation=(
                        "Ensure Production (PROD/MFG) and Expiry (EXP) dates are clearly stamped in Day/Month/Year format."
                    )
                )
            )

        # 3. Country of Origin & Importer Registration (GSO 9:2013 Clause 4.5)
        text_lower = raw_text.lower()
        has_origin = any(kw in text_lower for kw in ["made in", "product of", "country of origin", "صنع في"])
        if not has_origin:
            violations.append(
                AuditViolation(
                    rule_id="UAE-ORIGIN-003",
                    regulatory_clause="UAE GSO 9:2013 Clause 4.5",
                    severity=Severity.WARNING,
                    detected_issue="Country of Origin statement was not detected on the label.",
                    snippet=None,
                    remediation_recommendation=(
                        "Add explicit country of manufacture (e.g., 'Made in UAE' or 'Product of USA')."
                    )
                )
            )

        return violations
