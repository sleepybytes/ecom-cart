from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.core.dependencies import get_db
from app.models.product import Product
from app.models.promotion import Promotion
from main import app

# Single in-memory DB shared across all connections in a test run
ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=ENGINE)


def utc_dt(**delta) -> datetime:
    """Return UTC datetime offset from now by the given timedelta kwargs."""
    return datetime.now(timezone.utc) + timedelta(**delta)


# ── DB lifecycle ──────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_db():
    """Recreate all tables before every test, tear down after."""
    Base.metadata.create_all(ENGINE)
    yield
    Base.metadata.drop_all(ENGINE)


@pytest.fixture
def db():
    session = TestingSession()
    yield session
    session.close()


# ── FastAPI test client ───────────────────────────────────────────────────────

@pytest.fixture
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── Seed helpers ──────────────────────────────────────────────────────────────

@pytest.fixture
def products(db):
    items = [
        Product(id="p1",  name="Organic Banana",  price=0.79,  inventory=120, category="produce"),
        Product(id="p2",  name="Whole Milk",       price=4.99,  inventory=50,  category="dairy"),
        Product(id="p3",  name="Brown Eggs",       price=6.49,  inventory=35,  category="dairy"),
        Product(id="p5",  name="Chicken Breast",   price=12.99, inventory=40,  category="meat"),
        Product(id="p7",  name="Frozen Pizza",     price=8.99,  inventory=5,   category="frozen"),
        Product(id="p10", name="Coffee Beans",     price=15.99, inventory=28,  category="pantry"),
        Product(id="p11", name="Pasta",            price=2.99,  inventory=90,  category="pantry"),
    ]
    db.add_all(items)
    db.commit()
    return {p.id: p for p in items}


@pytest.fixture
def promotions(db):
    promos = [
        Promotion(
            id="promo_pct",
            description="20% Off Dairy",
            type="PERCENTAGE",
            value=20,
            start_date=utc_dt(days=-10),
            end_date=utc_dt(days=30),
            applicable_product_ids=["p2", "p3"],
        ),
        Promotion(
            id="promo_fixed",
            description="$2 Off Frozen",
            type="FIXED",
            value=2,
            start_date=utc_dt(days=-5),
            end_date=utc_dt(days=30),
            applicable_product_ids=["p7"],
        ),
        Promotion(
            id="promo_expired",
            description="Expired 50% Off",
            type="PERCENTAGE",
            value=50,
            start_date=utc_dt(days=-60),
            end_date=utc_dt(days=-10),
            applicable_product_ids=["p2"],
        ),
        Promotion(
            id="promo_future",
            description="Future 30% Off",
            type="PERCENTAGE",
            value=30,
            start_date=utc_dt(days=10),
            end_date=utc_dt(days=40),
            applicable_product_ids=["p2"],
        ),
        Promotion(
            id="promo_pantry",
            description="10% Off Pantry",
            type="PERCENTAGE",
            value=10,
            start_date=utc_dt(days=-5),
            end_date=utc_dt(days=30),
            applicable_product_ids=["p10", "p11"],
        ),
    ]
    db.add_all(promos)
    db.commit()
    return {p.id: p for p in promos}
