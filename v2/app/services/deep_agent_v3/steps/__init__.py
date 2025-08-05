
from .fetch_raw_logs import fetch_raw_logs
from .enrich_and_cluster import enrich_and_cluster
from .propose_optimal_policies import propose_optimal_policies
from .simulate_policy import simulate_policy
from .generate_final_report import generate_final_report

ALL_STEPS = {
    "fetch_raw_logs": fetch_raw_logs,
    "enrich_and_cluster": enrich_and_cluster,
    "propose_optimal_policies": propose_optimal_policies,
    "simulate_policy": simulate_policy,
    "generate_final_report": generate_final_report,
}
