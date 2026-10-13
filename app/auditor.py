import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import List

from app.schemas import (
    Jurisdiction,
    Severity,
    LabelInspectionPayload,
    AuditResult,
    AuditViolation
)
from app.rule_engine import RegulatoryRuleEngine

class ComplianceAuditor:
    def __init__(self):
        self.engine = RegulatoryRuleEngine()

    def audit_label(self, payload: LabelInspectionPayload) -> AuditResult:
        audit_id = f"AUD-{uuid.uuid4().hex[:8].upper()}"
        timestamp = datetime.now(timezone.utc).isoformat()

        # Evaluate by jurisdiction
        if payload.jurisdiction == Jurisdiction.FDA_US:
            violations = self.engine.evaluate_fda(payload)
        elif payload.jurisdiction == Jurisdiction.MOIAT_UAE:
            violations = self.engine.evaluate_moiat_uae(payload)
        else:
            # Fallback evaluation combines FDA general checks
            violations = self.engine.evaluate_fda(payload)

        # Calculate score and criticality
        critical_count = sum(1 for v in violations if v.severity == Severity.CRITICAL)
        warning_count = sum(1 for v in violations if v.severity == Severity.WARNING)
        advisory_count = sum(1 for v in violations if v.severity == Severity.ADVISORY)

        penalty = (critical_count * 35.0) + (warning_count * 15.0) + (advisory_count * 5.0)
        score = max(0.0, 100.0 - penalty)

        if critical_count > 0:
            status = "REJECTED"
        elif score >= 85.0:
            status = "PASSED"
        else:
            status = "FLAGGED"

        # Cryptographic Audit Proof (SHA-256)
        proof_payload = {
            "audit_id": audit_id,
            "label_id": payload.label_id,
            "product_name": payload.product_name,
            "jurisdiction": payload.jurisdiction.value,
            "timestamp": timestamp,
            "status": status,
            "violations_fingerprint": [f"{v.rule_id}:{v.severity.value}" for v in violations]
        }
        proof_str = json.dumps(proof_payload, sort_keys=True)
        audit_hash = hashlib.sha256(proof_str.encode("utf-8")).hexdigest()

        return AuditResult(
            audit_id=audit_id,
            label_id=payload.label_id,
            jurisdiction=payload.jurisdiction,
            product_name=payload.product_name,
            product_category=payload.product_category,
            timestamp=timestamp,
            compliance_score=score,
            status=status,
            violations_count=len(violations),
            critical_count=critical_count,
            violations=violations,
            cryptographic_audit_hash=audit_hash
        )
