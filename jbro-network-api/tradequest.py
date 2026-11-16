"""JBRO TradeQuest — private, evidence-reviewed mission board, not a financial game."""
import logging
from flask import Blueprint, request, jsonify

bp = Blueprint("tradequest", __name__)
log = logging.getLogger(__name__)
DB = None
ADMIN = None
PARTNER = None
CATEGORIES = {"semiconductor", "industrial", "logistics", "other"}

def init(app, connection, authorized_admin, authorized_partner_id):
    global DB, ADMIN, PARTNER
    DB, ADMIN, PARTNER = connection, authorized_admin, authorized_partner_id
    app.register_blueprint(bp)

def ensure_schema():
    with DB() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS tradequest_missions (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            title VARCHAR(140) NOT NULL, description VARCHAR(900) NOT NULL,
            category VARCHAR(32) NOT NULL CHECK(category IN ('semiconductor','industrial','logistics','other')),
            reward_xp SMALLINT NOT NULL CHECK(reward_xp BETWEEN 10 AND 200),
            state VARCHAR(16) NOT NULL DEFAULT 'draft' CHECK(state IN ('draft','open','closed')),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(), closes_at TIMESTAMPTZ)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS tradequest_claims (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            mission_id BIGINT NOT NULL REFERENCES tradequest_missions(id),
            application_id BIGINT NOT NULL REFERENCES partner_applications(id),
            contribution VARCHAR(900) NOT NULL,
            state VARCHAR(16) NOT NULL DEFAULT 'pending' CHECK(state IN ('pending','verified','rejected')),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(), reviewed_at TIMESTAMPTZ,
            UNIQUE(mission_id,application_id))""")
        conn.execute("""CREATE TABLE IF NOT EXISTS tradequest_xp_ledger (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            application_id BIGINT NOT NULL REFERENCES partner_applications(id),
            claim_id BIGINT NOT NULL UNIQUE REFERENCES tradequest_claims(id),
            xp SMALLINT NOT NULL CHECK(xp BETWEEN 10 AND 200),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now())""")
        conn.execute("CREATE INDEX IF NOT EXISTS tradequest_claims_partner_idx ON tradequest_claims(application_id,created_at DESC)")

@bp.get("/api/partner/tradequest")
def partner_board():
    try:
        aid=PARTNER()
        if aid is None:
            return jsonify(error="unauthorized"),401
        with DB() as conn:
            missions=conn.execute("""SELECT m.id,m.title,m.description,m.category,m.reward_xp,m.closes_at,
                c.state AS my_claim_state FROM tradequest_missions m
                LEFT JOIN tradequest_claims c ON c.mission_id=m.id AND c.application_id=%s
                WHERE m.state='open' AND (m.closes_at IS NULL OR m.closes_at>now())
                ORDER BY m.created_at DESC LIMIT 50""",(aid,)).fetchall()
            score=conn.execute("SELECT coalesce(sum(xp),0)::int AS xp FROM tradequest_xp_ledger WHERE application_id=%s",(aid,)).fetchone()["xp"]
        for m in missions:
            if m["closes_at"]:m["closes_at"]=m["closes_at"].isoformat()
        return jsonify(missions=missions,xp=score)
    except Exception:
        log.exception("Partner mission board failed")
        return jsonify(error="temporarily_unavailable"),503

@bp.post("/api/partner/tradequest/<int:mission_id>/claim")
def claim_mission(mission_id):
    try:
        aid=PARTNER()
        if aid is None:return jsonify(error="unauthorized"),401
        payload=request.get_json(silent=True)
        if not isinstance(payload,dict):return jsonify(error="json_required"),400
        contribution=payload.get("contribution")
        if not isinstance(contribution,str) or not 30<=len(contribution.strip())<=900 or payload.get("nonconfidential") is not True:
            return jsonify(error="invalid_fields"),400
        with DB() as conn:
            with conn.cursor() as cur:
                row=cur.execute("""SELECT id FROM tradequest_missions
                    WHERE id=%s AND state='open' AND (closes_at IS NULL OR closes_at>now())""",(mission_id,)).fetchone()
                if row is None:return jsonify(error="mission_not_open"),404
                # One claim per mission per partner, including rejected claims.
                created=cur.execute("""INSERT INTO tradequest_claims(mission_id,application_id,contribution)
                    VALUES (%s,%s,%s) ON CONFLICT (mission_id,application_id) DO NOTHING RETURNING id""",
                    (mission_id,aid,contribution.strip())).fetchone()
                if not created:return jsonify(error="already_claimed"),409
        return jsonify(status="pending_review",claim_id=created["id"]),201
    except Exception:
        log.exception("Mission claim failed")
        return jsonify(error="temporarily_unavailable"),503

@bp.route("/api/admin/tradequest/missions",methods=["GET","POST"])
def admin_missions():
    if not ADMIN():return jsonify(error="unauthorized"),401
    try:
        if request.method=="GET":
            with DB() as conn:
                missions=conn.execute("""SELECT id,title,description,category,reward_xp,state,created_at
                    FROM tradequest_missions ORDER BY created_at DESC LIMIT 100""").fetchall()
            for m in missions:m["created_at"]=m["created_at"].isoformat()
            return jsonify(missions=missions)
        payload=request.get_json(silent=True)
        if not isinstance(payload,dict):return jsonify(error="json_required"),400
        title=payload.get("title");description=payload.get("description")
        category=payload.get("category");xp=payload.get("reward_xp")
        if not isinstance(title,str) or not 8<=len(title.strip())<=140 or not isinstance(description,str) or not 30<=len(description.strip())<=900 or category not in CATEGORIES or type(xp)!=int or not 10<=xp<=200:
            return jsonify(error="invalid_fields"),400
        # Draft by default: explicit separate publishing action.
        with DB() as conn:
            m=conn.execute("""INSERT INTO tradequest_missions(title,description,category,reward_xp)
                 VALUES (%s,%s,%s,%s) RETURNING id""",(title.strip(),description.strip(),category,xp)).fetchone()
        return jsonify(mission_id=m["id"],state="draft"),201
    except Exception:
        log.exception("Admin missions failed")
        return jsonify(error="temporarily_unavailable"),503

@bp.patch("/api/admin/tradequest/missions/<int:mission_id>")
def admin_publish(mission_id):
    if not ADMIN():return jsonify(error="unauthorized"),401
    data=request.get_json(silent=True)
    state=data.get("state") if isinstance(data,dict) else None
    if state not in ("draft","open","closed"):return jsonify(error="invalid_state"),400
    try:
        with DB() as conn:
            row=conn.execute("UPDATE tradequest_missions SET state=%s WHERE id=%s RETURNING id",(state,mission_id)).fetchone()
        if not row:return jsonify(error="not_found"),404
        return jsonify(mission_id=mission_id,state=state)
    except Exception:
        log.exception("Mission publish failed")
        return jsonify(error="temporarily_unavailable"),503

@bp.get("/api/admin/tradequest/claims")
def admin_claims():
    if not ADMIN():return jsonify(error="unauthorized"),401
    try:
        with DB() as conn:
            rows=conn.execute("""SELECT c.id,c.state,c.contribution,c.created_at,m.title,m.reward_xp,
                a.organization,a.id AS application_id FROM tradequest_claims c
                JOIN tradequest_missions m ON m.id=c.mission_id
                JOIN partner_applications a ON a.id=c.application_id
                ORDER BY c.created_at DESC LIMIT 100""").fetchall()
        for r in rows:r["created_at"]=r["created_at"].isoformat()
        return jsonify(claims=rows)
    except Exception:
        return jsonify(error="temporarily_unavailable"),503

@bp.patch("/api/admin/tradequest/claims/<int:claim_id>")
def admin_verify_claim(claim_id):
    if not ADMIN():return jsonify(error="unauthorized"),401
    data=request.get_json(silent=True)
    state=data.get("state") if isinstance(data,dict) else None
    if state not in ("verified","rejected"):return jsonify(error="invalid_state"),400
    try:
        with DB() as conn:
            with conn.cursor() as cur:
                row=cur.execute("""SELECT c.id,c.state,c.application_id,m.reward_xp
                    FROM tradequest_claims c JOIN tradequest_missions m ON m.id=c.mission_id
                    WHERE c.id=%s FOR UPDATE OF c""",(claim_id,)).fetchone()
                if not row:return jsonify(error="not_found"),404
                if row["state"]!="pending":return jsonify(error="already_reviewed"),409
                cur.execute("UPDATE tradequest_claims SET state=%s, reviewed_at=now() WHERE id=%s",(state,claim_id))
                if state=="verified":
                    cur.execute("""INSERT INTO tradequest_xp_ledger(application_id,claim_id,xp)
                        VALUES (%s,%s,%s) ON CONFLICT (claim_id) DO NOTHING""",
                        (row["application_id"],claim_id,row["reward_xp"]))
        return jsonify(claim_id=claim_id,state=state,credited_xp=row["reward_xp"] if state=="verified" else 0)
    except Exception:
        log.exception("Mission verification failed")
        return jsonify(error="temporarily_unavailable"),503
