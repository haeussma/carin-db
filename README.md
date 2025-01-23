# Carin DB

A data management application with a Neo4j database backend and a Next.js frontend.

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)

## Setup & Installation

1. Download the repository: [Download Carin DB](https://github.com/haeussma/carin-db/archive/refs/heads/main.zip)
2. Unzip the file and navigate to the project directory:
    ```bash
    cd ~/Downloads
    unzip carin-db-main.zip
    cd carin-db-main
    ```

3. Make sure Docker Desktop is running and execute:
   ```bash
   docker-compose up -d
   ```

   This will start:
   - Frontend (Next.js)
   - Backend (FastAPI)
   - Database (Neo4j)

3. Access the services through Docker Desktop:
   - Open Docker Desktop
   - Go to "Containers"
   - Find "carin-db"
   - Click the port numbers to open in browser:
     - `3000` for Frontend
     - `7470` for Neo4j Browser
     - `8000` for Backend API

   Or use direct URLs:
   - Frontend: [http://localhost:3000](http://localhost:3000)
   - Neo4j Browser: [http://localhost:7470](http://localhost:7470)
   - Backend API: [http://localhost:8000](http://localhost:8000)

To stop the application:
```bash
docker-compose down        # Stop services
docker-compose down -v     # Stop and remove data
```

## Troubleshooting

### Windows
- If you get permission errors, make sure Docker Desktop is running with administrator privileges
- If ports are already in use, you can modify them in the `docker-compose.yml` file

### macOS
- If you get permission errors for mounted volumes, check Docker Desktop's file sharing settings
- On Apple Silicon (M1/M2), Docker Desktop should automatically use the correct architecture

### Common Issues
- If the frontend can't connect to the backend, check if all containers are running using `docker-compose ps`
- If Neo4j is not accessible, wait a few seconds after startup for the database to initialize
- If changes don't appear after rebuilding, try:
  ```bash
  docker-compose down
  docker-compose build --no-cache
  docker-compose up -d
  ``` 