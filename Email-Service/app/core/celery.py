from celery import Celery
from kombu import Queue

from app.core.config import settings


celery_app = Celery(
    "email_service_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.email_tasks"],
)

# docs: https://docs.celeryq.dev/en/main/userguide/configuration.html
celery_app.conf.update(
    # serialization settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # timezone settings
    timezone="UTC",
    enable_utc=True,
    # reliability settings
    task_acks_late=True,  # acknowledge after task completes (not before)
    task_reject_on_worker_lost=True,  # requeue task if worker crashes
    worker_prefetch_multiplier=1,  # fetch one task at a time for fair distribution, incr for more throughput
    task_track_started=True,  # gives a "STARTED" state when the worker begins executing the task, by default state is "PENDING"
    # result backend settings
    result_expires=3600,  # clean up results after 1 hour to save memory
    result_extended=True,  # store task name, args, worker, retries (extra metadata) in result backend — useful for debugging
    result_backend_thread_safe=True,  # ensure thread safety for multi-threaded workers
    # task queues and routing settings
    task_default_queue="default",
    task_default_routing_key="default",
    task_queues=(
        Queue(
            "default", routing_key="default"
        ),  # can use Exchange() inside Queue when using RabbitMQ
        Queue("high", routing_key="high"),
        Queue("low", routing_key="low"),
    ),
    task_routes={
        # if task has custom name use that name, otherwise use the path to the task fn
        "send_welcome_email_task": {"queue": "default"},
        "send_notification_email_task": {"queue": "high"},
        "send_pwd_reset_email_task": {"queue": "low"},
    },
    # result backend retry settings
    # result_backend_always_retry=True, # retry transient result backend errors automatically
    # result_backend_max_retries=5,
    # result_backend_max_sleep_between_retries_ms=2000,
    # global task rate limit settings
    # task_default_rate_limit="100/s", # limit to 100 tasks per second globally
    # global task time limits settings
    # task_soft_time_limit=300, # raises SoftTimeLimitExceeded at 5 min → lets task clean up
    # task_time_limit=360, # hard kill at 6 min if soft limit ignored
    # global task retry settings
    # task_publish_retry=True, # retry publishing (default)
    # task_publish_retry_policy={
    #     "max_retries": 5,
    #     "interval_start": 0,
    #     "interval_step": 0.5,
    #     "interval_max": 3,
    #     "retry_errors": (ConnectionError, TimeoutError), # only retry on these errors
    # },
)

# load config from separate module (optional, can also configure directly in code as above)
# celery_app.config_from_object("config_module")
