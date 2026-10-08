"""Evaluate model suitability before saving the selected buyer-pattern models."""

from scripts.model_evaluation import run
from threadpoolctl import threadpool_limits

if __name__ == "__main__":
    with threadpool_limits(limits=4):
        run()
