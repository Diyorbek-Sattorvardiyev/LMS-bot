import firebase_admin
from firebase_admin import credentials, firestore
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    ContextTypes,
)

# Firebase initialization
cred = credentials.Certificate("lmsbot-18a44-firebase-adminsdk-mpn8z-9ed43638d1.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Function to add a student to the database (Initially inactive)
def add_student_to_db(student_id, name):
    db.collection("students").document(student_id).set({
        "name": name,
        "is_active": False,  
        "assignments": {},
        "results": {},
    })


def activate_student(student_id):
    db.collection("students").document(student_id).update({"is_active": True})


def create_assignment(assignment_id, title, description, deadline):
    db.collection("assignments").document(assignment_id).set({
        "title": title,
        "description": description,
        "deadline": deadline,
        "submissions": {},
    })

# Function to submit an assignment
def submit_assignment(student_id, assignment_id, submission):
    assignment_ref = db.collection("assignments").document(assignment_id)
    assignment = assignment_ref.get().to_dict()

    if assignment:
        submissions = assignment.get("submissions", {})
        submissions[student_id] = submission
        assignment_ref.update({"submissions": submissions})

# Function to grade an assignment
def grade_assignment(assignment_id, student_id, grade):
    assignment_ref = db.collection("assignments").document(assignment_id)
    assignment = assignment_ref.get().to_dict()

    if assignment:
        submissions = assignment.get("submissions", {})
        if student_id in submissions:
            db.collection("students").document(student_id).update({
                f"results.{assignment_id}": grade
            })

# Notify all students about a new assignment
async def notify_students(context, assignment_id, title, description, deadline):
    students = db.collection("students").stream()
    message = (
        f"Yangi topshiriq yaratilgan:\n\n"
        f"ID: {assignment_id}\nSarlavha: {title}\nTavsif: {description}\nMuddat: {deadline}"
    )
    for student in students:
        student_data = student.to_dict()
        student_id = student.id
        if student_data.get("is_active", False):  
            await context.bot.send_message(chat_id=student_id, text=message)

# Command Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    await update.message.reply_text(f"Salom {user.first_name}! LMS botiga xush kelibsiz.")

    # Role-based menu with inline buttons
    keyboard = [
        [
            InlineKeyboardButton("Talaba", callback_data="role_student"),
            InlineKeyboardButton("Admin", callback_data="role_admin"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Siz Talaba yoki Adminmisiz?", reply_markup=reply_markup)

async def role_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "role_student":
        await query.edit_message_text("Xush kelibsiz, Talaba!\n /submit buyrug'ini topshiriqlarni yuborish uchun va \n/results buyrug'ini natijalarni ko'rish uchun ishlating.")
    elif query.data == "role_admin":
        await query.edit_message_text("Xush kelibsiz, Admin!\n /create buyrug'ini topshiriqlar yaratish uchun,\n /grade buyrug'ini topshiriqlarni baholash uchun,\n /add buyrug'ini talabalarni qo'shish uchun, va \n/view_students buyrug'ini talabalar ro'yxatini ko'rish uchun ishlating.")

# Student Commands
async def submit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Iltimos, topshiriq ID sini va topshiriqni yuboring:\n`<assignment_id> <your_submission>` formatida yuboring.")

async def save_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    student_id = str(user.id)
    text = update.message.text.split(" ", 1)

    if len(text) < 2:
        await update.message.reply_text("Noto'g'ri format. Iltimos, quyidagi formatda yuboring: <assignment_id> <your_submission>")
        return

    assignment_id, submission = text
    submit_assignment(student_id, assignment_id, submission)
    await update.message.reply_text("Topshiriq muvaffaqiyatli saqlandi!")

async def results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    student_id = str(user.id)

    student_ref = db.collection("students").document(student_id)
    student = student_ref.get().to_dict()

    if student and student.get("is_active"):
        results = student.get("results", {})
        if results:
            response = "Sizning natijalaringiz:\n"
            for assignment_id, grade in results.items():
                response += f"{assignment_id}: {grade}\n"
            await update.message.reply_text(response)
        else:
            await update.message.reply_text("Hali natijalar mavjud emas.")
    else:
        await update.message.reply_text("Talaba topilmadi yoki faollashtirilmagan. Iltimos, admin bilan bog'laning.")

# Admin Commands
async def create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Iltimos, topshiriq ma'lumotlarini quyidagi formatda yuboring:\n`<assignment_id> <title> <description> <deadline>`")

async def save_assignment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.split(" ", 3)

    if len(text) < 4:
        await update.message.reply_text("Noto'g'ri format. Iltimos, quyidagi formatda yuboring: <assignment_id> <title> <description> <deadline>")
        return

    assignment_id, title, description, deadline = text
    create_assignment(assignment_id, title, description, deadline)
    await notify_students(context, assignment_id, title, description, deadline)
    await update.message.reply_text("Topshiriq yaratildi va talabalar xabardor qilindi!")

async def grade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Iltimos, baholash ma'lumotlarini quyidagi formatda yuboring:\n`<assignment_id> <student_id> <grade>`")

async def save_grade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.split(" ", 2)

    if len(text) < 3:
        await update.message.reply_text("Noto'g'ri format. Iltimos, quyidagi formatda yuboring: <assignment_id> <student_id> <grade>")
        return

    assignment_id, student_id, grade = text
    grade_assignment(assignment_id, student_id, grade)
    await update.message.reply_text("Baholash muvaffaqiyatli saqlandi!")

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Iltimos, talaba ma'lumotlarini quyidagi formatda yuboring:\n`<student_id> <name>`")

async def save_student(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.split(" ", 1)

    if len(text) < 2:
        await update.message.reply_text("Noto'g'ri format. Iltimos, quyidagi formatda yuboring: <student_id> <name>")
        return

    student_id, name = text
    add_student_to_db(student_id, name)
    await update.message.reply_text("Talaba muvaffaqiyatli qo'shildi! Admin tasdiqlashini kuting.")

async def view_students(update: Update, context: ContextTypes.DEFAULT_TYPE):
    students = db.collection("students").stream()
    student_list = "Talabalar ro'yxati:\n"
    for student in students:
        student_data = student.to_dict()
        is_active = student_data.get("is_active", False)  # Default to False if not found
        
        student_list += f"{student.id}: {student_data['name']} - {'Faol' if is_active else 'Faol emas'}\n"
    
    # Create inline buttons for each student to activate them
    keyboard = [
        [InlineKeyboardButton(f"Faollashtirish: {student_data['name']}", callback_data=f"activate_{student.id}") for student in students]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(student_list, reply_markup=reply_markup)

async def activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    student_id = query.data.split("_")[1]
    activate_student(student_id)
    await query.edit_message_text(f"Talaba {student_id} faollashtirildi!")

# Main Function
def main():
    app = ApplicationBuilder().token("7635414762:AAFT3MwKoWr6EfCoRBe9oTofJ1NKIiIzjSA").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(role_selection))
    app.add_handler(CommandHandler("submit", submit))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^\S+ \S+$'), save_submission))
    app.add_handler(CommandHandler("results", results))
    app.add_handler(CommandHandler("create", create))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^\S+ \S+ .+ \S+$'), save_assignment))
    app.add_handler(CommandHandler("grade", grade))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^\S+ \S+ \S+$'), save_grade))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^\S+ \S+$'), save_student))
    app.add_handler(CommandHandler("view_students", view_students))
    app.add_handler(CallbackQueryHandler(activate, pattern=r"^activate_"))

    app.run_polling()

if __name__ == "__main__":
    main()
