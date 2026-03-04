"""DAG: Tune, train, validate, and register the forecasting model.

Runs after feature engineering completes.
"""

from datetime import datetime, timedelta

from airflow.sdk import dag, task
from dag_feature_engineering import FEATURES_READY


@dag(
    dag_id="model_training",
    description="Tune, train, validate, evaluate, and register the home value model",
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
    def tune() -> dict:
        """Run Bayesian hyperparameter tuning with Optuna."""
        import pandas as pd

        from pricepoint.config.settings import get_settings
        from pricepoint.db.engine import SessionLocal
        from pricepoint.features.store import load_feature_matrix

        settings = get_settings()

        if not settings.tuning_enabled:
            return {"best_params": None, "skipped": True}

        db = SessionLocal()
        try:
            features: pd.DataFrame = load_feature_matrix(db)
        finally:
            db.close()

        from pricepoint.models.tuning import tune_hyperparameters

        result = tune_hyperparameters(
            features=features,
            n_trials=settings.tuning_n_trials,
            timeout=settings.tuning_timeout_seconds,
            n_cv_folds=settings.tuning_cv_folds,
            early_stopping_rounds=settings.tuning_early_stopping_rounds,
            log_to_mlflow=True,
        )

        return {
            "best_params": result.best_params,
            "best_score": result.best_score,
            "n_trials": result.n_trials,
            "skipped": False,
        }

    @task()
    def train(tune_output: dict) -> dict:
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

        best_params = tune_output.get("best_params")
        model = train_model(features=features, params=best_params)
        model_bytes = pickle.dumps(model)

        # Build a small input example for MLflow signature inference
        target_col = "sold_price"
        feature_cols = [c for c in features.columns if c != target_col]
        sample_df = features[feature_cols].head(3).copy()
        # Fill NaN: "unknown" for categoricals, 0 for numerics
        for col in sample_df.columns:
            if sample_df[col].dtype.name == "category":
                sample_df[col] = sample_df[col].cat.add_categories("unknown").fillna("unknown")
            else:
                sample_df[col] = sample_df[col].fillna(0)
        input_sample = sample_df.to_dict(orient="list")

        return {
            "model_pickle_hex": model_bytes.hex(),
            "feature_columns": feature_cols,
            "input_example": input_sample,
            "n_samples": len(features),
        }

    @task()
    def validate(train_output: dict, tune_output: dict) -> dict:
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

        best_params = tune_output.get("best_params")
        cv_metrics = cross_validate(features=features, params=best_params)

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
            # Replace NaN with None for JSON serialization (XCom)
            result["_x_test_values"] = x_test.fillna(0.0).values.tolist()
            result["_x_test_columns"] = list(x_test.columns)

        return result

    @task()
    def register_model(
        validate_output: dict,
        evaluate_output: dict,
        train_output: dict,
        tune_output: dict,
    ) -> str:
        """Log model and metrics to MLflow."""
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

        # Add tuning metrics if available
        if not tune_output.get("skipped"):
            if tune_output.get("best_score") is not None:
                metrics["tuning_best_mae"] = tune_output["best_score"]
            if tune_output.get("n_trials") is not None:
                metrics["tuning_n_trials"] = tune_output["n_trials"]

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

    @task()
    def promote(run_id: str) -> dict:
        """Compare new model against champion and promote if better."""
        from pricepoint.config.settings import get_settings
        from pricepoint.models.registry import compare_and_promote

        settings = get_settings()
        return compare_and_promote(
            run_id=run_id,
            primary_metric=settings.model_primary_metric,
            auto_promote=settings.model_auto_promote,
        )

    tune_step = tune()
    train_step = train(tune_step)
    validate_step = validate(train_step, tune_step)
    evaluate_step = evaluate(train_step)
    register_step = register_model(validate_step, evaluate_step, train_step, tune_step)
    promote_step = promote(register_step)

    tune_step >> train_step >> [validate_step, evaluate_step] >> register_step >> promote_step


model_training()
