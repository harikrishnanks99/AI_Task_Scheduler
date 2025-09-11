# AI Task Scheduler

A sophisticated task scheduling system that uses AI to parse natural language task descriptions and automatically schedule them. The system consists of multiple microservices working together to provide an intelligent task scheduling solution.

## Architecture

The project is structured into three main components:

### 1. Task Parser Service
- Handles natural language processing of task descriptions
- Uses Gemini API for task interpretation
- Extracts key information like deadlines, priorities, and requirements

### 2. Celery Worker Service
- Manages task scheduling and execution
- Handles periodic tasks and scheduled jobs
- Integrates with the database for task persistence

### 3. Frontend Service
- React-based user interface
- Task creation and management interface
- Real-time task status updates

## Technology Stack

- **Frontend**: React + Vite
- **Backend**: FastAPI, Celery
- **Database**: PostgreSQL
- **AI Integration**: Google Gemini API
- **Containerization**: Docker
- **Reverse Proxy**: Nginx

## Getting Started

### Prerequisites
- Docker and Docker Compose
- Node.js (for local frontend development)
- Python 3.8+

### Installation

1. Clone the repository:
```bash
git clone https://github.com/harikrishnanks99/AI_Task_Scheduler.git
cd AI_Task_Scheduler
```

2. Create a .env file in the root directory with necessary environment variables:
```
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
POSTGRES_DB=your_db_name
GEMINI_API_KEY=your_api_key
```

3. Start the services using Docker Compose:
```bash
docker-compose up -d
```

### Development

- Frontend development server: `cd frontend && npm install && npm run dev`
- Task Parser service: Runs on port 8000
- Celery Worker: Handles background tasks
- PostgreSQL: Runs on port 5432

## Features

- Natural language task parsing
- Automated task scheduling
- Priority-based task management
- Real-time task status updates
- Docker containerization for easy deployment
- Scalable microservices architecture

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

