import { useState } from "react";
import { fetchProcessingTask, processProject, type ProcessingTask } from "../api/client";

export function ProcessingPanel({ projectId, onRefresh }: { projectId: string; onRefresh: () => Promise<void> }) {
  const [busy, setBusy] = useState(false);
  const [taskId, setTaskId] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [task, setTask] = useState<ProcessingTask | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function queue() {
    setBusy(true); setError(null); setTask(null); setTaskId("");
    try {
      const result = await processProject(projectId);
      setMessage(result.message);
      // The existing API carries the Celery task UUID only in its message.
      // Prefer an explicit task_id if a compatible backend later adds it.
      const id = result.task_id ?? result.message.match(/Processing task queued: ([0-9a-f-]{36})/i)?.[1];
      if (id) { setTaskId(id); setTask(await fetchProcessingTask(projectId, id)); }
      await onRefresh();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Processing request failed."); }
    finally { setBusy(false); }
  }

  async function refresh() {
    setBusy(true); setError(null);
    try {
      if (taskId) setTask(await fetchProcessingTask(projectId, taskId));
      await onRefresh();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Refresh failed."); }
    finally { setBusy(false); }
  }

  return <div className="processing-panel">
    <button className="process-button" disabled={busy} onClick={queue}>{busy ? "Checking…" : "Request pipeline processing"}</button>
    <p className="sidebar-note">Stored GeoJSON outputs are supported. Fresh segmentation/RL execution requires the missing inference implementation and trained model; the API reports this explicitly.</p>
    <button className="action-secondary" disabled={busy} onClick={refresh}>Refresh outputs{taskId ? " & task" : ""}</button>
    {message && <p className="panel-note" style={{ whiteSpace: "pre-wrap" }}>{message}</p>}
    {error && <p role="alert" className="panel-note">{error}</p>}
    {task && <div className="task-output"><strong>Task: {task.state}</strong><small>{task.task_id}</small>
      <p className="panel-note">A successful task does not by itself prove RL execution.</p>
      <pre aria-label="Backend task result">{task.result == null ? "No result returned yet." : JSON.stringify(task.result, null, 2)}</pre>
    </div>}
  </div>;
}
