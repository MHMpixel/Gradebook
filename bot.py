import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler
from database import init_db, add_user, is_teacher, add_grade_to_db, get_grades_for_student

# Setup logging for the bot
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants for the conversation
COLLEGE_ID = 0  # State for asking college ID

# Command to start the bot and ask for the college ID
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Welcome! Please enter your college ID to proceed.")
    return COLLEGE_ID

# Function to handle the college ID input and verify if the user is whitelisted
async def college_id(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)  # Use string for consistency
    college_id = update.message.text.strip()

    # Hardcoded roles for simplicity
    if college_id == "123":
        role = "teacher"
    elif college_id in ["1", "2", "3"]:
        role = "student"
    else:
        await update.message.reply_text("Access denied. Invalid college ID.")
        return ConversationHandler.END

    # Add user to the database
    add_user(user_id, college_id, role)

    if role == "teacher":
        await update.message.reply_text("College ID verified! You now have access to teacher features.")
        await update.message.reply_text("Type /add_grade to add grades.")
    else:
        await update.message.reply_text("College ID verified! You now have access to student features.")
        await update.message.reply_text("Type /view_grades to view your grades.")

    return ConversationHandler.END

# Teacher's "Add Grade" feature
async def add_grade(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)

    if not is_teacher(user_id):
        await update.message.reply_text("You are not authorized to add grades.")
        return

    # Check if the correct arguments are provided
    if len(context.args) < 3:
        await update.message.reply_text("Usage: /add_grade <student_id> <subject> <grade>")
        return

    student_id = context.args[0]  # Ensure this is consistent with user IDs in the database
    subject = context.args[1]
    grade = float(context.args[2])

    # Add the grade to the database
    add_grade_to_db(student_id, subject, grade)
    await update.message.reply_text(f"Grade added for student {student_id}: {subject} - {grade}")

# Student's "View Grades" feature
async def view_grades(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)

    # Fetch grades for the student
    grades = get_grades_for_student(user_id)

    if not grades:
        await update.message.reply_text("No grades found.")
        return

    grade_details = "\n".join([f"{subject}: {grade}" for subject, grade in grades])
    await update.message.reply_text(f"Your grades:\n{grade_details}")

# Main function to start the bot
def main():
    # Initialize the database
    init_db()

    # Create the bot application
    application = Application.builder().token("7517397372:AAGsNzeo_SAKdnNTRVhmHhaSFK7ViZ6PIvU").build()

    # Conversation handler to ask for the college ID
    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            COLLEGE_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, college_id)],
        },
        fallbacks=[],
    )

    # Register handlers
    application.add_handler(conversation_handler)
    application.add_handler(CommandHandler("add_grade", add_grade))
    application.add_handler(CommandHandler("view_grades", view_grades))

    # Start the bot
    application.run_polling()

if __name__ == "__main__":
    main()
