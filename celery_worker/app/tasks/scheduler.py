from datetime import datetime, timedelta
import pytz
from celery import shared_task, chain
from sqlalchemy.orm import Session
from croniter import croniter

# This import works because of the volume mount. It now imports our updated Task model.
from sql_models import Task
from database import get_db_session
from celery_app import celery_app

@shared_task(name="dispatch_periodic_tasks")
def dispatch_periodic_tasks():
    """
    The main scheduler task run by Celery Beat every minute.
    This version reads task workflows from the DB and dispatches them as Celery Chains.
    """

    db_session_gen = get_db_session()
    db: Session = next(db_session_gen)
    
    now_utc = datetime.now(pytz.utc)
    print(f"\n--- [Workflow Scheduler Beat @ {now_utc.isoformat()}] ---")
    
    try:
        active_tasks = db.query(Task).filter(Task.is_active == True).all()
        print(f"Found {len(active_tasks)} active tasks to evaluate.")

        due_tasks = []
        for task in active_tasks:
            schedule_type = task.schedule_details.get('type')
            is_due = False


            #debugging print
            print(f"\nEvaluating Task #{task.id}: Name='{task.task_name}', Timezone='{task.timezone}'")
            print(f"  - Schedule Details from DB: {task.schedule_details}")


            # --- Evaluate if task is due based on its schedule ---
            if schedule_type == 'cron':
                cron_str = task.schedule_details['value']
                task_tz = pytz.timezone(task.timezone)
                base_time = now_utc.astimezone(task_tz)
                itr = croniter(cron_str, base_time)
                prev_run_time = itr.get_prev(datetime)
                if (base_time - prev_run_time).total_seconds() <= 60:
                    is_due = True

            elif schedule_type == 'interval':
                if task.last_run_at:
                    interval_val = task.schedule_details
                    delta_args = {interval_val['period']: interval_val['every']}
                    next_run_time = task.last_run_at + timedelta(**delta_args)
                else:
                    next_run_time = now_utc
                if next_run_time <= now_utc:
                    is_due = True
                    task.last_run_at = now_utc # Update last run time

            elif schedule_type == 'datetime':
                scheduled_time_str = task.schedule_details['value']
                scheduled_time_naive = datetime.fromisoformat(scheduled_time_str)
                task_tz = pytz.timezone(task.timezone)
                scheduled_time_aware = task_tz.localize(scheduled_time_naive)
                if scheduled_time_aware <= now_utc:
                    is_due = True
                    task.is_active = False # Deactivate after running

            if is_due:
                print(f"Task #{task.id} ('{task.task_name}') is due.")
                due_tasks.append(task)

        # --- Dispatch all due tasks ---
        for task_record in due_tasks:
            # --- THE NEW WORKFLOW LOGIC ---
            task_signatures = []
            for step in task_record.workflow:
                # Create a Celery "signature" for each step in the workflow
                sig = celery_app.signature(
                    step['tool_name'],
                    kwargs=step['parameters']
                )
                task_signatures.append(sig)
            
            if not task_signatures:
                print(f"  -> Task #{task_record.id} has an empty workflow. Skipping.")
                continue

            # Link the signatures together into a chain.
            # If there's only one, it's a chain of one.
            workflow_chain = chain(task_signatures)
            
            print(f"  -> Dispatching workflow for task #{task_record.id} to Redis queue.")
            workflow_chain.apply_async()
            # --- END NEW WORKFLOW LOGIC ---
        
        # Commit all state changes (last_run_at, is_active) to the database
        if due_tasks:
            db.commit()

    except Exception as e:
        print(f"!!! SCHEDULER ERROR: {e} !!!")
        db.rollback()
    finally:
        db.close()
        print("--- [Scheduler Beat Finished] ---")