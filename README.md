# tune-trail-service

This is the backend for the Tune Trail project, which provides location-based music streaming services.

## Prerequisites

Before setting up and running the project, make sure you have the following tools installed:

- **Python 3.7+**: The project requires Python 3.7 or later. You can download it from the [official Python website](https://www.python.org/downloads/).
- **pip**: The Python package installer. It is included by default with Python, but you can update it using:
   ```bash
   python -m pip install --upgrade pip
   ```
- **Azure CLI**: The Azure CLI is required to interact with Azure resources. If you haven't already, install it from the [official Azure CLI installation guide](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli).
- **Python 3.11 or higher**
- **PostgreSQL 15 or higher with the `postgis` extension installed**

## Test Prerequisites

For running the integration tests, you need:
- A local PostgreSQL database with the PostGIS extension installed
- The database should be accessible with the following credentials:
  - Host: localhost
  - Port: 5432
  - Database: tune_trail_test
  - Username: postgres
  - Password: postgres

To install PostGIS on PostgreSQL:
```bash
# On Ubuntu/Debian
sudo apt-get install postgresql-15-postgis-3

# On macOS with Homebrew
brew install postgis
```

## Setup Instructions

### 1. Set Up a Virtual Environment

To isolate the dependencies for this project, it is recommended to use a Python virtual environment.

#### On Windows:
1. Open a terminal in the project directory.
2. Run the following command to create a virtual environment:
   ```bash
   python -m venv venv
   ```

#### On macOS/Linux:
1. Open a terminal in the project directory.
2. Run the following command to create a virtual environment:
   ```bash
   python3 -m venv venv
   ```

### 2. Activate the Virtual Environment

#### On Windows:
1. To activate the virtual environment, run:
   ```bash
   .\venv\Scripts\activate
   ```

#### On macOS/Linux:
1. To activate the virtual environment, run:
   ```bash
   source venv/bin/activate
   ```

Once activated, your terminal should show the virtual environment name in parentheses, e.g., `(venv)`.

### 3. Install Dependencies

With the virtual environment activated, install the necessary dependencies from the `requirements.txt` file.

Run the following command to install the dependencies:
```bash
pip install -r requirements.txt
```

### 4. Azure Login (Required for Azure Resources)

Before running the application, you must authenticate with Azure to access the necessary resources. Run the following command to log in to your Azure account:

```bash
az login
```

This will open a browser window where you can log in with your Azure credentials. Ensure that you have the necessary permissions to access the Azure resources (e.g., PostgreSQL databases) for the project.

### 5. Running the Application

To run the program, you can use the following command:

#### On Windows:
```bash
python .\app\main.py
```

#### On macOS/Linux:
```bash
python3 ./app/main.py
```

This will start the FastAPI server, and you can access the service at `http://127.0.0.1:8000/` (or another specified port).

### 6. Optional: Running with `uvicorn` (for better performance and reloading)

You can also run the application using `uvicorn`, which provides better performance and automatically reloads the server during development. To run with `uvicorn`, use the following command:

```bash
uvicorn app.main:app --reload
```

This will start the server with auto-reloading enabled.

## Running Tests

1. Create the test database:
```bash
createdb tune_trail_test
psql tune_trail_test -c "CREATE EXTENSION postgis;"
```

2. Run the tests:
```bash
# Run all tests
pytest

# Run tests with coverage report
pytest --cov=app tests/

# Run specific test file
pytest tests/test_routes/test_localities.py

# Run tests with verbose output
pytest -v
```