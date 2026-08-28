"""Celery tasks for BhumiSetu processing pipeline."""

from backend.api.app.tasks.celery_app import celery_app


@celery_app.task(name="bhumisetu.process_project")
def process_project(project_id: str) -> dict:
    """
    Orchestrates the ML pipeline.

    Dev 1:
        ingestion -> segmentation

    Dev 2:
        vectorization -> RL refinement

    For the hackathon demo, the actual ML work can remain mocked.
    The important part is that the API submits an asynchronous task.
    """

    print(f"[CELERY] Processing project: {project_id}")

    # TODO:
    # 1. Trigger Dev 1 ingestion/segmentation
    # 2. Trigger Dev 2 vectorization/RL refinement
    # 3. Update project status
    # 4. Store resulting features in PostGIS

    return {
        "project_id": project_id,
        "status": "review",
        "demo": True,
        "ml": False,
    }