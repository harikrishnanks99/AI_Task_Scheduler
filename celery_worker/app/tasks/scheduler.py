from datetime import datetime, timedelta
import pytz
from celery import shared_task
from sqlalchemy.orm import Session
from croniter import croniter

# This import works because of the volume mount and sys.path modification
from sql_models import Task
from database import get_db_session
from celery_app import celery_app


def schedule_task_execution(task: Task):
    """
    Helper function to push a task to the Redis queue for immediate execution by a worker.
    """
    print(f"  -> Dispatching task #{task.id} ('{task.tool_to_use}') to Redis queue.")
    celery_app.send_task(
        name=task.tool_to_use,
        kwargs=task.parameters,
        # Create a unique ID for this specific execution run
        task_id=f"exec-{task.id}-{datetime.now(pytz.utc).timestamp()}"
    )

@shared_task(name="dispatch_periodic_tasks")
def dispatch_periodic_tasks():
    """
    The main scheduler task run by Celery Beat every minute.
    It connects to the DB, finds due tasks, dispatches them, and updates their state.
    """
    db_session_gen = get_db_session()
    db: Session = next(db_session_gen)
    
    # Use timezone-aware UTC time for all comparisons
    now_utc = datetime.now(pytz.utc)
    print(f"\n--- [Scheduler Beat @ {now_utc.isoformat()}] ---")
    
    try:
        # Fetch all tasks that are currently marked as active
        active_tasks = db.query(Task).filter(Task.is_active == True).all()
        print(f"Found {len(active_tasks)} active tasks to evaluate.")

        for task in active_tasks:
            task_type = task.schedule_details.get('type')

            # --- 1. Evaluate CRON tasks ---
            if task_type == 'cron':
                cron_val = task.schedule_details['value']
                cron_str = f"{cron_val['minute']} {cron_val['hour']} {cron_val['day_of_month']} {cron_val['month_of_year']} {cron_val['day_of_week']}"
                
                # The schedule is relative to the task's own timezone
                task_tz = pytz.timezone(task.timezone)
                base_time = now_utc.astimezone(task_tz)
                
                # croniter tells us the last scheduled time before the current time
                itr = croniter(cron_str, base_time)
                prev_run_time = itr.get_prev(datetime)

                # If the last scheduled run time was within the last 60 seconds, it's due now
                if (base_time - prev_run_time).total_seconds() <= 60:
                    print(f"CRON task due: #{task.id} ('{task.task_name}')")
                    schedule_task_execution(task)

            # --- 2. Evaluate INTERVAL tasks ---
            elif task_type == 'interval':
                if task.last_run_at:
                    interval_val = task.schedule_details['value']
                    # Build timedelta arguments dynamically (e.g., {'minutes': 5})
                    delta_args = {interval_val['period']: interval_val['every']}
                    next_run_time = task.last_run_at + timedelta(**delta_args)
                else:
                    # If it has never run, it's due immediately
                    next_run_time = now_utc

                if next_run_time <= now_utc:
                    print(f"INTERVAL task due: #{task.id} ('{task.task_name}')")
                    schedule_task_execution(task)
                    # CRITICAL: Update the last_run_at time to now
                    task.last_run_at = now_utc
            
            # --- 3. Evaluate DATETIME tasks ---
            elif task_type == 'datetime':
                scheduled_time_str = task.schedule_details['value']['iso_datetime']
                scheduled_time_naive = datetime.fromisoformat(scheduled_time_str)
                
                # Make the naive datetime object timezone-aware using its own timezone
                task_tz = pytz.timezone(task.timezone)
                scheduled_time_aware = task_tz.localize(scheduled_time_naive)
                
                # If the scheduled time is now or in the past, it's due
                if scheduled_time_aware <= now_utc:
                    print(f"DATETIME task due: #{task.id} ('{task.task_name}')")
                    schedule_task_execution(task)
                    # CRITICAL: Deactivate the task so it never runs again
                    task.is_active = False
        
        # Commit all state changes (last_run_at, is_active) to the database at once
        db.commit()

    except Exception as e:
        print(f"!!! SCHEDULER ERROR: {e} !!!")
        db.rollback() # Rollback any partial changes on error
    finally:
        db.close()
        print("--- [Scheduler Beat Finished] ---")