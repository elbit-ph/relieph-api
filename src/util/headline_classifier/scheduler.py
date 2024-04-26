from pytz import utc
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from .save import start_model

jobstore = MemoryJobStore()

executors = {
    'default': ThreadPoolExecutor(5),
    'processpool': ProcessPoolExecutor(3)
}
job_defaults = {
    'coalesce': False,
    'max_instances': 3
}

scheduler_headline = BackgroundScheduler(
    jobstores={'memory': jobstore},
    executors=executors,
    job_defaults=job_defaults,
    timezone=utc
)

scheduler_headline.add_job(start_model, 'interval', seconds=3600)

