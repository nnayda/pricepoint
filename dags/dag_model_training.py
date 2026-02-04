"""DAG: Train, validate, and register the forecasting model.

Runs after feature engineering completes.
"""

from datetime import datetime, timedelta

from airflow.decorators import dag, task
from airflow.sensors.external_task import ExternalTaskSensor


@dag(
    dag_id="model_training",
    description="Train, validate, evaluate, and register the home value model",
    schedule="@daily",
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
    wait_for_features = ExternalTaskSensor(
        task_id="wait_for_feature_engineering",
        external_dag_id="feature_engineering",
        external_task_id="assemble_feature_matrix",
        timeout=3600,
        poke_interval=60,
    )

    @task()
    def train():
        """Train the forecasting model."""
        raise NotImplementedError("Stub: implement model training")

    @task()
    def validate():
        """Run cross-validation on the trained model."""
        raise NotImplementedError("Stub: implement model validation")

    @task()
    def evaluate():
        """Evaluate the model on held-out test data."""
        raise NotImplementedError("Stub: implement model evaluation")

    @task()
    def register_model():
        """Log model and metrics to MLflow; promote if improved."""
        raise NotImplementedError("Stub: implement model registration")

    train_step = train()
    validate_step = validate()
    evaluate_step = evaluate()
    register_step = register_model()

    wait_for_features >> train_step >> validate_step >> evaluate_step >> register_step


model_training()
