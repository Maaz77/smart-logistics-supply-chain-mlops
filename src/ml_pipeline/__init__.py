"""
Machine Learning Pipeline Module for Smart Logistics Supply Chain.

This module contains all pipeline components:
- ingest: Data ingestion from Kaggle
- preprocess: Feature engineering and data splitting
- train: Model training and MLflow registration
- common: Shared utilities
"""

from src.ml_pipeline.ingest import run_ingestion
from src.ml_pipeline.preprocess import run_preprocessing
from src.ml_pipeline.train import run_training

__all__ = ["run_ingestion", "run_preprocessing", "run_training"]
