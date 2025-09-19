import { useState } from 'react';
import toast from 'react-hot-toast';

function TaskForm({ onTaskCreated }) {
  const [prompt, setPrompt] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  // We no longer need the `error` state, so it's gone.

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!prompt.trim()) return;

    setIsLoading(true);
    const toastId = toast.loading('Scheduling new task...');

    try {
      const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
      const response = await fetch('/api/parse-task', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, timezone }),
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Failed to create task');
      }

      toast.success('Task scheduled successfully!', { id: toastId });
      setPrompt('');
      onTaskCreated();

    } catch (err) {
      toast.error(`Error: ${err.message}`, { id: toastId });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="form-container">
      <h2>Create a New Task</h2>
      <form onSubmit={handleSubmit}>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="e.g., Scrape headlines from news.ycombinator.com and email them to me every hour"
          rows={4}
          disabled={isLoading}
        />
        <button type="submit" disabled={isLoading}>
          {isLoading ? 'Scheduling...' : 'Schedule Task'}
        </button>
      </form>
    </div>
  );
}

export default TaskForm;