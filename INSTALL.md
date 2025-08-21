# Installation

This document provides instructions for setting up the necessary environment and installing the required packages for the Pixel-Portal application.

## Prerequisites

- Python 3.x
- GTK+ 3 development libraries

On Debian-based systems (like Ubuntu), you can install the GTK+ 3 development libraries with the following command:

```bash
sudo apt-get update
sudo apt-get install -y libgtk-3-dev
```

This is required for `wxPython`, which is a graphical user interface toolkit used by this application.

## Installation Steps

1.  **Create a virtual environment:**

    It is recommended to use a virtual environment to manage the project's dependencies. To create one, run the following command in the root directory of the project:

    ```bash
    python -m venv venv
    ```

2.  **Activate the virtual environment:**

    -   **On Windows:**
        ```bash
        venv\\Scripts\\activate
        ```

    -   **On macOS and Linux:**
        ```bash
        source venv/bin/activate
        ```

3.  **Install the required packages:**

    With the virtual environment activated, install the packages listed in `requirements.txt` using `pip`:

    ```bash
    pip install -r requirements.txt
    ```

Once these steps are completed, you should be able to run the application.
