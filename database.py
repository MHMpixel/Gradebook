import sqlite3
import logging

# Setup logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# SQLite database file
DB_FILE = "gradebook.db"

# Function to initialize the database
def init_db():
    try:
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
        logger.info("Database initialized successfully.")
    except sqlite3.Error as e:
        logger.error(f"Error initializing the database: {e}")
    finally:
        conn.close()

# Function to add a user to the `users` table
def add_user(user_id, college_id, role):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (id, college_id, role) VALUES (?, ?, ?)", (user_id, college_id, role))
        conn.commit()
        logger.info(f"User {user_id} added successfully with role: {role}")
    except sqlite3.Error as e:
        logger.error(f"Error adding user {user_id}: {e}")
    finally:
        conn.close()

# Function to check if a user is a teacher
def is_teacher(user_id):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT role FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        return result and result[0] == "teacher"
    except sqlite3.Error as e:
        logger.error(f"Error checking if user {user_id} is a teacher: {e}")
        return False
    finally:
        conn.close()

# Function to add a grade to the `grades` table
def add_grade_to_db(student_id, subject, grade):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO grades (student_id, subject, grade) VALUES (?, ?, ?)", (student_id, subject, grade))
        conn.commit()
        logger.info(f"Grade added for student {student_id}: {subject} - {grade}")
    except sqlite3.Error as e:
        logger.error(f"Error adding grade for student {student_id}: {e}")
    finally:
        conn.close()

# Function to get grades for a student
def get_grades_for_student(student_id):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT subject, grade FROM grades WHERE student_id = ?", (student_id,))
        grades = cursor.fetchall()
        logger.info(f"Grades fetched for student {student_id}: {grades}")
        return grades
    except sqlite3.Error as e:
        logger.error(f"Error fetching grades for student {student_id}: {e}")
        return []
    finally:
        conn.close()

# Test database initialization
if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
