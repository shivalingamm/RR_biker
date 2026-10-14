"""Development seed data.

Everything created here is clearly labelled as *demonstration* data. No real
motorcycle specifications, prices, mechanic listings, or reviews are fabricated
as if they were live. Replace with verified data before any production launch.

Usage:
    python -m scripts.seed
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import Base, SessionLocal, engine  # noqa: E402
import app.models  # noqa: E402,F401
from app.core.security import hash_password  # noqa: E402
from app.models import (  # noqa: E402
    Cart,
    MechanicReview,
    MechanicService,
    MechanicShop,
    Motorcycle3DAsset,
    MotorcycleCatalogue,
    MotorcycleProductCompatibility,
    MotorcycleSpecification,
    Product,
    ProductCategory,
    ProductImage,
    Seller,
    User,
    UserProfile,
)
from app.core.config import settings  # noqa: E402

IMG = "https://picsum.photos/seed/biker-{seed}/600/600"


def reset() -> None:
    if settings.is_production:
        raise SystemExit("Refusing to seed a production database.")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def seed_categories(db) -> dict[str, ProductCategory]:
    data = [
        ("tyres-tubes", "Tyres and Tubes", "Front and rear tyres, tubes and puncture kits."),
        ("helmets", "Helmets", "Full-face, modular and open-face helmets."),
        ("gloves", "Riding Gloves", "Leather and mesh riding gloves."),
        ("jackets", "Riding Jackets", "Armoured and textile riding jackets."),
        ("mirrors", "Mirrors", "Rear-view mirrors and mirror extenders."),
        ("indicators", "Indicators", "Turn signal lamps and LED indicators."),
        ("brake-pads", "Brake Pads", "Front and rear brake pads."),
        ("chains-sprockets", "Chains and Sprockets", "Drive chains, sprockets and kits."),
        ("phone-holders", "Phone Holders", "Handlebar and tank phone mounts."),
        ("seat-covers", "Seat Covers", "Comfort and waterproof seat covers."),
        ("bike-covers", "Bike Covers", "Dust and rain protection covers."),
        ("accessories", "Other Compatible Accessories", "Miscellaneous compatible accessories."),
    ]
    out: dict[str, ProductCategory] = {}
    for slug, name, desc in data:
        cat = ProductCategory(slug=slug, name=name, description=desc)
        db.add(cat)
        out[slug] = cat
    db.flush()
    return out


DEMO_PRODUCTS = [
    ("tyres-tubes", "Tyre 100/80-17 Tubeless (Demo)", "DemoTyre", 2450, 10, 24, 12),
    ("tyres-tubes", "Rear Tube 120/80-17 (Demo)", "DemoTyre", 520, 0, 6, 40),
    ("helmets", "Full-Face Helmet ISI (Demo)", "DemoRider", 3200, 15, 30, 18),
    ("helmets", "Open-Face Helmet (Demo)", "DemoRider", 1450, 5, 25, 22),
    ("gloves", "Leather Riding Gloves (Demo)", "DemoGear", 1899, 20, 40, 14),
    ("jackets", "Armoured Riding Jacket (Demo)", "DemoGear", 6990, 25, 12, 8),
    ("mirrors", "Bar-End Mirror Set (Demo)", "DemoParts", 1100, 0, 20, 25),
    ("indicators", "LED Indicator Pair (Demo)", "DemoParts", 780, 10, 50, 30),
    ("brake-pads", "Front Brake Pad Set (Demo)", "DemoParts", 640, 0, 60, 35),
    ("chains-sprockets", "Chain + Sprocket Kit (Demo)", "DemoDrive", 2350, 12, 18, 10),
    ("phone-holders", "Handlebar Phone Mount (Demo)", "DemoGear", 899, 30, 45, 20),
    ("seat-covers", "Waterproof Seat Cover (Demo)", "DemoGear", 749, 15, 35, 16),
    ("bike-covers", "All-Weather Bike Cover (Demo)", "DemoGear", 1299, 20, 22, 12),
    ("accessories", "USB Charger + Mount (Demo)", "DemoParts", 1399, 10, 28, 15),
]


def seed_products(db, cats: dict[str, ProductCategory]) -> None:
    seller = Seller(name="BIKER Demo Store", city="Bengaluru", is_verified=False, is_demonstration=True)
    db.add(seller)
    db.flush()

    products: list[Product] = []
    for i, (slug, name, brand, price, disc, stock, warranty) in enumerate(DEMO_PRODUCTS):
        p = Product(
            category_id=cats[slug].id,
            seller_id=seller.id,
            name=name,
            slug=f"{slug}-{i+1}-demo",
            description=(
                "Demonstration catalogue item. This is sample development data and "
                "not a real purchasable product. Replace with verified inventory."
            ),
            brand=brand,
            price=Decimal(price),
            discount_percent=disc,
            stock_qty=stock,
            warranty_months=warranty,
            compatibility_notes="Compatibility must be confirmed against explicit records.",
            rating_avg=None,
            rating_count=0,
            is_demonstration=True,
        )
        db.add(p)
        db.flush()
        for n in range(2):
            db.add(ProductImage(product_id=p.id, url=IMG.format(seed=f"{i}-{n}"), alt_text=name, sort_order=n))
        products.append(p)

    # Explicit compatibility records only for the demonstration catalogue bikes.
    compat_map = {
        "Commuter 150": ["tyres-tubes", "helmets", "gloves", "mirrors", "brake-pads", "chains-sprockets", "bike-covers"],
        "Street 250": ["tyres-tubes", "helmets", "gloves", "jackets", "indicators", "brake-pads", "phone-holders", "bike-covers"],
        "Cruiser 350": ["tyres-tubes", "helmets", "gloves", "jackets", "mirrors", "seat-covers", "bike-covers"],
    }
    slug_to_cat = {v.slug: v.id for v in cats.values()}
    for model, slugs in compat_map.items():
        allowed_ids = {slug_to_cat[s] for s in slugs}
        for p in products:
            if p.category_id in allowed_ids:
                db.add(MotorcycleProductCompatibility(
                    product_id=p.id,
                    manufacturer="BIKER Demo",
                    model=model,
                    notes="Demonstration compatibility record.",
                ))


def seed_catalogue(db) -> None:
    """Demonstration catalogue entries with clearly fictional identities.

    We intentionally do NOT attach real manufacturer names to invented specs.
    """
    entries = [
        {
            "model": "Commuter 150",
            "variant": "Std",
            "category": "commuter",
            "price": Decimal("89000"),
            "spec": {"engine_cc": 149, "max_power_ps": Decimal("12.5"), "max_power_rpm": 8000,
                     "max_torque_nm": Decimal("12.8"), "max_torque_rpm": 6000,
                     "transmission": "5-speed", "seat_height_mm": 790, "kerb_weight_kg": 128,
                     "mileage_kmpl": Decimal("55"), "mileage_context": "Demonstration estimate",
                     "colours": "Red, Blue, Black"},
        },
        {
            "model": "Street 250",
            "variant": "ABS",
            "category": "sport",
            "price": Decimal("189000"),
            "spec": {"engine_cc": 249, "max_power_ps": Decimal("27.0"), "max_power_rpm": 8500,
                     "max_torque_nm": Decimal("23.5"), "max_torque_rpm": 6500,
                     "transmission": "6-speed", "seat_height_mm": 810, "kerb_weight_kg": 158,
                     "mileage_kmpl": Decimal("38"), "mileage_context": "Demonstration estimate",
                     "colours": "Racing Red, Matte Black"},
        },
        {
            "model": "Cruiser 350",
            "variant": "Classic",
            "category": "cruiser",
            "price": Decimal("245000"),
            "spec": {"engine_cc": 349, "max_power_ps": Decimal("20.2"), "max_power_rpm": 6100,
                     "max_torque_nm": Decimal("27.0"), "max_torque_rpm": 4000,
                     "transmission": "5-speed", "seat_height_mm": 805, "kerb_weight_kg": 195,
                     "mileage_kmpl": Decimal("35"), "mileage_context": "Demonstration estimate",
                     "colours": "Gunmetal Grey, Deep Blue"},
        },
    ]
    for e in entries:
        cat = MotorcycleCatalogue(
            manufacturer="BIKER Demo",
            model=e["model"],
            variant=e["variant"],
            model_year=date.today().year,
            category=e["category"],
            fuel_type="petrol",
            ex_showroom_price=e["price"],
            currency="INR",
            image_url=IMG.format(seed=e["model"].replace(" ", "")),
            official_url=None,
            is_verified=False,
            is_demonstration=True,
            spec_source="Demonstration data — not verified",
            last_verified_date=None,
        )
        db.add(cat)
        db.flush()
        db.add(MotorcycleSpecification(catalogue_id=cat.id, **e["spec"]))
        # Registry entry with no real GLB -> viewer shows a labelled fallback.
        db.add(Motorcycle3DAsset(
            catalogue_id=cat.id,
            asset_url=None,
            format="procedural",
            fallback_image_url=cat.image_url,
            licence="Original procedural geometry (BIKER)",
            attribution="BIKER demonstration viewer",
            is_demonstration=True,
        ))


def seed_mechanics(db) -> None:
    shops = [
        ("Bengaluru", "Indiranagar", "Demo Moto Works", "100 Ft Road, Indiranagar", 12.9719, 77.6412,
         "Mon-Sat 9:00-19:00", "BIKER Demo", ["General Service", "Brake Service", "Chain Adjustment"]),
        ("Bengaluru", "Koramangala", "Demo Bike Care", "80 Ft Road, Koramangala", 12.9352, 77.6245,
         "Mon-Sat 10:00-20:00", "BIKER Demo", ["General Service", "Electrical", "Tyres"]),
        ("Mumbai", "Andheri", "Demo Motors Garage", "Link Road, Andheri West", 19.1197, 72.8464,
         "Tue-Sun 9:30-18:30", "BIKER Demo", ["Engine Repair", "General Service"]),
    ]
    for city, locality, name, address, lat, lon, hours, brands, services in shops:
        shop = MechanicShop(
            name=name, address=address, locality=locality, city=city,
            latitude=lat, longitude=lon, phone="+91 90000 00000",
            opening_hours=hours, brands_serviced=brands,
            is_verified=False, is_demonstration=True,
        )
        db.add(shop)
        db.flush()
        for s in services:
            db.add(MechanicService(shop_id=shop.id, name=s, description=None, estimated_price=None))


def seed_demo_user(db) -> None:
    user = User(
        email="demo@biker.app",
        phone="9000000000",
        password_hash=hash_password("Demo1234"),
    )
    user.profile = UserProfile(display_name="Demo Rider", city="Bengaluru")
    user.cart = Cart()
    db.add(user)


def main() -> None:
    reset()
    db = SessionLocal()
    try:
        cats = seed_categories(db)
        db.flush()
        seed_products(db, cats)
        seed_catalogue(db)
        seed_mechanics(db)
        seed_demo_user(db)
        db.commit()
        print("Seed complete:")
        print("  categories:", len(cats))
        print("  products:", len(DEMO_PRODUCTS))
        print("  catalogue entries: 3 (demonstration)")
        print("  mechanics: 3 (demonstration)")
        print("  demo user: demo@biker.app / Demo1234")
    finally:
        db.close()


if __name__ == "__main__":
    main()
