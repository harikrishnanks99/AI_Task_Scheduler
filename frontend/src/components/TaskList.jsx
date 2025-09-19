import { useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import { FaPlay, FaPause, FaTrash, FaInfoCircle } from 'react-icons/fa';
import TaskDetailsModal from './TaskDetailsModal';

function TaskList({ onTaskAction }) {
  const [tasks, setTasks] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedTask, setSelectedTask] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Fetch tasks on mount and then poll every 10 seconds
  useEffect(() => {
    // This console log is helpful for debugging, you can keep or remove it.
    console.log("TaskList useEffect is running and will fetch tasks.");
    
    const fetchTasks = async () => {
      try {
        const response = await fetch('/api/tasks');
        if (!response.ok) throw new Error('Failed to fetch tasks from API');
        const data = await response.json();
        setTasks(data.sort((a, b) => b.id - a.id));
      } catch (err) {
        setError(err.message);
        // We only toast on error, not on every fetch.
        // toast.error(err.message); 
      } finally {
        setIsLoading(false);
      }
    };

    fetchTasks(); // Initial fetch
    const intervalId = setInterval(fetchTasks, 10000); // Poll every 10 seconds

    return () => clearInterval(intervalId); // Cleanup on unmount
  }, []);

  const handleDelete = async (taskId) => {
    if (!window.confirm('Are you sure you want to delete this task?')) return;
    const toastId = toast.loading('Deleting task...');
    try {
      const response = await fetch(`/api/tasks/${taskId}`, { method: 'DELETE' });
      if (!response.ok) throw new Error('Failed to delete task');
      toast.success('Task deleted!', { id: toastId });
      onTaskAction(); // Trigger a manual refresh in the parent component
    } catch (err) {
      toast.error(`Error: ${err.message}`, { id: toastId });
    }
  };

  const toggleTaskStatus = async (task) => {
    const newStatus = !task.isActive;
    const toastId = toast.loading(`${newStatus ? 'Resuming' : 'Pausing'} task...`);
    try {
      const response = await fetch(`/api/tasks/${task.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        // NOTE: The backend expects snake_case for this PATCH request body
        body: JSON.stringify({ is_active: newStatus }),
      });
      if (!response.ok) throw new Error('Failed to update task');
      toast.success(`Task ${newStatus ? 'resumed' : 'paused'}!`, { id: toastId });
      onTaskAction();
    } catch (err) {
      toast.error(`Error: ${err.message}`, { id: toastId });
    }
  };

  const openModal = (task) => {
    setSelectedTask(task);
    setIsModalOpen(true);
  };

  // Render a loading message while the initial fetch is in progress
  if (isLoading) return <p>Loading tasks...</p>;
  
  // Render an error message if the fetch failed and there are no tasks to show
  if (error && tasks.length === 0) return <p className="error-message">{error}</p>;

  // --- This is the main return statement with the corrected JSX ---
  return (
    <>
      <div className="task-list-container">
        <h2>Scheduled Tasks</h2>
        {tasks.length === 0 ? (
          <p>No tasks scheduled yet. Create one above!</p>
        ) : (
          <table className="task-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Task Name</th>
                <th>Workflow</th>
                <th>Schedule Type</th>
                <th>Status</th>
                <th>Created At</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
            {tasks.map(task => (
              <tr key={task.id}>
                <td>{task.id}</td>
                <td>{task.taskName || 'No Name'}</td>
                
                {/* 
                  Optional chaining (?.) safely handles cases where 'workflow' might be null or undefined.
                  If it's missing, it will display 'N/A' instead of crashing the app.
                */}
                <td>{task.workflow?.map(step => step.toolName).join(' -> ') || 'N/A'}</td>
                
                {/* 
                  This is the primary fix. It safely accesses '.type' only if 'scheduleDetails' exists.
                  Otherwise, it displays 'N/A'.
                */}
                <td>{task.scheduleDetails?.type || 'N/A'}</td>
                
                <td>
                  <span className={task.isActive ? 'status-active' : 'status-inactive'}>
                    {task.isActive ? 'Active' : 'Inactive'}
                  </span>
                </td>
                
                <td>{new Date(task.createdAt).toLocaleString()}</td>
                
                <td className="actions-cell">
                  <button 
                    onClick={() => toggleTaskStatus(task)} 
                    className="icon-button" 
                    title={task.isActive ? 'Pause Task' : 'Resume Task'}
                  >
                    {task.isActive ? <FaPause /> : <FaPlay />}
                  </button>
                  <button 
                    onClick={() => openModal(task)} 
                    className="icon-button" 
                    title="View Details"
                  >
                    <FaInfoCircle />
                  </button>
                  <button 
                    onClick={() => handleDelete(task.id)} 
                    className="icon-button danger" 
                    title="Delete Task"
                  >
                    <FaTrash />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
          </table>
        )}
      </div>
      {isModalOpen && <TaskDetailsModal task={selectedTask} onClose={() => setIsModalOpen(false)} />}
    </>
  );
}

export default TaskList;