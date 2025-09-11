from datetime import datetime, timedelta
import pytz
from celery import shared_task, chain
from sqlalchemy.orm import Session
from croniter import croniter

from sql_models import Task
from database import get_db_session
from celery_app import celery_app

@shared_task(name="dispatch_periodic_tasks")
def dispatch_periodic_tasks():
    """
    The main scheduler task. This version uses a robust two-phase commit pattern
    to find, lock, update, and then dispatch tasks, preventing re-execution.
    """
    now_utc = datetime.now(pytz.utc)
    print(f"\n--- [Scheduler Beat @ {now_utc.isoformat()}] ---")
    
    dispatch_payloads = []
    
    # --- PHASE 1: Find, Lock, and Update Tasks Atomically ---
    db_session_gen = get_db_session()
    db: Session = next(db_session_gen)
    try:
        # Query for all potentially due tasks and lock the rows for update.
        # This prevents other transactions from interfering.
        tasks_to_evaluate = db.query(Task).filter(Task.is_active == True).with_for_update().all()
        print(f"Found {len(tasks_to_evaluate)} active tasks to evaluate.")

        for task in tasks_to_evaluate:
            schedule_details = task.schedule_details
            schedule_type = schedule_details.get('type')
            is_due = False

            # --- Evaluation logic (this part is correct) ---
            if schedule_type == 'cron':
                cron_str = schedule_details.get('value')
                if not cron_str: continue
                task_tz = pytz.timezone(task.timezone)
                base_time = now_utc.astimezone(task_tz)
                itr = croniter(cron_str, base_time)
                prev_run_time = itr.get_prev(datetime)
                if (base_time - prev_run_time).total_seconds() <= 60:
                    is_due = True

            elif schedule_type == 'interval':
                every = schedule_details.get('every')
                period = schedule_details.get('period')
                if not all([every, period]): continue
                if task.last_run_at:
                    next_run_time = task.last_run_at + timedelta(**{period: every})
                else:
                    next_run_time = now_utc
                if next_run_time <= now_utc:
                    is_due = True
                    task.last_run_at = now_utc # Mark for update

            elif schedule_type == 'datetime':
                scheduled_time_str = schedule_details.get('value')
                if not scheduled_time_str: continue
                scheduled_time_naive = datetime.fromisoformat(scheduled_time_str)
                task_tz = pytz.timezone(task.timezone)
                scheduled_time_aware = task_tz.localize(scheduled_time_naive)
                if scheduled_time_aware <= now_utc:
                    is_due = True
                    task.is_active = False # Mark for deactivation
            
            if is_due:
                print(f"  -> Task #{task.id} ('{task.task_name}') is due. Preparing payload.")
                # We still create the clean payload for dispatching later.
                dispatch_payloads.append({
                    "id": task.id,
                    "workflow": task.workflow
                })
        
        # If we found any due tasks, commit their state changes.
        # This commit releases the locks and makes the changes permanent and visible.
        if dispatch_payloads:
            print(f"Committing state changes for {len(dispatch_payloads)} due tasks.")
            db.commit()
        else:
            print("No tasks are due at this time.")

    except Exception as e:
        print(f"!!! SCHEDULER ERROR during evaluation/commit phase: {e} !!!")
        db.rollback()
    finally:
        db.close()

    # --- PHASE 2: Dispatch the tasks using the clean payloads ---
    # This happens *after* the database transaction is completely finished.
    if dispatch_payloads:
        print("Dispatching workflows to Redis...")
        for payload in dispatch_payloads:
            try:
                task_signatures = []
                for step in payload['workflow']:
                    sig = celery_app.signature(
                        step.get('tool_name'),
                        kwargs=step.get('parameters', {})
                    )
                    task_signatures.append(sig)
                
                if task_signatures:
                    workflow_chain = chain(task_signatures)
                    workflow_chain.apply_async()
                    print(f"  -> Successfully dispatched workflow for task #{payload['id']}")
            except Exception as e:
                print(f"!!! FAILED TO DISPATCH Task #{payload['id']}: {e} !!!")
    
    print("--- [Scheduler Beat Finished] ---")