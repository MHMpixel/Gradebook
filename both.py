import sqlite3
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler

# Setup logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# SQLite database file
DB_FILE = "gradebook.db"

# Conversation state for college ID
COLLEGE_ID = 0

# Function to initialize the database
def init_db():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Create `users` table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            college_id TEXT NOT NULL,
            role TEXT NOT NULL
        )
        """)

        # Create `grades` table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS grades (
            student_id TEXT NOT NULL,
            subject TEXT NOT NULL,
            grade REAL NOT NULL,
            PRIMARY KEY (student_id, subject)
        )
        """)

        # Prepopulate users table
        users = [
            ("1", "1", "student"),
            ("2", "2", "student"),
            ("3", "3", "student"),
            ("123", "123", "teacher")
        ]
        cursor.executemany("INSERT OR IGNORE INTO users (id, college_id, role) VALUES (?, ?, ?)", users)
        conn.commit()
        logger.info("Database initialized successfully.")
    except sqlite3.Error as e:
        logger.error(f"Error initializing database: {e}")
    finally:
        conn.close()

# Function to add a user
def add_user(user_id, college_id, role):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (id, college_id, role) VALUES (?, ?, ?)", (user_id, college_id, role))
        conn.commit()
        logger.info(f"User {user_id} added successfully with role {role}.")
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
        logger.error(f"Error checking user role for {user_id}: {e}")
        return False
    finally:
        conn.close()

# Function to add a grade
def add_grade_to_db(student_id, subject, grade):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO grades (student_id, subject, grade) VALUES (?, ?, ?)", (student_id, subject, grade))
        conn.commit()
        logger.info(f"Grade added for student {student_id}: {subject} - {grade}")
    except sqlite3.Error as e:
        logger.error(f"Error adding grade for {student_id}: {e}")
    finally:
        conn.close()

# Function to fetch grades for a student
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

# Function to fetch the college ID of a user
def get_college_id(user_id):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT college_id FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    except sqlite3.Error as e:
        logger.error(f"Error fetching college ID for user {user_id}: {e}")
        return None
    finally:
        conn.close()

# Command: Start and prompt for college ID
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Welcome! Please enter your college ID to proceed.")
    return COLLEGE_ID

# Handle college ID and determine user role
async def college_id(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    college_id = update.message.text.strip()

    # Determine role
    if college_id == "123":
        role = "teacher"
    elif college_id in ["1", "2", "3"]:
        role = "student"
    else:
        await update.message.reply_text("Access denied. Invalid college ID.")
        return ConversationHandler.END

    # Add user to database
    add_user(user_id, college_id, role)

    if role == "teacher":
        await update.message.reply_text("College ID verified! You are logged in as a teacher. Use /add_grade to add grades.")
    else:
        await update.message.reply_text("College ID verified! You are logged in as a student. Use /view_grades to see your grades.")
    return ConversationHandler.END

# Teacher: Add Grade
async def add_grade(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)

    if not is_teacher(user_id):
        await update.message.reply_text("You are not authorized to add grades.")
        return

    if len(context.args) < 3:
        await update.message.reply_text("Usage: /add_grade <student_college_id> <subject> <grade>")
        return

    student_id, subject, grade = context.args[0], context.args[1], context.args[2]
    try:
        grade = float(grade)
    except ValueError:
        await update.message.reply_text("Invalid grade. Please provide a number.")
        return

    # Check if student exists
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE college_id = ?", (student_id,))
    student_exists = cursor.fetchone()
    conn.close()

    if not student_exists:
        await update.message.reply_text(f"Student with college ID {student_id} not found.")
        return

    add_grade_to_db(student_id, subject, grade)
    await update.message.reply_text(f"Grade added: {student_id}, {subject} - {grade}")

# Student: View Grades (updated)
async def view_grades(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    college_id = get_college_id(user_id)  # Map user_id to college_id

    if not college_id:
        await update.message.reply_text("Error: Your college ID could not be found. Please log in again.")
        return

    grades = get_grades_for_student(college_id)

    if not grades:
        await update.message.reply_text("No grades found.")
    else:
        grade_list = "\n".join([f"{subject}: {grade}" for subject, grade in grades])
        await update.message.reply_text(f"Your grades:\n{grade_list}")

# Main: Start bot
def main():
    # Initialize database
    init_db()

    # Bot setup
    application = Application.builder().token("token").build()

    # Handlers
    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={COLLEGE_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, college_id)]},
        fallbacks=[],
    )
    application.add_handler(conversation_handler)
    application.add_handler(CommandHandler("add_grade", add_grade))
    application.add_handler(CommandHandler("view_grades", view_grades))

    # Run bot
    application.run_polling()

if __name__ == "__main__":
    main()
