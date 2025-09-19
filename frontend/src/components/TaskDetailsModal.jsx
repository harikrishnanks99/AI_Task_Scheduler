function TaskDetailsModal({ task, onClose }) {
  // Prevent clicks inside the modal from closing it
  const handleModalContentClick = (e) => {
    e.stopPropagation();
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={handleModalContentClick}>
        <button className="modal-close-button" onClick={onClose}>&times;</button>
        <h2>Task #{task.id}: {task.taskName}</h2>
        <div className="modal-section">
          <h3>Schedule</h3>
          <pre>{JSON.stringify(task.scheduleDetails, null, 2)}</pre>
        </div>
        <div className="modal-section">
          <h3>Workflow Steps</h3>
          {task.workflow.map((step, index) => (
            <div key={index} className="workflow-step">
              <h4>Step {index + 1}: {step.toolName}</h4>
              <pre>{JSON.stringify(step.parameters, null, 2)}</pre>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default TaskDetailsModal;