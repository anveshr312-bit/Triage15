"""Suggestions are read-only: this router never creates doubts or allocations."""
from fastapi import APIRouter
from pydantic import Field
from .schemas import Input
from ml.predictor import predictor

router = APIRouter(prefix='/api/ml', tags=['Optional skill suggestions'])


class PredictionInput(Input):
    title: str = Field(min_length=3, max_length=150)
    description: str = Field(min_length=5, max_length=3000)


@router.post('/predict-tags')
def predict_tags(body: PredictionInput):
    return predictor.predict(body.title, body.description)


@router.get('/status')
def status():
    return predictor.status()


@router.get('/metrics')
def measured_metrics():
    return predictor.reports()


@router.get('/model-info')
def model_info():
    status = predictor.status()
    return {**status, 'metadata': predictor.metadata if status['available'] else None}
