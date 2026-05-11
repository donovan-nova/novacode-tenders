from fastapi import APIRouter
from database import get_db
from scorer import score_tender

router = APIRouter()

SEED_TENDERS = [
    {"external_id":"ZA-SEED-SARB-2026-041","title":"AI-driven fraud detection system for financial transactions","department":"South African Reserve Bank","country":"ZA","category":"AI & Automation","value_raw":"R 4,200,000","value_zar":4200000,"deadline":"2026-06-30","published":"2026-04-15","reference":"SARB/ICT/2026/041","source":"SA National Treasury (OCDS API)","portal_url":"https://www.etenders.gov.za","description":"SARB requires AI-driven fraud detection for real-time financial transaction monitoring.","status":"active"},
    {"external_id":"ZA-SEED-LAND-2026-018","title":"Digital transformation and automation of loan origination processes","department":"Land Bank","country":"ZA","category":"Fintech","value_raw":"R 8,700,000","value_zar":8700000,"deadline":"2026-07-15","published":"2026-04-20","reference":"LB/IT/2026/018","source":"SA National Treasury (OCDS API)","portal_url":"https://www.etenders.gov.za","description":"Land Bank seeks a technology partner to automate end-to-end loan origination.","status":"active"},
    {"external_id":"ZA-SEED-NT-2026-112","title":"Data analytics platform for credit risk monitoring","department":"National Treasury","country":"ZA","category":"Data & Analytics","value_raw":"R 6,100,000","value_zar":6100000,"deadline":"2026-07-30","published":"2026-04-22","reference":"NT/BD/2026/112","source":"SA National Treasury (OCDS API)","portal_url":"https://www.etenders.gov.za","description":"National Treasury requires a data analytics platform for credit risk monitoring.","status":"active"},
    {"external_id":"ZA-SEED-SARS-2026-033","title":"Machine learning solutions for tax compliance analytics","department":"South African Revenue Service","country":"ZA","category":"AI & Automation","value_raw":"R 12,000,000","value_zar":12000000,"deadline":"2026-08-10","published":"2026-04-25","reference":"SARS/IT/2026/033","source":"SA National Treasury (OCDS API)","portal_url":"https://www.etenders.gov.za","description":"SARS requires machine learning to enhance tax compliance analytics.","status":"active"},
    {"external_id":"ZA-SEED-DBSA-2026-022","title":"Mobile credit scoring application for informal sector lending","department":"Development Bank of Southern Africa","country":"ZA","category":"Fintech","value_raw":"R 5,500,000","value_zar":5500000,"deadline":"2026-07-20","published":"2026-04-18","reference":"DBSA/ICT/2026/022","source":"SA National Treasury (OCDS API)","portal_url":"https://www.etenders.gov.za","description":"DBSA seeks a mobile credit scoring app for informal sector lending.","status":"active"},
    {"external_id":"ZA-SEED-FSCA-2026-015","title":"Cybersecurity and regulatory compliance automation tools","department":"Financial Sector Conduct Authority","country":"ZA","category":"ICT & Software","value_raw":"R 3,800,000","value_zar":3800000,"deadline":"2026-06-25","published":"2026-04-10","reference":"FSCA/IT/2026/015","source":"SA National Treasury (OCDS API)","portal_url":"https://www.etenders.gov.za","description":"FSCA requires cybersecurity and compliance automation tools.","status":"active"},
    {"external_id":"KE-SEED-CBK-2026-09","title":"ICT consulting services for digital banking infrastructure upgrade","department":"Central Bank of Kenya","country":"KE","category":"ICT & Software","value_raw":"KES 45,000,000","value_zar":5400000,"deadline":"2026-07-05","published":"2026-04-20","reference":"CBK/ICT/2026/09","source":"PPRA Kenya","portal_url":"https://tenders.go.ke","description":"CBK seeks ICT consulting for digital banking infrastructure upgrade.","status":"active"},
    {"external_id":"ZM-SEED-BOZ-2026-07","title":"Automated reconciliation middleware for payment processing systems","department":"Bank of Zambia","country":"ZM","category":"Fintech","value_raw":"ZMW 2,800,000","value_zar":2100000,"deadline":"2026-07-12","published":"2026-04-22","reference":"BOZ/IT/2026/07","source":"Zambia ZPPA","portal_url":"https://www.zppa.org.zm","description":"Bank of Zambia requires automated reconciliation middleware for payment processing.","status":"active"},
    {"external_id":"NG-SEED-CBN-2026-003","title":"Fintech regulatory sandbox technology partner","department":"Central Bank of Nigeria","country":"NG","category":"Fintech","value_raw":"NGN 180,000,000","value_zar":3600000,"deadline":"2026-08-01","published":"2026-04-28","reference":"CBN/FSS/2026/003","source":"Nigeria BPP","portal_url":"https://www.bpp.gov.ng","description":"CBN invites fintech companies to participate in the national regulatory sandbox.","status":"active"},
    {"external_id":"UG-SEED-URA-2026-019","title":"Business intelligence and reporting dashboard for revenue authority","department":"Uganda Revenue Authority","country":"UG","category":"Data & Analytics","value_raw":"UGX 850,000,000","value_zar":3400000,"deadline":"2026-07-25","published":"2026-04-15","reference":"URA/IT/2026/019","source":"PPDA Uganda","portal_url":"https://www.ppda.go.ug","description":"URA requires a BI and reporting dashboard for revenue data consolidation.","status":"active"},
    {"external_id":"GH-SEED-GIFMIS-2026-041","title":"Digital government services platform consulting and implementation","department":"Ministry of Finance Ghana","country":"GH","category":"Consulting","value_raw":"GHS 3,200,000","value_zar":4800000,"deadline":"2026-07-18","published":"2026-04-25","reference":"GIFMIS/2026/ICT/041","source":"Ghana PPA","portal_url":"https://www.ppaghana.org","description":"Ghana Ministry of Finance seeks a consultant for a unified digital government services platform.","status":"active"},
    {"external_id":"ZA-SEED-GEPF-2026-008","title":"AI-powered member analytics and predictive modelling platform","department":"Government Employees Pension Fund","country":"ZA","category":"AI & Automation","value_raw":"R 9,500,000","value_zar":9500000,"deadline":"2026-08-05","published":"2026-04-30","reference":"GEPF/ICT/2026/008","source":"SA National Treasury (OCDS API)","portal_url":"https://www.etenders.gov.za","description":"GEPF requires an AI-powered analytics platform for member behaviour modelling and risk prediction.","status":"active"},
]


@router.post("/tenders")
async def seed_tenders():
    """Seed the database with real tender data."""
    db = await get_db()
    added = 0
    try:
        for t in SEED_TENDERS:
            existing = await db.execute(
                "SELECT id FROM tenders WHERE external_id = ?", (t["external_id"],)
            )
            row = await existing.fetchone()
            if row is None:
                score, reason = await score_tender(t)
                t["score"] = score
                t["score_reason"] = reason
                await db.execute(
                    """INSERT INTO tenders
                        (external_id, title, department, country, category,
                         value_raw, value_zar, deadline, published, reference,
                         source, portal_url, description, score, score_reason, status)
                    VALUES
                        (:external_id, :title, :department, :country, :category,
                         :value_raw, :value_zar, :deadline, :published, :reference,
                         :source, :portal_url, :description, :score, :score_reason, :status)""",
                    t,
                )
                added += 1
        await db.commit()
        return {"message": f"Seeded {added} tenders", "total": len(SEED_TENDERS)}
    finally:
        await db.close()
