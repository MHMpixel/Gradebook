import sqlite3

# SQLite database file
DB_FILE = "gradebook.db"

# Function to initialize the database
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Drop existing tables if they exist (for a clean start)
    cursor.execute("DROP TABLE IF EXISTS users")
    cursor.execute("DROP TABLE IF EXISTS grades")

    # Create the `users` table
    cursor.execute("""
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        college_id TEXT NOT NULL,
        role TEXT NOT NULL
    )
    """)

    # Create the `grades` table
    cursor.execute("""
    CREATE TABLE grades (
        student_id TEXT NOT NULL,
        subject TEXT NOT NULL,
        grade REAL NOT NULL,
        PRIMARY KEY (student_id, subject)
    )
    """)

    # Prepopulate the `users` table
    users = [
        (1, "1", "student"),
        (2, "2", "student"),
        (3, "3", "student"),
        (123, "123", "teacher")
    ]
    cursor.executemany("INSERT OR IGNORE INTO users (id, college_id, role) VALUES (?, ?, ?)", users)

    conn.commit()
    conn.close()

# Function to add a user to the `users` table
def add_user(user_id, college_id, role):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (id, college_id, role) VALUES (?, ?, ?)", (user_id, college_id, role))
    conn.commit()
    conn.close()

# Function to check if a user is a teacher
def is_teacher(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT role FROM users WHERE id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result and result[0] == "teacher"

# Function to add a grade to the `grades` table
def add_grade_to_db(student_id, subject, grade):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO grades (student_id, subject, grade) VALUES (?, ?, ?)", (student_id, subject, grade))
    conn.commit()
    conn.close()

# Function to get grades for a student
def get_grades_for_student(student_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT subject, grade FROM grades WHERE student_id = ?", (student_id,))
    grades = cursor.fetchall()
    conn.close()
    return grades

# Test database initialization
if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
