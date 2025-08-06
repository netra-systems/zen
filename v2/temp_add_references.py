from app.db.session import SessionLocal
from app.db.models_postgres import Reference

db = SessionLocal()

references = [
    Reference(name="Synthetic Data", type="source", value="synthetic_data"),
    Reference(name="Real-time Data", type="source", value="real_time_data"),
    Reference(name="Last 24 Hours", type="time_period", value="last_24_hours"),
    Reference(name="Last 7 Days", type="time_period", value="last_7_days"),
    Reference(name="Last 30 Days", type="time_period", value="last_30_days"),
]

db.add_all(references)
db.commit()
