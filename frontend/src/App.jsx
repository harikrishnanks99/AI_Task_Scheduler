import { useState, useCallback } from 'react';
import './App.css';
import TaskForm from './components/TaskForm';
import TaskList from './components/TaskList';

function App() {
  // This state is used to trigger a refresh of the TaskList from the TaskForm
  const [refreshKey, setRefreshKey] = useState(0);

  const handleTaskCreated = useCallback(() => {
    setRefreshKey(oldKey => oldKey + 1);
  }, []);

  return (
    <div className="app-container">
      <header>
        <h1>AI Task Scheduler</h1>
        <p>Schedule your tasks using natural language.</p>
      </header>
      <main>
        <TaskForm onTaskCreated={handleTaskCreated} />
        <TaskList key={refreshKey} />
      </main>
    </div>
  );
}

export default App;