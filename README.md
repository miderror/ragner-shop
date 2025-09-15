# Ragner Shop Bot

A Telegram bot for a digital goods shop, built with Django, Aiogram, and Celery, managed with Docker.

## Prerequisites

-   Docker
-   Docker Compose

## Project Setup

1.  **Clone the repository:**
    ```bash
    git clone <repo-url>
    cd ragner-shop
    ```

2.  **Configure environment variables:**
    This project uses separate configurations for development and production.

    -   For **development**, copy `.env.example` to `.env.dev` and fill in the variables.
        ```bash
        cp .env.example .env.dev
        ```
    -   For **production**, create a `.env.prod` file with your production settings.

## Development Environment

All commands are managed via the `Makefile` for convenience.

#### Basic Commands

-   **Build containers:**
    ```bash
    make dev-build
    ```
-   **Start all services in the background:**
    ```bash
    make dev-up
    ```
-   **Stop and remove all services:**
    ```bash
    make dev-down
    ```
-   **View logs for a specific service (e.g., `bot` or `admin_panel`):**
    ```bash
    make dev-logs s=bot
    ```

#### Management Commands

-   **Apply database migrations:**
    ```bash
    make dev-migrate
    ```
-   **Create a superuser for the admin panel:**
    ```bash
    make dev-superuser
    ```
-   **Load initial live configurations:**
    ```bash
    make dev-load-config
    ```

#### Mock Data (for testing)

To populate the database with test data, run these commands in order:
```bash
make dev-mock-chats
make dev-mock-items
make dev-mock-codes
```

## Production Deployment

Commands are similar to development but use the `prod-` prefix, which corresponds to the `docker-compose.prod.yaml` configuration.

-   **Build production containers:**
    ```bash
    make prod-build
    ```
-   **Start production services:**
    ```bash
    make prod-up
    ```
-   **Stop and remove production services:**
    ```bash
    make prod-down
    ```
-   **Apply migrations and create a superuser in production:**
    ```bash
    make prod-migrate
    make prod-superuser
    ```
-   **Load initial live configurations:**
    ```bash
    make prod-load-config
    ```


## Локальный запуск Celery на Windows

```bash
celery -A backend worker --loglevel info --pool=solo
```