"""
Seeds ChromaDB from the single roster in `src/domain/clients.py`.

The profile prose and the policy numbers now come from the same objects, so the
document the model reads and the limits the guard enforces cannot drift apart.
Policy fields are stored as ChromaDB metadata so callers can read them structurally
instead of sniffing the text (see D-08).
"""

from src.rag.vector_store import collection
from src.domain.clients import HERO_CLIENTS


def seed_database():
    documents = []
    metadatas = []
    ids = []

    for i, profile in enumerate(HERO_CLIENTS):
        documents.append(profile.narrative.strip())
        metadatas.append({
            "client_name": profile.name,
            "tier": profile.tier,
            "contact": profile.contact,
            "terms": profile.terms,
            "risk_level": profile.risk_level,
            "max_autonomous_stage": profile.max_autonomous_stage,
            "discount_authority_pct": profile.discount_authority_pct,
            "allow_payment_plan": profile.allow_payment_plan,
            "requires_split_billing": profile.requires_split_billing,
            "escalation_patience_days": profile.escalation_patience_days,
            "relationship_value": profile.relationship_value,
            # ChromaDB metadata values must be scalars, so the list is joined.
            "guardrails": " | ".join(profile.guardrails),
        })
        ids.append(f"profile_{i}")

    collection.upsert(documents=documents, metadatas=metadatas, ids=ids)
