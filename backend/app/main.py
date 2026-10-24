"""FastAPI app: routes and error handlers only. Business logic lives in other modules."""

from fastapi import FastAPI

app = FastAPI(
    title="Redline Review API",
    description="Propose, preview, and apply contract edits, and search across documents.",
)


@app.get("/health")
def health():
    # Lets the frontend (and humans) check that the API is up.
    return {"status": "ok"}
