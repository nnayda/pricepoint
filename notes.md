# DAG
KubernetesPodOperator(
    task_id="cary_collector",
    ...,
    # Here is where you change the behavior dynamically!
    env_vars={
        "PRICEPOINT_TABLE_NAME": "prod_police_incidents_cary", # Override for Prod
        "PRICEPOINT_ODS_BASE_URL": Variable.get("CARY_API_URL") # Securely fetched
    }
)