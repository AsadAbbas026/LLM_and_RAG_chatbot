from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from functions.RAG import RAGChatbot
from functions.chatbot import LLMChatbot
from functions.delete_vectorStores import delete_chroma_db, delete_pinecone_index
import sqlite3
import hashlib
import secrets
import os

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # Replace with a secure secret key

UPLOAD_FOLDER = 'uploads'  # Directory where uploaded files will be saved
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx'}
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
llm_chatbot = LLMChatbot()

def create_connection():
    return sqlite3.connect('users.db')

def init_db():
    conn = create_connection()
    c = conn.cursor()
    # Create the users table if it does not exist
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def index():
    return render_template("index.html")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('register'))

        # Hash the password using SHA-256
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        # Insert the new user into the database
        conn = create_connection()
        c = conn.cursor()
        try:
            c.execute('INSERT INTO users (full_name, email, password) VALUES (?, ?, ?)', 
                      (full_name, email, hashed_password))
            conn.commit()
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email already exists! Please use a different email.', 'danger')
            return redirect(url_for('register'))
        finally:
            conn.close()

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Hash the provided password using SHA-256
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        # Check the credentials against the database
        conn = create_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE email = ? AND password = ?', 
                  (email, hashed_password))
        user = c.fetchone()
        conn.close()

        if user:
            session['user_id'] = user[0]  # Store user ID in session
            flash('Login successful!', 'success')
            return redirect(url_for('upload'))
        else:
            flash('Invalid email or password!', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route("/upload", methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        delete_chroma_db()
        delete_pinecone_index()
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filename)
            flash('File successfully uploaded!', 'success')
            return redirect(url_for('chat'))

        flash('File type not allowed or file too large', 'danger')
        return redirect(request.url)

    return render_template("upload.html")

@app.route("/chat", methods=['GET', 'POST'])
def chat():
    if request.method == 'POST':
        user_prompt = request.json.get('prompt')
        rag_chatbot = RAGChatbot()

        response = rag_chatbot.generate_response(user_prompt)

        # Check if the response is "Text not found" or confidence is low
        if not response or response == "Text not found":
            # Retrieve session history from Flask session
            session_history = [msg.to_dict() for msg in session.get('chat_history', [])]
            llm_chatbot.session_history.messages = [msg for msg in session_history]
            response = llm_chatbot.generate_response(user_prompt)
            # Update session history
            #session['chat_history'] = [msg.to_dict() for msg in llm_chatbot.session_history.messages]

        return jsonify({'response': response})
    return render_template("chat.html")

@app.route("/contact")
def  contact():
    return render_template("contact.html")

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    init_db()  # Ensure the database and table are created
    app.run(debug=True)
