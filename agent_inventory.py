"""Internal-only, read-only company catalog evidence for the AI Agent research dashboard.

The Groq provider is not called here. Company names, SKUs and inventory do
NOT enter any LLM prompts/tools; a separate authenticated ERP query returns
business evidence directly to authorized users. This prevents accidental
cross-boundary data egress while enabling meaningful operational verification.
"""
from typing import Literal

from pydantic import BaseModel

from multi_ai import score_products

CASE_IDS = Literal[
    "STRAWBERRY_DAIRY", "MANGO_BEVERAGE", "VANILLA_BAKERY",
    "LEMON_POWDER", "RASPBERRY_ABSTAIN"
]


class CatalogPreviewRequest(BaseModel):
    case_id: CASE_IDS


def catalog_preview(db, case_id: str, cases: dict) -> dict:
    if case_id not in cases:
        raise ValueError("Unknown approved research inquiry")

    # Read only. This function performs no commits and makes no remote API calls.
    products = [dict(r) for r in db.execute(
        """SELECT p.id,p.sku,p.name,p.description,p.profile,p.application,
                  p.source_ref,
                  v.qty_packages,v.package_uom,v.package_content,
                  v.content_uom,v.dispatch_uom_status,v.confirmation_status
           FROM products p
           LEFT JOIN physical_inventory_stock v ON v.sku=p.sku
           ORDER BY p.sku"""
    ).fetchall()]
    ranked = score_products(cases[case_id], products)
    by_id = {int(p["id"]): p for p in products}
    candidates = []
    for r in ranked:
        product = by_id[int(r["product_id"])]
        has_stock = product["qty_packages"] is not None
        packages = float(product["qty_packages"]) if has_stock else None
        contents = product["package_content"]
        candidates.append({
            "rank": r["rank"],
            "sku": r["sku"],
            "name": r["name"],
            "bm25_score": r["score"],
            "stock_packages": packages,
            "stock_uom": product["package_uom"] if has_stock else "UNKNOWN",
            "pack_size": float(contents) if contents is not None else None,
            "pack_content_uom": product["content_uom"],
            "physical_stock_confirmation": product["confirmation_status"] if has_stock else "UNKNOWN",
            "package_mapping": product["dispatch_uom_status"] if has_stock else "UNKNOWN",
            "has_confirmed_on_hand": bool(has_stock and packages > 0),
            "technical_fit_verified": False,
            "source_ref": product["source_ref"],
        })
    return {
        "case_id": case_id,
        "query": cases[case_id],
        "ranker": "BM25_CATALOG_BASELINE",
        "candidate_count": len(candidates),
        "candidates": candidates,
        "catalog_rows_considered": len(products),
        "company_data_sent_to_groq": False,
        "database_mutated": False,
        "decision_status": "TECHNICAL_REVIEW_REQUIRED",
        "limitations": (
            "Stok fisik dikonfirmasi pengguna, namun belum dikurangi oleh transaksi ini. "
            "Kecocokan produk, regulatory, halal dan TDS masih memerlukan review Technical. "
            "Skor BM25 bukan probabilitas kelayakan."
        ),
    }


def inventory_lookup(db, sku: str) -> dict | None:
    sku = sku.strip()
    if not sku or len(sku) > 90:
        return None
    row = db.execute(
        """SELECT p.sku,p.name,p.source_ref,
                  v.qty_packages,v.package_uom,v.package_content,v.content_uom,
                  v.confirmation_status,v.dispatch_uom_status,v.confirmed_at
           FROM products p LEFT JOIN physical_inventory_stock v ON v.sku=p.sku
           WHERE LOWER(p.sku)=LOWER(?) LIMIT 1""", (sku,)
    ).fetchone()
    if not row:
        return None
    data = dict(row)
    physical = data.pop("qty_packages")
    content = data.pop("package_content")
    return {
        "sku": data["sku"],
        "product": data["name"],
        "stock_packages": float(physical) if physical is not None else None,
        "package_uom": data["package_uom"] or "UNKNOWN",
        "pack_size": float(content) if content is not None else None,
        "pack_content_uom": data["content_uom"],
        "stock_status": data["confirmation_status"] or "NOT_CONFIRMED",
        "package_mapping_status": data["dispatch_uom_status"] or "UNKNOWN",
        "confirmed_at": data["confirmed_at"],
        "catalog_source_ref": data["source_ref"],
        "can_prove_technical_suitability": False,
        "is_live_stock_deduction": False,
        "company_data_sent_to_groq": False,
    }


def local_readiness(db, cases: dict, make_snapshot) -> dict:
    statuses = []
    for case_id in cases:
        data = make_snapshot(case_id)
        statuses.append({
            "case_id": case_id,
            "has_ai01": isinstance(data.get("AI-01", {}).get("output"), dict),
            "has_ai02": isinstance(data.get("AI-02", {}).get("top5"), list),
            "has_ai03": isinstance(data.get("AI-03", {}).get("rules"), list),
            "has_ai04": isinstance(data.get("AI-04", {}).get("forecast"), dict),
        })
    row = db.execute(
        """SELECT COUNT(*) AS sku_count,
          COALESCE(SUM(qty_packages),0) AS total_packages,
          COUNT(*) FILTER(WHERE dispatch_uom_status='UNIT_DEFINED') AS uom_mapped,
          COUNT(*) FILTER(WHERE dispatch_uom_status='UOM_PENDING') AS uom_pending
          FROM physical_inventory_stock"""
    ).fetchone()
    return {
        "baseline_functional_checks_passed": all(
            x[k] for x in statuses for k in ("has_ai01","has_ai02","has_ai03","has_ai04")
        ),
        "checked_cases": statuses,
        "physical_stock_skus": int(row["sku_count"]),
        "package_types_mapped": int(row["uom_mapped"]),
        "package_types_pending": int(row["uom_pending"]),
        "company_inventory_readonly": True,
        "company_inventory_to_llm": False,
        "agent_provider_live_call_executed_by_check": False,
        "research_validation_completed": False,
    }
