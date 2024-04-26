from pytz import utc
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from services.db.database import engine
from ..generate_relief.save import start_model
from ..headline_classifier.save import start_gen

jobstore = SQLAlchemyJobStore(engine=engine)

executors = {
    'default': ThreadPoolExecutor(5),
    'processpool': ProcessPoolExecutor(3)
}
job_defaults = {
    'coalesce': False,
    'max_instances': 3
}

sched = BackgroundScheduler(
    jobstores={'memory': jobstore},
    executors=executors,
    job_defaults=job_defaults,
    timezone=utc
)

sched.add_job(start_model, 'interval', seconds=3600)
sched.add_job(start_gen, 'interval', seconds=1200)

