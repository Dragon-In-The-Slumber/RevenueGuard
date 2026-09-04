from src.rag.vector_store import collection

seed_profiles = [
    {
        "client_name": "Acme Corp",
        "content": """
- Company: Acme Corp (Fortune 500 Manufacturing)
- Contract: Master Service Agreement dated Jan 2024. Net-60 payment terms.
- Key Contact: Rajesh Kumar, Finance Manager (rajesh.kumar@acme.com)
- Payment History: 12 invoices in last 12 months. 10 paid on time. 2 paid 5-8 days late.
- Notes: Very reliable. Delays usually due to internal approval cycles, not cash flow.
  Never threaten legal action — they are a Tier 1 client worth ₹2Cr annually.
- Preferred Channel: Email. CC to accounts@acme.com for invoices > ₹5,00,000.
"""
    },
    {
        "client_name": "Globex Solutions",
        "content": """
- Company: Globex Solutions (Series B SaaS Startup, 150 employees)
- Contract: Service Agreement dated Mar 2024. Net-30 payment terms. 1.5% monthly late fee clause.
- Key Contact: Priya Mehta, Head of Finance (priya@globex.io)
- Payment History: 6 invoices in last 8 months. 2 paid on time. 3 paid 15-25 days late.
  1 still outstanding (INV-2024-0612, ₹3,40,000, 45 days overdue).
- Past Disputes: Disputed INV-2024-0489 ("Wrong quantity billed for API calls"). Resolved
  in 8 days after credit note of ₹12,000.
- Notes: HIGH RISK. Has broken two Promise-to-Pay commitments in 2024 (promised Oct 15,
  paid Nov 3; promised Jul 20, paid Aug 8). Cash flow constrained — "budget cycle" is
  frequently cited. Requires firm but professional tone. Escalate to human after Stage 2.
"""
    },
    {
        "client_name": "Pinnacle Industries",
        "content": """
- Company: Pinnacle Industries (Listed Conglomerate, 5000+ employees)
- Contract: Annual Retainer Agreement. Net-45 terms. Auto-renewal clause.
- Key Contact: Vikram Singh, VP Finance (v.singh@pinnacle.co.in)
- Payment History: 8 invoices. 5 paid on time. 3 disputed (2 resolved, 1 pending).
- Past Disputes: Pattern of disputing consulting hours (Milestone 2 charges).
  Always accepts Milestone 1 (deliverables). Average dispute resolution: 12 days.
- Notes: Do NOT combine Milestone 1 and 2 in a single payment link. Issue separate
  links for undisputed and disputed portions. VP Singh responds only to Stage 2+ emails.
  Prefers formal language with contract clause references.
"""
    },
    {
        "client_name": "NovaTech Labs",
        "content": """
- Company: NovaTech Labs (Seed-stage AI startup, 12 employees)
- Contract: Project-based SOW. Net-15 payment terms. No late fee clause.
- Key Contact: Arjun Patel, CEO (arjun@novatech.ai)
- Payment History: 3 invoices. 1 paid on time. 2 ghosted (no response to any
  communication for 30+ days).
- Notes: EXTREME HIGH RISK. Company may be running out of runway. CEO is the only
  contact. No finance team. After Stage 2, escalate to human immediately — do not
  waste further automated outreach. Consider offering a 10% early payment discount
  to accelerate recovery of whatever is possible.
"""
    }
]

def seed_database():
    documents = []
    metadatas = []
    ids = []
    
    for i, profile in enumerate(seed_profiles):
        documents.append(profile["content"])
        metadatas.append({"client_name": profile["client_name"]})
        ids.append(f"profile_{i}")
        
    collection.upsert(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
