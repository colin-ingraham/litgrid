Litgrid 📚
The Daily Literary Puzzle

Litgrid is a browser-based trivia game for book lovers, inspired by the "Immaculate Grid" format. Players must fill a 3x3 grid by finding books that satisfy intersecting categories (e.g., Genre: Horror intersecting with Decade: 1990s).

<img width="2276" height="1332" alt="image" src="https://github.com/user-attachments/assets/d2fdc650-b9cc-4d33-a875-2068d6629fc1" />


📖 How It Works
The Grid: A daily 3x3 board with specific categories for rows and columns.

The Goal: Enter a valid book title for each cell that matches both the row and column criteria.

Constraints: Players have a limited number of guesses (12) to solve the 9 cells. Each book can only be used once per board.

Social: Players can share their results via a spoiler-free emoji grid (🟩⬛🟩).

🛠️ Tech Stack
Backend: Python, Django

Frontend: HTML5, CSS3, JavaScript (jQuery)

APIs: Google Books API & OpenLibrary API (for book validation and cover fetching)

Database: SQLite (Development)

✨ Key Features
Dynamic Validation: Validates user guesses against complex category logic (e.g., page counts, publication years, title patterns) using live API data.

Daily Puzzles: System to generate and serve specific puzzles based on the current date.

Archive System: Players can go back and play puzzles from previous dates.

Responsive Design: Fully playable on desktop and mobile devices.

Game State: Saves progress locally so users can leave and come back without losing their grid.
