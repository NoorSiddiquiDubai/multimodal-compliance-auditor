from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class Jurisdiction(str, Enum):
    FDA_US = "FDA_US"
    MOIAT_UAE = "MOIAT_UAE"
    EU_EFSA = "EU_EFSA"

class ProductCategory(str, Enum):
    DIETARY_SUPPLEMENT = "DIETARY_SUPPLEMENT"
    FOOD_AND_BEVERAGE = "FOOD_AND_BEVERAGE"
    WELLNESS_COSMETICS = "WELLNESS_COSMETICS"

class Severity(str, Enum):
    CRITICAL = "CRITICAL"    # Non-negotiable regulatory barrier (product recall / seizure risk)
    WARNING = "WARNING"      # Formatting or non-fatal omission
    ADVISORY = "ADVISORY"    # Best practice recommendation

class ComplianceRule(BaseModel):
    rule_id: str
    jurisdiction: Jurisdiction
    category: str
    regulatory_clause: str
    description: str
    severity: Severity

class AuditViolation(BaseModel):
    rule_id: str
    regulatory_clause: str
    severity: Severity
    detected_issue: str
    snippet: Optional[str] = None
    remediation_recommendation: str

class LabelInspectionPayload(BaseModel):
    label_id: str
    product_name: str
    product_category: ProductCategory
    jurisdiction: Jurisdiction = Jurisdiction.FDA_US
    raw_text: str = Field(..., description="OCR/Vision extracted text from label artwork")
    layout_sections: Optional[Dict[str, str]] = Field(
        default_factory=dict,
        description="Optional parsed sections: primary_display_panel, info_panel, nutrition_facts, etc."
    )
    declared_allergens: Optional[List[str]] = Field(default_factory=list)

class AuditResult(BaseModel):
    audit_id: str
    label_id: str
    jurisdiction: Jurisdiction
    product_name: str
    product_category: ProductCategory
    timestamp: str
    compliance_score: float = Field(..., ge=0.0, le=100.0)
    status: str = Field(..., description="PASSED, FLAGGED, or REJECTED")
    violations_count: int
    critical_count: int
    violations: List[AuditViolation]
    cryptographic_audit_hash: str
    auditor_signature: str = "Noor Siddiqui Deterministic Compliance Engine v1.0"
