"""JBRO FIRST10M fee coupon: waive the 2.5% fee on first KRW 10m of a first eligible deal.

A coupon belongs to ONE approved fee-paying counterparty (buyer OR seller) and
ONE linked draft Deal Room + Reward Deal; unique per application. No retroactivity.
No effect on third-party contracts or fees on the other side of a deal.
"""
import logging
from flask import Blueprint, request, jsonify

bp=Blueprint("promotions",__name__)
DB=ADMIN=PARTNER=None
log=logging.getLogger(__name__)
CODE="FIRST10M"
CAP_VALUE_WON=10_000_000
FEE_BPS=250
MAX_DISCOUNT_WON=CAP_VALUE_WON*FEE_BPS//10000

def init(app,connection,admin_auth,partner_auth):
    global DB,ADMIN,PARTNER
    DB,ADMIN,PARTNER=connection,admin_auth,partner_auth
    app.register_blueprint(bp)

def ensure_schema():
    with DB() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS promo_fee_coupons (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            application_id BIGINT NOT NULL UNIQUE REFERENCES partner_applications(id),
            reward_deal_id BIGINT NOT NULL UNIQUE REFERENCES reward_deals(id),
            deal_room_id BIGINT NOT NULL UNIQUE REFERENCES deal_rooms(id),
            campaign VARCHAR(20) NOT NULL DEFAULT 'FIRST10M' CHECK(campaign='FIRST10M'),
            discount_won BIGINT NOT NULL CHECK(discount_won BETWEEN 1 AND 250000),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT coupon_discount_valid CHECK(discount_won>0)
        )""")

def discount(value):
    return min(value,CAP_VALUE_WON)*FEE_BPS//10000

def net_fee(value,discount_won):
    return max(0,value*FEE_BPS//10000-discount_won)

@bp.get("/api/public/first-trade-coupon")
def public_coupon():
    return jsonify(code=CODE,first_deal_value_waived_won=CAP_VALUE_WON,
        jbro_fee_bps=FEE_BPS,max_discount_won=MAX_DISCOUNT_WON,
        note="Pilot offer subject to eligibility and written JBRO approval. Only the agreed 2.5% JBRO fee stream for one first eligible buyer or seller transaction. No other-side fee relief. Not retroactive or stackable."),200

@bp.post("/api/admin/rewards/<int:deal_id>/first-trade-coupon")
def assign_coupon(deal_id):
    if not ADMIN():return jsonify(error="unauthorized"),401
    data=request.get_json(silent=True)
    aid=data.get("application_id") if isinstance(data,dict) else None
    if type(aid) is not int or aid<1 or data.get("confirm_eligibility_and_fee_terms") is not True:
        return jsonify(error="eligibility_confirmation_required"),400
    try:
        with DB() as conn:
            with conn.cursor() as cur:
                # Serialization lock covers concurrent coupon issuance for each partner.
                applicant=cur.execute("SELECT id,status FROM partner_applications WHERE id=%s FOR UPDATE",(aid,)).fetchone()
                if not applicant or applicant["status"]!="approved":
                    return jsonify(error="approved_partner_required"),409
                deal=cur.execute("""SELECT id,status,deal_value_won,fee_bps FROM reward_deals WHERE id=%s FOR UPDATE""",
                    (deal_id,)).fetchone()
                if not deal or deal["status"]!="draft":
                    return jsonify(error="draft_reward_deal_required"),409
                room=cur.execute("""SELECT id,status,buyer_application_id,seller_application_id
                    FROM deal_rooms WHERE reward_deal_id=%s FOR UPDATE""",(deal_id,)).fetchone()
                if not room or room["status"]!="draft":
                    return jsonify(error="linked_draft_sale_room_required"),409
                if aid not in (room["buyer_application_id"],room["seller_application_id"]):
                    return jsonify(error="coupon_holder_must_be_counterparty"),409
                if cur.execute("SELECT 1 FROM reward_contracts WHERE deal_id=%s LIMIT 1",(deal_id,)).fetchone():
                    return jsonify(error="reward_terms_already_issued"),409
                if cur.execute("SELECT 1 FROM promo_fee_coupons WHERE application_id=%s OR reward_deal_id=%s",(aid,deal_id)).fetchone():
                    return jsonify(error="coupon_already_claimed"),409
                if cur.execute("""SELECT 1 FROM deal_rooms WHERE (buyer_application_id=%s OR seller_application_id=%s)
                      AND status='signed' LIMIT 1""",(aid,aid)).fetchone():
                    return jsonify(error="existing_signed_trade_ineligible"),409
                # Do not allow attaching a coupon when either counterparty has already signed fee terms.
                if cur.execute("SELECT 1 FROM reward_receipts WHERE deal_id=%s LIMIT 1",(deal_id,)).fetchone():
                    return jsonify(error="fee_receipt_already_recorded"),409
                amount=discount(deal["deal_value_won"])
                if amount<1:return jsonify(error="invalid_discount"),400
                row=cur.execute("""INSERT INTO promo_fee_coupons
                    (application_id,reward_deal_id,deal_room_id,discount_won)
                    VALUES (%s,%s,%s,%s) RETURNING id""",
                    (aid,deal_id,room["id"],amount)).fetchone()
                cur.execute("""INSERT INTO reward_audit(deal_id,action,reference)
                    VALUES(%s,'first_trade_coupon_issued',%s)""",(deal_id,CODE+":"+str(aid)))
        return jsonify(coupon_id=row["id"],campaign=CODE,
           discount_won=amount,fee_after_discount_won=net_fee(deal["deal_value_won"],amount)),201
    except Exception:
        log.exception("First-trade coupon issue failed")
        return jsonify(error="temporarily_unavailable"),503

@bp.get("/api/partner/first-trade-coupon")
def partner_coupon():
    try:
        aid=PARTNER()
        if aid is None:return jsonify(error="unauthorized"),401
        with DB() as conn:
            row=conn.execute("""SELECT p.campaign,p.discount_won,p.deal_room_id,
              r.status AS reward_deal_status FROM promo_fee_coupons p
              JOIN reward_deals r ON r.id=p.reward_deal_id
              WHERE p.application_id=%s""",(aid,)).fetchone()
        return jsonify(coupon=row,offer=CODE,max_discount_won=MAX_DISCOUNT_WON,
            note="Subject to eligibility approval; no coupon is active until JBRO attaches it to an eligible draft Deal Room."),200
    except Exception:
        return jsonify(error="temporarily_unavailable"),503
