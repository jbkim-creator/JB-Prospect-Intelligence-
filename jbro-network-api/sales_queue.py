"""Private sales queue; read-only recommendations, never sends messages."""
from datetime import datetime, timezone, date
from zoneinfo import ZoneInfo
from flask import jsonify

STAGE_WEIGHT={"order_pending":35,"fee_agreed":32,"negotiation":28,"quote_received":25,"qualified":12,"intake":5}
OPEN_STAGES=set(STAGE_WEIGHT)

def prioritize(case,stats,today):
    stage=case["stage"]
    if stage not in OPEN_STAGES:
        return None
    due=case.get("due_date")
    days=(due-today).days if due else None
    weight=STAGE_WEIGHT[stage]
    reasons=["stage:"+stage]
    if days is not None:
        if days<0:
            weight+=40
            reasons.append("overdue")
        elif days==0:
            weight+=30
            reasons.append("due_today")
        elif days<=2:
            weight+=18
            reasons.append("due_within_two_days")
    if case["sector"]=="semiconductor":
        weight+=15
        reasons.append("semiconductor_focus")
    if stats.get("exact_pairs",0):
        weight+=8
        reasons.append("exact_mpn_candidates")
    if case["fee_state"] in ("unconfirmed","proposed") and stage in ("negotiation","fee_agreed","order_pending"):
        weight+=7
        reasons.append("fee_protection_pending")
    return dict(deal_key=case["deal_key"],title=case["title"],sector=case["sector"],
                stage=stage,due_date=due.isoformat() if due else None,days_to_due=days,
                score=weight,priority="urgent" if days is not None and days<=0 else
                ("high" if weight>=55 else "normal"),reasons=reasons,
                fee_state=case["fee_state"],blocker=case["blocker"],next_action=case["next_action"],
                source_ref=case["source_ref"],revision=case["revision"],matching=stats,
                decision="review_required",dispatch_permitted=False)

def matching_stats(lines):
    """Count potential exact pairs, not verified matches; do not infer availability."""
    from collections import defaultdict
    from matching import classify
    grouped=defaultdict(list)
    for l in lines: grouped[l["mpn"]].append(l)
    out=defaultdict(lambda:dict(exact_pairs=0,review_required=0,expired=0,commercial_candidate=0))
    today=datetime.now(timezone.utc).date()
    for group in grouped.values():
        buys=[l for l in group if l["side"]=="buy"]
        sells=[l for l in group if l["side"]=="sell"]
        for b in buys:
            for s in sells:
                m=classify(b,s,today)
                if m is None: continue
                for key in {b["case_key"],s["case_key"]}:
                    out[key]["exact_pairs"]+=1
                    out[key][m["status"]]+=1
    return out

def init(app,connection,authorized_admin):
    @app.get("/api/admin/sales-queue")
    def sales_queue():
        if not authorized_admin():
            return jsonify(error="unauthorized"),401
        try:
            with connection() as conn:
                cases=conn.execute("""
                SELECT deal_key,title,sector,stage,due_date,fee_state,blocker,next_action,source_ref,revision
                FROM closing_desk_cases WHERE stage NOT IN ('lost','on_hold','handoff')
                ORDER BY due_date ASC NULLS LAST, id LIMIT 501
                """).fetchall()
                lines=conn.execute("""
                SELECT l.* FROM trade_match_lines l JOIN closing_desk_cases c ON c.deal_key=l.case_key
                WHERE l.active AND c.stage NOT IN ('lost','on_hold','handoff')
                ORDER BY l.id DESC LIMIT 501
                """).fetchall()
            stats=matching_stats(lines[:500])
            today=datetime.now(ZoneInfo("Asia/Seoul")).date()
            zero=dict(exact_pairs=0,review_required=0,expired=0,commercial_candidate=0)
            items=[x for c in cases[:500] if (x:=prioritize(c,stats.get(c["deal_key"],zero),today)) is not None]
            items.sort(key=lambda x:(0 if x["priority"]=="urgent" else 1,-x["score"],x["due_date"] or "9999-12-31",x["deal_key"]))
            return jsonify(items=items[:200],summary=dict(in_scope=len(items),shown=min(200,len(items)),
                urgent=sum(x["priority"]=="urgent" for x in items),high=sum(x["priority"]=="high" for x in items),
                semiconductor=sum(x["sector"]=="semiconductor" for x in items)),
                case_limit=500,line_limit=500,case_scope_truncated=len(cases)>500,line_scope_truncated=len(lines)>500,
                as_of=today.isoformat(),timezone="Asia/Seoul",
                definition="Rule-based private recommendations. Source references and recent sent/draft mail must be checked before outreach. No dispatch or automatic stage change.")
        except Exception:
            app.logger.warning("Sales queue read failed")
            return jsonify(error="temporarily_unavailable"),503
