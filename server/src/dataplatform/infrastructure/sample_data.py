"""Deterministic synthetic sample data for the manufacturing and retail catalogs.

The same seed always produces the same rows, so tests, demos and agents give reproducible
answers. All names are synthetic: the data set contains no real personal data.
"""

import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from itertools import accumulate
from typing import Any

Row = tuple[Any, ...]

DATA_START = date(2025, 1, 1)
DATA_END = date(2026, 6, 30)
AS_OF = datetime(2026, 7, 1, 0, 0, 0)
"""Reference "now" of the data set, used by agents for relative questions (e.g. overdue)."""

_REGIONS: dict[str, tuple[str, ...]] = {
    "North": ("Lille", "Amiens", "Rouen"),
    "South": ("Marseille", "Nice", "Montpellier", "Toulouse"),
    "East": ("Strasbourg", "Metz", "Nancy"),
    "West": ("Nantes", "Rennes", "Bordeaux"),
    "Central": ("Paris", "Lyon", "Orléans", "Dijon"),
}

_FIRST_NAMES = (
    "Emma",
    "Louis",
    "Jade",
    "Gabriel",
    "Louise",
    "Léo",
    "Alice",
    "Raphaël",
    "Chloé",
    "Arthur",
    "Lina",
    "Jules",
    "Mia",
    "Adam",
    "Rose",
    "Hugo",
    "Anna",
    "Nathan",
    "Inès",
    "Lucas",
    "Léa",
    "Tom",
    "Manon",
    "Noah",
    "Camille",
    "Ethan",
    "Zoé",
    "Paul",
    "Sarah",
    "Victor",
)
_LAST_NAMES = (
    "Martin",
    "Bernard",
    "Thomas",
    "Petit",
    "Robert",
    "Richard",
    "Durand",
    "Dubois",
    "Moreau",
    "Laurent",
    "Simon",
    "Michel",
    "Lefebvre",
    "Leroy",
    "Roux",
    "David",
    "Bertrand",
    "Morel",
    "Fournier",
    "Girard",
    "Bonnet",
    "Dupont",
    "Lambert",
    "Fontaine",
    "Rousseau",
    "Vincent",
)

_CATEGORIES: dict[str, tuple[tuple[str, ...], tuple[str, ...], tuple[float, float]]] = {
    # category: (brands, product nouns, price range)
    "Electronics": (
        ("Voltix", "Nordwave", "Pixelon", "Auralis"),
        (
            "Wireless Earbuds",
            "4K Monitor",
            "Bluetooth Speaker",
            "Smartwatch",
            "Tablet",
            "USB-C Hub",
            "Gaming Mouse",
            "Mechanical Keyboard",
            "Action Camera",
            "Power Bank",
        ),
        (19.0, 649.0),
    ),
    "Home & Kitchen": (
        ("Casaluce", "Kitchora", "Maison Vive"),
        (
            "Espresso Machine",
            "Air Fryer",
            "Chef Knife Set",
            "Cast Iron Pan",
            "Blender",
            "Linen Duvet",
            "Table Lamp",
            "Storage Box",
            "Kettle",
            "Cookware Set",
        ),
        (9.0, 399.0),
    ),
    "Grocery": (
        ("Terroir", "Bio Jardin", "Petit Marché"),
        (
            "Olive Oil",
            "Organic Coffee",
            "Dark Chocolate",
            "Basmati Rice",
            "Pasta",
            "Honey",
            "Green Tea",
            "Granola",
            "Sparkling Water",
            "Tomato Sauce",
        ),
        (1.5, 24.0),
    ),
    "Beauty": (
        ("Lumière", "Pure Botanica", "Éclat"),
        (
            "Face Serum",
            "Moisturiser",
            "Shampoo",
            "Perfume",
            "Lip Balm",
            "Sunscreen",
            "Hand Cream",
            "Conditioner",
            "Body Wash",
            "Night Cream",
        ),
        (4.0, 119.0),
    ),
    "Sports": (
        ("Altura", "Stride", "Vertex"),
        (
            "Running Shoes",
            "Yoga Mat",
            "Dumbbell Set",
            "Cycling Helmet",
            "Tennis Racket",
            "Hiking Backpack",
            "Water Bottle",
            "Fitness Tracker",
            "Swim Goggles",
            "Football",
        ),
        (8.0, 249.0),
    ),
    "Toys": (
        ("Kidoo", "Brickly", "Wonderbox"),
        (
            "Building Blocks",
            "Puzzle 1000pc",
            "Plush Bear",
            "Board Game",
            "RC Car",
            "Doll House",
            "Science Kit",
            "Wooden Train",
            "Art Set",
            "Card Game",
        ),
        (6.0, 129.0),
    ),
    "Clothing": (
        ("Atelier Nord", "Urbanite", "Coton & Co"),
        (
            "Denim Jacket",
            "Wool Sweater",
            "T-Shirt",
            "Chinos",
            "Rain Coat",
            "Sneakers",
            "Scarf",
            "Dress",
            "Hoodie",
            "Leather Belt",
        ),
        (12.0, 189.0),
    ),
    "Garden": (
        ("Verdana", "GreenHand"),
        (
            "Garden Hose",
            "Pruning Shears",
            "Plant Pot",
            "Lawn Mower",
            "Seed Kit",
            "Watering Can",
            "Outdoor Chair",
            "Solar Lights",
            "Compost Bin",
            "Hedge Trimmer",
        ),
        (5.0, 449.0),
    ),
}

_PLANTS = (
    ("PL-LYO", "Lyon Assembly", "Lyon", "France", 1998, 2_400),
    ("PL-STR", "Stuttgart Precision", "Stuttgart", "Germany", 2005, 3_100),
    ("PL-TUR", "Turin Components", "Turin", "Italy", 2011, 1_800),
    ("PL-WRO", "Wrocław Motors", "Wrocław", "Poland", 2018, 2_700),
)
_PRODUCT_FAMILIES = ("Electric Motors", "Pumps", "Gearboxes", "Control Units", "Compressors")
_MACHINE_TYPES = (
    "CNC Mill",
    "Hydraulic Press",
    "Robot Arm",
    "Laser Cutter",
    "Injection Molder",
    "Conveyor",
    "Paint Booth",
    "Test Bench",
)
_MACHINE_VENDORS = ("Fanuc", "Siemens", "ABB", "KUKA", "Trumpf", "DMG Mori", "Haas", "Bosch Rexroth")
_DEFECT_TYPES = ("dimensional", "surface scratch", "porosity", "misalignment", "electrical fault", "paint defect")
_MATERIAL_CATEGORIES: dict[str, tuple[str, tuple[str, ...]]] = {
    "Metals": ("kg", ("Steel Sheet", "Aluminium Bar", "Copper Wire", "Stainless Rod", "Cast Iron Blank")),
    "Plastics": ("kg", ("ABS Pellets", "Polycarbonate Resin", "Nylon Granulate", "PVC Tube")),
    "Electronics": ("pcs", ("PCB Assembly", "Microcontroller", "Hall Sensor", "Power MOSFET", "Connector Kit")),
    "Fasteners": ("pcs", ("M6 Bolt", "M8 Nut", "Lock Washer", "Rivet", "Hex Screw")),
    "Chemicals": ("l", ("Industrial Paint", "Lubricant Oil", "Epoxy Adhesive", "Degreaser")),
}
_SUPPLIER_COUNTRIES = {
    "France": "SAS",
    "Germany": "GmbH",
    "Italy": "S.p.A.",
    "Poland": "Sp. z o.o.",
    "Spain": "S.L.",
    "Czechia": "s.r.o.",
    "China": "Co., Ltd.",
    "Taiwan": "Co., Ltd.",
    "Mexico": "S.A. de C.V.",
}
_SUPPLIER_WORDS = ("Metal", "Tech", "Industrie", "Components", "Supply", "Polymer", "Precision", "Electro")
_SUPPLIER_PREFIXES = ("Alpen", "Rhône", "Baltic", "Iberia", "Nordic", "Delta", "Orion", "Atlas", "Vega", "Helios")


@dataclass
class SampleData:
    """Generated rows keyed by the table full name (``catalog.schema.table``)."""

    tables: dict[str, list[Row]]


def _days(start: date, end: date) -> list[date]:
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def _money(value: float) -> float:
    return round(value, 2)


def _generate_retail(rng: random.Random) -> dict[str, list[Row]]:
    stores: list[Row] = []
    cities = [(region, city) for region, cs in _REGIONS.items() for city in cs]
    formats = ("hypermarket", "supermarket", "express")
    sizes = {"hypermarket": (8_000, 14_000), "supermarket": (1_500, 4_000), "express": (200, 600)}
    for i, (region, city) in enumerate(cities, start=1):
        fmt = formats[i % 3]
        stores.append(
            (
                f"S{i:03d}",
                f"Contoso {city} {fmt.title()}",
                city,
                region,
                fmt,
                date(2008, 1, 1) + timedelta(days=rng.randint(0, 5_000)),
                rng.randint(*sizes[fmt]),
            )
        )
    online_id = f"S{len(cities) + 1:03d}"
    stores.append((online_id, "Contoso Online", "Paris", "Online", "online", date(2016, 3, 1), None))

    products: list[Row] = []
    product_weights: list[float] = []
    product_category: list[str] = []
    pid = 0
    for category, (brands, nouns, (low, high)) in _CATEGORIES.items():
        for noun in nouns:
            for tier in ("Essential", "Pro", "Premium"):
                pid += 1
                factor = {"Essential": 0.35, "Pro": 0.65, "Premium": 1.0}[tier]
                price = _money(low + (high - low) * factor * rng.uniform(0.7, 1.0))
                cost = _money(price * rng.uniform(0.45, 0.7))
                brand = rng.choice(brands)
                products.append(
                    (
                        f"P{pid:04d}",
                        f"{category[:3].upper()}-{pid:05d}",
                        f"{brand} {noun} {tier}",
                        category,
                        brand,
                        price,
                        cost,
                    )
                )
                product_weights.append(rng.paretovariate(1.3))
                product_category.append(category)

    customers: list[Row] = []
    for i in range(1, 3_001):
        region, city = rng.choice(cities)
        tier = rng.choices(("bronze", "silver", "gold", "platinum"), weights=(55, 28, 13, 4))[0]
        customers.append(
            (
                f"C{i:05d}",
                rng.choice(_FIRST_NAMES),
                rng.choice(_LAST_NAMES),
                city,
                region,
                tier,
                date(2018, 1, 1) + timedelta(days=rng.randint(0, 2_700)),
            )
        )

    orders: list[Row] = []
    items: list[Row] = []
    days = _days(DATA_START, DATA_END)
    seasonality = {
        1: 0.8,
        2: 0.75,
        3: 0.9,
        4: 0.95,
        5: 1.0,
        6: 1.05,
        7: 1.0,
        8: 0.9,
        9: 0.95,
        10: 1.05,
        11: 1.35,
        12: 1.7,
    }
    day_weights = [
        seasonality[d.month] * (1.25 if d.weekday() >= 5 else 1.0) * (1 + 0.15 * (d - DATA_START).days / 545)
        for d in days
    ]
    day_cum = list(accumulate(day_weights))
    product_cum = list(accumulate(product_weights))
    product_indexes = range(len(products))
    physical_ids = [s[0] for s in stores if s[4] != "online"]
    store_weights = [{"hypermarket": 3.0, "supermarket": 2.0, "express": 1.0}[s[4]] for s in stores[:-1]]
    item_id = 0
    for o in range(1, 15_001):
        order_date = rng.choices(days, cum_weights=day_cum)[0]
        customer = rng.choice(customers)
        if rng.random() < 0.28:
            store_id, channel = online_id, "online"
        else:
            store_id = rng.choices(physical_ids, weights=store_weights)[0]
            channel = "click_and_collect" if rng.random() < 0.15 else "in_store"
        status = rng.choices(("completed", "returned", "cancelled"), weights=(92, 5, 3))[0]
        total = 0.0
        order_id = f"O{o:06d}"
        for _ in range(rng.choices((1, 2, 3, 4, 5), weights=(30, 30, 20, 12, 8))[0]):
            idx = rng.choices(product_indexes, cum_weights=product_cum)[0]
            product = products[idx]
            if product_category[idx] == "Garden" and order_date.month not in (3, 4, 5, 6, 7):
                idx = rng.choices(product_indexes, cum_weights=product_cum)[0]
                product = products[idx]
            quantity = rng.choices((1, 2, 3, 4), weights=(70, 18, 8, 4))[0]
            discount = rng.choices((0.0, 0.05, 0.1, 0.2, 0.3), weights=(70, 10, 10, 7, 3))[0]
            if order_date.month == 11 and order_date.day >= 24:
                discount = max(discount, 0.2)
            unit_price = float(product[5])
            line_total = _money(unit_price * quantity * (1 - discount))
            total += line_total
            item_id += 1
            items.append((f"OI{item_id:07d}", order_id, product[0], quantity, unit_price, discount, line_total))
        orders.append((order_id, customer[0], store_id, channel, order_date, status, _money(total)))

    inventory: list[Row] = []
    for store in stores:
        for product in products:
            reorder_point = rng.randint(5, 40)
            on_hand = rng.randint(0, reorder_point - 1) if rng.random() < 0.08 else rng.randint(reorder_point, 250)
            inventory.append(
                (store[0], product[0], on_hand, reorder_point, DATA_END - timedelta(days=rng.randint(0, 45)))
            )

    campaigns: list[Row] = []
    campaign_names = (
        "Spring Refresh",
        "Summer Sale",
        "Back to School",
        "Black Friday",
        "Holiday Gifts",
        "New Year Wellness",
        "Garden Days",
        "Tech Week",
        "Beauty Month",
        "Kids Festival",
    )
    for i in range(1, 31):
        start = DATA_START + timedelta(days=rng.randint(0, 520))
        category = rng.choice(list(_CATEGORIES))
        campaigns.append(
            (
                f"CMP{i:03d}",
                f"{rng.choice(campaign_names)} {start.year}",
                rng.choice(("email", "social", "tv", "search", "in_store")),
                start,
                start + timedelta(days=rng.randint(7, 45)),
                _money(rng.uniform(5_000, 250_000)),
                category,
            )
        )

    return {
        "retail.sales.stores": stores,
        "retail.sales.products": products,
        "retail.sales.customers": customers,
        "retail.sales.orders": orders,
        "retail.sales.order_items": items,
        "retail.inventory.store_inventory": inventory,
        "retail.marketing.campaigns": campaigns,
    }


def _generate_manufacturing(rng: random.Random) -> dict[str, list[Row]]:
    plants: list[Row] = list(_PLANTS)
    lines: list[Row] = []
    line_quality: dict[str, float] = {}
    for plant in plants:
        for n in range(1, rng.randint(3, 4) + 1):
            line_id = f"{plant[0]}-L{n}"
            status = rng.choices(("running", "idle", "maintenance"), weights=(80, 12, 8))[0]
            lines.append((line_id, plant[0], f"{plant[2]} Line {n}", rng.choice(_PRODUCT_FAMILIES), status))
            line_quality[line_id] = rng.uniform(0.012, 0.06)

    machines: list[Row] = []
    degraded: set[str] = set()
    m = 0
    for line in lines:
        for _ in range(rng.randint(4, 6)):
            m += 1
            machine_id = f"M{m:04d}"
            status = rng.choices(("operational", "degraded", "down"), weights=(85, 11, 4))[0]
            if status != "operational":
                degraded.add(machine_id)
            last_maintenance = AS_OF.date() - timedelta(days=rng.randint(3, 200))
            machines.append(
                (
                    machine_id,
                    line[0],
                    rng.choice(_MACHINE_TYPES),
                    rng.choice(_MACHINE_VENDORS),
                    date(2012, 1, 1) + timedelta(days=rng.randint(0, 4_500)),
                    status,
                    last_maintenance,
                )
            )

    work_orders: list[Row] = []
    inspections: list[Row] = []
    span_hours = int((AS_OF - datetime.combine(DATA_START, datetime.min.time())).total_seconds() // 3600)
    for w in range(1, 5_001):
        line = rng.choice(lines)
        start = datetime.combine(DATA_START, datetime.min.time()) + timedelta(hours=rng.randint(0, span_hours - 72))
        planned = rng.randrange(200, 2_001, 50)
        defect_rate = line_quality[line[0]]
        status = rng.choices(("completed", "cancelled"), weights=(97, 3))[0]
        if start > AS_OF - timedelta(days=3):
            status = "in_progress"
        produced = 0 if status == "cancelled" else int(planned * rng.uniform(0.9, 1.0) * (1 - defect_rate))
        scrap = 0 if status == "cancelled" else int(planned * defect_rate * rng.uniform(0.6, 1.4))
        end = None if status == "in_progress" else start + timedelta(hours=rng.randint(6, 60))
        wo_id = f"WO{w:06d}"
        sku = f"{line[3][:3].upper()}-{rng.randint(100, 999)}"
        work_orders.append((wo_id, line[0], sku, planned, produced, scrap, start, end, status))
        if status != "cancelled" and rng.random() < 0.8:
            sample = rng.choice((20, 50, 80, 125))
            defects = sum(1 for _ in range(sample) if rng.random() < defect_rate)
            inspections.append(
                (
                    f"QI{len(inspections) + 1:06d}",
                    wo_id,
                    start + timedelta(hours=rng.randint(2, 10)),
                    sample,
                    defects,
                    rng.choice(_DEFECT_TYPES) if defects else None,
                    "fail" if defects / sample > 0.05 else "pass",
                )
            )

    readings: list[Row] = []
    reading_id = 0
    telemetry_start = AS_OF - timedelta(days=14)
    for machine in machines:
        base_temp = rng.uniform(38, 62)
        base_vib = rng.uniform(1.2, 3.5)
        base_power = rng.uniform(4, 45)
        is_degraded = machine[0] in degraded
        for hour in range(14 * 24):
            reading_id += 1
            drift = (hour / (14 * 24)) if is_degraded else 0.0
            temp = round(base_temp + rng.gauss(0, 1.5) + drift * 18, 2)
            vib = round(max(0.1, base_vib + rng.gauss(0, 0.3) + drift * 4.5), 3)
            power = round(max(0.5, base_power + rng.gauss(0, 1.2) + drift * 6), 2)
            anomaly = temp > 75 or vib > 7.1
            readings.append(
                (reading_id, machine[0], telemetry_start + timedelta(hours=hour), temp, vib, power, anomaly)
            )

    suppliers: list[Row] = []
    supplier_delay: dict[str, float] = {}
    supplier_names = rng.sample([f"{p} {w}" for p in _SUPPLIER_PREFIXES for w in _SUPPLIER_WORDS], 25)
    for s, base_name in enumerate(supplier_names, start=1):
        supplier_id = f"SUP{s:03d}"
        country = rng.choice(tuple(_SUPPLIER_COUNTRIES))
        name = f"{base_name} {_SUPPLIER_COUNTRIES[country]}"
        suppliers.append((supplier_id, name, country, round(rng.uniform(2.6, 5.0), 1), rng.randint(5, 45)))
        supplier_delay[supplier_id] = rng.choice((0.05, 0.1, 0.2, 0.35, 0.6))

    materials: list[Row] = []
    mat = 0
    for category, (unit, names) in _MATERIAL_CATEGORIES.items():
        for name in names:
            for grade in ("A", "B", "C", "D"):
                mat += 1
                materials.append(
                    (
                        f"MAT{mat:04d}",
                        f"{name} Grade {grade}",
                        category,
                        unit,
                        _money(rng.uniform(0.05, 180.0)),
                        rng.choice(suppliers)[0],
                    )
                )

    material_inventory: list[Row] = []
    for material in materials:
        for plant in plants:
            reorder_point = rng.randint(100, 2_000)
            safety = int(reorder_point * 0.4)
            on_hand = (
                rng.randint(0, reorder_point) if rng.random() < 0.12 else rng.randint(reorder_point, reorder_point * 5)
            )
            material_inventory.append(
                (material[0], plant[0], on_hand, reorder_point, safety, AS_OF - timedelta(hours=rng.randint(1, 96)))
            )

    purchase_orders: list[Row] = []
    lead_times = {s[0]: s[4] for s in suppliers}
    for p in range(1, 2_501):
        material = rng.choice(materials)
        supplier_id = material[5]
        order_date = DATA_START + timedelta(days=rng.randint(0, (DATA_END - DATA_START).days))
        expected = order_date + timedelta(days=lead_times[supplier_id])
        if expected >= AS_OF.date():
            status, received = "open", None
        elif rng.random() < 0.03:
            status, received = "cancelled", None
        else:
            late = rng.random() < supplier_delay[supplier_id]
            received = expected + timedelta(days=rng.randint(1, 20) if late else -rng.randint(0, 3))
            status = "received"
        unit_price = _money(float(material[4]) * rng.uniform(0.9, 1.1))
        purchase_orders.append(
            (
                f"PO{p:06d}",
                supplier_id,
                material[0],
                rng.randrange(100, 10_001, 100),
                unit_price,
                order_date,
                expected,
                received,
                status,
            )
        )

    return {
        "manufacturing.production.plants": plants,
        "manufacturing.production.production_lines": lines,
        "manufacturing.production.machines": machines,
        "manufacturing.production.work_orders": work_orders,
        "manufacturing.production.quality_inspections": inspections,
        "manufacturing.production.sensor_readings": readings,
        "manufacturing.supply_chain.suppliers": suppliers,
        "manufacturing.supply_chain.materials": materials,
        "manufacturing.supply_chain.material_inventory": material_inventory,
        "manufacturing.supply_chain.purchase_orders": purchase_orders,
    }


def generate_sample_data(seed: int = 42) -> SampleData:
    """Generate every table of the mock catalog.

    Args:
        seed: Random seed; the same seed yields identical data.

    Returns:
        Rows for each table, in the column order declared in ``catalog_metadata``.

    """
    rng = random.Random(seed)
    tables = _generate_manufacturing(rng)
    tables.update(_generate_retail(rng))
    return SampleData(tables=tables)
