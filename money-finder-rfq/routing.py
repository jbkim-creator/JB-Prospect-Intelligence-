def classify(*, private_verified=False, dnc_checked=False, protected=False, expired=False, stock_verified=False, fee_confirmed=False, partner_approved=False, consent_confirmed=False):
    if protected or expired:
        return "excluded"
    if not (private_verified and dnc_checked and fee_confirmed):
        return "review"
    if stock_verified:
        return "direct"
    if partner_approved and consent_confirmed:
        return "co_broker"
    return "review"

if __name__ == "__main__":
    assert classify() == "review"
    assert classify(protected=True) == "excluded"
    assert classify(expired=True) == "excluded"
    base = dict(private_verified=True,dnc_checked=True,fee_confirmed=True)
    assert classify(**base,stock_verified=True) == "direct"
    assert classify(**base,partner_approved=True) == "review"
    assert classify(**base,partner_approved=True,consent_confirmed=True) == "co_broker"
    print("Six routing assertions passed")
