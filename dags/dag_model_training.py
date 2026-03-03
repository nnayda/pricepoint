"""DAG: Train, validate, and register the forecasting model.

Runs after feature engineering completes.
"""

from datetime import datetime, timedelta

from airflow.sdk import dag, task
from dag_feature_engineering import FEATURES_READY


@dag(
    dag_id="model_training",
    description="Train, validate, evaluate, and register the home value model",
    schedule=(FEATURES_READY,),
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
    },
    tags=["model", "training"],
)
def model_training():

    @task()
    def train() -> dict:
        """Train the forecasting model."""
        import pickle

        import pandas as pd

        from pricepoint.db.engine import SessionLocal
        from pricepoint.features.store import load_feature_matrix
        from pricepoint.models.training import train_model

        db = SessionLocal()
        try:
            features: pd.DataFrame = load_feature_matrix(db)
        finally:
            db.close()

        model = train_model(features=features)
        model_bytes = pickle.dumps(model)

        # Build a small input example for MLflow signature inference
        target_col = "sold_price"
        feature_cols = [c for c in features.columns if c != target_col]
        input_sample = features[feature_cols].head(3).fillna(0).to_dict(orient="list")

        return {
            "model_pickle_hex": model_bytes.hex(),
            "feature_columns": feature_cols,
            "input_example": input_sample,
            "n_samples": len(features),
        }

    @task()
    def validate(train_output: dict) -> dict:
        """Run cross-validation on the trained model."""
        import pandas as pd

        from pricepoint.db.engine import SessionLocal
        from pricepoint.features.store import load_feature_matrix
        from pricepoint.models.validation import cross_validate

        db = SessionLocal()
        try:
            features: pd.DataFrame = load_feature_matrix(db)
        finally:
            db.close()

        cv_metrics = cross_validate(features=features)

        return {
            "cv_metrics": cv_metrics,
            "model_pickle_hex": train_output["model_pickle_hex"],
        }

    @task()
    def evaluate(train_output: dict) -> dict:
        """Evaluate the model on held-out test data."""
        import pickle

        import pandas as pd

        from pricepoint.db.engine import SessionLocal
        from pricepoint.features.store import load_feature_matrix
        from pricepoint.models.evaluation import evaluate_model

        db = SessionLocal()
        try:
            features: pd.DataFrame = load_feature_matrix(db)
        finally:
            db.close()

        model = pickle.loads(bytes.fromhex(train_output["model_pickle_hex"]))  # noqa: S301
        eval_metrics = evaluate_model(model=model, test_features=features)

        # Extract arrays for downstream plot generation (not JSON-serializable as-is)
        y_true = eval_metrics.pop("_y_true", None)
        y_pred = eval_metrics.pop("_y_pred", None)
        x_test = eval_metrics.pop("_x_test", None)

        result: dict = {
            "eval_metrics": eval_metrics,
            "model_pickle_hex": train_output["model_pickle_hex"],
        }

        if y_true is not None:
            result["_y_true"] = y_true.tolist()
        if y_pred is not None:
            result["_y_pred"] = y_pred.tolist()
        if x_test is not None:
            result["_x_test_values"] = x_test.values.tolist()
            result["_x_test_columns"] = list(x_test.columns)

        return result

    @task()
    def register_model(validate_output: dict, evaluate_output: dict, train_output: dict) -> str:
        """Log model and metrics to MLflow; promote if improved."""
        import pickle

        import numpy as np
        import pandas as pd

        from pricepoint.models.registry import log_model

        model = pickle.loads(  # noqa: S301
            bytes.fromhex(validate_output["model_pickle_hex"])
        )
        metrics: dict = {
            **validate_output.get("cv_metrics", {}),
            **evaluate_output.get("eval_metrics", {}),
        }

        # Reconstruct prediction arrays for plot generation
        if "_y_true" in evaluate_output:
            metrics["_y_true"] = np.array(evaluate_output["_y_true"], dtype=np.float64)
        if "_y_pred" in evaluate_output:
            metrics["_y_pred"] = np.array(evaluate_output["_y_pred"], dtype=np.float64)
        if "_x_test_values" in evaluate_output and "_x_test_columns" in evaluate_output:
            metrics["_x_test"] = pd.DataFrame(
                evaluate_output["_x_test_values"],
                columns=evaluate_output["_x_test_columns"],
            )

        input_example = pd.DataFrame(train_output.get("input_example", {}))

        run_id = log_model(
            model=model,
            metrics=metrics,
            run_name="daily_training",
            input_example=input_example,
        )
        return run_id

    train_step = train()
    validate_step = validate(train_step)
    evaluate_step = evaluate(train_step)
    register_step = register_model(validate_step, evaluate_step, train_step)

    train_step >> [validate_step, evaluate_step] >> register_step


model_training()
