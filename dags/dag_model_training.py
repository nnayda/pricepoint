"""DAG: Tune, train, validate, and register the forecasting model.

Runs after feature engineering completes.
"""

from datetime import UTC, datetime, timedelta

from airflow.sdk import Asset, dag, task


@dag(
    dag_id="model_training",
    description="Tune, train, validate, evaluate, and register the home value model",
    schedule=None,
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
            optimization_metric=settings.model_primary_metric,
        )

        return {
            "best_params": result.best_params,
            "best_score": result.best_score,
            "n_trials": result.n_trials,
            "skipped": False,
        }

    @task()
    def load_training_matrix() -> dict:
        """Load the expanded multi-sale training matrix from S3.

        Falls back to the single-record feature store if the parquet
        file does not exist (e.g. first run before feature engineering
        produces the training matrix).
        """
        import io
        import logging

        import boto3
        import pandas as pd
        from botocore.exceptions import ClientError

        from pricepoint.config.settings import get_settings

        log = logging.getLogger(__name__)
        settings = get_settings()

        key = "training/feature_matrix.parquet"
        try:
            s3 = boto3.client(
                "s3",
                endpoint_url=settings.s3_endpoint_url,
                aws_access_key_id=settings.s3_access_key,
                aws_secret_access_key=settings.s3_secret_key,
            )
            obj = s3.get_object(Bucket=settings.s3_bucket, Key=key)
            buf = io.BytesIO(obj["Body"].read())
            df = pd.read_parquet(buf, engine="pyarrow")

            n_properties = df["property_id"].nunique() if "property_id" in df.columns else len(df)
            expansion = len(df) / n_properties if n_properties > 0 else 1.0
            log.info(
                "Loaded training matrix from S3: %d rows, %d properties (%.1fx expansion)",
                len(df),
                n_properties,
                expansion,
            )
            return {
                "source": "s3",
                "n_rows": len(df),
                "n_properties": n_properties,
                "expansion_ratio": expansion,
            }
        except ClientError:
            log.warning("Training matrix not found in S3; will use feature store")
            return {
                "source": "feature_store",
                "n_rows": 0,
                "n_properties": 0,
                "expansion_ratio": 1.0,
            }

    @task()
    def train(tune_output: dict, matrix_info: dict) -> dict:
        """Train the forecasting model on the expanded training matrix."""
        import io
        import pickle

        import boto3
        import pandas as pd
        from botocore.exceptions import ClientError

        from pricepoint.config.settings import get_settings
        from pricepoint.db.engine import SessionLocal
        from pricepoint.features.store import load_feature_matrix
        from pricepoint.models.training import train_model

        settings = get_settings()

        # Load features from S3 training matrix or fall back to feature store
        if matrix_info.get("source") == "s3":
            s3 = boto3.client(
                "s3",
                endpoint_url=settings.s3_endpoint_url,
                aws_access_key_id=settings.s3_access_key,
                aws_secret_access_key=settings.s3_secret_key,
            )
            key = "training/feature_matrix.parquet"
            try:
                obj = s3.get_object(Bucket=settings.s3_bucket, Key=key)
                buf = io.BytesIO(obj["Body"].read())
                features: pd.DataFrame = pd.read_parquet(buf, engine="pyarrow")

                # Restore categorical dtypes
                from pricepoint.features.housing import CATEGORICAL_COLUMNS

                for col in CATEGORICAL_COLUMNS:
                    if col in features.columns:
                        features[col] = features[col].astype("category")
            except ClientError:
                # Fallback to feature store
                db = SessionLocal()
                try:
                    features = load_feature_matrix(db)
                finally:
                    db.close()
        else:
            db = SessionLocal()
            try:
                features = load_feature_matrix(db)
            finally:
                db.close()

        best_params = tune_output.get("best_params")
        model, test_indices = train_model(features=features, params=best_params)
        model_bytes = pickle.dumps(model)

        # Build a small input example for MLflow signature inference
        target_col = "sold_price"
        from pricepoint.models.training import TRAINING_METADATA_COLUMNS

        feature_cols = [
            c for c in features.columns if c != target_col and c not in TRAINING_METADATA_COLUMNS
        ]
        sample_df = features[feature_cols].head(3).copy()
        # Fill NaN: "unknown" for categoricals, 0 for numerics
        for col in sample_df.columns:
            if sample_df[col].dtype.name == "category":
                sample_df[col] = sample_df[col].cat.add_categories("unknown").fillna("unknown")
            else:
                sample_df[col] = sample_df[col].fillna(0)
        input_sample = sample_df.to_dict(orient="list")

        # Compute EDA metrics on cleaned training data
        from pricepoint.models.eda import compute_eda_metrics
        from pricepoint.models.selection import select_features
        from pricepoint.models.training import prepare_features

        x, y = prepare_features(features, target_col, log_transform_target=True)
        x = select_features(x)
        eda_metrics = compute_eda_metrics(x, y, log_transformed=True)

        return {
            "model_pickle_hex": model_bytes.hex(),
            "feature_columns": feature_cols,
            "input_example": input_sample,
            "n_samples": len(features),
            "n_properties": matrix_info.get("n_properties", len(features)),
            "expansion_ratio": matrix_info.get("expansion_ratio", 1.0),
            "training_source": matrix_info.get("source", "feature_store"),
            "test_indices": test_indices,
            "eda_metrics": eda_metrics,
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

        # Temporal CV as a diagnostic sanity check
        temporal_metrics = cross_validate(features=features, params=best_params, temporal=True)
        for k, v in temporal_metrics.items():
            cv_metrics[f"temporal_{k}"] = v

        return {
            "cv_metrics": cv_metrics,
            "model_pickle_hex": train_output["model_pickle_hex"],
        }

    @task()
    def evaluate(train_output: dict) -> dict:
        """Evaluate the model on held-out test data only."""
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

        # Filter to test-set rows only to avoid evaluating on training data
        test_indices = train_output.get("test_indices")
        if test_indices:
            valid = features.index.isin(test_indices)
            features = features.loc[valid]

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
            # Convert categoricals to their codes before fillna (avoids
            # "Cannot setitem on a Categorical with a new category" error)
            x_serializable = x_test.copy()
            for col in x_serializable.select_dtypes(include=["category"]).columns:
                x_serializable[col] = x_serializable[col].cat.codes
            result["_x_test_values"] = x_serializable.fillna(0.0).values.tolist()
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

        # Merge EDA metrics (data.* prefix prevents collisions)
        metrics.update(train_output.get("eda_metrics", {}))

        # Add tuning metrics if available
        if not tune_output.get("skipped"):
            if tune_output.get("best_score") is not None:
                metrics["tuning_best_mae"] = tune_output["best_score"]
            if tune_output.get("n_trials") is not None:
                metrics["tuning_n_trials"] = tune_output["n_trials"]

        # Log multi-sale training expansion metrics
        if train_output.get("expansion_ratio") is not None:
            metrics["training_expansion_ratio"] = train_output["expansion_ratio"]
        if train_output.get("n_properties") is not None:
            metrics["training_n_properties"] = train_output["n_properties"]
        if train_output.get("training_source"):
            metrics["training_source"] = train_output["training_source"]

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

        # Restore category dtype lost during XCom serialization so XGBoost
        # and MLflow signature inference see the same types used in training.
        from pricepoint.features.housing import CATEGORICAL_COLUMNS

        for col in CATEGORICAL_COLUMNS:
            if col in input_example.columns:
                input_example[col] = input_example[col].astype("category")

        # Reconstruct cleaned feature matrix for EDA plot generation
        eda_data = None
        try:
            from pricepoint.db.engine import SessionLocal
            from pricepoint.features.store import load_feature_matrix
            from pricepoint.models.selection import select_features
            from pricepoint.models.training import prepare_features

            db = SessionLocal()
            try:
                features: pd.DataFrame = load_feature_matrix(db)
            finally:
                db.close()
            x, y = prepare_features(features, "sold_price", log_transform_target=True)
            x = select_features(x)
            eda_data = (x, y)
        except Exception:
            import logging

            logging.getLogger(__name__).warning("Failed to load EDA data for plots", exc_info=True)

        run_id = log_model(
            model=model,
            metrics=metrics,
            run_name="daily_training",
            input_example=input_example,
            eda_data=eda_data,
        )
        return run_id

    @task()
    def promote(mlflow_run_id: str) -> dict:
        """Compare new model against champion and promote if better."""
        from pricepoint.config.settings import get_settings
        from pricepoint.models.registry import compare_and_promote

        settings = get_settings()
        return compare_and_promote(
            run_id=mlflow_run_id,
            primary_metric=settings.model_primary_metric,
            auto_promote=settings.model_auto_promote,
        )

    @task(outlets=[Asset("trained_model")])
    def notify_and_trigger(comparison: dict) -> dict:
        """Send ntfy notification and trigger batch scoring if promoted."""
        import json
        import logging
        import urllib.request

        from common.task_helpers import send_ntfy_notification

        from pricepoint.config.settings import get_settings

        log = logging.getLogger(__name__)
        settings = get_settings()

        promoted = comparison.get("promoted", False)
        reason = comparison.get("reason", "")
        metric = comparison.get("metric", "")
        new_value = comparison.get("new_value")
        old_value = comparison.get("old_value")

        # --- Trigger batch scoring if a new champion was promoted --------
        triggered = False
        if promoted:
            try:
                base = settings.airflow_base_url

                # Airflow 3 uses JWT auth — obtain token first
                token_url = f"{base}/auth/token"
                token_payload = json.dumps(
                    {
                        "username": settings.airflow_username,
                        "password": settings.airflow_password,
                    }
                ).encode()
                token_req = urllib.request.Request(
                    token_url,
                    data=token_payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(token_req, timeout=30) as token_resp:  # noqa: S310
                    token_data = json.loads(token_resp.read().decode())
                access_token = token_data["access_token"]

                # Trigger the DAG run
                url = f"{base}/api/v2/dags/batch_scoring/dagRuns"
                payload = json.dumps(
                    {
                        "logical_date": datetime.now(UTC).isoformat(),
                        "conf": {"trigger_reason": f"Auto-triggered: {reason}"},
                    }
                ).encode()
                req = urllib.request.Request(
                    url,
                    data=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {access_token}",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
                    log.info("Triggered batch_scoring DAG (%s)", resp.status)
                    triggered = True
            except Exception:
                log.exception("Failed to trigger batch_scoring DAG")

        # --- Send ntfy notification -------------------------------------
        if settings.ntfy_enabled and settings.ntfy_topic:
            status_emoji = "white_check_mark" if promoted else "information_source"
            title = "New champion promoted" if promoted else "Model training complete"
            lines = [reason]
            if metric and new_value is not None:
                line = f"{metric}: {new_value:.4f}"
                if old_value is not None:
                    line += f" (prev: {old_value:.4f})"
                lines.append(line)
            if promoted and triggered:
                lines.append("Batch scoring triggered.")

            send_ntfy_notification(
                topic=settings.ntfy_topic,
                title=title,
                message="\n".join(lines),
                server_url=settings.ntfy_server_url,
                priority="high" if promoted else "default",
                tags=[status_emoji, "robot"],
            )

        return {
            "promoted": promoted,
            "triggered": triggered,
            "reason": reason,
        }

    tune_step = tune()
    matrix_step = load_training_matrix()
    train_step = train(tune_step, matrix_step)
    validate_step = validate(train_step, tune_step)
    evaluate_step = evaluate(train_step)
    register_step = register_model(validate_step, evaluate_step, train_step, tune_step)
    promote_step = promote(register_step)
    notify_step = notify_and_trigger(promote_step)

    (
        [tune_step, matrix_step]
        >> train_step
        >> [validate_step, evaluate_step]
        >> register_step
        >> promote_step
        >> notify_step
    )


model_training()
