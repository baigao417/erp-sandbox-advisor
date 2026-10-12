"""Pure calculations; no file writes, network calls, or embedded event rules."""

from decimal import Decimal, InvalidOperation


def amount(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        raise ValueError(f"{label} must be a finite number")
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"{label} must be a finite number") from exc
    if not result.is_finite():
        raise ValueError(f"{label} must be a finite number")
    return result


def nonnegative(value, label):
    result = amount(value, label)
    if result < 0:
        raise ValueError(f"{label} must be nonnegative")
    return result


def count(value, label):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be a nonnegative integer")
    return value


def names(value, label):
    if not isinstance(value, list) or any(not isinstance(v, str) or not v.strip() for v in value):
        raise ValueError(f"{label} must be a list of nonempty strings")
    return set(value)


def fields(value, required, label):
    if not isinstance(value, dict) or set(value) != set(required.split()):
        raise ValueError(f"{label} requires exactly: {required}")


def cash_projection(opening, events):
    """Respect caller-provided chronological order, including intra-quarter events."""
    balance = nonnegative(opening, "opening_cash")
    minimum = balance
    rows = []
    if not isinstance(events, list):
        raise ValueError("cash_events must be a list")
    for event in events:
        fields(event, "label inflow outflow", "cash event")
        if not isinstance(event["label"], str) or not event["label"].strip():
            raise ValueError("cash event label must be nonempty")
        balance += nonnegative(event["inflow"], "inflow") - nonnegative(event["outflow"], "outflow")
        minimum = min(minimum, balance)
        rows.append({"label": event["label"], "closing_cash": str(balance), "shortfall": balance < 0})
    return {"events": rows, "closing_cash": str(balance), "minimum_cash": str(minimum),
            "funding_gap": str(max(Decimal(0), -minimum)), "safe": minimum >= 0}


def ranking_score(equity, advertising, equity_weight, advertising_weight):
    ew = nonnegative(equity_weight, "equity_weight")
    aw = nonnegative(advertising_weight, "advertising_weight")
    if ew + aw != 1:
        raise ValueError("ranking weights must sum to one")
    return nonnegative(equity, "equity") * ew + nonnegative(advertising, "advertising") * aw


def inventory_cost(inventory, rules):
    fields(rules, "per_product_limit total_limit penalty_per_unit overlap annual_bands", "inventory rules")
    if not isinstance(inventory, dict) or any(not isinstance(k, str) or not k.strip() for k in inventory):
        raise ValueError("inventory must map product names to quantities")
    quantities = [count(v, "inventory quantity") for v in inventory.values()]
    per_limit = count(rules["per_product_limit"], "per_product_limit")
    total_limit = count(rules["total_limit"], "total_limit")
    per_excess = sum(max(0, n - per_limit) for n in quantities)
    total = sum(quantities)
    total_excess = max(0, total - total_limit)
    if rules["overlap"] == "max":
        charged = max(per_excess, total_excess)
    elif rules["overlap"] == "add":
        charged = per_excess + total_excess
    else:
        raise ValueError("overlap must be max or add")
    rate = nonnegative(rules["penalty_per_unit"], "penalty_per_unit")
    bands = rules["annual_bands"]
    if not isinstance(bands, list):
        raise ValueError("annual_bands must be a list")
    previous = -1
    annual_fee = Decimal(0)
    for band in bands:
        fields(band, "above fee", "annual band")
        threshold = count(band["above"], "above")
        fee = nonnegative(band["fee"], "fee")
        if threshold <= previous:
            raise ValueError("annual band thresholds must strictly increase")
        previous = threshold
        if total > threshold:
            annual_fee = fee
    return {"total_units": total, "per_product_excess": per_excess,
            "total_excess": total_excess, "charged_units": charged,
            "period_penalty": str(rate * charged), "annual_fee": str(annual_fee)}


def evaluate_order(order, company):
    fields(order, "id market product quantity unit_price unit_cost allocated_cost required_certifications delivery_period ready_period available_units", "order")
    for key in ("id", "market", "product"):
        if not isinstance(order[key], str) or not order[key].strip():
            raise ValueError(f"order {key} must be nonempty")
    quantity = count(order["quantity"], "quantity")
    if quantity == 0:
        raise ValueError("order quantity must be positive")
    available = count(order["available_units"], "available_units")
    delivery = count(order["delivery_period"], "delivery_period")
    ready = count(order["ready_period"], "ready_period")
    revenue = quantity * nonnegative(order["unit_price"], "unit_price")
    contribution = revenue - quantity * nonnegative(order["unit_cost"], "unit_cost") - nonnegative(order["allocated_cost"], "allocated_cost")
    blockers = []
    if order["market"] not in names(company["markets"], "markets"):
        blockers.append("market_not_qualified")
    if order["product"] not in names(company["products"], "products"):
        blockers.append("product_not_qualified")
    if not names(order["required_certifications"], "required_certifications") <= names(company["certifications"], "certifications"):
        blockers.append("certification_missing")
    if ready > delivery:
        blockers.append("delivery_too_late")
    if available < quantity:
        blockers.append("insufficient_units")
    return {"id": order["id"], "revenue": str(revenue), "contribution": str(contribution),
            "eligible": not blockers, "profitable": contribution > 0, "blockers": blockers}


def analyze(data):
    fields(data, "schema_version company cash_events inventory orders ranking inventory_rules", "input")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise ValueError("schema_version must be 1")
    company = data["company"]
    fields(company, "opening_cash equity markets products certifications", "company")
    for key in ("markets", "products", "certifications"):
        names(company[key], key)
    ranking = data["ranking"]
    fields(ranking, "advertising equity_weight advertising_weight", "ranking")
    if not isinstance(data["orders"], list):
        raise ValueError("orders must be a list")
    orders = [evaluate_order(order, company) for order in data["orders"]]
    if len({order["id"] for order in orders}) != len(orders):
        raise ValueError("order ids must be unique")
    orders.sort(key=lambda order: (not order["eligible"], -Decimal(order["contribution"]), order["id"]))
    return {
        "schema_version": 1,
        "cash": cash_projection(company["opening_cash"], data["cash_events"]),
        "ranking_score": str(ranking_score(company["equity"], ranking["advertising"], ranking["equity_weight"], ranking["advertising_weight"])),
        "inventory": inventory_cost(data["inventory"], data["inventory_rules"]),
        "orders": orders,
        "assumptions": [
            "Input cash events are chronological; each event nets its inflow and outflow.",
            "Orders are evaluated independently, not as a jointly feasible portfolio.",
            "Available units and ready periods are supplied, not scheduled or verified.",
            "Cash events must already include all costs and collections; orders and fees are not auto-posted.",
            "Contribution is not net profit; missing costs are not inferred.",
            "Inventory fees apply only to the supplied snapshot and configured bands.",
        ],
    }
