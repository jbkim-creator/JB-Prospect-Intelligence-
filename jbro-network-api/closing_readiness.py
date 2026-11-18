"""Administrator-only evidence checklist. No contracts, orders or payments are created."""
from flask import jsonify, request
from datetime import datetime
from zoneinfo import ZoneInfo

CHECKS = {
    "semiconductor": ("buyer_quantity_price","stock_traceability","inspection_acceptance","payment_delivery","fee_protection","compliance","written_order"),
    "industrial": ("buyer_quantity_price","asset_ownership_condition","inspection_acceptance","payment_delivery","fee_protection","compliance","written_order"),
    "vehicle": ("buyer_quantity_price","vehicle_title_condition","inspection_acceptance","payment_delivery","fee_protection","compliance","written_order"),
    "infrastructure": ("buyer_mandate","asset_authority","commercial_terms","payment_delivery","fee_protection","compliance","written_order"),
    "other": ("buyer_quantity_price","seller_authority","commercial_terms","payment_delivery","fee_protection","compliance","written_order"),
}
STATES={"pending","documented","not_applicable"}
OPTIONAL={"inspection_acceptance"}

def summarize(case, rows):
    required=CHECKS.get(case["sector"],CHECKS["other"])
    evidence={r["check_key"]:r for r in rows}
    checks=[]
    for key in required:
        r=evidence.get(key,{})
        state=r.get("state","pending")
        ref=r.get("evidence_ref","")
        if not ref or (state=="not_applicable" and key not in OPTIONAL):
            state="pending"
        if key=="fee_protection" and case["fee_state"] not in ("written_agreement","waived"):
            state="pending"
        checks.append(dict(key=key,state=state,evidence_ref=ref,note=r.get("note",""),revision=r.get("revision",0)))
    missing=[c["key"] for c in checks if c["state"] not in ("documented","not_applicable")]
    return dict(deal_key=case["deal_key"],title=case["title"],stage=case["stage"],
        sector=case["sector"],fee_state=case["fee_state"],checks=checks,
        documented_count=len(checks)-len(missing),total=len(checks),missing=missing,
        status="review_for_handoff" if not missing else "evidence_pending",
        blocker=case["blocker"],next_action=case["next_action"],
        decision="manual_review_required")

def ensure_schema(connection):
    with connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS closing_readiness_checks (
                deal_key VARCHAR(64) NOT NULL REFERENCES closing_desk_cases(deal_key),
                check_key VARCHAR(48) NOT NULL,
                state VARCHAR(20) NOT NULL CHECK(state IN ('pending','documented','not_applicable')),
                evidence_ref VARCHAR(240) NOT NULL DEFAULT '',
                note VARCHAR(600) NOT NULL DEFAULT '',
                revision INTEGER NOT NULL DEFAULT 1 CHECK(revision>0),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                PRIMARY KEY(deal_key,check_key),
                CHECK(state='pending' OR length(trim(evidence_ref))>0)
            )
        """)

def init(app,connection,authorized_admin):
    @app.get("/api/admin/closing-readiness")
    def readiness():
        if not authorized_admin(): return jsonify(error="unauthorized"),401
        try:
            ensure_schema(connection)
            with connection() as conn:
                cases=conn.execute("SELECT deal_key,title,sector,stage,fee_state,blocker,next_action FROM closing_desk_cases WHERE stage NOT IN ('lost','on_hold','handoff') ORDER BY due_date ASC NULLS LAST,id LIMIT 201").fetchall()
                visible=cases[:200]
                rows=conn.execute("SELECT * FROM closing_readiness_checks WHERE deal_key=ANY(%s)",([c["deal_key"] for c in visible],)).fetchall() if visible else []
            grouped={}
            for row in rows: grouped.setdefault(row["deal_key"],[]).append(row)
            return jsonify(items=[summarize(c,grouped.get(c["deal_key"],[])) for c in visible],
                truncated=len(cases)>200,as_of=datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat(),
                definition="Document checklist only; never approval, trade, compliance clearance or collected revenue.")
        except Exception:
            app.logger.warning("Closing readiness read failed")
            return jsonify(error="temporarily_unavailable"),503

    @app.post("/api/admin/closing-readiness/check")
    def save_check():
        if not authorized_admin(): return jsonify(error="unauthorized"),401
        d=request.get_json(silent=True)
        if not isinstance(d,dict): return jsonify(error="invalid_payload"),400
        key=d.get("deal_key"); check=d.get("check_key"); state=d.get("state")
        ref=d.get("evidence_ref",""); note=d.get("note",""); rev=d.get("revision")
        if not all(isinstance(x,str) for x in (key,check,state,ref,note)): return jsonify(error="invalid_fields"),400
        if not key or len(key)>64 or len(check)>48 or state not in STATES or len(ref)>240 or len(note)>600 or type(rev) is not int or rev<0:
            return jsonify(error="invalid_fields"),400
        if state!="pending" and not ref.strip(): return jsonify(error="evidence_required"),400
        if state=="not_applicable" and check not in OPTIONAL: return jsonify(error="required_check"),400
        try:
            ensure_schema(connection)
            with connection() as conn:
                c=conn.execute("SELECT sector,stage,fee_state FROM closing_desk_cases WHERE deal_key=%s FOR UPDATE",(key,)).fetchone()
                if not c or c["stage"] in ("lost","on_hold","handoff"): return jsonify(error="case_not_active"),400
                if check not in CHECKS.get(c["sector"],CHECKS["other"]): return jsonify(error="invalid_check"),400
                if check=="fee_protection" and state=="documented" and c["fee_state"] not in ("written_agreement","waived"):
                    return jsonify(error="closing_desk_fee_agreement_required"),400
                if rev==0:
                    row=conn.execute("INSERT INTO closing_readiness_checks(deal_key,check_key,state,evidence_ref,note) VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING RETURNING revision",(key,check,state,ref.strip(),note.strip())).fetchone()
                else:
                    row=conn.execute("UPDATE closing_readiness_checks SET state=%s,evidence_ref=%s,note=%s,revision=revision+1,updated_at=now() WHERE deal_key=%s AND check_key=%s AND revision=%s RETURNING revision",(state,ref.strip(),note.strip(),key,check,rev)).fetchone()
                if not row: return jsonify(error="stale_revision"),409
                return jsonify(saved=True,revision=row["revision"])
        except Exception:
            app.logger.warning("Closing readiness save failed")
            return jsonify(error="temporarily_unavailable"),503
