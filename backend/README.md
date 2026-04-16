# PrecisionPros Billing Backend

## Running the Backend

The backend API **must run on port 8010** to match the frontend configuration.

### Start the Backend

```bash
uvicorn main:app --port 8010
```

⚠️ **Important:** Do not omit `--port 8010` — the default port is 8000, which will cause API connection failures in the frontend.

### Development Mode

For auto-reload during development:

```bash
uvicorn main:app --port 8010 --reload
```

## Environment Setup

1. Ensure `.env` is configured with database credentials
2. Database must be running (MySQL on localhost:3306)
3. Run any pending migrations or setup scripts before starting

## API Documentation

Once running, view interactive API docs at:
- **Swagger UI:** `http://localhost:8010/api/docs`
- **ReDoc:** `http://localhost:8010/api/redoc`
