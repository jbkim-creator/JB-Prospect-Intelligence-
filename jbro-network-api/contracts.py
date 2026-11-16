"""JBRO platform-native participation fee agreements (pilot).

Each approved partner signs their OWN separately frozen participation/reward
agreement with JBRO; no customer sale contract, legal e-signature service,
identity proofing or payouts are provided.
"""
import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request

bp=Blueprint("contracts",__name__)
DB=ADMIN=PARTNER=None
log=logging.getLogger(__name__)

def init(app, connection, admin_auth, partner_auth):
    global DB,ADMIN,PARTNER
    DB,ADMIN,PARTNER=connection,admin_auth,partner_auth
    app.register_blueprint(bp)

def ensure_schema():
    with DB() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS reward_contracts (
          id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
          deal_id BIGINT NOT NULL REFERENCES reward_deals(id),
          contributor_id BIGINT NOT NULL UNIQUE REFERENCES reward_contributors(id),
          version INTEGER NOT NULL DEFAULT 1,
          status VARCHAR(20) NOT NULL DEFAULT 'pending'
              CHECK (status IN ('pending','fully_signed')),
          agreement_text TEXT NOT NULL,
          agreement_sha256 CHAR(64) NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          completed_at TIMESTAMPTZ,
          CONSTRAINT reward_contract_document_size CHECK (length(agreement_text) BETWEEN 100 AND 16000)
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS reward_contract_assents (
          id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
          contract_id BIGINT NOT NULL REFERENCES reward_contracts(id),
          signer VARCHAR(16) NOT NULL CHECK (signer IN ('partner','jbro')),
          application_id BIGINT REFERENCES partner_applications(id),
          representative VARCHAR(120) NOT NULL,
          document_sha256 CHAR(64) NOT NULL,
          accepted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          ip_hmac CHAR(64),
          user_agent VARCHAR(240),
          UNIQUE(contract_id,signer),
          CONSTRAINT signer_ownership CHECK ((signer='partner' AND application_id IS NOT NULL)
                                         OR (signer='jbro' AND application_id IS NULL))
        )""")

def failure(code,status=400):return jsonify(error=code),status

def signature_audit():
    ip=(request.headers.get("X-Forwarded-For","").split(",")[0].strip() or request.remote_addr or "unknown")[:80]
    secret=os.getenv("JBRO_ADMIN_TOKEN","")
    fingerprint=hmac.new(secret.encode(),ip.encode(),hashlib.sha256).hexdigest() if secret else None
    return fingerprint,(request.headers.get("User-Agent") or "")[:240]

def frozen_terms(deal, contributor):
    # Each partner sees their own allocation, not other participants' private terms.
    now=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
      "type":"JBRO PARTICIPATION AND SUCCESS-FEE SHARING AGREEMENT (PILOT)",
      "version":1,"issued_utc":now,
      "parties":{"platform":"JBRO / Jbro Capital Ltd. (legal name and registration to be verified)",
                 "participant":contributor["organization"],
                 "application_id":contributor["application_id"]},
      "transaction":{"deal_reference":deal["id"],"title":deal["title"],
                     "reference_deal_value_krw":deal["deal_value_won"],
                     "jbro_fee_rate_bps":250,"jbro_fee_side":"JBRO's one agreed 2.5% fee stream only"},
      "reward":{"pool_percent_of_commission_received":deal["reward_share_pct"],
                "participant_pool_allocation_percent":contributor["allocation_pct"],
                "participant_role":contributor["role"],
                "participation_terms_reference":contributor["agreement_reference"]},
      "conditions":[
        "The participant supplies legitimate, accurate and authorized deal-sourcing, verification or execution services as described in its role.",
        "The participant reward arises only from the relevant JBRO commission ACTUALLY received from the agreed transaction; no completed trade or receipt means no cash reward.",
        "The aggregate partner reward pool is the agreed percentage of JBRO's actual net-of-VAT commission cash received in the specified 2.5% stream, subject to signed transaction terms and lawful tax/withholding treatment.",
        "The participant's allocation is a percentage of that pool, not a percentage of deal principal or the entire two-sided brokerage fees.",
        "No commissions are promised for trades completed independently before this agreement or without demonstrated and documented contribution. Duplicated referrals are reviewed and may be excluded with documented reasons.",
        "No participant may disclose other parties' identities, pricing, or restricted transaction information without written authorization. Nothing here guarantees access to confidential information.",
        "Reward payments require fee receipt confirmation, identity and sanctions screening as applicable, relevant invoice/tax documentation, and JBRO compliance and payout approval. The platform does NOT transfer funds.",
        "Any corrections, refund, dispute, chargeback, cancellation, or taxes are resolved through a separately documented adjustment and legally agreed process before payment.",
        "The XP/reputation program is informational only and is not money, equity, a transferable right or an automatic commission entitlement.",
        "This participation document is not a goods purchase contract, agency appointment, exclusivity agreement, securities offering, or proof of buyer/seller authority.",
        "Parties should verify legal entity details, governing law, jurisdiction, applicable intermediary regulation, tax requirements and signatory authority before relying on this document commercially.",
        "Each party agrees electronically to this exact immutable document, identified by SHA-256, through its authenticated portal session. Both assents are required to complete platform agreement."
      ]
    }

def documents_for_admin(conn, deal_id):
    docs=conn.execute("""SELECT r.id,r.deal_id,r.contributor_id,r.version,r.status,
            r.agreement_sha256,r.agreement_text,r.completed_at,a.organization,
            c.application_id,c.role,c.allocation_pct,
            EXISTS(SELECT 1 FROM reward_contract_assents s WHERE s.contract_id=r.id AND s.signer='partner') AS partner_signed,
            EXISTS(SELECT 1 FROM reward_contract_assents s WHERE s.contract_id=r.id AND s.signer='jbro') AS jbro_signed
          FROM reward_contracts r JOIN reward_contributors c ON c.id=r.contributor_id
          JOIN partner_applications a ON a.id=c.application_id
          WHERE r.deal_id=%s ORDER BY r.id""",(deal_id,)).fetchall()
    for d in docs:
        if d["completed_at"]:d["completed_at"]=d["completed_at"].isoformat()
    return docs

@bp.post("/api/admin/rewards/<int:deal_id>/contracts/issue")
def issue_contracts(deal_id):
    if not ADMIN():return failure("unauthorized",401)
    payload=request.get_json(silent=True) or {}
    if not isinstance(payload,dict) or payload.get("confirm_legal_terms_reviewed") is not True:
        return failure("legal_terms_review_confirmation_required")
    try:
        with DB() as conn:
            with conn.cursor() as cur:
                deal=cur.execute("""SELECT id,title,deal_value_won,reward_share_pct,status FROM reward_deals
                        WHERE id=%s FOR UPDATE""",(deal_id,)).fetchone()
                if not deal:return failure("not_found",404)
                if deal["status"]!="draft":return failure("deal_not_draft",409)
                if cur.execute("SELECT 1 FROM reward_contracts WHERE deal_id=%s LIMIT 1",(deal_id,)).fetchone():
                    return failure("contracts_already_issued",409)
                contributors=cur.execute("""SELECT c.id,c.application_id,c.role,c.allocation_pct,
                    c.agreement_reference,a.organization FROM reward_contributors c
                    JOIN partner_applications a ON a.id=c.application_id
                    WHERE c.deal_id=%s AND a.status='approved' ORDER BY c.id""",(deal_id,)).fetchall()
                if not contributors or sum(c["allocation_pct"] for c in contributors)!=100:
                    return failure("approved_allocations_must_total_100",409)
                for item in contributors:
                    frozen=json.dumps(frozen_terms(deal,item),ensure_ascii=False,sort_keys=True,separators=(",",":"))
                    digest=hashlib.sha256(frozen.encode()).hexdigest()
                    cur.execute("""INSERT INTO reward_contracts(deal_id,contributor_id,agreement_text,agreement_sha256)
                        VALUES (%s,%s,%s,%s)""",(deal_id,item["id"],frozen,digest))
                cur.execute("INSERT INTO reward_audit(deal_id,action) VALUES (%s,'platform_contracts_issued')",(deal_id,))
        return jsonify(status="pending",contracts_count=len(contributors)),201
    except Exception:
        log.exception("Contract issuance failed");return failure("temporarily_unavailable",503)

@bp.get("/api/admin/rewards/<int:deal_id>/contracts")
def list_admin_contracts(deal_id):
    if not ADMIN():return failure("unauthorized",401)
    try:
        with DB() as conn:return jsonify(contracts=documents_for_admin(conn,deal_id))
    except Exception:
        return failure("temporarily_unavailable",503)

@bp.get("/api/partner/contracts")
def my_contracts():
    try:
        aid=PARTNER()
        if aid is None:return failure("unauthorized",401)
        with DB() as conn:
            rows=conn.execute("""SELECT r.id,r.deal_id,r.version,r.status,r.agreement_text,r.agreement_sha256,
                d.title,
                EXISTS(SELECT 1 FROM reward_contract_assents s WHERE s.contract_id=r.id AND s.signer='partner') AS partner_signed,
                EXISTS(SELECT 1 FROM reward_contract_assents s WHERE s.contract_id=r.id AND s.signer='jbro') AS jbro_signed
                FROM reward_contracts r JOIN reward_contributors c ON c.id=r.contributor_id
                JOIN reward_deals d ON d.id=r.deal_id
                WHERE c.application_id=%s ORDER BY r.id DESC LIMIT 100""",(aid,)).fetchall()
        return jsonify(contracts=rows)
    except Exception:
        log.exception("Partner contract list failed");return failure("temporarily_unavailable",503)

@bp.post("/api/partner/contracts/<int:contract_id>/accept")
def accept_contract(contract_id):
    try:
        aid=PARTNER()
        if aid is None:return failure("unauthorized",401)
        body=request.get_json(silent=True)
        if not isinstance(body,dict):return failure("invalid_payload")
        representative=body.get("representative");hash_claim=body.get("document_sha256")
        if (not isinstance(representative,str) or not 2<=len(representative.strip())<=120
          or not isinstance(hash_claim,str) or len(hash_claim)!=64
          or body.get("confirm_authorized_signatory") is not True
          or body.get("confirm_read_and_accept") is not True):
            return failure("affirmative_consent_required")
        fingerprint,agent=signature_audit()
        with DB() as conn:
            with conn.cursor() as cur:
                r=cur.execute("""SELECT r.id,r.status,r.agreement_sha256 FROM reward_contracts r
                    JOIN reward_contributors c ON c.id=r.contributor_id
                    JOIN reward_deals d ON d.id=r.deal_id
                    WHERE r.id=%s AND c.application_id=%s AND d.status='draft'
                    FOR UPDATE OF r""",(contract_id,aid)).fetchone()
                if not r:return failure("not_found_or_locked",404)
                if r["agreement_sha256"]!=hash_claim:return failure("document_changed",409)
                if cur.execute("SELECT 1 FROM reward_contract_assents WHERE contract_id=%s AND signer='partner'",(contract_id,)).fetchone():
                    return failure("already_accepted",409)
                cur.execute("""INSERT INTO reward_contract_assents(contract_id,signer,application_id,
                    representative,document_sha256,ip_hmac,user_agent) VALUES(%s,'partner',%s,%s,%s,%s,%s)""",
                    (contract_id,aid,representative.strip(),hash_claim,fingerprint,agent))
                other=cur.execute("SELECT 1 FROM reward_contract_assents WHERE contract_id=%s AND signer='jbro'",(contract_id,)).fetchone()
                if other:cur.execute("UPDATE reward_contracts SET status='fully_signed',completed_at=now() WHERE id=%s",(contract_id,))
        return jsonify(status="fully_signed" if other else "pending",contract_id=contract_id),200
    except Exception:
        log.exception("Partner agreement acceptance failed");return failure("temporarily_unavailable",503)

@bp.post("/api/admin/contracts/<int:contract_id>/countersign")
def countersign(contract_id):
    if not ADMIN():return failure("unauthorized",401)
    body=request.get_json(silent=True)
    if not isinstance(body,dict):return failure("invalid_payload")
    rep=body.get("representative");digest=body.get("document_sha256")
    if (not isinstance(rep,str) or not 2<=len(rep.strip())<=120 or not isinstance(digest,str) or len(digest)!=64
        or body.get("confirm_company_authority") is not True or body.get("confirm_read_and_accept") is not True):
        return failure("affirmative_consent_required")
    fingerprint,agent=signature_audit()
    try:
        with DB() as conn:
            with conn.cursor() as cur:
                r=cur.execute("""SELECT r.id,r.agreement_sha256,r.deal_id FROM reward_contracts r
                    JOIN reward_deals d ON d.id=r.deal_id
                    WHERE r.id=%s AND d.status='draft' FOR UPDATE OF r""",(contract_id,)).fetchone()
                if not r:return failure("not_found_or_locked",404)
                if r["agreement_sha256"]!=digest:return failure("document_changed",409)
                if cur.execute("SELECT 1 FROM reward_contract_assents WHERE contract_id=%s AND signer='jbro'",(contract_id,)).fetchone():
                    return failure("already_accepted",409)
                cur.execute("""INSERT INTO reward_contract_assents(contract_id,signer,representative,
                    document_sha256,ip_hmac,user_agent) VALUES(%s,'jbro',%s,%s,%s,%s)""",
                    (contract_id,rep.strip(),digest,fingerprint,agent))
                partner=cur.execute("SELECT 1 FROM reward_contract_assents WHERE contract_id=%s AND signer='partner'",(contract_id,)).fetchone()
                if partner:cur.execute("UPDATE reward_contracts SET status='fully_signed',completed_at=now() WHERE id=%s",(contract_id,))
                cur.execute("INSERT INTO reward_audit(deal_id,action,reference) VALUES (%s,'platform_countersigned',%s)",(r["deal_id"],str(contract_id)))
        return jsonify(status="fully_signed" if partner else "pending",contract_id=contract_id),200
    except Exception:
        log.exception("JBRO countersign failed");return failure("temporarily_unavailable",503)

@bp.post("/api/admin/rewards/<int:deal_id>/contracts/finalize")
def finalize(deal_id):
    if not ADMIN():return failure("unauthorized",401)
    body=request.get_json(silent=True)
    if not isinstance(body,dict) or body.get("confirm_all_party_authority_checked") is not True:
        return failure("legal_verification_required")
    try:
        with DB() as conn:
            with conn.cursor() as cur:
                deal=cur.execute("SELECT id,status FROM reward_deals WHERE id=%s FOR UPDATE",(deal_id,)).fetchone()
                if not deal:return failure("not_found",404)
                if deal["status"]!="draft":return failure("already_signed",409)
                rows=cur.execute("""SELECT r.id,r.status,r.agreement_sha256,
                    (SELECT count(*) FROM reward_contract_assents s WHERE s.contract_id=r.id) AS signatures
                    FROM reward_contracts r WHERE r.deal_id=%s ORDER BY r.id""",(deal_id,)).fetchall()
                contribution_count=cur.execute("SELECT count(*) AS n,coalesce(sum(allocation_pct),0) AS total FROM reward_contributors WHERE deal_id=%s",(deal_id,)).fetchone()
                if not rows or len(rows)!=contribution_count["n"] or contribution_count["total"]!=100 or any(row["status"]!="fully_signed" or row["signatures"]!=2 for row in rows):
                    return failure("all_parties_must_sign",409)
                bundle_hash=hashlib.sha256("".join(r["agreement_sha256"] for r in rows).encode()).hexdigest()
                cur.execute("""UPDATE reward_deals SET status='signed', signed_reference=%s,signed_at=now() WHERE id=%s""",
                    ("PLATFORM-SHA256-"+bundle_hash[:40],deal_id))
                cur.execute("INSERT INTO reward_audit(deal_id,action,reference) VALUES (%s,'platform_agreements_finalized',%s)",(deal_id,bundle_hash[:40]))
        return jsonify(status="signed",contract_count=len(rows),bundle_sha256=bundle_hash),200
    except Exception:
        log.exception("Platform contract finalization failed");return failure("temporarily_unavailable",503)
