import sqlite3
import logging
import csv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler

# Setup logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# SQLite database file
DB_FILE = "gradebook.db"

# Conversation states
COLLEGE_ID = 0
LOGGED_IN = {}

# Helper function for database connections
def db_connection():
    try:
        conn = sqlite3.connect(DB_FILE)
        return conn
    except sqlite3.Error as e:
        logger.error(f"Database connection error: {e}")
        return None

# Function to initialize the database
def init_db():
    conn = db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                college_id TEXT NOT NULL,
                role TEXT NOT NULL
            )
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS grades (
                student_id TEXT NOT NULL,
                subject TEXT NOT NULL,
                grade REAL NOT NULL,
                PRIMARY KEY (student_id, subject)
            )
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS detailed_grades (
                student_id TEXT NOT NULL,
                subject TEXT NOT NULL,
                homework REAL,
                quizzes REAL,
                midterm REAL,
                final REAL,
                attendance REAL,
                overall REAL,
                PRIMARY KEY (student_id, subject)
            )
            """)

            # Check if the columns exist
            cursor.execute("PRAGMA table_info(detailed_grades)")
            columns = cursor.fetchall()
            column_names = [column[1] for column in columns]
            if "overall" not in column_names:
                cursor.execute("ALTER TABLE detailed_grades ADD COLUMN overall REAL")

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS grading_logic (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT
            )
            """)

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
    conn = db_connection()
    if conn:
        try:
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
    conn = db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT role FROM users WHERE id = ?", (user_id,))
            result = cursor.fetchone()
            return result and result[0] == "teacher"
        except sqlite3.Error as e:
            logger.error(f"Error checking user role for {user_id}: {e}")
            return False
        finally:
            conn.close()
    return False

# Function to add detailed grade components to the database
def add_detailed_grade_to_db(student_id, subject, homework, quizzes, midterm, final, attendance, overall):
    conn = db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO detailed_grades (student_id, subject, homework, quizzes, midterm, final, attendance, overall) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                           (student_id, subject, homework, quizzes, midterm, final, attendance, overall))
            conn.commit()
            logger.info(f"Detailed grades added for student {student_id}: {subject} - Homework: {homework}, Quizzes: {quizzes}, Midterm: {midterm}, Final: {final}, Attendance: {attendance}, Overall: {overall}")
        except sqlite3.Error as e:
            logger.error(f"Error adding detailed grades for {student_id}: {e}")
        finally:
            conn.close()

# Function to fetch grades for a student
def get_grades_for_student(student_id):
    conn = db_connection()
    if conn:
        try:
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
    return []

# Function to fetch detailed grades for a student
def get_detailed_grades_for_student(student_id):
    conn = db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT subject, homework, quizzes, midterm, final, attendance, overall FROM detailed_grades WHERE student_id = ?", (student_id,))
            grades = cursor.fetchall()
            logger.info(f"Detailed grades fetched for student {student_id}: {grades}")
            return grades
        except sqlite3.Error as e:
            logger.error(f"Error fetching detailed grades for student {student_id}: {e}")
            return []
        finally:
            conn.close()
    return []

# Function to fetch the college ID of a user
def get_college_id(user_id):
    conn = db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT college_id FROM users WHERE id = ?", (user_id,))
            result = cursor.fetchone()
            logger.info(f"Fetched college_id {result} for user_id {user_id}")
            return result[0] if result else None
        except sqlite3.Error as e:
            logger.error(f"Error fetching college ID for user {user_id}: {e}")
            return None
        finally:
            conn.close()
    return None

# Function to define grading logic
def define_grading_logic(description):
    conn = db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO grading_logic (description) VALUES (?)", (description,))
            conn.commit()
            logger.info("Grading logic defined successfully.")
        except sqlite3.Error as e:
            logger.error(f"Error defining grading logic: {e}")
        finally:
            conn.close()

# Function to reset grades and grading logic
async def reset(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)

    if not is_teacher(user_id):
        await update.message.reply_text("You are not authorized to reset grades and grading logic.")
        return

    conn = db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM grades")
            cursor.execute("DELETE FROM detailed_grades")
            cursor.execute("DELETE FROM grading_logic")
            conn.commit()
            logger.info("Grades and grading logic reset successfully.")
            await update.message.reply_text("Grades and grading logic have been reset.")
        except sqlite3.Error as e:
            logger.error(f"Error resetting grades and grading logic: {e}")
            await update.message.reply_text("Error resetting grades and grading logic.")
        finally:
            conn.close()

# Function to fetch grading logic
def get_grading_logic():
    conn = db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT description FROM grading_logic")
            logic = cursor.fetchall()
            logger.info(f"Grading logic fetched: {logic}")
            if not logic:
                logger.info("No grading logic found in the database.")
            return logic
        except sqlite3.Error as e:
            logger.error(f"Error fetching grading logic: {e}")
            return []
        finally:
            conn.close()
    return []

# Command: Show Available Commands
async def show_commands(role):
    if role == "teacher":
        return """
Available commands for teachers:
/add_grade <student_college_id> <subject> <homework> <quizzes> <midterm> <final> <attendance> <overall> - Add a grade for a student.
/upload_grades <csv_file_path> - Upload grades from a CSV file.
/view_all_grades - View all grades.
/grading_logic <description> - Define grading logic.
/view_grading_logic - View current grading logic.
/reset - Reset grades and grading logic for all students.
/logout - Log out.
"""
    else:  # role is "student"
        return """
Available commands for students:
/view_grades - View your grades.
/view_detailed_grades - View detailed grades during the term.
/view_grading_logic - View current grading logic defined by the teacher.
/logout - Log out.
"""

# Command: Start and prompt for college ID
async def start(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    if user_id in LOGGED_IN:
        await update.message.reply_text("You are already logged in. Use /logout to log out.")
    else:
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

    # Add user to database and log them in
    add_user(user_id, college_id, role)
    LOGGED_IN[user_id] = (college_id, role)

    commands = await show_commands(role)
    await update.message.reply_text(f"College ID verified! You are logged in as a {role}.\n{commands}")
    return ConversationHandler.END

# Command: Logout
async def logout(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    if user_id in LOGGED_IN:
        del LOGGED_IN[user_id]
        await update.message.reply_text("You have been logged out.")
    else:
        await update.message.reply_text("You are not logged in.")

# Teacher: Add Grade (continued)
async def add_grade(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)

    if not is_teacher(user_id):
        await update.message.reply_text("You are not authorized to add grades.")
        return

    # Check if grading logic is defined
    logic = get_grading_logic()
    if not logic:
        await update.message.reply_text("Please set a grading logic before adding grades.")
        return

    if len(context.args) < 8:  # Requires at least 7 grading components plus the overall grade
        await update.message.reply_text("Usage: /add_grade <student_college_id> <subject> <homework> <quizzes> <midterm> <final> <attendance> <overall>")
        return

    student_id, subject, homework, quizzes, midterm, final, attendance, overall = context.args[0], context.args[1], context.args[2], context.args[3], context.args[4], context.args[5], context.args[6], context.args[7]
    
    try:
        homework = float(homework)
        quizzes = float(quizzes)
        midterm = float(midterm)
        final = float(final)
        attendance = float(attendance)
        overall = float(overall)
    except ValueError:
        await update.message.reply_text("Invalid grade. Please provide numbers for all grading components.")
        return

    # Check if student exists
    conn = db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE college_id = ?", (student_id,))
        student_exists = cursor.fetchone()
        conn.close()

        if not student_exists:
            await update.message.reply_text(f"Student with college ID {student_id} not found.")
            return

        # Add detailed grades and overall grade
        add_detailed_grade_to_db(student_id, subject, homework, quizzes, midterm, final, attendance, overall)
        await update.message.reply_text(f"Grades added: {student_id}, {subject} - Homework: {homework}, Quizzes: {quizzes}, Midterm: {midterm}, Final: {final}, Attendance: {attendance}, Overall: {overall}")

# Teacher: Define Grading Logic
async def grading_logic(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)

    if not is_teacher(user_id):
        await update.message.reply_text("You are not authorized to define grading logic.")
        return

    if len(context.args) < 1:
        await update.message.reply_text("Usage: /grading_logic <description>")
        return

    description = " ".join(context.args)
    define_grading_logic(description)
    await update.message.reply_text("Grading logic defined.")

# Teacher: Upload Grades from CSV
async def upload_grades(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)

    if not is_teacher(user_id):
        await update.message.reply_text("You are not authorized to upload grades.")
        return

    if len(context.args) < 1:
        await update.message.reply_text("Usage: /upload_grades <csv_file_path>")
        return

    csv_file_path = context.args[0]

    try:
        with open(csv_file_path, newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                student_id, subject, homework, quizzes, midterm, final, attendance, overall = row
                try:
                    homework = float(homework)
                    quizzes = float(quizzes)
                    midterm = float(midterm)
                    final = float(final)
                    attendance = float(attendance)
                    overall = float(overall)
                    add_detailed_grade_to_db(student_id, subject, homework, quizzes, midterm, final, attendance, overall)
                except ValueError:
                    logger.error(f"Invalid grade value in CSV: {row}")
        await update.message.reply_text(f"Grades uploaded from {csv_file_path}")
    except Exception as e:
        logger.error(f"Error reading CSV file {csv_file_path}: {e}")
        await update.message.reply_text(f"Error uploading grades from {csv_file_path}")

# Teacher: View All Grades
async def view_all_grades(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)

    if not is_teacher(user_id):
        await update.message.reply_text("You are not authorized to view all grades.")
        return

    conn = db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT student_id, subject, homework, quizzes, midterm, final, attendance, overall FROM detailed_grades")
            grades = cursor.fetchall()
            if not grades:
                await update.message.reply_text("No grades found.")
                logger.info("No grades found in the database.")
            else:
                grade_list = ""
                for student_id, subject, homework, quizzes, midterm, final, attendance, overall in grades:
                    grade_list += f"Student ID: {student_id}\nSubject: {subject}\nHomework: {homework}\nQuizzes: {quizzes}\nMidterm: {midterm}\nFinal: {final}\nAttendance: {attendance}\nOverall: {overall}\n\n"
                await update.message.reply_text(f"All grades:\n{grade_list}")
        except sqlite3.Error as e:
            logger.error(f"Error fetching all grades: {e}")
            await update.message.reply_text("Error fetching all grades.")
        finally:
            conn.close()

# Student: View Grades
async def view_grades(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    college_id, role = LOGGED_IN.get(user_id, (None, None))

    if not college_id:
        await update.message.reply_text("Error: Your college ID could not be found. Please log in again.")
        return

    if role != "student":
        await update.message.reply_text("You are not authorized to view grades.")
        return

    conn = db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT overall FROM detailed_grades WHERE student_id = ?", (college_id,))
            grades = cursor.fetchall()
            logger.info(f"Grades fetched for student {college_id}: {grades}")
            if not grades:
                await update.message.reply_text("No grades found.")
            else:
                grade_list = "\n".join([f"Overall: {grade[0]}" for grade in grades])
                await update.message.reply_text(f"Your overall grade:\n{grade_list}")
        except sqlite3.Error as e:
            logger.error(f"Error fetching grades for student {college_id}: {e}")
            await update.message.reply_text("Error fetching your grades.")
        finally:
            conn.close()
            
# Student: View Detailed Grades
async def view_detailed_grades(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    college_id, role = LOGGED_IN.get(user_id, (None, None))

    if not college_id:
        await update.message.reply_text("Error: Your college ID could not be found. Please log in again.")
        return

    if role != "student":
        await update.message.reply_text("You are not authorized to view grades.")
        return

    conn = db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT subject, homework, quizzes, midterm, final, attendance, overall FROM detailed_grades WHERE student_id = ?", (college_id,))
            grades = cursor.fetchall()
            logger.info(f"Detailed grades fetched for student {college_id}: {grades}")
            if not grades:
                await update.message.reply_text("No grades found.")
            else:
                grade_list = "\n".join([f"Subject: {subject}, Homework: {homework}, Quizzes: {quizzes}, Midterm: {midterm}, Final: {final}, Attendance: {attendance}, Overall: {overall}" for subject, homework, quizzes, midterm, final, attendance, overall in grades])
                await update.message.reply_text(f"Your detailed grades:\n{grade_list}")
        except sqlite3.Error as e:
            logger.error(f"Error fetching detailed grades for student {college_id}: {e}")
            await update.message.reply_text("Error fetching your detailed grades.")
        finally:
            conn.close()

# Student/Teacher: View Grading Logic
async def view_grading_logic(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    logic = get_grading_logic()

    if not logic:
        await update.message.reply_text("No grading logic defined yet.")
        logger.info(f"No grading logic found for user {user_id}.")
        await update.message.reply_text("Test message: No logic found.")
    else:
        # Flatten the list of tuples to a list of strings
        logic_list = [desc[0] for desc in logic]
        logger.info(f"Constructed logic list: {logic_list}")

        # Join the list into a single string
        logic_text = "\n".join(logic_list)
        logger.info(f"Constructed logic text: {logic_text}")
        await update.message.reply_text("Test message: Logic found.")
        
        # Check if the logic_text is empty or None
        if not logic_text:
            await update.message.reply_text("No grading logic found or unable to construct the list.")
            logger.error(f"Failed to construct logic text for user {user_id}.")
        else:
            await update.message.reply_text(f"Current grading logic:\n{logic_text}")
            logger.info(f"Grading logic sent to user {user_id}: {logic_text}")
            
# Main: Start bot
def main():
    # Initialize database
    init_db()

    # Bot setup
    application = Application.builder().token("7517397372:AAGsNzeo_SAKdnNTRVhmHhaSFK7ViZ6PIvU").build()

    # Handlers
    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={COLLEGE_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, college_id)]},
        fallbacks=[],
    )
    application.add_handler(conversation_handler)
    application.add_handler(CommandHandler("logout", logout))
    application.add_handler(CommandHandler("add_grade", add_grade))
    application.add_handler(CommandHandler("upload_grades", upload_grades))
    application.add_handler(CommandHandler("view_all_grades", view_all_grades))
    application.add_handler(CommandHandler("view_grades", view_grades))
    application.add_handler(CommandHandler("view_detailed_grades", view_detailed_grades))
    application.add_handler(CommandHandler("grading_logic", grading_logic))
    application.add_handler(CommandHandler("view_grading_logic", view_grading_logic))  # Add this line
    application.add_handler(CommandHandler("reset", reset))

    # Run bot
    application.run_polling()

if __name__ == "__main__":
    main()