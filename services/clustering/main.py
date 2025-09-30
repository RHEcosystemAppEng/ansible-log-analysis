from fastapi import FastAPI
from pydantic import BaseModel
import joblib
import numpy as np
import os
from model_loader import load_from_minio
from sklearn.base import BaseEstimator

app = FastAPI()
# TODO change it for cluster deployment to be model registry.
if os.getenv("MINIO_BUCKET_NAME"):
    model: BaseEstimator = load_from_minio(
        os.getenv("MINIO_BUCKET_NAME"), "clustering_model.joblib"
    )
else:
    model = joblib.load("clustering_model.joblib")


class InputData(BaseModel):
    embeddings: list[float]  # Adjust based on your model's input shape


@app.get("/health")
def health_check():
    """Health check endpoint for Kubernetes liveness and readiness probes"""
    return {"status": "healthy"}


@app.post("/cluster")
def predict(data: InputData):
    input_array = np.array(data.embeddings)
    prediction = model.predict(input_array)
    return {"labels": prediction.tolist()}


def main():
    import uvicorn

    # Run with: python -m uvicorn main:app --reload
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)


if __name__ == "__main__":
    main()
