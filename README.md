# tune-trail-service

This is the backend for the Tune Trail project, which provides location-based music streaming services.

## Prerequisites

Before setting up and running the project, make sure you have the following tools installed:

- **Python 3.7+**: The project requires Python 3.7 or later. You can download it from the [official Python website](https://www.python.org/downloads/).
- **pip**: The Python package installer. It is included by default with Python, but you can update it using:
   ```bash
   python -m pip install --upgrade pip
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

### 4. Running the Application

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

### 5. Optional: Running with `uvicorn` (for better performance and reloading)

You can also run the application using `uvicorn`, which provides better performance and automatically reloads the server during development. To run with `uvicorn`, use the following command:

```bash
uvicorn app.main:app --reload
```

This will start the server with auto-reloading enabled.