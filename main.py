from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api.routes import products, cart, promotions

app = FastAPI(title="Cart Management API", version="1.0.0")

app.include_router(products.router)
app.include_router(cart.router)
app.include_router(promotions.router)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", include_in_schema=False)
def serve_ui():
    return FileResponse("static/index.html")
