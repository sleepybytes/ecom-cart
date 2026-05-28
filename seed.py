from datetime import datetime, timezone
from app.core.database import SessionLocal
from app.models.product import Product
from app.models.promotion import Promotion


def utc(year, month, day, hour=0, minute=0, second=0):
    return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)


PRODUCTS = [
    Product(id="p1",  name="Organic Banana",   price=0.79,  inventory=120, category="produce"),
    Product(id="p2",  name="Whole Milk",        price=4.99,  inventory=50,  category="dairy"),
    Product(id="p3",  name="Brown Eggs",        price=6.49,  inventory=35,  category="dairy"),
    Product(id="p4",  name="Greek Yogurt",      price=5.99,  inventory=25,  category="dairy"),
    Product(id="p5",  name="Chicken Breast",    price=12.99, inventory=40,  category="meat"),
    Product(id="p6",  name="Salmon Fillet",     price=18.99, inventory=18,  category="seafood"),
    Product(id="p7",  name="Frozen Pizza",      price=8.99,  inventory=60,  category="frozen"),
    Product(id="p8",  name="Orange Juice",      price=5.49,  inventory=22,  category="beverages"),
    Product(id="p9",  name="Sparkling Water",   price=7.99,  inventory=80,  category="beverages"),
    Product(id="p10", name="Coffee Beans",      price=15.99, inventory=28,  category="pantry"),
    Product(id="p11", name="Pasta",             price=2.99,  inventory=90,  category="pantry"),
    Product(id="p12", name="Tomato Sauce",      price=3.49,  inventory=75,  category="pantry"),
    Product(id="p13", name="Avocado",           price=1.99,  inventory=55,  category="produce"),
    Product(id="p14", name="Blueberries",       price=4.49,  inventory=30,  category="produce"),
    Product(id="p15", name="Ice Cream",         price=6.99,  inventory=20,  category="frozen"),
    Product(id="p16", name="Ground Beef",       price=10.99, inventory=26,  category="meat"),
    Product(id="p17", name="Cheddar Cheese",    price=7.49,  inventory=32,  category="dairy"),
    Product(id="p18", name="Protein Bar",       price=2.49,  inventory=100, category="snacks"),
    Product(id="p19", name="Potato Chips",      price=4.99,  inventory=70,  category="snacks"),
    Product(id="p20", name="Almond Butter",     price=11.99, inventory=24,  category="pantry"),
]

PROMOTIONS = [
    Promotion(
        id="promo_1",
        description="20% Off Dairy",
        type="PERCENTAGE",
        value=20,
        start_date=utc(2026, 5, 20),
        end_date=utc(2026, 5, 28, 23, 59, 59),
        applicable_product_ids=["p2", "p3"],
    ),
    Promotion(
        id="promo_2",
        description="$2 Off Frozen",
        type="FIXED",
        value=2,
        start_date=utc(2026, 5, 18),
        end_date=utc(2026, 5, 24, 23, 59, 59),
        applicable_product_ids=["p7", "p15"],
    ),
    Promotion(
        id="promo_3",
        description="10% Off Pantry",
        type="PERCENTAGE",
        value=10,
        start_date=utc(2026, 5, 21),
        end_date=utc(2026, 6, 1, 23, 59, 59),
        applicable_product_ids=["p10", "p11"],
    ),
    Promotion(
        id="promo_4",
        description="Buy More Save More",
        type="PERCENTAGE",
        value=15,
        start_date=utc(2026, 5, 15),
        end_date=utc(2026, 5, 30, 23, 59, 59),
        applicable_product_ids=["p5", "p16"],
    ),
    Promotion(
        id="promo_5",
        description="Weekend Produce Sale",
        type="PERCENTAGE",
        value=25,
        start_date=utc(2026, 5, 23),
        end_date=utc(2026, 5, 26, 23, 59, 59),
        applicable_product_ids=["p1", "p14"],
    ),
]


def seed():
    db = SessionLocal()
    try:
        for product in PRODUCTS:
            existing = db.get(Product, product.id)
            if not existing:
                db.add(product)

        for promo in PROMOTIONS:
            existing = db.get(Promotion, promo.id)
            if not existing:
                db.add(promo)

        db.commit()
        print(f"Seeded {len(PRODUCTS)} products and {len(PROMOTIONS)} promotions.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
