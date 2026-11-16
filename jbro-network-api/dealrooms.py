"""JBRO Deal Rooms: private buyer/seller order terms and authenticated assent MVP.

This is NOT verified qualified e-signature, escrow, payment processing, or proof
of buyer/seller representative authority. KRW-only pilot, manual administrator review.
"""
import hashlib
import hmac
import json
import logging
import os
from flask import Blueprint, jsonify, request

bp=Blueprint("dealrooms", __name__)
DB=ADMIN=PARTNER=None
log=logging.getLogger(__name__)
MAX_WON=10**15
FIELDS={
 "buyer_legal_name":(3,160),"seller_legal_name":(3,160),
 "item_description":(10,1400),"quantity_unit":(2,100),
 "delivery_terms":(8,500),"inspection_terms":(8,500),
 "payment_terms":(8,500),"governing_law":(3,180),
 "dispute_resolution":(8,500),"additional_terms":(0,1400),
}
def init(app, connection, admin_auth, partner_auth):
    global DB,ADMIN,PARTNER
    DB,ADMIN,PARTNER=connection,admin_auth,partner_auth
    app.register_blueprint(bp)

def ensure_schema():
    with DB() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS deal_rooms (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            buyer_application_id BIGINT NOT NULL REFERENCES partner_applications(id),
            seller_application_id BIGINT NOT NULL REFERENCES partner_applications(id),
            reward_deal_id BIGINT UNIQUE REFERENCES reward_deals(id),
            title VARCHAR(160) NOT NULL,
            status VARCHAR(16) NOT NULL DEFAULT 'draft'
                CHECK(status IN ('draft','issued','signed','cancelled')),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT distinct_trade_parties CHECK(buyer_application_id<>seller_application_id)
        )""")
        conn.execute("ALTER TABLE deal_rooms ADD COLUMN IF NOT EXISTS currency VARCHAR(3) NOT NULL DEFAULT 'KRW' CHECK(currency IN ('KRW','USD'))")
        conn.execute("""CREATE TABLE IF NOT EXISTS deal_sale_contracts (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            room_id BIGINT NOT NULL REFERENCES deal_rooms(id),
            version INTEGER NOT NULL DEFAULT 1,
            terms_json TEXT NOT NULL,
            document_sha256 CHAR(64) NOT NULL,
            status VARCHAR(16) NOT NULL DEFAULT 'draft'
                CHECK(status IN ('draft','issued','signed','cancelled')),
            issued_at TIMESTAMPTZ,completed_at TIMESTAMPTZ,
            UNIQUE(room_id,version),
            CONSTRAINT terms_size CHECK(length(terms_json) BETWEEN 150 AND 10000)
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS deal_sale_assents (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            contract_id BIGINT NOT NULL REFERENCES deal_sale_contracts(id),
            signer_role VARCHAR(8) NOT NULL CHECK(signer_role IN ('buyer','seller')),
            application_id BIGINT NOT NULL REFERENCES partner_applications(id),
            representative VARCHAR(120) NOT NULL,
            document_sha256 CHAR(64) NOT NULL,
            accepted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            ip_hmac CHAR(64),user_agent VARCHAR(240),
            UNIQUE(contract_id,signer_role)
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS deal_room_audit(
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            room_id BIGINT NOT NULL REFERENCES deal_rooms(id),
            event VARCHAR(48) NOT NULL, reference VARCHAR(160),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS deal_rooms_buyer_idx ON deal_rooms(buyer_application_id,id DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS deal_rooms_seller_idx ON deal_rooms(seller_application_id,id DESC)")

def error(msg,status=400):return jsonify(error=msg),status
def canonical(terms):return json.dumps(terms,sort_keys=True,ensure_ascii=False,separators=(",",":"))
def digest(content):return hashlib.sha256(content.encode()).hexdigest()
def audit_request():
    ip=(request.headers.get("X-Forwarded-For","").split(",")[0].strip() or request.remote_addr or "unknown")[:80]
    secret=os.getenv("JBRO_ADMIN_TOKEN","")
    fingerprint=hmac.new(secret.encode(),ip.encode(),hashlib.sha256).hexdigest() if secret else None
    return fingerprint,(request.headers.get("User-Agent") or "")[:240]
def check_terms(obj):
    if not isinstance(obj,dict):return None
    clean={}
    for key,(minimum,maximum) in FIELDS.items():
        v=obj.get(key,"")
        if not isinstance(v,str) or not minimum<=len(v.strip())<=maximum:return None
        clean[key]=v.strip()
    currency=obj.get("currency","KRW")
    if currency not in ("KRW","USD"):return None
    price=obj.get("total_contract_value_minor") if currency=="USD" else obj.get("total_contract_value_won")
    if type(price) is not int or not 0<price<=MAX_WON:return None
    clean["currency"]=currency
    clean["total_contract_value_minor"]=price
    if currency=="KRW":clean["total_contract_value_won"]=price
    # Party IDs and roles are fixed by the administrator, never provided by a partner.
    return clean

def current_contract(conn,room_id):
    return conn.execute("""SELECT id,room_id,version,terms_json,document_sha256,status,
              issued_at,completed_at FROM deal_sale_contracts
              WHERE room_id=%s ORDER BY version DESC LIMIT 1""",(room_id,)).fetchone()

def enriched(conn,room,partner_id=None):
    c=current_contract(conn,room["id"])
    result={"id":room["id"],"title":room["title"],"status":room["status"],
            "reward_deal_id":room["reward_deal_id"],"currency":room["currency"],
            "buyer_application_id":room["buyer_application_id"],
            "seller_application_id":room["seller_application_id"]}
    if partner_id is not None:
        result.pop("buyer_application_id");result.pop("seller_application_id")
        result["my_role"]="buyer" if room["buyer_application_id"]==partner_id else "seller"
        result["reward_deal_id"]=None  # Never disclose internal broker fee references to transaction counterparties.
    if c:
        assents=conn.execute("""SELECT signer_role,representative,accepted_at FROM deal_sale_assents
                    WHERE contract_id=%s ORDER BY signer_role""",(c["id"],)).fetchall()
        result["contract"]={"id":c["id"],"version":c["version"],"terms_json":c["terms_json"],
              "document_sha256":c["document_sha256"],"status":c["status"],
              "signatures":[{"role":x["signer_role"],"signed_at":x["accepted_at"].isoformat()}
                    for x in assents]}
    return result

@bp.route("/api/admin/deal-rooms",methods=["GET","POST"])
def admin_rooms():
    if not ADMIN():return error("unauthorized",401)
    try:
        if request.method=="GET":
            with DB() as conn:
                rows=conn.execute("SELECT * FROM deal_rooms ORDER BY id DESC LIMIT 50").fetchall()
                return jsonify(rooms=[enriched(conn,x) for x in rows])
        body=request.get_json(silent=True)
        if not isinstance(body,dict):return error("invalid_payload")
        buyer=body.get("buyer_application_id");seller=body.get("seller_application_id")
        title=body.get("title");reward_id=body.get("reward_deal_id")
        terms=check_terms(body.get("terms"))
        if (type(buyer) is not int or type(seller) is not int or buyer<1 or seller<1 or buyer==seller
            or not isinstance(title,str) or not 8<=len(title.strip())<=160 or not terms
            or (reward_id is not None and (type(reward_id) is not int or reward_id<1))):
            return error("invalid_fields")
        with DB() as conn:
            with conn.cursor() as cur:
                partners=cur.execute("SELECT id FROM partner_applications WHERE id IN (%s,%s) AND status='approved'",(buyer,seller)).fetchall()
                if len(partners)!=2:return error("both_counterparties_must_be_approved",409)
                if reward_id is not None:
                    reward=cur.execute("SELECT deal_value_won,currency,status FROM reward_deals WHERE id=%s FOR UPDATE",(reward_id,)).fetchone()
                    if not reward or reward["status"]!='draft':return error("reward_deal_not_draft",409)
                    if reward["currency"]!=terms["currency"] or reward["deal_value_won"]!=terms["total_contract_value_minor"]:
                        return error("reward_deal_value_mismatch",409)
                cur.execute("""INSERT INTO deal_rooms(buyer_application_id,seller_application_id,reward_deal_id,title,currency)
                      VALUES(%s,%s,%s,%s,%s) RETURNING id""",(buyer,seller,reward_id,title.strip(),terms["currency"]))
                room_id=cur.fetchone()["id"]
                content=canonical({"document_type":"B2B SALE AND PURCHASE TERMS — PILOT",
                     "version":1,"deal_room_id":room_id,"buyer_application_id":buyer,
                     "seller_application_id":seller,"terms":terms,
                     "notices":[
                       "This document is a bilateral buyer/seller sale agreement, not a JBRO commission agreement.",
                       "The signers declare authority to bind their respective companies; platform access alone is not verified identity or qualified electronic signature.",
                       "No funds, goods, title, inspection results or escrow services are transferred by this platform.",
                       "Any taxes, export controls, sanctions, Incoterms, governing law and dispute terms require independent legal and commercial review."
                     ]})
                cur.execute("""INSERT INTO deal_sale_contracts(room_id,version,terms_json,document_sha256)
                        VALUES(%s,1,%s,%s)""",(room_id,content,digest(content)))
                cur.execute("INSERT INTO deal_room_audit(room_id,event) VALUES(%s,'draft_created')",(room_id,))
        return jsonify(room_id=room_id,status="draft"),201
    except Exception:
        log.exception("Admin deal rooms failed");return error("temporarily_unavailable",503)

@bp.post("/api/admin/deal-rooms/<int:room_id>/issue")
def issue_room(room_id):
    if not ADMIN():return error("unauthorized",401)
    body=request.get_json(silent=True)
    if not isinstance(body,dict) or body.get("confirm_sale_terms_legal_review") is not True:
        return error("legal_review_confirmation_required")
    try:
        with DB() as conn:
            with conn.cursor() as cur:
                room=cur.execute("SELECT id,status FROM deal_rooms WHERE id=%s FOR UPDATE",(room_id,)).fetchone()
                if not room:return error("not_found",404)
                if room["status"]!="draft":return error("not_draft",409)
                cur.execute("UPDATE deal_rooms SET status='issued' WHERE id=%s",(room_id,))
                cur.execute("UPDATE deal_sale_contracts SET status='issued',issued_at=now() WHERE room_id=%s AND status='draft'",(room_id,))
                cur.execute("INSERT INTO deal_room_audit(room_id,event) VALUES(%s,'issued_for_signing')",(room_id,))
        return jsonify(status="issued"),200
    except Exception:
        log.exception("Deal room issuance failed");return error("temporarily_unavailable",503)

@bp.get("/api/partner/deal-rooms")
def partner_rooms():
    try:
        aid=PARTNER()
        if aid is None:return error("unauthorized",401)
        with DB() as conn:
            rows=conn.execute("""SELECT * FROM deal_rooms
                  WHERE (buyer_application_id=%s OR seller_application_id=%s)
                    AND status IN ('issued','signed','cancelled')
                  ORDER BY id DESC LIMIT 50""",(aid,aid)).fetchall()
            return jsonify(rooms=[enriched(conn,r,aid) for r in rows])
    except Exception:
        log.exception("Partner deal rooms failed");return error("temporarily_unavailable",503)

@bp.post("/api/partner/deal-rooms/<int:room_id>/accept")
def partner_accept_sale(room_id):
    try:
        aid=PARTNER()
        if aid is None:return error("unauthorized",401)
        body=request.get_json(silent=True)
        if not isinstance(body,dict):return error("invalid_payload")
        name=body.get("representative");hash_claim=body.get("document_sha256")
        if (not isinstance(name,str) or not 2<=len(name.strip())<=120
            or not isinstance(hash_claim,str) or len(hash_claim)!=64
            or body.get("confirm_authorized_signatory") is not True
            or body.get("confirm_read_and_accept") is not True):
            return error("affirmative_consent_required")
        fingerprint,ua=audit_request()
        with DB() as conn:
            with conn.cursor() as cur:
                room=cur.execute("""SELECT * FROM deal_rooms WHERE id=%s AND status='issued'
                    AND (buyer_application_id=%s OR seller_application_id=%s) FOR UPDATE""",
                    (room_id,aid,aid)).fetchone()
                if not room:return error("not_found_or_locked",404)
                role="buyer" if room["buyer_application_id"]==aid else "seller"
                contract=current_contract(conn,room_id)
                if not contract or contract["status"]!='issued':return error("contract_not_issued",409)
                if not hmac.compare_digest(contract["document_sha256"],hash_claim):
                    return error("document_changed",409)
                if cur.execute("SELECT 1 FROM deal_sale_assents WHERE contract_id=%s AND signer_role=%s",
                        (contract["id"],role)).fetchone():
                    return error("already_accepted",409)
                cur.execute("""INSERT INTO deal_sale_assents(contract_id,signer_role,application_id,representative,
                    document_sha256,ip_hmac,user_agent) VALUES(%s,%s,%s,%s,%s,%s,%s)""",
                    (contract["id"],role,aid,name.strip(),hash_claim,fingerprint,ua))
                other="seller" if role=="buyer" else "buyer"
                other_sig=cur.execute("""SELECT 1 FROM deal_sale_assents WHERE contract_id=%s AND signer_role=%s""",
                    (contract["id"],other)).fetchone()
                if other_sig:
                    cur.execute("UPDATE deal_rooms SET status='signed' WHERE id=%s",(room_id,))
                    cur.execute("UPDATE deal_sale_contracts SET status='signed',completed_at=now() WHERE id=%s",(contract["id"],))
                    cur.execute("INSERT INTO deal_room_audit(room_id,event,reference) VALUES(%s,'sale_accepted_by_both',%s)",
                        (room_id,contract["document_sha256"]))
                else:
                    cur.execute("INSERT INTO deal_room_audit(room_id,event,reference) VALUES(%s,'sale_acceptance',%s)",(room_id,role))
        return jsonify(status="signed" if other_sig else "issued",accepted_as=role),200
    except Exception:
        log.exception("Deal room acceptance failed");return error("temporarily_unavailable",503)

@bp.get("/api/admin/deal-rooms/<int:room_id>/status")
def room_status(room_id):
    if not ADMIN():return error("unauthorized",401)
    try:
        with DB() as conn:
            room=conn.execute("SELECT * FROM deal_rooms WHERE id=%s",(room_id,)).fetchone()
            if not room:return error("not_found",404)
            data=enriched(conn,room)
            if room["reward_deal_id"]:
                reward=conn.execute("SELECT status,signed_reference FROM reward_deals WHERE id=%s",
                    (room["reward_deal_id"],)).fetchone()
                data["reward_status"]=dict(reward) if reward else None
            return jsonify(room=data)
    except Exception:
        return error("temporarily_unavailable",503)


def smoke_test(app, admin_secret, origin):
    """Real Neon smoke test with three synthetic parties. All test rows removed."""
    import secrets
    nonce=secrets.token_hex(7)
    client=app.test_client()
    auth={"Authorization":"Bearer "+admin_secret}
    aids=[];tokens=[];room_id=None;reward_id=None
    try:
        for idx in range(3):
            registration=client.post("/api/partner-applications",json={
                "organization":"JBRO_SALE_QA_"+nonce+"_"+str(idx),
                "email":"sale-"+nonce+"-"+str(idx)+"@example.invalid",
                "country":"Test","role":"Buyer" if idx==0 else "Supplier",
                "summary":"Synthetic QA entity, not a genuine counterparty.",
                "consent":True
            },headers={"Origin":origin})
            assert registration.status_code==201,("register",registration.status_code)
            aid=int(registration.get_json()["reference"].split("-")[-1]);aids.append(aid)
            approved=client.patch("/api/admin/applications/"+str(aid),headers=auth,json={"status":"approved"})
            assert approved.status_code==200,("approved",approved.status_code)
            invite=client.post("/api/admin/applications/"+str(aid)+"/issue-access",headers=auth)
            assert invite.status_code==200,("token issue",invite.status_code)
            tokens.append(invite.get_json()["access_token"])
        reward=client.post("/api/admin/rewards",headers=auth,json={
            "title":"QA buyer seller reward deal "+nonce,"deal_value_won":100000000,"reward_share_pct":30})
        assert reward.status_code==201,("reward draft",reward.status_code)
        reward_id=reward.get_json()["deal_id"]
        for idx in range(2):
            rr=client.post("/api/admin/rewards/"+str(reward_id)+"/contributors",headers=auth,json={
                "application_id":aids[idx],"role":"buyer_introduction" if idx==0 else "supplier_introduction",
                "allocation_pct":50,"agreement_reference":"QA-CONT-"+nonce+"-"+str(idx)})
            assert rr.status_code==201,("reward contributor",rr.status_code)
        terms={
          "buyer_legal_name":"Synthetic Buyer Corporation",
          "seller_legal_name":"Synthetic Seller Corporation",
          "item_description":"Synthetic test-only industrial computing boards; this is not a real sale.",
          "quantity_unit":"100 pieces",
          "total_contract_value_won":100000000,
          "delivery_terms":"DAP test warehouse in Republic of Korea, no real shipment.",
          "inspection_terms":"Test specification and inspection only; no real inspection.",
          "payment_terms":"Test-only payment description; no actual funds are exchanged.",
          "governing_law":"Republic of Korea",
          "dispute_resolution":"Synthetic arbitration clause for QA only, no real agreement.",
          "additional_terms":"Nonbinding controlled test, not a genuine order."
        }
        created=client.post("/api/admin/deal-rooms",headers=auth,json={
            "title":"QA synthetic sale room "+nonce,
            "buyer_application_id":aids[0],"seller_application_id":aids[1],
            "reward_deal_id":reward_id,"terms":terms})
        assert created.status_code==201,("sale create",created.status_code)
        room_id=created.get_json()["room_id"]
        linked=client.get("/api/admin/deal-rooms/"+str(room_id)+"/status",headers=auth)
        assert linked.status_code==200 and linked.get_json()["room"]["reward_deal_id"]==reward_id
        issued=client.post("/api/admin/rewards/"+str(reward_id)+"/contracts/issue",headers=auth,
                           json={"confirm_legal_terms_reviewed":True})
        assert issued.status_code==201,("fee docs issued",issued.status_code)
        rdocs=client.get("/api/admin/rewards/"+str(reward_id)+"/contracts",headers=auth).get_json()["contracts"]
        assert len(rdocs)==2
        for i,doc in enumerate(rdocs):
            who=next(j for j,aid in enumerate(aids[:2]) if aid==doc["application_id"])
            sign=client.post("/api/partner/contracts/"+str(doc["id"])+"/accept",
                 headers={"Authorization":"Bearer "+tokens[who]},
                 json={"representative":"Synthetic Director","document_sha256":doc["agreement_sha256"],
                       "confirm_authorized_signatory":True,"confirm_read_and_accept":True})
            assert sign.status_code==200,("reward partner assent",sign.status_code)
            sign=client.post("/api/admin/contracts/"+str(doc["id"])+"/countersign",headers=auth,
                 json={"representative":"Synthetic JBRO Signer","document_sha256":doc["agreement_sha256"],
                       "confirm_company_authority":True,"confirm_read_and_accept":True})
            assert sign.status_code==200,("reward countersign",sign.status_code)
        premature=client.post("/api/admin/rewards/"+str(reward_id)+"/contracts/finalize",headers=auth,
             json={"confirm_all_party_authority_checked":True})
        assert premature.status_code==409,("reward deal finalized before sale",premature.status_code)
        draft_hidden=client.get("/api/partner/deal-rooms",headers={"Authorization":"Bearer "+tokens[0]})
        assert draft_hidden.status_code==200 and not draft_hidden.get_json()["rooms"]
        issue=client.post("/api/admin/deal-rooms/"+str(room_id)+"/issue",headers=auth,
             json={"confirm_sale_terms_legal_review":True})
        assert issue.status_code==200,("sale issue",issue.status_code)
        unauthorized=client.get("/api/partner/deal-rooms")
        assert unauthorized.status_code==401
        other=client.get("/api/partner/deal-rooms",headers={"Authorization":"Bearer "+tokens[2]})
        assert other.status_code==200 and not other.get_json()["rooms"],"cross-partner visibility"
        first=client.get("/api/partner/deal-rooms",headers={"Authorization":"Bearer "+tokens[0]})
        assert first.status_code==200 and len(first.get_json()["rooms"])==1
        doc=first.get_json()["rooms"][0]["contract"]
        assert hashlib.sha256(doc["terms_json"].encode()).hexdigest()==doc["document_sha256"]
        third_sig=client.post("/api/partner/deal-rooms/"+str(room_id)+"/accept",
              headers={"Authorization":"Bearer "+tokens[2]},
              json={"representative":"Unauthorized third","document_sha256":doc["document_sha256"],
                    "confirm_authorized_signatory":True,"confirm_read_and_accept":True})
        assert third_sig.status_code==404,"unauthorized third party accepted"
        changed=client.post("/api/partner/deal-rooms/"+str(room_id)+"/accept",
              headers={"Authorization":"Bearer "+tokens[0]},
              json={"representative":"Buyer Director","document_sha256":"0"*64,
                    "confirm_authorized_signatory":True,"confirm_read_and_accept":True})
        assert changed.status_code==409,"changed hash accepted"
        for idx in range(2):
            sign=client.post("/api/partner/deal-rooms/"+str(room_id)+"/accept",
                  headers={"Authorization":"Bearer "+tokens[idx]},
                  json={"representative":"Synthetic Authorized Signer",
                        "document_sha256":doc["document_sha256"],
                        "confirm_authorized_signatory":True,"confirm_read_and_accept":True})
            assert sign.status_code==200,("sale assent",sign.status_code)
        assert sign.get_json()["status"]=="signed","both party signatures incomplete"
        repeated=client.post("/api/partner/deal-rooms/"+str(room_id)+"/accept",
                  headers={"Authorization":"Bearer "+tokens[0]},
                  json={"representative":"Duplicate Buyer","document_sha256":doc["document_sha256"],
                  "confirm_authorized_signatory":True,"confirm_read_and_accept":True})
        assert repeated.status_code==404,"accepted after signed"
        finalized=client.post("/api/admin/rewards/"+str(reward_id)+"/contracts/finalize",headers=auth,
                       json={"confirm_all_party_authority_checked":True})
        assert finalized.status_code==200,("linked fee finalize",finalized.status_code)
        assert client.post("/api/admin/rewards/"+str(reward_id)+"/approve-settlements",headers=auth,
                 json={"confirm_compliance_review":True}).status_code==409,"approved without fee receipt"
        log.info("JBRO_DEALROOM_SMOKE_PASS")
    finally:
        with DB() as conn:
            with conn.cursor() as cur:
                if room_id is not None:
                    rr=cur.execute("SELECT id FROM deal_rooms WHERE id=%s AND title=%s",
                              (room_id,"QA synthetic sale room "+nonce)).fetchone()
                    if rr:
                        cur.execute("DELETE FROM deal_sale_assents WHERE contract_id IN (SELECT id FROM deal_sale_contracts WHERE room_id=%s)",(room_id,))
                        cur.execute("DELETE FROM deal_sale_contracts WHERE room_id=%s",(room_id,))
                        cur.execute("DELETE FROM deal_room_audit WHERE room_id=%s",(room_id,))
                        cur.execute("DELETE FROM deal_rooms WHERE id=%s",(room_id,))
                if reward_id is not None:
                    rr=cur.execute("SELECT id FROM reward_deals WHERE id=%s AND title=%s",
                        (reward_id,"QA buyer seller reward deal "+nonce)).fetchone()
                    if rr:
                        cur.execute("DELETE FROM reward_contract_assents WHERE contract_id IN (SELECT id FROM reward_contracts WHERE deal_id=%s)",(reward_id,))
                        cur.execute("DELETE FROM reward_contracts WHERE deal_id=%s",(reward_id,))
                        cur.execute("DELETE FROM reward_audit WHERE deal_id=%s",(reward_id,))
                        cur.execute("DELETE FROM reward_settlements WHERE contributor_id IN (SELECT id FROM reward_contributors WHERE deal_id=%s)",(reward_id,))
                        cur.execute("DELETE FROM reward_receipts WHERE deal_id=%s",(reward_id,))
                        cur.execute("DELETE FROM reward_contributors WHERE deal_id=%s",(reward_id,))
                        cur.execute("DELETE FROM reward_deals WHERE id=%s",(reward_id,))
                for aid in aids:
                    rr=cur.execute("SELECT id FROM partner_applications WHERE id=%s AND organization LIKE %s",
                              (aid,"JBRO_SALE_QA_"+nonce+"_%")).fetchone()
                    if rr:
                        cur.execute("DELETE FROM partner_access WHERE application_id=%s",(aid,))
                        cur.execute("DELETE FROM activity_events WHERE entity_type='partner_application' AND entity_id=%s",(aid,))
                        cur.execute("DELETE FROM partner_applications WHERE id=%s",(aid,))
