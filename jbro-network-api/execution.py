"""Post-signature Deal Room execution evidence and contract export (pilot).

Evidence references and status transitions are self-reported; JBRO must review.
No automatic bank reconciliation, tracking, escrow, or transfer of funds/title.
"""
import hashlib
import hmac
import json
import logging
from flask import Blueprint, jsonify, request, make_response

bp=Blueprint("execution",__name__)
DB=ADMIN=PARTNER=None
log=logging.getLogger(__name__)
STAGES={"inspection","shipment","delivery","payment"}
ACTORS={"buyer","seller"}

def init(app, connection, admin_auth, partner_auth):
    global DB,ADMIN,PARTNER
    DB,ADMIN,PARTNER=connection,admin_auth,partner_auth
    app.register_blueprint(bp)

def ensure_schema():
    with DB() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS deal_execution_events (
          id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
          room_id BIGINT NOT NULL REFERENCES deal_rooms(id),
          stage VARCHAR(20) NOT NULL CHECK(stage IN ('inspection','shipment','delivery','payment')),
          actor_application_id BIGINT NOT NULL REFERENCES partner_applications(id),
          evidence_reference VARCHAR(180) NOT NULL,
          note VARCHAR(900) NOT NULL,
          status VARCHAR(24) NOT NULL DEFAULT 'submitted'
             CHECK(status IN ('submitted','verified','rejected')),
          reviewed_at TIMESTAMPTZ,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS deal_execution_events_room_created_idx ON deal_execution_events(room_id,created_at DESC)")

def fail(message,status=400):return jsonify(error=message),status

def get_room(conn,room_id,aid=None):
    if aid is None:
        return conn.execute("SELECT * FROM deal_rooms WHERE id=%s",(room_id,)).fetchone()
    return conn.execute("""SELECT * FROM deal_rooms WHERE id=%s
         AND (buyer_application_id=%s OR seller_application_id=%s)""",(room_id,aid,aid)).fetchone()

def events(conn,room_id):
    rows=conn.execute("""SELECT e.id,e.stage,e.status,e.evidence_reference,e.note,e.created_at,
         e.actor_application_id,a.organization
         FROM deal_execution_events e JOIN partner_applications a ON a.id=e.actor_application_id
         WHERE e.room_id=%s ORDER BY e.id DESC LIMIT 100""",(room_id,)).fetchall()
    return [dict(x,created_at=x["created_at"].isoformat()) for x in rows]

def contract_bundle(conn,room):
    contract=conn.execute("""SELECT c.id,c.version,c.terms_json,c.document_sha256,c.status,c.issued_at,c.completed_at
        FROM deal_sale_contracts c WHERE c.room_id=%s ORDER BY c.version DESC LIMIT 1""",(room["id"],)).fetchone()
    if not contract:return None
    approvals=conn.execute("""SELECT signer_role,representative,document_sha256,accepted_at
        FROM deal_sale_assents WHERE contract_id=%s ORDER BY signer_role""",(contract["id"],)).fetchall()
    snapshot={
      "export_type":"JBRO_DEALROOM_CONTRACT_RECORD",
      "record_disclaimer":"Authentication-based pilot assent record. Not a qualified electronic signature or independent verification of signer authority.",
      "room_id":room["id"],
      "room_status":room["status"],
      "contract_id":contract["id"],
      "version":contract["version"],
      "document_sha256":contract["document_sha256"],
      "document_text":contract["terms_json"],
      "issued_at":contract["issued_at"].isoformat() if contract["issued_at"] else None,
      "completed_at":contract["completed_at"].isoformat() if contract["completed_at"] else None,
      "assents":[{"signer_role":x["signer_role"],"representative":x["representative"],
           "document_sha256":x["document_sha256"],"accepted_at":x["accepted_at"].isoformat()} for x in approvals]
    }
    snapshot["export_sha256"]=hashlib.sha256(json.dumps(snapshot,sort_keys=True,ensure_ascii=False,
        separators=(",",":")).encode()).hexdigest()
    return snapshot

@bp.get("/api/admin/deal-rooms/<int:room_id>/contract-export")
def admin_contract_export(room_id):
    if not ADMIN():return fail("unauthorized",401)
    try:
        with DB() as conn:
            room=get_room(conn,room_id)
            if not room:return fail("not_found",404)
            bundle=contract_bundle(conn,room)
        if not bundle:return fail("not_found",404)
        response=make_response(jsonify(bundle))
        response.headers["Content-Disposition"]=f'attachment; filename="JBRO-Deal-{room_id}-contract-record.json"'
        response.headers["Cache-Control"]="no-store"
        return response
    except Exception:
        log.exception("Admin contract export failed");return fail("temporarily_unavailable",503)

@bp.get("/api/partner/deal-rooms/<int:room_id>/contract-export")
def partner_contract_export(room_id):
    try:
        aid=PARTNER()
        if aid is None:return fail("unauthorized",401)
        with DB() as conn:
            room=get_room(conn,room_id,aid)
            if not room or room["status"]=="draft":return fail("not_found",404)
            bundle=contract_bundle(conn,room)
        if not bundle:return fail("not_found",404)
        response=make_response(jsonify(bundle))
        response.headers["Content-Disposition"]=f'attachment; filename="JBRO-Deal-{room_id}-contract-record.json"'
        response.headers["Cache-Control"]="no-store"
        return response
    except Exception:
        log.exception("Partner contract export failed");return fail("temporarily_unavailable",503)

@bp.get("/api/admin/deal-rooms/<int:room_id>/execution")
def admin_execution(room_id):
    if not ADMIN():return fail("unauthorized",401)
    try:
        with DB() as conn:
            room=get_room(conn,room_id)
            if not room:return fail("not_found",404)
            return jsonify(events=events(conn,room_id))
    except Exception:
        return fail("temporarily_unavailable",503)

@bp.get("/api/partner/deal-rooms/<int:room_id>/execution")
def partner_execution(room_id):
    try:
        aid=PARTNER()
        if aid is None:return fail("unauthorized",401)
        with DB() as conn:
            room=get_room(conn,room_id,aid)
            if not room or room["status"]=="draft":return fail("not_found",404)
            return jsonify(events=events(conn,room_id))
    except Exception:
        return fail("temporarily_unavailable",503)

@bp.post("/api/partner/deal-rooms/<int:room_id>/execution")
def submit_evidence(room_id):
    try:
        aid=PARTNER()
        if aid is None:return fail("unauthorized",401)
        data=request.get_json(silent=True)
        if not isinstance(data,dict):return fail("invalid_payload")
        stage=data.get("stage");ref=data.get("evidence_reference");note=data.get("note")
        if (stage not in STAGES or not isinstance(ref,str) or not 4<=len(ref.strip())<=180
            or not isinstance(note,str) or not 10<=len(note.strip())<=900
            or data.get("confirm_accurate_and_authorized") is not True):
            return fail("invalid_fields")
        with DB() as conn:
            with conn.cursor() as cur:
                room=cur.execute("""SELECT id,status FROM deal_rooms WHERE id=%s
                    AND (buyer_application_id=%s OR seller_application_id=%s) FOR UPDATE""",
                    (room_id,aid,aid)).fetchone()
                if not room or room["status"]!="signed":return fail("signed_sale_contract_required",409)
                count=cur.execute("""SELECT count(*)::int AS n FROM deal_execution_events
                    WHERE room_id=%s AND actor_application_id=%s AND created_at>=now()-interval '24 hours'""",
                    (room_id,aid)).fetchone()["n"]
                if count>=20:return fail("daily_submission_limit",429)
                row=cur.execute("""INSERT INTO deal_execution_events(room_id,stage,actor_application_id,
                    evidence_reference,note) VALUES(%s,%s,%s,%s,%s) RETURNING id""",
                    (room_id,stage,aid,ref.strip(),note.strip())).fetchone()
                cur.execute("INSERT INTO deal_room_audit(room_id,event,reference) VALUES(%s,'execution_evidence_submitted',%s)",
                    (room_id,str(row["id"])))
        return jsonify(event_id=row["id"],status="submitted",note="Evidence awaiting JBRO verification; no real-world milestone is confirmed."),201
    except Exception:
        log.exception("Submit execution evidence failed");return fail("temporarily_unavailable",503)

@bp.patch("/api/admin/deal-rooms/<int:room_id>/execution/<int:event_id>")
def review_evidence(room_id,event_id):
    if not ADMIN():return fail("unauthorized",401)
    data=request.get_json(silent=True)
    if not isinstance(data,dict) or data.get("status") not in ("verified","rejected") or data.get("confirm_reviewed_evidence") is not True:
        return fail("verification_required")
    status=data["status"]
    try:
        with DB() as conn:
            with conn.cursor() as cur:
                room=cur.execute("SELECT status FROM deal_rooms WHERE id=%s FOR UPDATE",(room_id,)).fetchone()
                if not room:return fail("not_found",404)
                if room["status"]!="signed":return fail("signed_sale_contract_required",409)
                row=cur.execute("""UPDATE deal_execution_events SET status=%s,reviewed_at=now()
                    WHERE id=%s AND room_id=%s AND status='submitted' RETURNING id""",
                    (status,event_id,room_id)).fetchone()
                if not row:return fail("not_found_or_already_reviewed",409)
                cur.execute("INSERT INTO deal_room_audit(room_id,event,reference) VALUES(%s,%s,%s)",
                    (room_id,"execution_"+status,str(event_id)))
        return jsonify(event_id=event_id,status=status),200
    except Exception:
        log.exception("Execution review failed");return fail("temporarily_unavailable",503)


def smoke_test(app, admin_token, origin):
    """Real Neon E2E: bilateral sale sign -> private export -> evidence -> review -> cleanup."""
    import secrets
    nonce=secrets.token_hex(7)
    client=app.test_client()
    admin={"Authorization":"Bearer "+admin_token}
    aids=[];tokens=[];room_id=None
    try:
        for i in range(3):
            r=client.post("/api/partner-applications",json={
              "organization":"JBRO_EXECUTION_QA_"+nonce+"_"+str(i),
              "email":"execution-"+nonce+"-"+str(i)+"@example.invalid",
              "country":"Test","role":"Buyer" if i==0 else "Supplier",
              "summary":"Synthetic test-only execution participant, not a real entity.","consent":True
            },headers={"Origin":origin})
            assert r.status_code==201,("intake",r.status_code)
            aid=int(r.get_json()["reference"].split("-")[-1]);aids.append(aid)
            assert client.patch("/api/admin/applications/"+str(aid),headers=admin,json={"status":"approved"}).status_code==200
            invite=client.post("/api/admin/applications/"+str(aid)+"/issue-access",headers=admin)
            assert invite.status_code==200
            tokens.append(invite.get_json()["access_token"])
        terms={
          "buyer_legal_name":"Synthetic Buyer Incorporated",
          "seller_legal_name":"Synthetic Supplier Incorporated",
          "item_description":"Synthetic verification-only computing devices, not a genuine commercial offer.",
          "quantity_unit":"12 units",
          "total_contract_value_won":100000000,
          "delivery_terms":"DAP test-only warehouse in South Korea; no physical shipping.",
          "inspection_terms":"Test-only inspection; no goods are checked in real life.",
          "payment_terms":"Test-only payment terms; no money is transferred by this test.",
          "governing_law":"Republic of Korea",
          "dispute_resolution":"Synthetic pilot arbitration clause, not a binding instruction.",
          "additional_terms":"This record is synthetic and not a real buyer or seller agreement."
        }
        r=client.post("/api/admin/deal-rooms",headers=admin,json={
           "title":"JBRO evidence smoke test "+nonce,"buyer_application_id":aids[0],
           "seller_application_id":aids[1],"terms":terms})
        assert r.status_code==201,("room create",r.status_code)
        room_id=r.get_json()["room_id"]
        header0={"Authorization":"Bearer "+tokens[0]}
        header1={"Authorization":"Bearer "+tokens[1]}
        header2={"Authorization":"Bearer "+tokens[2]}
        premature=client.post("/api/partner/deal-rooms/"+str(room_id)+"/execution",
            headers=header0,json={"stage":"inspection","evidence_reference":"QA-REPORT-"+nonce,
               "note":"Test data only: no actual inspection was completed.","confirm_accurate_and_authorized":True})
        assert premature.status_code==409,"draft allowed evidence submission"
        assert client.post("/api/admin/deal-rooms/"+str(room_id)+"/issue",
              headers=admin,json={"confirm_sale_terms_legal_review":True}).status_code==200
        export=client.get("/api/partner/deal-rooms/"+str(room_id)+"/contract-export",headers=header0)
        assert export.status_code==200,("authorized download",export.status_code)
        bundle=export.get_json()
        assert hashlib.sha256(bundle["document_text"].encode()).hexdigest()==bundle["document_sha256"]
        copy=dict(bundle);fingerprint=copy.pop("export_sha256")
        assert hashlib.sha256(json.dumps(copy,sort_keys=True,ensure_ascii=False,
            separators=(",",":")).encode()).hexdigest()==fingerprint
        assert "attachment;" in export.headers.get("Content-Disposition","")
        assert client.get("/api/partner/deal-rooms/"+str(room_id)+"/contract-export",headers=header2).status_code==404
        doc_hash=bundle["document_sha256"]
        for header in (header0,header1):
            sign=client.post("/api/partner/deal-rooms/"+str(room_id)+"/accept",headers=header,
                json={"representative":"Synthetic Authorized Officer",
                 "document_sha256":doc_hash,"confirm_authorized_signatory":True,
                 "confirm_read_and_accept":True})
            assert sign.status_code==200,("assent",sign.status_code)
        executed=client.post("/api/partner/deal-rooms/"+str(room_id)+"/execution",
            headers=header1,json={"stage":"shipment","evidence_reference":"QA-SHIP-"+nonce,
              "note":"Synthetic shipment evidence for automated integration test only.",
              "confirm_accurate_and_authorized":True})
        assert executed.status_code==201,("evidence",executed.status_code)
        event_id=executed.get_json()["event_id"]
        assert client.get("/api/partner/deal-rooms/"+str(room_id)+"/execution",headers=header2).status_code==404
        first=client.get("/api/admin/deal-rooms/"+str(room_id)+"/execution",headers=admin)
        assert first.status_code==200 and first.get_json()["events"][0]["status"]=="submitted"
        wrong=client.patch("/api/admin/deal-rooms/"+str(room_id)+"/execution/"+str(event_id),
            headers=admin,json={"status":"verified","confirm_reviewed_evidence":False})
        assert wrong.status_code==400,"verified without explicit review"
        accepted=client.patch("/api/admin/deal-rooms/"+str(room_id)+"/execution/"+str(event_id),
            headers=admin,json={"status":"verified","confirm_reviewed_evidence":True})
        assert accepted.status_code==200,("evidence review",accepted.status_code)
        duplicate=client.patch("/api/admin/deal-rooms/"+str(room_id)+"/execution/"+str(event_id),
            headers=admin,json={"status":"verified","confirm_reviewed_evidence":True})
        assert duplicate.status_code==409,"duplicate review"
        assert client.get("/api/admin/deal-rooms/"+str(room_id)+"/contract-export",headers=admin).status_code==200
        assert client.get("/api/admin/deal-rooms/"+str(room_id)+"/contract-export").status_code==401
        log.info("JBRO_EXECUTION_SMOKE_PASS")
    finally:
        with DB() as conn:
            with conn.cursor() as cur:
                if room_id:
                    row=cur.execute("SELECT id FROM deal_rooms WHERE id=%s AND title=%s",
                       (room_id,"JBRO evidence smoke test "+nonce)).fetchone()
                    if row:
                        cur.execute("DELETE FROM deal_execution_events WHERE room_id=%s",(room_id,))
                        cur.execute("DELETE FROM deal_sale_assents WHERE contract_id IN (SELECT id FROM deal_sale_contracts WHERE room_id=%s)",(room_id,))
                        cur.execute("DELETE FROM deal_sale_contracts WHERE room_id=%s",(room_id,))
                        cur.execute("DELETE FROM deal_room_audit WHERE room_id=%s",(room_id,))
                        cur.execute("DELETE FROM deal_rooms WHERE id=%s",(room_id,))
                for aid in aids:
                    row=cur.execute("SELECT id FROM partner_applications WHERE id=%s AND organization LIKE %s",
                       (aid,"JBRO_EXECUTION_QA_"+nonce+"_%")).fetchone()
                    if row:
                        cur.execute("DELETE FROM partner_access WHERE application_id=%s",(aid,))
                        cur.execute("DELETE FROM activity_events WHERE entity_type='partner_application' AND entity_id=%s",(aid,))
                        cur.execute("DELETE FROM partner_applications WHERE id=%s",(aid,))
