"""Static definition of the mock catalog: catalogs, schemas, tables and columns.

This is the single source of truth for the DDL, for the metadata served by the API, and for
the allowlist of identifiers that may appear in generated SQL.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ColumnDef:
    """A column definition."""

    name: str
    type: str
    description: str
    nullable: bool = True
    primary_key: bool = False

    @property
    def is_text(self) -> bool:
        """Whether the column holds free text (used by global search)."""
        return self.type == "VARCHAR"


@dataclass(frozen=True)
class TableDef:
    """A table definition."""

    catalog: str
    schema: str
    name: str
    description: str
    columns: tuple[ColumnDef, ...]

    @property
    def full_name(self) -> str:
        """Three-part name ``catalog.schema.table``."""
        return f"{self.catalog}.{self.schema}.{self.name}"

    @property
    def quoted_name(self) -> str:
        """Three-part name with every identifier double-quoted."""
        return f'"{self.catalog}"."{self.schema}"."{self.name}"'

    def column(self, name: str) -> ColumnDef | None:
        """Return the column called ``name`` or ``None``."""
        return next((c for c in self.columns if c.name == name), None)


@dataclass(frozen=True)
class SchemaDef:
    """A schema definition."""

    catalog: str
    name: str
    description: str
    tables: tuple[TableDef, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class CatalogDef:
    """A catalog definition."""

    name: str
    description: str
    schemas: tuple[SchemaDef, ...] = field(default_factory=tuple)


def _pk(name: str, type_: str, description: str) -> ColumnDef:
    return ColumnDef(name, type_, description, nullable=False, primary_key=True)


def _req(name: str, type_: str, description: str) -> ColumnDef:
    return ColumnDef(name, type_, description, nullable=False)


def _opt(name: str, type_: str, description: str) -> ColumnDef:
    return ColumnDef(name, type_, description, nullable=True)


MONEY = "DECIMAL(12,2)"

_PRODUCTION = (
    TableDef(
        "manufacturing",
        "production",
        "plants",
        "Manufacturing plants and their daily capacity.",
        (
            _pk("plant_id", "VARCHAR", "Plant identifier."),
            _req("name", "VARCHAR", "Plant name."),
            _req("city", "VARCHAR", "City."),
            _req("country", "VARCHAR", "Country."),
            _req("opened_year", "INTEGER", "Year the plant opened."),
            _req("capacity_units_per_day", "INTEGER", "Nominal output capacity per day."),
        ),
    ),
    TableDef(
        "manufacturing",
        "production",
        "production_lines",
        "Assembly and processing lines inside each plant.",
        (
            _pk("line_id", "VARCHAR", "Line identifier."),
            _req("plant_id", "VARCHAR", "Owning plant (plants.plant_id)."),
            _req("name", "VARCHAR", "Line name."),
            _req("product_family", "VARCHAR", "Product family produced on the line."),
            _req("status", "VARCHAR", "running, idle or maintenance."),
        ),
    ),
    TableDef(
        "manufacturing",
        "production",
        "machines",
        "Machines installed on production lines.",
        (
            _pk("machine_id", "VARCHAR", "Machine identifier."),
            _req("line_id", "VARCHAR", "Line the machine belongs to (production_lines.line_id)."),
            _req("machine_type", "VARCHAR", "CNC mill, press, robot arm..."),
            _req("manufacturer", "VARCHAR", "Machine vendor."),
            _req("install_date", "DATE", "Installation date."),
            _req("status", "VARCHAR", "operational, degraded or down."),
            _req("last_maintenance_date", "DATE", "Date of the last preventive maintenance."),
        ),
    ),
    TableDef(
        "manufacturing",
        "production",
        "work_orders",
        "Production work orders with planned, produced and scrapped quantities.",
        (
            _pk("work_order_id", "VARCHAR", "Work order identifier."),
            _req("line_id", "VARCHAR", "Line executing the order."),
            _req("product_sku", "VARCHAR", "Produced SKU."),
            _req("planned_qty", "INTEGER", "Planned quantity."),
            _req("produced_qty", "INTEGER", "Good units produced."),
            _req("scrap_qty", "INTEGER", "Scrapped units."),
            _req("start_time", "TIMESTAMP", "Start of production."),
            _opt("end_time", "TIMESTAMP", "End of production (null while in progress)."),
            _req("status", "VARCHAR", "completed, in_progress or cancelled."),
        ),
    ),
    TableDef(
        "manufacturing",
        "production",
        "quality_inspections",
        "Quality inspections sampled from work orders.",
        (
            _pk("inspection_id", "VARCHAR", "Inspection identifier."),
            _req("work_order_id", "VARCHAR", "Inspected work order."),
            _req("inspected_at", "TIMESTAMP", "Inspection time."),
            _req("sample_size", "INTEGER", "Units inspected."),
            _req("defects_found", "INTEGER", "Defective units found."),
            _opt("defect_type", "VARCHAR", "Dominant defect type (null when no defect)."),
            _req("result", "VARCHAR", "pass or fail."),
        ),
    ),
    TableDef(
        "manufacturing",
        "production",
        "sensor_readings",
        "IoT telemetry emitted by machines.",
        (
            _pk("reading_id", "BIGINT", "Reading identifier."),
            _req("machine_id", "VARCHAR", "Emitting machine."),
            _req("recorded_at", "TIMESTAMP", "Measurement time."),
            _req("temperature_c", "DOUBLE", "Temperature in °C."),
            _req("vibration_mm_s", "DOUBLE", "Vibration velocity in mm/s."),
            _req("power_kw", "DOUBLE", "Power draw in kW."),
            _req("anomaly_flag", "BOOLEAN", "True when the reading breaches a threshold."),
        ),
    ),
)

_SUPPLY_CHAIN = (
    TableDef(
        "manufacturing",
        "supply_chain",
        "suppliers",
        "Raw material and component suppliers.",
        (
            _pk("supplier_id", "VARCHAR", "Supplier identifier."),
            _req("name", "VARCHAR", "Supplier name."),
            _req("country", "VARCHAR", "Country."),
            _req("rating", "DOUBLE", "Quality rating from 1 to 5."),
            _req("avg_lead_time_days", "INTEGER", "Contractual lead time in days."),
        ),
    ),
    TableDef(
        "manufacturing",
        "supply_chain",
        "materials",
        "Raw materials and components.",
        (
            _pk("material_id", "VARCHAR", "Material identifier."),
            _req("name", "VARCHAR", "Material name."),
            _req("category", "VARCHAR", "Metals, plastics, electronics..."),
            _req("unit", "VARCHAR", "Unit of measure."),
            _req("unit_cost", MONEY, "Standard cost per unit (EUR)."),
            _req("supplier_id", "VARCHAR", "Preferred supplier."),
        ),
    ),
    TableDef(
        "manufacturing",
        "supply_chain",
        "material_inventory",
        "On-hand material stock per plant.",
        (
            _req("material_id", "VARCHAR", "Material."),
            _req("plant_id", "VARCHAR", "Plant."),
            _req("on_hand_qty", "INTEGER", "Quantity on hand."),
            _req("reorder_point", "INTEGER", "Reorder point."),
            _req("safety_stock", "INTEGER", "Safety stock."),
            _req("updated_at", "TIMESTAMP", "Last stock count."),
        ),
    ),
    TableDef(
        "manufacturing",
        "supply_chain",
        "purchase_orders",
        "Purchase orders placed with suppliers.",
        (
            _pk("po_id", "VARCHAR", "Purchase order identifier."),
            _req("supplier_id", "VARCHAR", "Supplier."),
            _req("material_id", "VARCHAR", "Ordered material."),
            _req("quantity", "INTEGER", "Ordered quantity."),
            _req("unit_price", MONEY, "Negotiated unit price (EUR)."),
            _req("order_date", "DATE", "Order date."),
            _req("expected_date", "DATE", "Expected delivery date."),
            _opt("received_date", "DATE", "Actual delivery date (null while open)."),
            _req("status", "VARCHAR", "open, received or cancelled."),
        ),
    ),
)

_SALES = (
    TableDef(
        "retail",
        "sales",
        "stores",
        "Physical stores and the online shop.",
        (
            _pk("store_id", "VARCHAR", "Store identifier."),
            _req("name", "VARCHAR", "Store name."),
            _req("city", "VARCHAR", "City."),
            _req("region", "VARCHAR", "Sales region."),
            _req("format", "VARCHAR", "hypermarket, supermarket, express or online."),
            _req("opened_date", "DATE", "Opening date."),
            _opt("square_meters", "INTEGER", "Sales area (null for online)."),
        ),
    ),
    TableDef(
        "retail",
        "sales",
        "products",
        "Product catalogue.",
        (
            _pk("product_id", "VARCHAR", "Product identifier."),
            _req("sku", "VARCHAR", "Stock keeping unit."),
            _req("name", "VARCHAR", "Product name."),
            _req("category", "VARCHAR", "Product category."),
            _req("brand", "VARCHAR", "Brand."),
            _req("unit_price", MONEY, "List price (EUR)."),
            _req("unit_cost", MONEY, "Unit cost (EUR)."),
        ),
    ),
    TableDef(
        "retail",
        "sales",
        "customers",
        "Loyalty programme members (synthetic, no real personal data).",
        (
            _pk("customer_id", "VARCHAR", "Customer identifier."),
            _req("first_name", "VARCHAR", "Synthetic first name."),
            _req("last_name", "VARCHAR", "Synthetic last name."),
            _req("city", "VARCHAR", "City."),
            _req("region", "VARCHAR", "Region."),
            _req("loyalty_tier", "VARCHAR", "bronze, silver, gold or platinum."),
            _req("signup_date", "DATE", "Loyalty programme signup date."),
        ),
    ),
    TableDef(
        "retail",
        "sales",
        "orders",
        "Customer orders (header).",
        (
            _pk("order_id", "VARCHAR", "Order identifier."),
            _req("customer_id", "VARCHAR", "Customer."),
            _req("store_id", "VARCHAR", "Selling store."),
            _req("channel", "VARCHAR", "in_store, online or click_and_collect."),
            _req("order_date", "DATE", "Order date."),
            _req("status", "VARCHAR", "completed, returned or cancelled."),
            _req("total_amount", MONEY, "Order total after discounts (EUR)."),
        ),
    ),
    TableDef(
        "retail",
        "sales",
        "order_items",
        "Order lines.",
        (
            _pk("order_item_id", "VARCHAR", "Order line identifier."),
            _req("order_id", "VARCHAR", "Order."),
            _req("product_id", "VARCHAR", "Product."),
            _req("quantity", "INTEGER", "Units sold."),
            _req("unit_price", MONEY, "Unit price charged (EUR)."),
            _req("discount", "DOUBLE", "Discount rate between 0 and 1."),
            _req("line_total", MONEY, "Line total after discount (EUR)."),
        ),
    ),
)

_INVENTORY = (
    TableDef(
        "retail",
        "inventory",
        "store_inventory",
        "On-hand stock per store and product.",
        (
            _req("store_id", "VARCHAR", "Store."),
            _req("product_id", "VARCHAR", "Product."),
            _req("on_hand_qty", "INTEGER", "Units on hand."),
            _req("reorder_point", "INTEGER", "Reorder point."),
            _req("last_restock_date", "DATE", "Last replenishment date."),
        ),
    ),
)

_MARKETING = (
    TableDef(
        "retail",
        "marketing",
        "campaigns",
        "Marketing campaigns.",
        (
            _pk("campaign_id", "VARCHAR", "Campaign identifier."),
            _req("name", "VARCHAR", "Campaign name."),
            _req("channel", "VARCHAR", "email, social, tv, search or in_store."),
            _req("start_date", "DATE", "Start date."),
            _req("end_date", "DATE", "End date."),
            _req("budget", MONEY, "Budget (EUR)."),
            _req("target_category", "VARCHAR", "Promoted product category."),
        ),
    ),
)

CATALOGS: tuple[CatalogDef, ...] = (
    CatalogDef(
        "manufacturing",
        "Discrete manufacturing: plants, lines, machines, quality and supply chain.",
        (
            SchemaDef("manufacturing", "production", "Shop-floor operations and IoT telemetry.", _PRODUCTION),
            SchemaDef("manufacturing", "supply_chain", "Suppliers, materials and procurement.", _SUPPLY_CHAIN),
        ),
    ),
    CatalogDef(
        "retail",
        "Omnichannel retail: stores, products, customers, orders and marketing.",
        (
            SchemaDef("retail", "sales", "Point-of-sale and e-commerce transactions.", _SALES),
            SchemaDef("retail", "inventory", "Store stock levels.", _INVENTORY),
            SchemaDef("retail", "marketing", "Campaigns and promotions.", _MARKETING),
        ),
    ),
)


def all_tables() -> list[TableDef]:
    """Return every table definition, in catalog order."""
    return [t for c in CATALOGS for s in c.schemas for t in s.tables]
