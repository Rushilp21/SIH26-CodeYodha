"""Demo/mock pipeline. This is NOT live ML. Status updates only so the UI can show processing."""

from backend.api.app.tasks.celery_app import celery_app


@celery_app.task(name="bhumisetu.process_project")
def process_project(project_id: str) -> dict:
    # TODO(dev4): enqueue Dev1 ingestion/segmentation artifacts then Dev2 vector+RL.
    return {"project_id": project_id, "status": "review", "demo": True, "ml": False}
