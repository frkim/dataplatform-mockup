"""Supply Chain agent: store stock-outs, material shortages, supplier performance and open POs."""

from dataplatform.agents.base import Agent, AgentContext, Skill, patterns, reply
from dataplatform.agents.nlp import extract_top_n, extract_value, fmt_money, fmt_number, sql_literal, wants_ascending
from dataplatform.domain.models import AgentReply

AGENT_ID = "supply-chain"


def plant_filter(message: str, ctx: AgentContext, column: str) -> tuple[str, str]:
    """Return an SQL condition (prefixed with AND) and a label for a plant mentioned in the message."""
    match = extract_value(message, list(ctx.vocabulary.plants))
    if match is None:
        return "", ""
    plant_id = ctx.vocabulary.plants[match.lower()]
    return f" AND {column} = {sql_literal(plant_id)}", f" at plant {plant_id}"


def store_low_stock(message: str, ctx: AgentContext) -> AgentReply:
    """Store products below their reorder point."""
    n = extract_top_n(message, default=20)
    conditions = ["i.on_hand_qty < i.reorder_point"]
    labels: list[str] = []
    region = extract_value(message, ctx.vocabulary.regions)
    if region is not None:
        conditions.append(f"s.region = {sql_literal(region)}")
        labels.append(f"region {region}")
    category = extract_value(message, ctx.vocabulary.categories)
    if category is not None:
        conditions.append(f"p.category = {sql_literal(category)}")
        labels.append(category)
    where = " AND ".join(conditions)
    sql = f"""SELECT s.name AS store, s.region, p.name AS product, p.category, i.on_hand_qty, i.reorder_point,
       i.reorder_point - i.on_hand_qty AS shortfall, count(*) OVER () AS total_items_below_reorder_point
FROM retail.inventory.store_inventory i
JOIN retail.sales.stores s USING (store_id)
JOIN retail.sales.products p USING (product_id)
WHERE {where}
ORDER BY shortfall DESC, store, product
LIMIT {n}"""
    result = ctx.run_sql(sql)
    scope = f" ({', '.join(labels)})" if labels else ""
    if not result.rows:
        return reply(AGENT_ID, "store-low-stock", f"No store items are below their reorder point{scope}. 🎉", sql, result)
    total = result.rows[0]["total_items_below_reorder_point"]
    out_of_stock = sum(1 for r in result.rows if r["on_hand_qty"] == 0)
    lines = [
        f"**{fmt_number(total)} store items are below their reorder point**{scope}. "
        f"Largest shortfalls ({out_of_stock} of the listed items are out of stock):",
        "",
    ]
    lines += [
        f"- {r['store']}: {r['product']} — {r['on_hand_qty']} on hand vs reorder point {r['reorder_point']}"
        for r in result.rows[:10]
    ]
    lines += ["", "Recommendation: raise replenishment orders for the items with the largest shortfall first."]
    return reply(AGENT_ID, "store-low-stock", "\n".join(lines), sql, result)


def material_shortages(message: str, ctx: AgentContext) -> AgentReply:
    """Plant materials below their reorder point, with the supplier to call."""
    n = extract_top_n(message, default=20)
    plant_condition, plant_label = plant_filter(message, ctx, "mi.plant_id")
    sql = f"""SELECT mi.plant_id, m.name AS material, m.category, mi.on_hand_qty, mi.reorder_point, mi.safety_stock,
       s.name AS supplier, s.avg_lead_time_days,
       CASE WHEN mi.on_hand_qty < mi.safety_stock THEN 'critical' ELSE 'reorder' END AS severity,
       count(*) OVER () AS total_below_reorder,
       count(*) FILTER (WHERE mi.on_hand_qty < mi.safety_stock) OVER () AS total_critical
FROM manufacturing.supply_chain.material_inventory mi
JOIN manufacturing.supply_chain.materials m USING (material_id)
JOIN manufacturing.supply_chain.suppliers s ON s.supplier_id = m.supplier_id
WHERE mi.on_hand_qty < mi.reorder_point{plant_condition}
ORDER BY severity, mi.reorder_point - mi.on_hand_qty DESC
LIMIT {n}"""
    result = ctx.run_sql(sql)
    if not result.rows:
        return reply(AGENT_ID, "material-shortages", f"No material is below its reorder point{plant_label}.", sql, result)
    first = result.rows[0]
    lines = [
        f"**{fmt_number(first['total_below_reorder'])} materials below reorder point{plant_label}**, "
        f"{fmt_number(first['total_critical'])} of them below safety stock (critical). Most urgent:",
        "",
    ]
    lines += [
        f"- [{r['severity']}] {r['plant_id']} · {r['material']}: {fmt_number(r['on_hand_qty'])} on hand "
        f"(reorder at {fmt_number(r['reorder_point'])}) — order from {r['supplier']}, lead time {r['avg_lead_time_days']} days"
        for r in result.rows[:10]
    ]
    return reply(AGENT_ID, "material-shortages", "\n".join(lines), sql, result)


def supplier_performance(message: str, ctx: AgentContext) -> AgentReply:
    """On-time delivery rate and average delay per supplier."""
    n = extract_top_n(message)
    best_first = not wants_ascending(message) and any(w in message.lower() for w in ("best", "most reliable", "top"))
    sql = f"""SELECT s.name AS supplier, s.country, s.rating, count(*) AS delivered_orders,
       round(100 * avg(CASE WHEN po.received_date <= po.expected_date THEN 1 ELSE 0 END), 1) AS on_time_pct,
       round(avg(greatest(date_diff('day', po.expected_date, po.received_date), 0)), 1) AS avg_delay_days
FROM manufacturing.supply_chain.purchase_orders po
JOIN manufacturing.supply_chain.suppliers s USING (supplier_id)
WHERE po.status = 'received'
GROUP BY ALL
ORDER BY on_time_pct {"DESC" if best_first else "ASC"}, delivered_orders DESC
LIMIT {n}"""
    result = ctx.run_sql(sql)
    heading = "Most reliable suppliers" if best_first else "Suppliers with the weakest on-time delivery"
    lines = [f"**{heading}:**", ""]
    lines += [
        f"{i}. {r['supplier']} ({r['country']}) — {r['on_time_pct']}% on time, "
        f"average delay {r['avg_delay_days']} days over {fmt_number(r['delivered_orders'])} deliveries"
        for i, r in enumerate(result.rows, 1)
    ]
    return reply(AGENT_ID, "supplier-performance", "\n".join(lines), sql, result)


def open_purchase_orders(message: str, ctx: AgentContext) -> AgentReply:
    """Open purchase orders by supplier."""
    n = extract_top_n(message)
    sql = f"""SELECT s.name AS supplier, count(*) AS open_orders, sum(po.quantity) AS open_quantity,
       round(sum(po.quantity * po.unit_price), 2) AS open_value, min(po.expected_date) AS next_expected_date
FROM manufacturing.supply_chain.purchase_orders po
JOIN manufacturing.supply_chain.suppliers s USING (supplier_id)
WHERE po.status = 'open'
GROUP BY ALL
ORDER BY open_value DESC
LIMIT {n}"""
    result = ctx.run_sql(sql)
    total = sum(float(r["open_value"]) for r in result.rows)
    lines = [f"**Open purchase orders** — {fmt_money(total)} across the {len(result.rows)} largest suppliers:", ""]
    lines += [
        f"- {r['supplier']}: {r['open_orders']} open orders worth {fmt_money(r['open_value'])}, "
        f"next delivery expected {r['next_expected_date']}"
        for r in result.rows
    ]
    return reply(AGENT_ID, "open-purchase-orders", "\n".join(lines), sql, result)


def create_agent() -> Agent:
    """Create the Supply Chain agent."""
    return Agent(
        AGENT_ID,
        "Supply Chain Agent",
        "Monitors inventory and procurement: store stock-outs, plant material shortages, supplier on-time "
        "performance and open purchase orders.",
        "supply chain",
        [
            Skill(
                "material-shortages",
                "Material shortages",
                "Plant materials below reorder point or safety stock, with the supplier to call.",
                ("Which materials are running low at the Lyon plant?", "Show critical material shortages"),
                patterns(r"\bmaterials?\b", r"\bshortages?\b", r"\braw\b", r"\bcomponents?\b"),
                material_shortages,
            ),
            Skill(
                "store-low-stock",
                "Store low stock",
                "Store products below their reorder point, optionally for a region or category.",
                ("Which products are low on stock in the North region?", "Show stock-outs for Toys"),
                patterns(
                    r"\blow\b.*\bstock\b", r"\bstock\b", r"\bstock[- ]?outs?\b", r"\bout of stock", r"\breorder",
                    r"\breplenish", r"\binventory\b",
                ),
                store_low_stock,
            ),
            Skill(
                "supplier-performance",
                "Supplier performance",
                "On-time delivery rate and average delay per supplier.",
                ("Which suppliers are most often late?", "Show the best suppliers by on-time delivery"),
                patterns(
                    r"\bsuppliers?\b", r"\bvendors?\b", r"\blead[- ]times?\b", r"\bon[- ]time\b", r"\blate\b",
                    r"\bdelay", r"\bdeliver",
                ),
                supplier_performance,
            ),
            Skill(
                "open-purchase-orders",
                "Open purchase orders",
                "Outstanding purchase orders and their value by supplier.",
                ("What purchase orders are still open?", "Open PO value by supplier"),
                patterns(r"\bpurchase[- ]orders?\b", r"\bpos?\b", r"\bopen\b", r"\bprocure", r"\bspend\b", r"\bexpected\b"),
                open_purchase_orders,
            ),
        ],
    )
