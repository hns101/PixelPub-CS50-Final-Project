# Pixelverse: A Real-Time Collaborative Pixel Art Canvas

#### Video Demo: 
> **Author**: Hans Bregman  
> **GitHub**: hns101 | **edX**: ------  
> **Location**: Lutjewinkel, North Holland, Netherlands  
> 

---

## About The Project

**Pixelverse** is a dynamic, multi-user web application that provides a digital space for creating and sharing pixel art. Inspired by collaborative projects like Reddit's `r/place`, Pixelverse allows users to draw on their own private canvases, share them in a public gallery, and contribute to large-scale community masterpieces in real-time.

The project was developed as a final project for Harvard's CS50x, combining a Python Flask backend with a highly interactive JavaScript frontend. The core of the application is its real-time engine, built using WebSockets, which ensures that when one user places a pixel, it appears instantly on the screens of all other connected users. This creates a lively and engaging collaborative environment.

Beyond simple drawing, Pixelverse features a unique **pixel history** system on community canvases. By hovering over any pixel, users can see which user last modified it and when, adding a layer of social accountability and history to the shared creations.

---

## Key Features

* **Real-Time Collaboration:** Utilizes **Flask-SocketIO** to broadcast drawing events instantly to all connected clients.
* **User Authentication:** Secure registration and login system to manage user accounts and creations.
* **Personal Canvases:** Logged-in users can create, save, and manage their own private canvases of various sizes.
* **Public Gallery:** Users can choose to make their personal canvases public, showcasing their work in a central gallery for everyone to see.
* **Community Canvases:** Three large, shared canvases are available for all users to contribute to simultaneously, fostering large-scale collaborative art.
* **Pixel History:** On community canvases, hovering over a pixel reveals the username of the last person who colored it and the time of the modification.
* **Admin Panel:** A protected administration dashboard allows for comprehensive user and content moderation, including deleting users and managing the public status of any canvas.

---

## Technology Stack

This project was built using a modern web development stack, focusing on a balance between a powerful backend and a responsive frontend.

| Technology | Role |
| :--- | :--- |
| **Python** | Core backend language. |
| **Flask** | A micro web framework for routing and application logic. |
| **Flask-SocketIO** | Enables real-time, bidirectional communication with WebSockets. |
| **SQLite** | The SQL database engine used for storing all user and canvas data. |
| **JavaScript** | Powers all client-side interactivity, from drawing to server communication. |
| **HTML5 Canvas** | The element used for rendering the pixel art grid and handling drawing. |
| **Bootstrap 5** | A CSS framework used for creating a clean and responsive user interface. |

---

## Database Schema

The application's data is organized across three main tables:

1.  **`users`**: Stores user account information, including a unique ID, username, hashed password, and user role (`'user'` or `'admin'`).
2.  **`canvases`**: Contains records for every canvas. This includes its name, dimensions, a foreign key to the `owner_id` (or `NULL` for community canvases), and flags for its public or community status. Crucially, the entire state of the canvas is stored as a single `JSON` string in the `canvas_data` column for efficient loading.
3.  **`pixel_history`**: Specifically for community canvases, this table logs every single pixel placement, storing the `canvas_id`, coordinates (`x`, `y`), the `modifier_id` (the user who placed it), and a `timestamp`.

---

## Setup and Installation

To run Pixelverse on a local machine, please follow these steps:

1.  **Clone the Repository**
    ```bash
    git clone --------
    cd pixelverse
    ```

2.  **Set Up a Virtual Environment** (Recommended)
    ```bash
    python -m venv venv
    # On Windows
    .\venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

3.  **Install Dependencies**
    All required packages are listed in `requirements.txt`. Install them with pip:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the Application**
    The application will automatically create and initialize the `project.db` database file on its first run.
    ```bash
    python app.py
    ```
    The application will be available at the given local port.

5.  **(Optional) Become an Admin**
    To access the admin panel, you must first register a user account through the web interface and then manually update its role in the database.
    ```bash
    # Open the database with the sqlite3 CLI
    sqlite3 project.db

    # Run the update command, replacing 'your_admin_user'
    sqlite> UPDATE users SET role = 'admin' WHERE username = 'your_admin_user';

    # Exit the CLI
    sqlite> .quit
    ```
