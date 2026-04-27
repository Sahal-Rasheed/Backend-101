import time
from typing import Any

from kombu import Queue
from sqlalchemy import select
from celery import Celery, Task
from celery.utils.log import get_task_logger  # noqa
from celery.signals import (
    task_retry,
    task_prerun,
    task_postrun,
    task_failure,
    task_success,
)

from app.core.config import settings
from app.models.email import EmailLog
from app.schemas.email import EmailStatus
from app.core.logging import setup_app_logger
from app.db.sync_session import get_sync_session

logger = setup_app_logger("app.celery.signals")


## ------------------------ ##
## celery app configuration ##
## ------------------------ ##

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


## ------------------------------------------------ ##
## signal handlers for logging, monitoring, DLQ etc ##
## ------------------------------------------------ ##

## docs: https://docs.celeryq.dev/en/main/userguide/signals.html


@task_prerun.connect
def task_prerun_handler(task_id: str, task: Task, args: tuple, kwargs: dict, **extra):
    """
    Dispatched before a task is executed.
    Sender is the task object being executed.

    Args:
        task_id (str): Id of the task to be executed.
        task (Task): The task being executed.
        args (tuple): The tasks positional arguments.
        kwargs (dict): The tasks keyword arguments.
    """
    # store start time on the task object itself, accessible in postrun
    task.request.prerun_time = time.monotonic()
    logger.info(
        "Task starting",
        extra={
            "task_id": task_id,
            "task_name": task.name,
            "task_args": args,
            "task_kwargs": kwargs,
            "retries": task.request.retries,
            "max_retries": task.max_retries,
        },
    )


@task_postrun.connect
def task_postrun_handler(
    task_id: str,
    task: Task,
    args: tuple,
    kwargs: dict,
    retval: Any,
    state: str,
    **extra,
):
    """
    Dispatched after a task has been executed.
    Sender is the task object executed.

    Args:
        task_id (str): Id of the task to be executed.
        task (Task): The task being executed.
        args (tuple): The tasks positional arguments.
        kwargs (dict): The tasks keyword arguments.
        retval (Any): The return value of the task.
        state (str): Name of the resulting state.
    """
    # access the start time set in prerun from task obj.
    duration = (
        time.monotonic() - task.request.prerun_time
        if hasattr(task.request, "prerun_time")
        else None
    )

    logger.info(
        "Task completed",
        extra={
            "task_id": task_id,
            "task_name": task.name,
            "state": state,
            "duration_seconds": round(duration, 4) if duration else None,
            "retval": retval,
        },
    )


@task_success.connect
def task_success_handler(sender: Task, result: Any, **extra):
    """
    Dispatched when a task succeeds.
    Sender is the task object executed.

    Args:
        result: Return value of the task.
    """
    logger.info(
        "Task succeeded",
        extra={
            "task_name": sender.name,
            "task_id": sender.request.id,
            "result": result,
            "retries": sender.request.retries,
        },
    )


# global error handler & DLQ for failed tasks
@task_failure.connect
def handle_task_failure(
    sender: Task,
    task_id: str,
    exception: Exception,
    args: tuple,
    kwargs: dict,
    traceback: Any,
    einfo: Any,
    **extra,
):
    """
    Dispatched when a task fails.
    Sender is the task object executed.

    Args:
    task_id: Id of the task.
    exception: The exception instance raised.
    args: Positional arguments the task was called with.
    kwargs: Keyword arguments the task was called with.
    traceback: Stack trace object.
    einfo: Exception info instance.
    """
    logger.error(
        "Task failed",
        extra={
            "task_id": task_id,
            "task_name": sender.name,
            "exception_type": type(exception).__name__,
            "exception_msg": str(exception),
            "task_args": args,
            "task_kwargs": kwargs,
            "retries": sender.request.retries,
            "traceback": str(einfo),
        },
        exc_info=True,
    )

    # only treat as dead letter if retries exhausted
    # DLQ handling
    if sender.request.retries >= sender.max_retries:
        logger.error(
            "Max retries exceeded",
            extra={
                "task_id": task_id,
                "task_name": sender.name,
            },
        )

        with get_sync_session() as db:
            email_log = db.execute(
                select(EmailLog).where(EmailLog.id == kwargs.get("data", {}).get("id"))
            ).scalar_one_or_none()
            email_log.status = EmailStatus.FAILED
            email_log.error = f"Max retries exceeded. Last error: {str(exception)}"
            db.commit()
            db.refresh(email_log)


@task_retry.connect
def task_retry_handler(sender: Task, request: Any, reason: str, einfo: Any, **extra):
    """
    Dispatched when a task will be retried.
    Sender is the task object.

    Args:
        request: The current task request.
        reason: Reason for retry (usually an exception instance, but can always be coerced to str).
        einfo: Detailed exception info.
    """
    logger.warning(
        "Task retrying",
        extra={
            "task_id": request.id,
            "task_name": sender.name,
            "reason": str(reason),
            "retry_number": request.retries,
            "max_retries": sender.max_retries,
        },
    )
