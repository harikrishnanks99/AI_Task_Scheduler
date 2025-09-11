import { useState, useEffect } from 'react';

function TaskList() {
  const [tasks, setTasks] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchTasks = async () => {
      setIsLoading(true);
      setError(null);

      try {
        console.log('Fetching tasks from API...');
        const response = await fetch('/api/tasks');
        console.log('Response status:', response.status);

        if (!response.ok) {
          throw new Error('Failed to fetch tasks');
        }

        const data = await response.json();
        console.log('Tasks fetched:', data);

        setTasks(data.sort((a, b) => b.id - a.id)); // Show newest first
      } catch (err) {
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    };

    fetchTasks();
  }, []);

  if (isLoading) return <p>Loading tasks...</p>;
  if (error) return <p className="error-message">{error}</p>;

  return (
    <div className="task-list-container">
      <h2>Scheduled Tasks</h2>
      {tasks.length === 0 ? (
        <p>No tasks scheduled yet. Create one above!</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Task Name</th>
              <th>Workflow</th>
              <th>Schedule</th>
              <th>Status</th>
              <th>Created At</th>
            </tr>
          </thead>
          <tbody>
            {tasks.map(task => (
              <tr key={task.id}>
                <td>{task.id}</td>
                <td>{task.taskName}</td>
                <td>{task.workflow?.map(step => step.toolName).join(' -> ') || 'N/A'}</td>
                <td>{task.scheduleDetails?.type || 'N/A'}</td>
                <td>
                  <span className={task.isActive ? 'status-active' : 'status-inactive'}>
                    {task.isActive ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td>{new Date(task.createdAt).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default TaskList;
