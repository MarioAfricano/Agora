from fastapi import FastAPI

app = FastAPI(title="Agora")


@app.get("/health")
async def health():
    return {"status": "ok"}