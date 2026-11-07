"""Read-only AI advisory for an existing Sales-created ERP inquiry.

This is a deterministic decision-support layer on the latest persisted BM25
retrieval and user-confirmed inventory. It NEVER invokes Groq or writes an
approval, expert review, dispatch, stock balance, or inference history.
Company data remains inside the ERP API response to authorized users.
"""
from fastapi import HTTPException
from multi_ai import interpret

ALLOWED={"admin","sales","technical","manager"}
NEXT_ACTIONS={
    "NEW": ("SALES","Jalankan pencarian BM25 pada transaksi terlebih dahulu."),
    "NO_MATCH": ("SALES","Klarifikasi kebutuhan; jangan memilih SKU tanpa kandidat."),
    "MATCHED": ("SALES","Tinjau kandidat dan submit permintaan sampel kepada Technical."),
    "TECH_REVIEWED": ("MANAGER","Periksa hasil Technical; keputusan akhir tidak otomatis."),
    "APPROVED": ("MANAGER","Lanjutkan proses operasional yang telah mendapat otorisasi."),
    "RETURNED": ("SALES","Revisi inquiry dan lakukan matching ulang."),
}

def _lookup(db,iid,user):
    if user["role"] not in ALLOWED:
        raise HTTPException(403,"Role access denied")
    row=db.execute(
        """SELECT id,created_by,status,requirement,created_at
           FROM inquiries WHERE id=?""",(iid,)
    ).fetchone()
    if not row:
        raise HTTPException(404,"Inquiry not found")
    q=dict(row)
    if user["role"]=="sales" and q["created_by"]!=user["id"]:
        raise HTTPException(403,"Not your Sales inquiry")
    return q

def list_inquiries(db,user,limit=50):
    if user["role"] not in ALLOWED:
        raise HTTPException(403,"Role access denied")
    if user["role"]=="sales":
        rows=db.execute(
            """SELECT id,status,created_at FROM inquiries
               WHERE created_by=? ORDER BY id DESC LIMIT ?""",
            (user["id"],limit)
        ).fetchall()
    else:
        rows=db.execute(
            """SELECT id,status,created_at FROM inquiries
               ORDER BY id DESC LIMIT ?""",(limit,)
        ).fetchall()
    return {"rows":[dict(r) for r in rows],
            "scope":"AUTHORISED_INQUIRY_METADATA_ONLY",
            "company_data_sent_to_groq":False}

def inquiry_advice(db,iid,user):
    q=_lookup(db,iid,user)
    requirement=q["requirement"] or ""
    attrs=interpret(requirement)
    run=db.execute(
        """SELECT id,method,latency_ms,created_at FROM runs
           WHERE inquiry_id=? ORDER BY id DESC LIMIT 1""",(iid,)
    ).fetchone()
    run=dict(run) if run else None
    # Returned/new inquiries can have historical runs. They are NOT current.
    current_run=bool(run and q["status"] not in ("NEW","RETURNED"))
    rows=[]
    if current_run:
        rows=db.execute(
            """SELECT c.rank,c.score,p.sku,p.name,p.source_ref,
                      v.qty_packages,v.package_uom,v.package_content,
                      v.content_uom,v.confirmation_status,
                      v.dispatch_uom_status,
                      (SELECT rv.decision FROM reviews rv
                       WHERE rv.run_id=c.run_id AND rv.product_id=c.product_id
                       ORDER BY rv.id DESC LIMIT 1) AS technical_decision,
                      (SELECT rv.label FROM reviews rv
                       WHERE rv.run_id=c.run_id AND rv.product_id=c.product_id
                       ORDER BY rv.id DESC LIMIT 1) AS technical_label
               FROM candidates c
               JOIN products p ON p.id=c.product_id
               LEFT JOIN physical_inventory_stock v ON v.sku=p.sku
               WHERE c.run_id=?
               ORDER BY c.rank LIMIT 5""",(run["id"],)
        ).fetchall()
    candidates=[]
    for r in rows:
        row=dict(r)
        available=row["qty_packages"]
        qty=float(available) if available is not None else None
        mapping=row["dispatch_uom_status"] or "UNKNOWN"
        decision=row["technical_decision"]
        grade=row["technical_label"]
        flags=["DATASHEET_UNVERIFIED","REGULATORY_UNVERIFIED","HALAL_UNVERIFIED"]
        if qty is None: flags.append("STOCK_NOT_CONFIRMED")
        elif qty<=0: flags.append("OUT_OF_STOCK")
        if mapping!="UNIT_DEFINED":flags.append("PACKAGE_UOM_NOT_DEFINED")
        if decision is None:flags.append("EXPERT_REVIEW_PENDING")
        elif decision=="REJECT":flags.append("EXPERT_REJECTED")
        elif decision=="NEEDS_INFO":flags.append("EXPERT_MORE_INFO")
        elif decision=="ACCEPT" and grade!=3:flags.append("EXPERT_LABEL_INCONSISTENT")
        candidates.append({
            "rank":row["rank"],"sku":row["sku"],"name":row["name"],
            "bm25_score":float(row["score"]),
            "source_ref":row["source_ref"],
            "stock_packages":qty,
            "package_uom":row["package_uom"] or "UNKNOWN",
            "pack_size":float(row["package_content"]) if row["package_content"] is not None else None,
            "pack_content_uom":row["content_uom"],
            "user_confirmed_physical_stock":row["confirmation_status"] in
                ("USER_CONFIRMED_PHYSICAL","PHYSICAL_COUNT_UPDATED"),
            "package_mapping":mapping,
            "technical_decision":decision,
            "technical_label":grade,
            "technical_relevance_accepted":bool(decision=="ACCEPT" and grade==3),
            "technical_suitability_proven":False,
            "risk_flags":flags,
        })
    sample=db.execute(
        """SELECT status,product_id,qty_kg,run_id FROM sample_requests
           WHERE inquiry_id=?""",(iid,)
    ).fetchone()
    sample=dict(sample) if sample else None
    if sample and sample["status"]=="WAITING_TECHNICAL":
        actor,action="TECHNICAL","Catat label relevansi pakar 0–3 dan submit SKU yang dipilih."
    elif sample and sample["status"]=="WAITING_MANAGER":
        actor,action="MANAGER","Review rekomendasi Technical sebelum memutuskan."
    elif sample and sample["status"] in ("WAITING_WAREHOUSE","WAREHOUSE_READY"):
        actor,action="GUDANG","Periksa stok khusus sampel dalam alur UAT Gudang."
    elif sample and sample["status"]=="DISPATCHED_UAT":
        actor,action="COMPLETED","Surat Jalan UAT sudah diterbitkan; bukan pengiriman fisik."
    else:
        actor,action=NEXT_ACTIONS.get(q["status"],("SALES","Periksa status transaksi."))
    # Never expose recipient/destination/customer reference to advisory.
    package_summary=(
        f"{candidates[0]['stock_packages']:g} {candidates[0]['package_uom']}"
        if candidates and candidates[0]["stock_packages"] is not None
        else "belum terbukti"
    )
    insight=(
        f"Inquiry INQ-{iid}: kandidat BM25 pertama {candidates[0]['sku']} "
        f"memiliki catatan stok fisik {package_summary}. "
        "Ini hanya prioritas pencarian, bukan bukti kesesuaian teknis. "
        f"Tahap berikutnya: {actor}."
        if candidates else
        f"Inquiry INQ-{iid}: tidak ada kandidat aktif yang tersimpan. "
        "Jalankan matching pada halaman transaksi atau klarifikasi kebutuhan; "
        "jangan menggunakan hasil historis sebagai persetujuan."
    )
    return {
        "inquiry_id":iid,"status":q["status"],
        "created_at":q["created_at"],
        "requirement":requirement,
        "attributes":{
            "flavor":attrs["flavor"],
            "application":attrs["application"],
            "form":attrs["form"],
            "regulatory_status":"UNKNOWN",
            "halal_status":"UNKNOWN",
            "method":"RULE_BASED_NOT_TRAINED"
        },
        "latest_run_id":run["id"] if current_run else None,
        "previous_run_ignored":bool(run and not current_run),
        "ranking_method":run["method"] if current_run else "NOT_RUN",
        "candidate_count":len(candidates),
        "candidates":candidates,
        "sample_status":sample["status"] if sample else None,
        "next_actor":actor,"recommended_next_action":action,
        "executive_insight":insight,
        "advisory_only":True,"company_data_sent_to_groq":False,
        "database_mutated":False,
        "stock_deducted":False,"approval_created":False,
        "expert_validation_complete":False,
        "limitations":[
          "BM25 is an uncalibrated retrieval score, not a suitability probability.",
          "Stock on-hand is user-confirmed; UOM pending on some SKUs.",
          "Halal/regulatory/datasheet conformity requires independent Technical verification.",
          "This advice does not change Technical, Manager, or Gudang workflow.",
        ]
    }
