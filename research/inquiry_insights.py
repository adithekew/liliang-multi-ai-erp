"""Evidence-bound, deterministic insights for each ERP inquiry and saved ranking.

Notes interpret lexical/catalog evidence only. No generated facts, no LLM, no
learned confidence, and no claim that a candidate is suitable or compliant.
Historical legacy rankings are NOT retroactively rescored or overwritten.
"""
from research.catalog_matcher import query_intent, normalized_tokens, _product_form, _product_application

def _word(xs):
    return ", ".join(xs) if xs else "belum ditentukan"

def candidate_insight(candidate, requirement):
    p=dict(candidate)
    expected=query_intent(requirement)
    title=set(normalized_tokens(p.get("name","")))
    known_flavors=set(expected["flavors"])
    matched=sorted(known_flavors & title)
    if known_flavors:
        flavor_state="NAME_MATCH" if matched else "MISMATCH"
        flavor_note=("Nama katalog mengandung rasa "+_word(matched)+"."
            if matched else "Nama produk tidak memuat rasa utama yang diminta ("+_word(sorted(known_flavors))+").")
    else:
        flavor_state="UNKNOWN"
        flavor_note="Rasa utama tidak dapat diekstrak dengan pasti dari inquiry."
    found_form=_product_form(p)
    wanted_forms=set(expected["forms"])
    if wanted_forms:
        if found_form in wanted_forms:
            form_state="CATALOG_MATCH";form_note="Indikasi bentuk produk: "+found_form+" (berdasarkan katalog)."
        elif found_form is None:
            form_state="UNKNOWN";form_note="Bentuk produk belum tercantum secara jelas dalam sumber katalog."
        else:
            form_state="MISMATCH";form_note="Bentuk tercatat "+found_form+", sedangkan dibutuhkan "+_word(sorted(wanted_forms))+"."
    else:
        form_state="NOT_REQUESTED";form_note="Bentuk fisik tidak menjadi persyaratan eksplisit pada inquiry."
    actual_apps=_product_application(p)
    wanted_apps=set(expected["applications"])
    if wanted_apps:
        overlap=sorted(wanted_apps & actual_apps)
        if overlap:
            app_state="CATALOG_MATCH"
            app_note="Katalog menyebut aplikasi "+_word(overlap)+"."
        elif actual_apps:
            app_state="NOT_EVIDENCED"
            app_note="Katalog menyebut "+_word(sorted(actual_apps))+", tetapi belum membuktikan aplikasi "+_word(sorted(wanted_apps))+"."
        else:
            app_state="UNKNOWN"
            app_note="Aplikasi "+_word(sorted(wanted_apps))+" belum didukung informasi katalog yang tersedia."
    else:
        app_state="NOT_REQUESTED";app_note="Aplikasi belum ditentukan oleh Sales/customer."
    blockers=[]
    if flavor_state=="MISMATCH":blockers.append("Rasa utama tidak sesuai")
    if form_state=="MISMATCH":blockers.append("Bentuk produk tidak sesuai")
    if actual_apps=={"vape"} and "vape" not in wanted_apps:
        blockers.append("Produk memiliki indikasi penggunaan non-pangan")
    if blockers:
        decision="DO_NOT_RECOMMEND"
        note="Jangan tawarkan kandidat ini: "+_word(blockers)+". Cari SKU lain atau klarifikasi kebutuhan."
        risk="HIGH"
    else:
        risk="REVIEW"
        decision="TECHNICAL_VALIDATION_REQUIRED"
        note=("Kandidat memenuhi sebagian indikasi teks pada katalog. "
              "Kesesuaian aplikasi, formula, dosis, sensori, kelarutan, regulasi, halal, "
              "dan bukti datasheet belum diverifikasi; perlu penilaian Technical.")
    flags=[
        {"aspect":"Rasa utama","status":flavor_state,"detail":flavor_note},
        {"aspect":"Bentuk produk","status":form_state,"detail":form_note},
        {"aspect":"Aplikasi","status":app_state,"detail":app_note},
        {"aspect":"Kesesuaian teknis, halal, regulatory","status":"UNKNOWN",
         "detail":"Belum ada verifikasi pakar/datasheet yang membuktikan kesesuaian atau kepatuhan."}
    ]
    if p.get("expert_decision"):
        # Keep human review provenance, not as a model accuracy signal.
        note+=" Catatan terpisah: reviewer Technical mencatat "+str(p["expert_decision"])+"."
    return {
        "product_id":p.get("product_id",p.get("id")),
        "sku":p.get("sku"),
        "decision_support":decision,
        "risk":risk,
        "flags":flags,
        "note":note,
        "catalog_source":p.get("source_ref") or "UNKNOWN",
        "evidence_classification":"CATALOG_TEXT_UNVERIFIED",
        "technical_decision":p.get("expert_decision"),
        "relevance_label":p.get("expert_relevance")
    }

def inquiry_insight(requirement, candidates, method=None, status=None):
    intent=query_intent(requirement)
    reasons=[candidate_insight(c,requirement) for c in candidates]
    permitted=sum(z["decision_support"]!="DO_NOT_RECOMMEND" for z in reasons)
    rejects=sum(z["decision_support"]=="DO_NOT_RECOMMEND" for z in reasons)
    if not reasons:
        summary="Tidak ada kandidat yang tersimpan. Mohon klarifikasi rasa, bentuk, aplikasi, atau cek cakupan katalog; jangan membuat substitusi otomatis."
        stage="CLARIFICATION_REQUIRED"
    elif permitted==0:
        summary="Seluruh kandidat memiliki konflik rasa/bentuk atau kategori penggunaan. Jangan direkomendasikan sampai kebutuhan dan sumber katalog diverifikasi."
        stage="CONFLICT_REVIEW_REQUIRED"
    else:
        summary=(str(permitted)+" kandidat memenuhi pemeriksaan awal teks katalog, "
                 +str(rejects)+" kandidat ditandai berisiko tidak sesuai. Belum ada SKU yang otomatis dinyatakan layak dipakai.")
        stage="TECHNICAL_REVIEW_REQUIRED"
    actions=[
        "Sales: konfirmasi rasa yang dimaksud customer serta bentuk, aplikasi, dan preferensi organoleptik.",
        "Technical: periksa datasheet asli, persentase dosis, kestabilan, kelarutan, sampel dan regulasi/halal sesuai pasar.",
        "Technical: berikan label relevansi 0–3 dan alasan berbasis bukti pada tiap kandidat; jangan anggap skor BM25 sebagai probabilitas.",
        "Manager: review hasil Technical sebelum approval; jangan menggunakan status pencarian sebagai persetujuan teknis."
    ]
    return {
        "insight_version":"deterministic-catalog-insight-v1",
        "generated_from":"CURRENT_INQUIRY_AND_SAVED_CANDIDATES",
        "ranking_method":method or "UNKNOWN",
        "inquiry_status":status or "UNKNOWN",
        "interpreted_requirement":{
            "flavors":intent["flavors"],
            "forms":intent["forms"],
            "applications":intent["applications"],
            "normalized_text":intent["normalized_text"]
        },
        "summary":summary,
        "stage":stage,
        "candidate_count":len(reasons),
        "technical_review_required":True,
        "model_accuracy_evidence":False,
        "next_actions":actions,
        "candidates":reasons,
        "notice":"Auto-generated explanation from unverified catalog text; it is neither LLM inference nor expert product validation. Legacy saved rankings may contain known mistakes."
    }
