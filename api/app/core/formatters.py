def format_currency_eu(val: float) -> str:
    """Formats value as 5.000,84 (European format)"""
    if val is None:
        return "N/A"
    return f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def format_change_eu(chg: float) -> str:
    """Formats change percentage as +1,23 or -1,23"""
    if chg is None:
        return "N/A"
    sign = "+" if chg > 0 else ""
    return f"{sign}{chg:.2f}".replace(".", ",")
