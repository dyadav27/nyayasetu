# NyayaSetu Blockchain — Setup Guide

## Prerequisites
- Docker Desktop installed and running
- 4GB RAM free

## One-Time Setup

### 1. Start the Fabric Network
Open PowerShell in this folder and run:

docker compose up -d

Wait ~30 seconds for all containers to start.

### 2. Verify Everything is Running

docker compose ps

You should see 6 containers: orderer, 2 peers, 2 couchdbs, fabric-rest-api.

### 3. Test the REST API

curl http://localhost:8080/health

Expected: `{"success":true,"message":"NyayaSetu Fabric REST API is running"}`

## Daily Usage
- Start:  `docker compose up -d`
- Stop:   `docker compose down`
- Logs:   `docker compose logs -f fabric-rest-api`

## API Endpoints (called automatically by NyayaSetu backend)
- POST http://localhost:8080/store   — store certificate hash on blockchain
- GET  http://localhost:8080/query  — query certificate by ID
- GET  http://localhost:8080/verify — verify SHA-256 hash matches ledger

## Note
The NyayaSetu Python backend (api.py) calls localhost:8080 automatically
when generating evidence certificates. No manual steps needed after setup.
EOF
echo "README created"
