from pytz import utc
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from .save import start_model

jobstore = MemoryJobStore()

executors = {
    'default': ThreadPoolExecutor(20),
    'processpool': ProcessPoolExecutor(5)
}
job_defaults = {
    'coalesce': False,
    'max_instances': 3
}

scheduler = BackgroundScheduler(
    jobstores={'memory': jobstore},
    executors=executors,
    job_defaults=job_defaults,
    timezone=utc
)

scheduler.add_job(start_model, 'interval', seconds=3600)

