import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict

app = FastAPI(title="Futuristic Corp MVP API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----- Pydantic Models (MVP) -----
class Section(BaseModel):
    type: str
    data: Dict[str, Any] = {}
    position: int = 0
    is_visible: bool = True

class Page(BaseModel):
    title: str
    slug: str
    status: str = "published"
    locale: str = "en"
    sections: List[Section] = []

class Product(BaseModel):
    name: str
    slug: str
    sku: Optional[str] = None
    short_desc: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = "USD"
    specs: Dict[str, Any] = {}
    category: Optional[str] = None
    model_3d_url: Optional[str] = None
    images: List[str] = []

class Lead(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None
    message: Optional[str] = None
    product_slug: Optional[str] = None
    source: Optional[str] = "website"

# ----- Utilities -----

def _db_available():
    try:
        from database import db
        return db is not None
    except Exception:
        return False


def _get_db():
    from database import db
    return db


# ----- Root & Health -----
@app.get("/")
def read_root():
    return {"message": "Futuristic Corp MVP API running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        from database import db
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else ("✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set")
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
                response["connection_status"] = "Connected"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except ImportError:
        response["database"] = "❌ Database module not found"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


# ----- Schema Introspection (for admin tooling) -----
@app.get("/schema")
def get_schema_overview():
    return {
        "entities": [
            {
                "name": "page",
                "fields": list(Page.model_fields.keys())
            },
            {
                "name": "section",
                "fields": list(Section.model_fields.keys())
            },
            {
                "name": "product",
                "fields": list(Product.model_fields.keys())
            },
            {
                "name": "lead",
                "fields": list(Lead.model_fields.keys())
            },
        ]
    }


# ----- CMS-like endpoints -----

def default_homepage() -> Page:
    hero = Section(
        type="hero_spline",
        position=0,
        data={
            "headline": "Engineered Excellence. Delivered Globally.",
            "subheadline": "A premium, cinematic 3D experience for a global technology group.",
            "cta": {"label": "Explore Verticals", "href": "#verticals"},
            "splineUrl": "https://prod.spline.design/EF7JOSsHLk16Tlw9/scene.splinecode"
        }
    )
    verticals = Section(
        type="feature_grid",
        position=1,
        data={
            "id": "verticals",
            "title": "Business Verticals",
            "items": [
                {"title": "Payment Devices", "subtitle": "POS, Tap & Pay, QR", "icon": "CreditCard"},
                {"title": "Smart Home & IoT", "subtitle": "AI cameras, locks, sensors", "icon": "Cpu"},
                {"title": "Mobile Accessories", "subtitle": "GaN chargers, power banks", "icon": "BatteryCharging"},
                {"title": "R&D & Manufacturing", "subtitle": "Vertically integrated", "icon": "Factory"}
            ]
        }
    )
    return Page(title="Home", slug="home", sections=[hero, verticals])


@app.get("/api/pages/{slug}")
def get_page(slug: str):
    if _db_available():
        try:
            db = _get_db()
            doc = db["page"].find_one({"slug": slug})
            if doc:
                # Convert to Page-like dict
                doc["sections"] = [Section(**s).model_dump() if isinstance(s, dict) else s for s in doc.get("sections", [])]
                return doc
        except Exception:
            pass
    # Fallback default
    if slug == "home":
        return default_homepage().model_dump()
    raise HTTPException(status_code=404, detail="Page not found")


# ----- Products -----

def _default_products() -> List[Product]:
    return [
        Product(name="POS Pro X", slug="pos-pro-x", sku="POS-PRO-X", short_desc="Rugged POS with NFC & printer", price=399, category="payment", images=["/images/pos-pro-x.jpg"]).model_dump(),
        Product(name="GaN Charger 30W", slug="gan-30w", sku="GAN-30W", short_desc="Ultra-compact fast charger", price=29, category="accessories", images=["/images/gan-30w.jpg"]).model_dump(),
        Product(name="AI Camera S1", slug="ai-cam-s1", sku="AI-CAM-S1", short_desc="Smart AI security camera", price=99, category="smarthome", images=["/images/ai-cam-s1.jpg"]).model_dump(),
    ]


@app.get("/api/products")
def list_products():
    if _db_available():
        try:
            db = _get_db()
            items = list(db["product"].find({}, {"_id": 0}))
            if items:
                return {"items": items}
        except Exception:
            pass
    return {"items": _default_products()}


@app.get("/api/products/{slug}")
def get_product(slug: str):
    if _db_available():
        try:
            db = _get_db()
            item = db["product"].find_one({"slug": slug}, {"_id": 0})
            if item:
                return item
        except Exception:
            pass
    for p in _default_products():
        if p["slug"] == slug:
            return p
    raise HTTPException(status_code=404, detail="Product not found")


# ----- Menus -----
@app.get("/api/menus/main")
def get_main_menu():
    items = [
        {"label": "Home", "href": "/"},
        {"label": "About", "href": "/about"},
        {"label": "Business Verticals", "href": "/business-verticals"},
        {"label": "Products", "href": "/products"},
        {"label": "Leadership", "href": "/leadership"},
        {"label": "Contact", "href": "/contact"},
    ]
    return {"items": items}


# ----- Leads (CRM) -----
@app.post("/api/leads")
def create_lead(lead: Lead):
    payload = lead.model_dump()
    if _db_available():
        try:
            from database import create_document
            create_document("lead", payload)
        except Exception:
            pass
    # Respond success regardless, MVP
    return {"status": "ok", "message": "Lead received", "lead": payload}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
