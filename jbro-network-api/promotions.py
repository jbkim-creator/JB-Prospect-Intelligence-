"""JBRO FIRST10M fee coupon: waive the 2.5% fee on first KRW 10m of a first eligible deal.

A coupon belongs to ONE approved fee-paying counterparty (buyer OR seller) and
ONE linked draft Deal Room + Reward Deal; unique per application. No retroactivity.
No effect on third-party contracts or fees on the other side of a deal.
"""
import logging
import json
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


def smoke_test(app,admin_token,origin):
    """Neon test: first KRW 10m fee waiver, partial waiver, partner isolation, fee cap."""
    import secrets
    nonce=secrets.token_hex(7)
    client=app.test_client()
    admin={"Authorization":"Bearer "+admin_token}
    aids=[];keys=[];deals=[];rooms=[]
    try:
        for i in range(3):
            r=client.post("/api/partner-applications",headers={"Origin":origin},json={
                "organization":"JBRO_COUPON_QA_"+nonce+"_"+str(i),
                "email":"coupon-"+nonce+"-"+str(i)+"@example.invalid",
                "country":"Test","role":"Buyer" if i<2 else "Supplier",
                "summary":"Only a synthetic FIRST10M coupon test entity.","consent":True})
            assert r.status_code==201,("intake",r.status_code)
            aid=int(r.get_json()["reference"].split("-")[-1]);aids.append(aid)
            assert client.patch("/api/admin/applications/"+str(aid),headers=admin,json={"status":"approved"}).status_code==200
            invite=client.post("/api/admin/applications/"+str(aid)+"/issue-access",headers=admin)
            assert invite.status_code==200
            keys.append(invite.get_json()["access_token"])
        assert client.get("/api/public/first-trade-coupon").get_json()["max_discount_won"]==250000
        for i,value in enumerate((20_000_000,5_000_000)):
            reward=client.post("/api/admin/rewards",headers=admin,json={
                "title":"Synthetic FIRST10M fee waiver "+nonce+" "+str(i),
                "deal_value_won":value,"reward_share_pct":30})
            assert reward.status_code==201,("reward create",reward.status_code)
            deal_id=reward.get_json()["deal_id"];deals.append(deal_id)
            terms={
             "buyer_legal_name":"Synthetic Coupon Buyer Company",
             "seller_legal_name":"Synthetic Verified Seller Company",
             "item_description":"Fictional industrial processing module sample, not real inventory or a real order.",
             "quantity_unit":"10 pieces","total_contract_value_won":value,
             "delivery_terms":"Synthetic warehouse in South Korea, no actual shipment.",
             "inspection_terms":"Simulation-only inspection conditions without physical goods.",
             "payment_terms":"Test-only bank terms with no real funds exchanged.",
             "governing_law":"Republic of Korea",
             "dispute_resolution":"Synthetic test dispute procedure, not real legal advice.",
             "additional_terms":"Synthetic QA contract, not intended to bind anyone."
            }
            room=client.post("/api/admin/deal-rooms",headers=admin,json={
                "title":"Synthetic FIRST10M dealroom "+nonce+" "+str(i),
                "buyer_application_id":aids[i],"seller_application_id":aids[2],
                "reward_deal_id":deal_id,"terms":terms})
            assert room.status_code==201,("room create",room.status_code)
            rooms.append(room.get_json()["room_id"])
            issued=client.post("/api/admin/rewards/"+str(deal_id)+"/first-trade-coupon",
                headers=admin,json={"application_id":aids[i],"confirm_eligibility_and_fee_terms":True})
            assert issued.status_code==201,("coupon issue",issued.status_code)
            expected=250000 if i==0 else 125000
            assert issued.get_json()["discount_won"]==expected
            assert issued.get_json()["fee_after_discount_won"]==(250000 if i==0 else 0)
            dup=client.post("/api/admin/rewards/"+str(deal_id)+"/first-trade-coupon",headers=admin,
                json={"application_id":aids[i],"confirm_eligibility_and_fee_terms":True})
            assert dup.status_code==409,"duplicate coupon"
            exposed=client.get("/api/partner/first-trade-coupon",headers={"Authorization":"Bearer "+keys[i]})
            assert exposed.status_code==200 and exposed.get_json()["coupon"]["discount_won"]==expected
            other=client.get("/api/partner/first-trade-coupon",headers={"Authorization":"Bearer "+keys[1-i]})
            if i==0:assert other.status_code==200 and other.get_json()["coupon"] is None
        listed=client.get("/api/admin/rewards",headers=admin)
        assert listed.status_code==200
        byid={d["id"]:d for d in listed.get_json()["deals"]}
        assert byid[deals[0]]["commission_ceiling_won"]==250000
        assert byid[deals[0]]["gross_commission_won"]==500000
        assert byid[deals[0]]["coupon_discount_won"]==250000
        assert byid[deals[1]]["commission_ceiling_won"]==0
        # Attach participating parties and fully countersign both the sale and reward documents
        deal_id=deals[0];room_id=rooms[0]
        for i in (0,2):
            contribution=client.post("/api/admin/rewards/"+str(deal_id)+"/contributors",headers=admin,json={
                "application_id":aids[i],"role":"buyer_introduction" if i==0 else "supplier_introduction",
                "allocation_pct":50,"agreement_reference":"QA-PROMO-AGREEMENT-"+nonce+"-"+str(i)})
            assert contribution.status_code==201,("add party",contribution.status_code)
        issue=client.post("/api/admin/rewards/"+str(deal_id)+"/contracts/issue",headers=admin,
            json={"confirm_legal_terms_reviewed":True})
        assert issue.status_code==201,("issue reward terms",issue.status_code)
        docs=client.get("/api/admin/rewards/"+str(deal_id)+"/contracts",headers=admin).get_json()["contracts"]
        assert len(docs)==2
        for doc in docs:
            parsed=json.loads(doc["agreement_text"])
            assert parsed["transaction"]["first_trade_discount_won"]==250000
            assert parsed["transaction"]["max_collectible_fee_won"]==250000
            i=aids.index(doc["application_id"])
            signed=client.post("/api/partner/contracts/"+str(doc["id"])+"/accept",
                headers={"Authorization":"Bearer "+keys[i]},json={
                "representative":"Synthetic Signer","document_sha256":doc["agreement_sha256"],
                "confirm_authorized_signatory":True,"confirm_read_and_accept":True})
            assert signed.status_code==200,("partner reward sign",signed.status_code)
            countersign=client.post("/api/admin/contracts/"+str(doc["id"])+"/countersign",
                headers=admin,json={"representative":"Synthetic JBRO signer",
                "document_sha256":doc["agreement_sha256"],
                "confirm_company_authority":True,"confirm_read_and_accept":True})
            assert countersign.status_code==200,("countersign",countersign.status_code)
        assert client.post("/api/admin/deal-rooms/"+str(room_id)+"/issue",headers=admin,
            json={"confirm_sale_terms_legal_review":True}).status_code==200
        sale_doc=client.get("/api/admin/deal-rooms/"+str(room_id)+"/status",headers=admin).get_json()["room"]["contract"]
        for i in (0,2):
            sale=client.post("/api/partner/deal-rooms/"+str(room_id)+"/accept",
                headers={"Authorization":"Bearer "+keys[i]},json={
                "representative":"Synthetic company officer",
                "document_sha256":sale_doc["document_sha256"],
                "confirm_authorized_signatory":True,"confirm_read_and_accept":True})
            assert sale.status_code==200,("sale assent",sale.status_code)
        final=client.post("/api/admin/rewards/"+str(deal_id)+"/contracts/finalize",
            headers=admin,json={"confirm_all_party_authority_checked":True})
        assert final.status_code==200,("reward finalize",final.status_code)
        exceeded=client.post("/api/admin/rewards/"+str(deal_id)+"/receipts",
            headers=admin,json={"amount_won":250001,
              "bank_reference":"QA-OVER-"+nonce,"confirm_bank_received":True})
        assert exceeded.status_code==409,"fee cap ignored"
        receipt=client.post("/api/admin/rewards/"+str(deal_id)+"/receipts",
            headers=admin,json={"amount_won":250000,
              "bank_reference":"QA-VALID-"+nonce,"confirm_bank_received":True})
        assert receipt.status_code==201,("net fee receipt",receipt.status_code)
        detail=client.get("/api/admin/rewards",headers=admin).get_json()["deals"]
        item=next(x for x in detail if x["id"]==deal_id)
        assert (item["commission_received_won"],item["reward_pool_won"],
                item["jbro_retained_before_costs_won"])==(250000,75000,175000)
        assert client.get("/api/admin/rewards").status_code==401
        log.info("JBRO_FIRST10M_SMOKE_PASS")
    finally:
        with DB() as conn:
            with conn.cursor() as cur:
                for room_id in rooms:
                    room=cur.execute("SELECT id FROM deal_rooms WHERE id=%s AND title LIKE %s",
                        (room_id,"Synthetic FIRST10M dealroom "+nonce+" %")).fetchone()
                    if room:
                        cur.execute("DELETE FROM promo_fee_coupons WHERE deal_room_id=%s",(room_id,))
                        cur.execute("DELETE FROM deal_execution_events WHERE room_id=%s",(room_id,))
                        cur.execute("DELETE FROM deal_sale_assents WHERE contract_id IN (SELECT id FROM deal_sale_contracts WHERE room_id=%s)",(room_id,))
                        cur.execute("DELETE FROM deal_sale_contracts WHERE room_id=%s",(room_id,))
                        cur.execute("DELETE FROM deal_room_audit WHERE room_id=%s",(room_id,))
                        cur.execute("DELETE FROM deal_rooms WHERE id=%s",(room_id,))
                for deal_id in deals:
                    row=cur.execute("SELECT id FROM reward_deals WHERE id=%s AND title LIKE %s",
                        (deal_id,"Synthetic FIRST10M fee waiver "+nonce+" %")).fetchone()
                    if row:
                        cur.execute("DELETE FROM reward_contract_assents WHERE contract_id IN (SELECT id FROM reward_contracts WHERE deal_id=%s)",(deal_id,))
                        cur.execute("DELETE FROM reward_contracts WHERE deal_id=%s",(deal_id,))
                        cur.execute("DELETE FROM reward_settlements WHERE contributor_id IN (SELECT id FROM reward_contributors WHERE deal_id=%s)",(deal_id,))
                        cur.execute("DELETE FROM reward_receipts WHERE deal_id=%s",(deal_id,))
                        cur.execute("DELETE FROM reward_contributors WHERE deal_id=%s",(deal_id,))
                        cur.execute("DELETE FROM reward_audit WHERE deal_id=%s",(deal_id,))
                        cur.execute("DELETE FROM reward_deals WHERE id=%s",(deal_id,))
                for aid in aids:
                    row=cur.execute("SELECT id FROM partner_applications WHERE id=%s AND organization LIKE %s",
                        (aid,"JBRO_COUPON_QA_"+nonce+"_%")).fetchone()
                    if row:
                        cur.execute("DELETE FROM partner_access WHERE application_id=%s",(aid,))
                        cur.execute("DELETE FROM activity_events WHERE entity_type='partner_application' AND entity_id=%s",(aid,))
                        cur.execute("DELETE FROM partner_applications WHERE id=%s",(aid,))
