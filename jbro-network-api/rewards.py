"""JBRO Deal Rewards: non-custodial, administrator-only cash commission accounting.

No bank transfers. No automatic participant entitlement. This is a draft
accounting ledger for separately signed reward-sharing agreements.
All amounts are KRW integer won; no token or multi-currency conversion.
"""
import logging
from flask import Blueprint, request, jsonify

bp = Blueprint("rewards", __name__)
logger = logging.getLogger(__name__)
DB = ADMIN = PARTNER = None
MAX_WON = 10**15
ROLES = {"buyer_introduction", "supplier_introduction", "verification", "execution"}

def init(app, connection, admin_auth, partner_auth):
    global DB, ADMIN, PARTNER
    DB, ADMIN, PARTNER = connection, admin_auth, partner_auth
    app.register_blueprint(bp)

def ensure_schema():
    with DB() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS reward_deals (
          id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
          title VARCHAR(160) NOT NULL,
          deal_value_won BIGINT NOT NULL CHECK(deal_value_won>0),
          fee_bps SMALLINT NOT NULL DEFAULT 250 CHECK(fee_bps=250),
          reward_share_pct SMALLINT NOT NULL DEFAULT 30 CHECK(reward_share_pct BETWEEN 0 AND 40),
          status VARCHAR(16) NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','signed','closed')),
          signed_reference VARCHAR(160),
          signed_at TIMESTAMPTZ,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          CONSTRAINT signed_reference_required CHECK (status='draft' OR signed_reference IS NOT NULL)
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS reward_contributors (
          id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
          deal_id BIGINT NOT NULL REFERENCES reward_deals(id),
          application_id BIGINT NOT NULL REFERENCES partner_applications(id),
          role VARCHAR(40) NOT NULL CHECK(role IN ('buyer_introduction','supplier_introduction','verification','execution')),
          allocation_pct SMALLINT NOT NULL CHECK(allocation_pct BETWEEN 1 AND 100),
          agreement_reference VARCHAR(160) NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          UNIQUE(deal_id,application_id,role)
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS reward_receipts (
          id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
          deal_id BIGINT NOT NULL REFERENCES reward_deals(id),
          amount_won BIGINT NOT NULL CHECK(amount_won>0),
          bank_reference VARCHAR(160) NOT NULL,
          confirmed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          UNIQUE(deal_id,bank_reference)
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS reward_settlements (
          id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
          contributor_id BIGINT NOT NULL UNIQUE REFERENCES reward_contributors(id),
          approved_won BIGINT NOT NULL CHECK(approved_won>=0),
          status VARCHAR(20) NOT NULL DEFAULT 'approved' CHECK(status IN ('approved','paid')),
          payout_reference VARCHAR(160),
          approved_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          paid_at TIMESTAMPTZ,
          CONSTRAINT paid_requires_reference CHECK(status='approved' OR payout_reference IS NOT NULL)
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS reward_audit (
          id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
          deal_id BIGINT NOT NULL REFERENCES reward_deals(id),
          action VARCHAR(48) NOT NULL, reference VARCHAR(160),
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )""")

def err(msg, code=400):return jsonify(error=msg),code

def valid_won(v):
    return type(v) is int and 0<v<=MAX_WON

def details(conn, deal_id):
    deal=conn.execute("SELECT id,title,deal_value_won,fee_bps,reward_share_pct,status,signed_reference FROM reward_deals WHERE id=%s",(deal_id,)).fetchone()
    if not deal:return None
    contributors=conn.execute("""SELECT c.id,c.application_id,c.role,c.allocation_pct,c.agreement_reference,
      a.organization,s.approved_won,s.status AS settlement_status,s.payout_reference
      FROM reward_contributors c JOIN partner_applications a ON a.id=c.application_id
      LEFT JOIN reward_settlements s ON s.contributor_id=c.id
      WHERE c.deal_id=%s ORDER BY c.id""",(deal_id,)).fetchall()
    receipt=conn.execute("SELECT coalesce(sum(amount_won),0)::bigint AS received FROM reward_receipts WHERE deal_id=%s",(deal_id,)).fetchone()["received"]
    fee_ceiling=deal["deal_value_won"]*deal["fee_bps"]//10000
    pool=receipt*deal["reward_share_pct"]//100
    return dict(deal,contributors=contributors,commission_ceiling_won=fee_ceiling,commission_received_won=receipt,
                reward_pool_won=pool,jbro_retained_before_costs_won=receipt-pool,
                allocation_total_pct=sum(c["allocation_pct"] for c in contributors))

@bp.route("/api/admin/rewards",methods=["GET","POST"])
def admin_rewards():
    if not ADMIN():return err("unauthorized",401)
    if request.method=="GET":
        try:
            with DB() as conn:
                ids=conn.execute("SELECT id FROM reward_deals ORDER BY id DESC LIMIT 50").fetchall()
                return jsonify(deals=[details(conn,i["id"]) for i in ids])
        except Exception:
            logger.exception("reward list failed");return err("temporarily_unavailable",503)
    body=request.get_json(silent=True)
    if not isinstance(body,dict):return err("invalid_payload")
    title=body.get("title");value=body.get("deal_value_won");share=body.get("reward_share_pct",30)
    if not isinstance(title,str) or not 8<=len(title.strip())<=160 or not valid_won(value) or type(share)!=int or not 0<=share<=40:
        return err("invalid_fields")
    try:
        with DB() as conn:
            row=conn.execute("""INSERT INTO reward_deals(title,deal_value_won,reward_share_pct)
                        VALUES (%s,%s,%s) RETURNING id""",(title.strip(),value,share)).fetchone()
            conn.execute("INSERT INTO reward_audit(deal_id,action) VALUES (%s,'draft_created')",(row["id"],))
        return jsonify(deal_id=row["id"],status="draft"),201
    except Exception:
        logger.exception("reward create failed");return err("temporarily_unavailable",503)

@bp.post("/api/admin/rewards/<int:deal_id>/contributors")
def add_contributor(deal_id):
    if not ADMIN():return err("unauthorized",401)
    body=request.get_json(silent=True)
    if not isinstance(body,dict):return err("invalid_payload")
    aid=body.get("application_id");role=body.get("role");percent=body.get("allocation_pct");agreement=body.get("agreement_reference")
    if type(aid)!=int or aid<1 or role not in ROLES or type(percent)!=int or not 1<=percent<=100 or not isinstance(agreement,str) or not 4<=len(agreement.strip())<=160:
        return err("invalid_fields")
    try:
        with DB() as conn:
            with conn.cursor() as cur:
                deal=cur.execute("SELECT status FROM reward_deals WHERE id=%s FOR UPDATE",(deal_id,)).fetchone()
                if not deal:return err("not_found",404)
                if deal["status"]!="draft":return err("agreement_locked",409)
                verified=cur.execute("SELECT id FROM partner_applications WHERE id=%s AND status='approved'",(aid,)).fetchone()
                if not verified:return err("partner_not_approved",409)
                total=cur.execute("SELECT coalesce(sum(allocation_pct),0)::int AS total FROM reward_contributors WHERE deal_id=%s",(deal_id,)).fetchone()["total"]
                if total+percent>100:return err("allocation_exceeds_100",409)
                row=cur.execute("""INSERT INTO reward_contributors(deal_id,application_id,role,allocation_pct,agreement_reference)
                    VALUES(%s,%s,%s,%s,%s) ON CONFLICT (deal_id,application_id,role) DO NOTHING RETURNING id""",
                    (deal_id,aid,role,percent,agreement.strip())).fetchone()
                if not row:return err("duplicate_contribution",409)
                cur.execute("INSERT INTO reward_audit(deal_id,action,reference) VALUES (%s,'contributor_added',%s)",(deal_id,agreement.strip()))
        return jsonify(contributor_id=row["id"]),201
    except Exception:
        logger.exception("reward contributor failed");return err("temporarily_unavailable",503)

@bp.post("/api/admin/rewards/<int:deal_id>/sign")
def sign_deal(deal_id):
    if not ADMIN():return err("unauthorized",401)
    body=request.get_json(silent=True);ref=body.get("signed_reference") if isinstance(body,dict) else None
    if not isinstance(ref,str) or not 4<=len(ref.strip())<=160:return err("signed_document_reference_required")
    try:
        with DB() as conn:
            with conn.cursor() as cur:
                row=cur.execute("SELECT status FROM reward_deals WHERE id=%s FOR UPDATE",(deal_id,)).fetchone()
                if not row:return err("not_found",404)
                if row["status"]!="draft":return err("already_signed",409)
                total=cur.execute("SELECT coalesce(sum(allocation_pct),0)::int AS total FROM reward_contributors WHERE deal_id=%s",(deal_id,)).fetchone()["total"]
                if total!=100:return err("allocations_must_total_100",409)
                cur.execute("UPDATE reward_deals SET status='signed',signed_reference=%s,signed_at=now() WHERE id=%s",(ref.strip(),deal_id))
                cur.execute("INSERT INTO reward_audit(deal_id,action,reference) VALUES (%s,'agreement_marked_signed',%s)",(deal_id,ref.strip()))
        return jsonify(status="signed"),200
    except Exception:
        logger.exception("reward sign failed");return err("temporarily_unavailable",503)

@bp.post("/api/admin/rewards/<int:deal_id>/receipts")
def record_receipt(deal_id):
    if not ADMIN():return err("unauthorized",401)
    body=request.get_json(silent=True);amount=body.get("amount_won") if isinstance(body,dict) else None
    reference=body.get("bank_reference") if isinstance(body,dict) else None
    confirm=body.get("confirm_bank_received") if isinstance(body,dict) else None
    if not valid_won(amount) or not isinstance(reference,str) or not 4<=len(reference.strip())<=160 or confirm is not True:
        return err("verified_receipt_required")
    try:
        with DB() as conn:
            with conn.cursor() as cur:
                deal=cur.execute("SELECT deal_value_won,fee_bps,status FROM reward_deals WHERE id=%s FOR UPDATE",(deal_id,)).fetchone()
                if not deal:return err("not_found",404)
                if deal["status"]!="signed":return err("signed_agreement_required",409)
                if cur.execute("SELECT 1 FROM reward_settlements s JOIN reward_contributors c ON c.id=s.contributor_id WHERE c.deal_id=%s LIMIT 1",(deal_id,)).fetchone():return err("settlement_locked_after_approval",409)
                current=cur.execute("SELECT coalesce(sum(amount_won),0)::bigint AS total FROM reward_receipts WHERE deal_id=%s",(deal_id,)).fetchone()["total"]
                if current+amount>deal["deal_value_won"]*deal["fee_bps"]//10000:return err("fee_receipts_exceed_ceiling",409)
                row=cur.execute("""INSERT INTO reward_receipts(deal_id,amount_won,bank_reference)
                    VALUES (%s,%s,%s) ON CONFLICT(deal_id,bank_reference) DO NOTHING RETURNING id""",
                    (deal_id,amount,reference.strip())).fetchone()
                if not row:return err("duplicate_bank_reference",409)
                cur.execute("INSERT INTO reward_audit(deal_id,action,reference) VALUES(%s,'commission_received',%s)",(deal_id,reference.strip()))
        return jsonify(receipt_id=row["id"]),201
    except Exception:
        logger.exception("receipt record failed");return err("temporarily_unavailable",503)

@bp.post("/api/admin/rewards/<int:deal_id>/approve-settlements")
def approve_settlements(deal_id):
    if not ADMIN():return err("unauthorized",401)
    body=request.get_json(silent=True)
    if not isinstance(body,dict) or body.get("confirm_compliance_review") is not True:return err("compliance_review_required")
    try:
        with DB() as conn:
            with conn.cursor() as cur:
                deal=cur.execute("SELECT status FROM reward_deals WHERE id=%s FOR UPDATE",(deal_id,)).fetchone()
                if not deal:return err("not_found",404)
                if deal["status"]!="signed":return err("signed_agreement_required",409)
                if cur.execute("""SELECT 1 FROM reward_settlements s JOIN reward_contributors c ON c.id=s.contributor_id WHERE c.deal_id=%s LIMIT 1""",(deal_id,)).fetchone():
                    return err("settlement_already_approved",409)
                d=details(conn,deal_id)
                if d["commission_received_won"]<=0:return err("commission_not_received",409)
                if d["allocation_total_pct"]!=100:return err("allocations_must_total_100",409)
                for c in d["contributors"]:
                    amount=d["reward_pool_won"]*c["allocation_pct"]//100
                    cur.execute("INSERT INTO reward_settlements(contributor_id,approved_won) VALUES (%s,%s)",(c["id"],amount))
                cur.execute("INSERT INTO reward_audit(deal_id,action) VALUES (%s,'settlements_approved')",(deal_id,))
        return jsonify(status="approved",note="No money was transferred. Approved amounts are ledger entries only."),200
    except Exception:
        logger.exception("settlement approval failed");return err("temporarily_unavailable",503)

@bp.post("/api/admin/rewards/settlements/<int:settlement_id>/mark-paid")
def mark_paid(settlement_id):
    if not ADMIN():return err("unauthorized",401)
    body=request.get_json(silent=True)
    ref=body.get("payout_reference") if isinstance(body,dict) else None
    if not isinstance(ref,str) or not 4<=len(ref.strip())<=160 or not isinstance(body,dict) or body.get("confirm_bank_payment") is not True:
        return err("payment_evidence_required")
    try:
        with DB() as conn:
            with conn.cursor() as cur:
                row=cur.execute("""UPDATE reward_settlements SET status='paid',payout_reference=%s,paid_at=now()
                     WHERE id=%s AND status='approved' RETURNING contributor_id""",(ref.strip(),settlement_id)).fetchone()
                if not row:return err("not_found_or_already_paid",409)
                deal=cur.execute("SELECT deal_id FROM reward_contributors WHERE id=%s",(row["contributor_id"],)).fetchone()
                cur.execute("INSERT INTO reward_audit(deal_id,action,reference) VALUES(%s,'payment_marked',%s)",(deal["deal_id"],ref.strip()))
        return jsonify(status="paid",note="This records a reported external transfer; the system does not send money."),200
    except Exception:
        logger.exception("payment record failed");return err("temporarily_unavailable",503)

@bp.get("/api/partner/rewards")
def partner_rewards():
    try:
        aid=PARTNER()
        if aid is None:return err("unauthorized",401)
        with DB() as conn:
            rows=conn.execute("""SELECT d.id AS deal_id,d.title,d.status AS deal_status,c.role,
                  c.allocation_pct,s.approved_won,s.status AS settlement_status
                  FROM reward_contributors c JOIN reward_deals d ON d.id=c.deal_id
                  LEFT JOIN reward_settlements s ON s.contributor_id=c.id
                  WHERE c.application_id=%s AND d.status IN ('signed','closed')
                  ORDER BY d.created_at DESC LIMIT 100""",(aid,)).fetchall()
        return jsonify(rewards=rows,note="Only signed agreements appear. XP is not money; no automatic payment."),200
    except Exception:
        logger.exception("partner reward lookup failed");return err("temporarily_unavailable",503)
