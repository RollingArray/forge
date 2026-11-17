# FORGE Local Development

## Starting FORGE

From the repository root, start the development environment:

``` bash
./start-forge.sh
```

The startup script checks required tools, environment configuration,
dependencies, and ports before starting the backend and frontend
services.

It starts both services, writes their logs separately, monitors the
processes, and shuts them down when you press `Ctrl+C`.

No manual virtual-environment activation is required when using this
script.

## Development URLs

  Service                     URL
  --------------------------- ----------------------------
  Frontend                    http://localhost:4200
  Backend API                 http://127.0.0.1:8000
  Backend API documentation   http://127.0.0.1:8000/docs

## Logs

The development startup script writes service logs to:

``` text
/tmp/forge-dev-logs/
```

The primary log files are:

-   `backend.log`
-   `frontend.log`

Use these files when investigating startup or runtime issues.

## Stopping FORGE

When FORGE is running through `start-forge.sh`, press:

``` text
Ctrl+C
```

The script monitors the services and handles shutdown.

## Running Services Individually

You can start either service independently when working on a specific
part of the application.

### Backend

From the repository root:

``` bash
./.venv/bin/python -m uvicorn app.main:app --app-dir backend/api --reload --host 127.0.0.1 --port 8000
```

The backend API is available at:

-   http://127.0.0.1:8000
-   http://127.0.0.1:8000/docs

### Frontend

From the repository root:

``` bash
cd frontend
npm start
```

The frontend is available at:

-   http://localhost:4200

## Related Documentation

-   [Environment Setup](environment-setup.md)
-   [Configuration](configuration.md)
-   [E2E Testing Guide](../testing/e2e-testing-guide.md)
