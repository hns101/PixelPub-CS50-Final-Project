# PixelPub: A Real-Time Social Pixel Art Platform

---
> **Author**: Hans Bregman  
> **GitHub**: hns101 | **edX**: hns101  
> **Location**: Lutjewinkel, North Holland, Netherlands  
> **Date**: June 26, 2025  
---

> **Showcase Website**: [pixelpub-cs50-final-project.onrender.com](https://pixelpub-cs50-final-project.onrender.com/)   

---

## About The Project

**PixelPub** is a dynamic, multi-user web application that provides a digital space for creating and sharing pixel art. The project has evolved from a simple drawing tool into a feature-rich social platform where users can collaborate in real-time. The core concept is the "Pub," a dedicated space containing a shared canvas and an integrated chat room.

This application was developed as a final project for Harvard's CS50x, combining a Python Flask backend with a highly interactive JavaScript frontend. Its real-time engine, built with **Flask-SocketIO**, ensures that when one user draws a pixel or sends a message, the update appears instantly on the screens of all other users in the same pub.

A key feature is the platform's accessibility, offering a **Guest Mode** that allows new visitors to immediately join a public "Guest Hub" without needing an account. Registered users can create their own private or public pubs, invite friends, customize their profiles with pixel art avatars, and interact with the wider community.

---

## Key Features

* **Real-Time Collaboration:** Utilizes **Flask-SocketIO** to broadcast drawing and chat events instantly to all connected clients within a specific pub.
* **Guest Mode:** Allows users without an account to join a dedicated community hub to experience the platform's core features.
* **User & Friends System:** Secure user registration and login. Registered users can send and accept friend requests to build a social network.
* **Custom Avatars:** Users can design their own 32x32 pixel avatars in a dedicated editor, which are displayed next to their chat messages and throughout the application.
* **The "Pub" System:**
    * Users can create their own "pubs," which are collaborative spaces with a unique canvas and chat room.
    * Pubs can be set to public (open to all registered users) or private (invite-only).
    * Owners can invite friends to their private pubs.
* **Advanced Drawing Tools:**
    * **Color Picker:** A full-spectrum color picker for unlimited creative choice.
    * **Variable Brush Size:** A slider allows users to change their brush diameter from 1 to 8 pixels for both detailed work and filling large areas.
    * **Zoom & Grid:** Users can zoom in and out of the canvas and toggle a grid overlay for precise pixel placement.
    * **Download Canvas:** Any canvas, including the avatar editor, can be downloaded as a high-quality PNG image.
* **Pixel History:** In any pub, hovering over a pixel reveals the username of the registered user who last modified it.
* **Admin Panel:** A protected dashboard allows administrators to manage the community by deleting users or pubs, and promoting other users to admin status.

---

## Technology Stack

| Technology      | Role                                                      |
| :-------------- | :-------------------------------------------------------- |
| **Python** | Core backend language.                                    |
| **Flask** | A web framework for routing and application logic.        |
| **Flask-SocketIO**| Enables real-time, bidirectional communication.           |
| **SQLite** | The database engine for storing all application data.     |
| **Pillow (PIL)**| A Python imaging library used to generate canvas previews. |
| **JavaScript** | Powers all client-side interactivity and server communication. |
| **HTML5 Canvas**| The element used for rendering and interacting with pixel art. |
| **Bootstrap 5** | A CSS framework for creating a clean and responsive UI.      |

---

## Database Schema

The application's data is organized across several interconnected tables:

1.  **`users`**: Stores account information, including `username`, `password_hash`, `role` (`'user'` or `'admin'`), and `avatar_data` (a JSON string representing the user's 32x32 pixel avatar). A special user with `id=0` is reserved for guest chat messages.
2.  **`canvases`**: Contains a record for every canvas, storing its `width`, `height`, and the entire state of the canvas as a `JSON` string in the `canvas_data` column for efficient loading.
3.  **`pubs`**: Defines each collaborative space. It links a `name`, `owner_id`, `is_private` status, and the corresponding `canvas_id`. Community pubs have a `NULL` `owner_id`.
4.  **`pub_members`**: A relational table tracking which users are members of which pubs.
5.  **`chat_messages`**: Stores all chat messages, linking them to a `pub_id` and `user_id`. The chat history is limited to the last 100 messages per pub.
6.  **`friendships`**: Manages the social graph, storing pairs of user IDs and their relationship `status` (e.g., `'pending'` or `'accepted'`).
7.  **`pixel_history`**: Logs every pixel placed by a registered user in any pub, storing the `canvas_id`, coordinates (`x`, `y`), the `modifier_id` (the user), and a `timestamp`.

---


