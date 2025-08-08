# Corpus Admin and Synthetic Data Implementation Plan

This document outlines the plan to implement the "Corpus Admin and Synthetic data" feature.

## Phase 1: Backend Implementation

1.  **Corpus Management API:**
    *   Create a new route file `app/routes/corpus.py`.
    *   Implement CRUD (Create, Read, Update, Delete) endpoints for managing corpus metadata in the PostgreSQL database. This will involve creating, retrieving, updating, and deleting `Corpus` records.
    *   The `Corpus` model will be defined in `app/db/models_postgres.py` and the corresponding Pydantic schema in `app/schemas.py`.
    *   The API will handle the lifecycle of a corpus, including its status (e.g., "creating", "available", "failed").

2.  **Synthetic Data Generation API:**
    *   Create a new route file `app/routes/synthetic_data.py`.
    *   Implement an endpoint to trigger the generation of synthetic data. This endpoint will take a corpus ID as input.
    *   The generation process will be a background task managed by the `BackgroundTaskManager`.
    *   The background task will:
        *   Fetch the corpus data from the corresponding ClickHouse table.
        *   Use the content of the corpus to generate synthetic data.
        *   Ingest the synthetic data into a new ClickHouse table.
        *   Update the status of the synthetic data generation job.

3.  **ClickHouse Integration:**
    *   Create a new service in `app/services/clickhouse_service.py` to encapsulate all ClickHouse-related logic.
    *   This service will include a method to list all available corpus tables in ClickHouse. This will be used to populate the list of available corpora in the frontend.
    *   The service will also handle the creation of new tables for corpora and synthetic data.

## Phase 2: Frontend Implementation

1.  **Corpus Admin Page:**
    *   Create a new page at `/admin/corpus`.
    *   This page will display a list of all existing corpora with their status.
    *   It will provide a form to create a new corpus, including a name and description.
    *   It will allow users to delete existing corpora.

2.  **Synthetic Data Generation Page:**
    *   Create a new page at `/data/synthetic`.
    *   This page will display a dropdown list of available corpora, populated by calling the backend API to get the list of corpus tables from ClickHouse.
    *   It will have a button to trigger the generation of synthetic data for the selected corpus.
    *   It will display the status of the generation process in real-time using WebSockets.

3.  **WebSocket Integration:**
    *   The frontend will use the existing WebSocket connection to receive real-time updates on the status of corpus creation and synthetic data generation.
    *   The backend will send WebSocket messages to the frontend whenever the status of a job changes.

## Phase 3: Validation and Testing

1.  **Backend Tests:**
    *   Write unit tests for the new API endpoints and services.
    *   Write integration tests to verify the end-to-end flow of creating a corpus, generating synthetic data, and ingesting it into ClickHouse.

2.  **Frontend Tests:**
    *   Write unit tests for the new React components.
    *   Write end-to-end tests to verify the user interface and the interaction with the backend.
