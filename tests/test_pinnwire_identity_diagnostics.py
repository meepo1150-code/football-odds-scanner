from odds_scanner.pinnwire_identity_diagnostics import norm
def test_norm_is_exact_casefold_only():
    assert norm(" Team FC ")=="team fc"
    assert norm("Inter Milano")!="inter milan"
