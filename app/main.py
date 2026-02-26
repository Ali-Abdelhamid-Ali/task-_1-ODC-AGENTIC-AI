from fastapi import FastAPI

# from app.db.init_db import init_db
from app.api.routes.chat import router as chat_router
from scalar_fastapi import get_scalar_api_reference

app = FastAPI()


@app.on_event("startup")
def startup():
    # init_db()
    pass

@app.get("/test_api")
def test_api():
    return {"message": "hello ENG.Hady!! :)"}


app.include_router(chat_router)


@app.get("/scalar", include_in_schema=False)
def scalar_docs():
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title=app.title,
    )
