"""Quality & Maintenance agent: defects, production yield, sensor anomalies and maintenance."""

from dataplatform.agents.base import Agent, AgentContext, Skill, patterns, reply
from dataplatform.agents.nlp import extract_top_n, fmt_number, sql_literal
from dataplatform.agents.supply_chain import plant_filter
from dataplatform.domain.models import AgentReply
from dataplatform.infrastructure.sample_data import AS_OF

AGENT_ID = "quality-maintenance"
MAINTENANCE_INTERVAL_DAYS = 90


def defect_analysis(message: str, ctx: AgentContext) -> AgentReply:
    """Defect rate by production line."""
    n = extract_top_n(message)
    plant_condition, plant_label = plant_filter(message, ctx, "l.plant_id")
    sql = f"""SELECT l.line_id, l.plant_id, l.product_family, count(*) AS inspections,
       sum(qi.defects_found) AS defects, sum(qi.sample_size) AS sampled_units,
       round(100 * sum(qi.defects_found) / sum(qi.sample_size), 2) AS defect_rate_pct,
       mode(qi.defect_type) AS top_defect_type,
       count(*) FILTER (WHERE qi.result = 'fail') AS failed_inspections
FROM manufacturing.production.quality_inspections qi
JOIN manufacturing.production.work_orders wo USING (work_order_id)
JOIN manufacturing.production.production_lines l ON l.line_id = wo.line_id
WHERE TRUE{plant_condition}
GROUP BY ALL
ORDER BY defect_rate_pct DESC
LIMIT {n}"""
    result = ctx.run_sql(sql)
    lines = [f"**Defect rate by production line{plant_label}** (highest first):", ""]
    lines += [
        f"- {r['line_id']} ({r['product_family']}): {r['defect_rate_pct']}% defective, "
        f"{r['failed_inspections']} failed inspections, mostly *{r['top_defect_type']}*"
        for r in result.rows
    ]
    if result.rows:
        worst = result.rows[0]
        lines += ["", f"Recommendation: start a root-cause analysis on **{worst['line_id']}** ({worst['top_defect_type']})."]
    return reply(AGENT_ID, "defect-analysis", "\n".join(lines), sql, result)


def production_yield(message: str, ctx: AgentContext) -> AgentReply:
    """Planned vs produced vs scrapped units per plant."""
    plant_condition, plant_label = plant_filter(message, ctx, "p.plant_id")
    sql = f"""SELECT p.plant_id, p.name AS plant, count(*) AS work_orders, sum(wo.planned_qty) AS planned_units,
       sum(wo.produced_qty) AS produced_units, sum(wo.scrap_qty) AS scrap_units,
       round(100 * sum(wo.produced_qty) / sum(wo.planned_qty), 1) AS yield_pct,
       round(100 * sum(wo.scrap_qty) / sum(wo.planned_qty), 2) AS scrap_pct
FROM manufacturing.production.work_orders wo
JOIN manufacturing.production.production_lines l USING (line_id)
JOIN manufacturing.production.plants p ON p.plant_id = l.plant_id
WHERE wo.status = 'completed'{plant_condition}
GROUP BY ALL
ORDER BY yield_pct DESC"""
    result = ctx.run_sql(sql)
    lines = [f"**Production yield{plant_label}** (completed work orders):", ""]
    lines += [
        f"- {r['plant']}: {r['yield_pct']}% yield, {r['scrap_pct']}% scrap, "
        f"{fmt_number(r['produced_units'])} good units from {fmt_number(r['work_orders'])} work orders"
        for r in result.rows
    ]
    return reply(AGENT_ID, "production-yield", "\n".join(lines), sql, result)


def machine_anomalies(message: str, ctx: AgentContext) -> AgentReply:
    """Machines with the most anomalous sensor readings over the telemetry window."""
    n = extract_top_n(message)
    sql = f"""SELECT m.machine_id, m.machine_type, m.line_id, m.status,
       count(*) FILTER (WHERE r.anomaly_flag) AS anomalies,
       round(avg(r.temperature_c), 1) AS avg_temperature_c, round(max(r.temperature_c), 1) AS max_temperature_c,
       round(max(r.vibration_mm_s), 2) AS max_vibration_mm_s
FROM manufacturing.production.sensor_readings r
JOIN manufacturing.production.machines m USING (machine_id)
GROUP BY ALL
HAVING count(*) FILTER (WHERE r.anomaly_flag) > 0
ORDER BY anomalies DESC, max_vibration_mm_s DESC
LIMIT {n}"""
    result = ctx.run_sql(sql)
    if not result.rows:
        return reply(AGENT_ID, "machine-anomalies", "No sensor anomalies in the telemetry window.", sql, result)
    lines = [f"**{len(result.rows)} machines with sensor anomalies** over the last 14 days of telemetry:", ""]
    lines += [
        f"- {r['machine_id']} ({r['machine_type']}, {r['line_id']}, {r['status']}): {r['anomalies']} anomalies, "
        f"max {r['max_temperature_c']} °C / {r['max_vibration_mm_s']} mm/s"
        for r in result.rows
    ]
    lines += ["", "Rising temperature and vibration together usually precede bearing failure — schedule an inspection."]
    return reply(AGENT_ID, "machine-anomalies", "\n".join(lines), sql, result)


def maintenance_due(message: str, ctx: AgentContext) -> AgentReply:
    """Machines overdue for preventive maintenance or not operational."""
    n = extract_top_n(message, default=20)
    as_of = sql_literal(AS_OF.date().isoformat())
    sql = f"""SELECT m.machine_id, m.machine_type, m.manufacturer, m.line_id, m.status, m.last_maintenance_date,
       date_diff('day', m.last_maintenance_date, DATE {as_of}) AS days_since_maintenance
FROM manufacturing.production.machines m
WHERE m.status <> 'operational'
   OR date_diff('day', m.last_maintenance_date, DATE {as_of}) > {MAINTENANCE_INTERVAL_DAYS}
ORDER BY m.status = 'down' DESC, m.status = 'degraded' DESC, days_since_maintenance DESC
LIMIT {n}"""
    result = ctx.run_sql(sql)
    down = sum(1 for r in result.rows if r["status"] == "down")
    degraded = sum(1 for r in result.rows if r["status"] == "degraded")
    lines = [
        f"**{len(result.rows)} machines need attention** as of {AS_OF.date().isoformat()}: {down} down, {degraded} degraded, "
        f"the rest overdue for their {MAINTENANCE_INTERVAL_DAYS}-day preventive maintenance.",
        "",
    ]
    lines += [
        f"- {r['machine_id']} ({r['machine_type']} by {r['manufacturer']}, {r['line_id']}): {r['status']}, "
        f"last maintained {r['days_since_maintenance']} days ago"
        for r in result.rows[:10]
    ]
    return reply(AGENT_ID, "maintenance-due", "\n".join(lines), sql, result)


def create_agent() -> Agent:
    """Create the Quality & Maintenance agent."""
    return Agent(
        AGENT_ID,
        "Quality & Maintenance Agent",
        "Watches the shop floor: defect rates, production yield and scrap, IoT sensor anomalies and "
        "predictive maintenance.",
        "manufacturing",
        [
            Skill(
                "defect-analysis",
                "Defect analysis",
                "Defect rate and dominant defect type per production line.",
                ("Which production lines have the highest defect rate?", "Quality issues at the Turin plant"),
                patterns(r"\bdefects?\b", r"\bquality\b", r"\binspections?\b", r"\bfail", r"\brejects?\b"),
                defect_analysis,
            ),
            Skill(
                "production-yield",
                "Production yield",
                "Planned vs produced vs scrapped units per plant.",
                ("What is the production yield per plant?", "How much scrap did Stuttgart produce?"),
                patterns(
                    r"\byield\b", r"\bscrap", r"\boutput\b", r"\bproduction\b", r"\bthroughput\b", r"\befficiency\b",
                    r"\boee\b", r"\bwork orders?\b",
                ),
                production_yield,
            ),
            Skill(
                "machine-anomalies",
                "Machine anomalies",
                "Machines with anomalous temperature or vibration readings.",
                ("Which machines show sensor anomalies?", "Top 5 machines by vibration anomalies"),
                patterns(
                    r"\banomal", r"\bsensors?\b", r"\btelemetry\b", r"\bvibration", r"\btemperature", r"\boverheat",
                    r"\biot\b",
                ),
                machine_anomalies,
            ),
            Skill(
                "maintenance-due",
                "Maintenance due",
                "Machines that are down, degraded, or overdue for preventive maintenance.",
                ("Which machines need maintenance?", "List machines overdue for service"),
                patterns(
                    r"\bmaintenance\b", r"\boverdue\b", r"\bservic", r"\bdegraded\b", r"\bdown\b", r"\bbreakdown",
                    r"\bpredictive\b", r"\brepair",
                ),
                maintenance_due,
            ),
        ],
    )
