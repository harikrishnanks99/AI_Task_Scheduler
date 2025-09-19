import { useState, useCallback } from 'react';
import { Toaster } from 'react-hot-toast'; // Import Toaster
import './App.css';
import TaskForm from './components/TaskForm';
import TaskList from './components/TaskList';

function App() {
  const [refreshKey, setRefreshKey] = useState(0);

  const handleTaskAction = useCallback(() => {
    setRefreshKey(oldKey => oldKey + 1);
  }, []);

  return (
    <div className="app-container">
      {/* Toaster component provides notifications for the whole app */}
      <Toaster position="top-center" reverseOrder={false} />
      <header>
        <h1>AI Task Scheduler</h1>
        <p>Schedule your tasks using natural language.</p>
      </header>
      <main>
        <TaskForm onTaskCreated={handleTaskAction} />
        <TaskList key={refreshKey} onTaskAction={handleTaskAction} />
      </main>
    </div>
  );
}

export default App;