import os
import pandas as pd
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext
from telegram.ext import filters  # Updated import path for filters

# Set up logging to console for debugging
logging.basicConfig(level=logging.DEBUG)

# کلاس‌های داده‌ای
class Professor:
    def __init__(self, first_name, last_name, employee_id, course):
        self.first_name = first_name
        self.last_name = last_name
        self.employee_id = employee_id
        self.course = course

class Student:
    def __init__(self, first_name, last_name, student_id, course):
        self.first_name = first_name
        self.last_name = last_name
        self.student_id = student_id
        self.course = course
        self.grade = None

# داده‌های پیش‌فرض
professor = Professor("علی", "رضایی", "P123", "ریاضیات")
students = {
    "S001": Student("مریم", "محمدی", "S001", "ریاضیات"),
    "S002": Student("پویا", "کریمی", "S002", "ریاضیات"),
    "S003": Student("سارا", "نجفی", "S003", "ریاضیات")
}

# ذخیره فایل‌های آپلود شده
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# دستورات ربات
async def start(update: Update, context: CallbackContext):
    logging.debug("start() - User initiated /start")
    await update.message.reply_text(
        "به سیستم مدیریت نمرات خوش آمدید!\n"
        "استاد: برای آپلود نمرات از /upload استفاده کنید.\n"
        "دانشجو: برای مشاهده نمره از /check_grade استفاده کنید."
    )

async def upload_grades(update: Update, context: CallbackContext):
    logging.debug("upload_grades() - User initiated /upload")
    await update.message.reply_text("لطفاً شماره پرسنلی خود را وارد کنید:")

async def verify_professor(update: Update, context: CallbackContext):
    logging.debug(f"verify_professor() - Verifying employee ID: {update.message.text}")
    employee_id = update.message.text
    if employee_id == professor.employee_id:
        await update.message.reply_text("لطفاً فایل اکسل نمرات را ارسال کنید.")
        context.user_data['awaiting_excel'] = True
    else:
        await update.message.reply_text("شماره پرسنلی نامعتبر!")

async def handle_excel(update: Update, context: CallbackContext):
    logging.debug("handle_excel() - Handling uploaded excel file.")
    if 'awaiting_excel' in context.user_data:
        file = update.message.document.get_file()
        file_path = os.path.join(UPLOAD_FOLDER, 'grades.xlsx')
        await file.download(file_path)
        
        try:
            df = pd.read_excel(file_path)
            if {'StudentID', 'Grade'}.issubset(df.columns):
                for _, row in df.iterrows():
                    student_id = str(row['StudentID'])
                    if student_id in students:
                        students[student_id].grade = row['Grade']
                await update.message.reply_text("نمرات با موفقیت آپدیت شدند!")
            else:
                await update.message.reply_text("فرمت فایل نامعتبر است!")
        except Exception as e:
            await update.message.reply_text(f"خطا در پردازش فایل: {str(e)}")
        del context.user_data['awaiting_excel']

async def check_grade(update: Update, context: CallbackContext):
    logging.debug("check_grade() - User initiated /check_grade")
    await update.message.reply_text("لطفاً شماره دانشجویی خود را وارد کنید:")

async def show_grade(update: Update, context: CallbackContext):
    logging.debug(f"show_grade() - Showing grade for student ID: {update.message.text}")
    student_id = update.message.text
    if student_id in students:
        student = students[student_id]
        if student.grade is not None:
            await update.message.reply_text(f"نمره شما در درس {student.course}: {student.grade}")
        else:
            await update.message.reply_text("نمره شما هنوز ثبت نشده است.")
    else:
        await update.message.reply_text("شماره دانشجویی نامعتبر!")

# Main function to run the bot
def main():
    TOKEN = "token"
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("upload", upload_grades))
    application.add_handler(CommandHandler("check_grade", check_grade))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, 
        lambda update, context: (
            verify_professor(update, context) if context.user_data.get('awaiting_employee_id') 
            else show_grade(update, context)
        )))
    
    application.add_handler(MessageHandler(filters.Document(), handle_excel))

    logging.debug("Bot started, polling for updates.")
    application.run_polling()

# Run the bot
if __name__ == "__main__":
    main()
