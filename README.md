KARMIC: KARMIC: Where Your Karma is Your Currency, Invest It Wisely
(Please Note that this is MVP-Minimum Viable Prototype and we may bring updates to this gradually)

Project Overview: KARMIC is a gamified peer-to-peer assistance platform designed to combat the "kindness deficit" and loneliness in campus environments. Students can post requests (e.g., "Need help with a code bug" or "Need someone to talk to") and offer a reward in Coins. Helpers gain Coins and Experience Points (XP) based on the task's difficulty, increasing their Karmic Rank and visibility on the Leaderboard.This application is built as a Flask (Python) mobile-first web app using SQLAlchemy for data persistence.

Core Features Implemented (Finalist MVP)Secure Authentication: User login/registration with hashed passwords.

Gamified Economy: Coins and XP are automatically scaled based on task difficulty (Easy: 10, Medium: 25, Hard: 50).

Two-Step Transaction: Requires both Helper confirmation and Requester approval to release funds, preventing cheating.

Karmic Ranks & Leaderboard: Users gain ranks (Newbie, Active Peer, Community Elder, etc.) and compete for the top spot based on XP.

Task-Specific Chat: Secure, dedicated chat interface for Requester and Helper coordination.

Dark Gamer UI: Attractive, mobile-responsive theme using purple and neon-green accents.

Technical Setup Guide1: Environment SetupTo run the application locally, you must use a virtual environment.

Create and Activate Virtual Environment: python -m venv venv
venv\Scripts\activate  # On Windows Command Prompt (CMD) or VS Code Terminal

Install Dependencies: pip install -r requirements.txt

Run the Server:python app.py
(The server will launch at http://127.0.0.1:5000/. The app automatically handles database creation.)
