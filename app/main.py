from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import LabelInspectionPayload, AuditResult, Jurisdiction, ProductCategory
from app.auditor import ComplianceAuditor

app = FastAPI(
    title="Multimodal Regulatory Packaging & Label Compliance Auditor",
    description="Automated, deterministic label compliance verification for FDA 21 CFR and UAE MoIAT standards.",
    version="1.0.0"
)

# Enable CORS for enterprise frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

auditor = ComplianceAuditor()

@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "HEALTHY",
        "service": "multimodal-compliance-auditor",
        "engine_version": "1.0.0",
        "architect": "Noor Siddiqui"
    }

@app.get("/api/v1/supported-jurisdictions", tags=["Metadata"])
def get_jurisdictions():
    return {
        "supported_jurisdictions": [j.value for j in Jurisdiction],
        "supported_categories": [c.value for c in ProductCategory]
    }

@app.post(
    "/api/v1/audit",
    response_model=AuditResult,
    status_code=status.HTTP_200_OK,
    tags=["Compliance Audit"]
)
def audit_packaging_label(payload: LabelInspectionPayload):
    try:
        result = auditor.audit_label(payload)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Auditing failure: {str(e)}"
        )
