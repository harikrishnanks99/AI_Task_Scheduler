import { useState } from 'react';

function TaskForm({ onTaskCreated }) {
  const [prompt, setPrompt] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!prompt.trim()) return;

    setIsLoading(true);
    setError(null);

    try {
      const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

      const response = await fetch('/parse-task', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, timezone }),
      });

      console.log('API Response Status:', response.status);

      if (!response.ok) {
        let errorMessage = 'Failed to create task';
        try {
          const errData = await response.json();
          errorMessage = errData.detail || errorMessage;
        } catch (_) { }
        throw new Error(errorMessage);
      }

      setPrompt('');
      onTaskCreated();

    } catch (err) {
      setError(err.message);
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
          placeholder="e.g., Scrape the headlines from news.ycombinator.com and email them to me every hour"
          rows={4}
          disabled={isLoading}
        />
        <button type="submit" disabled={isLoading}>
          {isLoading ? 'Scheduling...' : 'Schedule Task'}
        </button>
      </form>
      {error && <p className="error-message">{error}</p>}
    </div>
  );
}

export default TaskForm;
