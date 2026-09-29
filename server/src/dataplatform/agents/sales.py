"""Sales Insights agent: retail revenue, products, stores, channels and customer segments."""

from dataplatform.agents.base import Agent, AgentContext, Skill, patterns, reply
from dataplatform.agents.nlp import (
    extract_top_n,
    extract_value,
    extract_year,
    fmt_money,
    fmt_number,
    sql_literal,
    wants_ascending,
)
from dataplatform.domain.models import AgentReply

AGENT_ID = "sales-insights"


def _filters(
    message: str, ctx: AgentContext, *, region_col: str | None, category_col: str | None
) -> tuple[list[str], list[str]]:
    """Return SQL conditions and human-readable labels for the filters found in the message."""
    conditions = ["o.status = 'completed'"]
    labels: list[str] = []
    year = extract_year(message, ctx.vocabulary.years)
    if year is not None:
        conditions.append(f"year(o.order_date) = {sql_literal(year)}")
        labels.append(str(year))
    if region_col:
        region = extract_value(message, ctx.vocabulary.regions)
        if region is not None:
            conditions.append(f"{region_col} = {sql_literal(region)}")
            labels.append(f"region {region}")
    if category_col:
        category = extract_value(message, ctx.vocabulary.categories)
        if category is not None:
            conditions.append(f"{category_col} = {sql_literal(category)}")
            labels.append(category)
    return conditions, labels


def _scope(labels: list[str]) -> str:
    return f" ({', '.join(labels)})" if labels else ""


def top_products(message: str, ctx: AgentContext) -> AgentReply:
    """Rank products by revenue."""
    n = extract_top_n(message)
    ascending = wants_ascending(message)
    conditions, labels = _filters(message, ctx, region_col="s.region", category_col="p.category")
    sql = f"""SELECT p.name AS product, p.category, p.brand, sum(oi.quantity) AS units,
       round(sum(oi.line_total), 2) AS revenue
FROM retail.sales.order_items oi
JOIN retail.sales.orders o USING (order_id)
JOIN retail.sales.products p USING (product_id)
JOIN retail.sales.stores s ON s.store_id = o.store_id
WHERE {" AND ".join(conditions)}
GROUP BY ALL
ORDER BY revenue {"ASC" if ascending else "DESC"}
LIMIT {n}"""
    result = ctx.run_sql(sql)
    rank = "Bottom" if ascending else "Top"
    lines = [f"**{rank} {len(result.rows)} products by revenue**{_scope(labels)}:", ""]
    lines += [
        f"{i}. {r['product']} ({r['category']}) — {fmt_money(r['revenue'])}, {fmt_number(r['units'])} units"
        for i, r in enumerate(result.rows, 1)
    ]
    return reply(AGENT_ID, "top-products", "\n".join(lines), sql, result)


def store_performance(message: str, ctx: AgentContext) -> AgentReply:
    """Rank stores by revenue."""
    n = extract_top_n(message)
    ascending = wants_ascending(message)
    conditions, labels = _filters(message, ctx, region_col="s.region", category_col=None)
    sql = f"""SELECT s.name AS store, s.region, s.format, count(*) AS orders,
       round(sum(o.total_amount), 2) AS revenue,
       round(avg(o.total_amount), 2) AS avg_order_value
FROM retail.sales.orders o
JOIN retail.sales.stores s USING (store_id)
WHERE {" AND ".join(conditions)}
GROUP BY ALL
ORDER BY revenue {"ASC" if ascending else "DESC"}
LIMIT {n}"""
    result = ctx.run_sql(sql)
    rank = "Lowest" if ascending else "Top"
    lines = [f"**{rank} {len(result.rows)} stores by revenue**{_scope(labels)}:", ""]
    lines += [
        f"{i}. {r['store']} ({r['region']}, {r['format']}) — {fmt_money(r['revenue'])} "
        f"from {fmt_number(r['orders'])} orders (AOV {fmt_money(r['avg_order_value'])})"
        for i, r in enumerate(result.rows, 1)
    ]
    return reply(AGENT_ID, "store-performance", "\n".join(lines), sql, result)


def channel_mix(message: str, ctx: AgentContext) -> AgentReply:
    """Revenue split by sales channel."""
    conditions, labels = _filters(message, ctx, region_col=None, category_col=None)
    sql = f"""SELECT o.channel, count(*) AS orders, round(sum(o.total_amount), 2) AS revenue,
       round(100 * sum(o.total_amount) / sum(sum(o.total_amount)) OVER (), 1) AS revenue_share_pct
FROM retail.sales.orders o
WHERE {" AND ".join(conditions)}
GROUP BY ALL
ORDER BY revenue DESC"""
    result = ctx.run_sql(sql)
    lines = [f"**Revenue by channel**{_scope(labels)}:", ""]
    lines += [
        f"- {r['channel']}: {fmt_money(r['revenue'])} "
        f"({r['revenue_share_pct']}% of revenue, {fmt_number(r['orders'])} orders)"
        for r in result.rows
    ]
    return reply(AGENT_ID, "channel-mix", "\n".join(lines), sql, result)


def customer_segments(message: str, ctx: AgentContext) -> AgentReply:
    """Revenue and basket size by loyalty tier."""
    conditions, labels = _filters(message, ctx, region_col="c.region", category_col=None)
    sql = f"""SELECT c.loyalty_tier, count(DISTINCT c.customer_id) AS customers, count(*) AS orders,
       round(sum(o.total_amount), 2) AS revenue, round(avg(o.total_amount), 2) AS avg_order_value
FROM retail.sales.orders o
JOIN retail.sales.customers c USING (customer_id)
WHERE {" AND ".join(conditions)}
GROUP BY ALL
ORDER BY revenue DESC"""
    result = ctx.run_sql(sql)
    lines = [f"**Customer segments by loyalty tier**{_scope(labels)}:", ""]
    lines += [
        f"- {r['loyalty_tier']}: {fmt_number(r['customers'])} customers, {fmt_money(r['revenue'])} revenue, "
        f"average order {fmt_money(r['avg_order_value'])}"
        for r in result.rows
    ]
    return reply(AGENT_ID, "customer-segments", "\n".join(lines), sql, result)


def category_performance(message: str, ctx: AgentContext) -> AgentReply:
    """Revenue and gross margin by product category."""
    conditions, labels = _filters(message, ctx, region_col="s.region", category_col=None)
    sql = f"""SELECT p.category, sum(oi.quantity) AS units, round(sum(oi.line_total), 2) AS revenue,
       round(sum(oi.line_total - oi.quantity * p.unit_cost), 2) AS gross_margin,
       round(100 * sum(oi.line_total - oi.quantity * p.unit_cost) / sum(oi.line_total), 1) AS margin_pct
FROM retail.sales.order_items oi
JOIN retail.sales.orders o USING (order_id)
JOIN retail.sales.products p USING (product_id)
JOIN retail.sales.stores s ON s.store_id = o.store_id
WHERE {" AND ".join(conditions)}
GROUP BY ALL
ORDER BY revenue DESC"""
    result = ctx.run_sql(sql)
    lines = [f"**Category performance**{_scope(labels)}:", ""]
    lines += [
        f"- {r['category']}: {fmt_money(r['revenue'])} revenue, {r['margin_pct']}% gross margin" for r in result.rows
    ]
    return reply(AGENT_ID, "category-performance", "\n".join(lines), sql, result)


def revenue_trend(message: str, ctx: AgentContext) -> AgentReply:
    """Monthly revenue trend."""
    conditions, labels = _filters(message, ctx, region_col="s.region", category_col=None)
    sql = f"""SELECT strftime(o.order_date, '%Y-%m') AS month, count(*) AS orders,
       round(sum(o.total_amount), 2) AS revenue
FROM retail.sales.orders o
JOIN retail.sales.stores s USING (store_id)
WHERE {" AND ".join(conditions)}
GROUP BY ALL
ORDER BY month"""
    result = ctx.run_sql(sql)
    rows = result.rows
    if not rows:
        return reply(AGENT_ID, "revenue-trend", f"No completed orders found{_scope(labels)}.", sql, result)
    total = sum(float(r["revenue"]) for r in rows)
    best = max(rows, key=lambda r: float(r["revenue"]))
    worst = min(rows, key=lambda r: float(r["revenue"]))
    first, last = float(rows[0]["revenue"]), float(rows[-1]["revenue"])
    change = (last - first) / first * 100 if first else 0.0
    answer = "\n".join(
        [
            f"**Monthly revenue**{_scope(labels)} — {len(rows)} months, total {fmt_money(total)}.",
            "",
            f"- Best month: **{best['month']}** with {fmt_money(best['revenue'])}",
            f"- Weakest month: **{worst['month']}** with {fmt_money(worst['revenue'])}",
            f"- {rows[0]['month']} → {rows[-1]['month']}: {change:+.1f}%",
        ]
    )
    return reply(AGENT_ID, "revenue-trend", answer, sql, result)


def create_agent() -> Agent:
    """Create the Sales Insights agent."""
    return Agent(
        AGENT_ID,
        "Sales Insights Agent",
        "Answers retail sales questions: revenue trends, best-selling products, store and channel performance, "
        "customer segments and category margins.",
        "retail",
        [
            Skill(
                "top-products",
                "Top products",
                "Rank products by revenue, optionally for a category, region or year.",
                ("What are the top 5 products in Electronics?", "Worst 3 products in 2025"),
                patterns(r"\bproducts?\b", r"\bbest[- ]?sell", r"\bsku", r"\bitems?\b"),
                top_products,
            ),
            Skill(
                "store-performance",
                "Store performance",
                "Rank stores by revenue and average order value, optionally for a region.",
                ("Which stores perform best in the South region?", "Lowest 5 stores by revenue"),
                patterns(r"\bstores?\b", r"\bregions?\b", r"\bshops?\b", r"\blocations?\b"),
                store_performance,
            ),
            Skill(
                "channel-mix",
                "Channel mix",
                "Split revenue across in-store, online and click & collect.",
                ("What is the revenue split by channel?", "How much do we sell online?"),
                patterns(r"\bchannels?\b", r"\bonline\b", r"\bin[- ]store\b", r"\bclick", r"\be-?commerce\b"),
                channel_mix,
            ),
            Skill(
                "customer-segments",
                "Customer segments",
                "Compare loyalty tiers by customers, revenue and basket size.",
                ("How do loyalty tiers compare?", "Average order value by customer segment"),
                patterns(r"\bcustomers?\b", r"\bloyalty\b", r"\bsegments?\b", r"\btiers?\b", r"\bbasket\b"),
                customer_segments,
            ),
            Skill(
                "category-performance",
                "Category performance",
                "Revenue and gross margin by product category.",
                ("Which categories have the best margin?", "Category performance in 2026"),
                patterns(r"\bcategor(?:y|ies)\b", r"\bmargins?\b", r"\bprofit"),
                category_performance,
            ),
            Skill(
                "revenue-trend",
                "Revenue trend",
                "Monthly revenue, best and weakest months, and growth.",
                ("Show me the monthly revenue trend for 2025", "How are sales trending in the North region?"),
                patterns(
                    r"\btrend", r"\bmonth", r"\bseason", r"\bover time\b", r"\brevenue\b", r"\bsales\b", r"\bgrowth\b"
                ),
                revenue_trend,
            ),
        ],
    )
