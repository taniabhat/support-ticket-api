from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import Base, engine
from app.routers import queues, tickets, resolve


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Support Ticket API", lifespan=lifespan)

app.include_router(queues.router)
app.include_router(tickets.router)
app.include_router(resolve.router)


@app.get("/health")
def health():
    return {"status": "ok"}
