from fastapi import FastAPI

app = FastAPI(title="GridLock")

@app.get("/health")
def health():
    return {"status": "ok"}