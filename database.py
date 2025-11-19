import sqlite3
import json
import logging
from config import DATABASE_NAME

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.conn = sqlite3.connect(DATABASE_NAME, check_same_thread=False)
        self.create_tables()
    
    def create_tables(self):
        # Adminlar jadvali
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Fanlar jadvali
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                file_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Foydalanuvchi sessiyalari
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                user_id INTEGER,
                subject_id INTEGER,
                questions TEXT,
                current_question INTEGER,
                answers TEXT,
                score INTEGER,
                total_questions INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, subject_id)
            )
        ''')
        
        # Natijalar
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                user_name TEXT,
                subject_id INTEGER,
                score INTEGER,
                total_questions INTEGER,
                percentage REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()
    
    def is_admin(self, user_id):
        cursor = self.conn.execute('SELECT 1 FROM admins WHERE user_id = ?', (user_id,))
        return cursor.fetchone() is not None
    
    def add_admin(self, user_id, username):
        try:
            self.conn.execute('INSERT OR IGNORE INTO admins (user_id, username) VALUES (?, ?)', (user_id, username))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Admin qo'shishda xatolik: {e}")
            return False
    
    def remove_admin(self, user_id):
        try:
            self.conn.execute('DELETE FROM admins WHERE user_id = ?', (user_id,))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Admin o'chirishda xatolik: {e}")
            return False
    
    def get_admins(self):
        cursor = self.conn.execute('SELECT user_id, username FROM admins')
        return cursor.fetchall()
    
    def add_subject(self, name, file_path):
        try:
            self.conn.execute(
                'INSERT OR REPLACE INTO subjects (name, file_path) VALUES (?, ?)',
                (name, file_path)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Fanni qo'shishda xatolik: {e}")
            return False
    
    def get_subjects(self):
        cursor = self.conn.execute('SELECT id, name FROM subjects ORDER BY id')
        return cursor.fetchall()
    
    def get_subject_file(self, subject_id):
        cursor = self.conn.execute('SELECT name, file_path FROM subjects WHERE id = ?', (subject_id,))
        return cursor.fetchone()
    
    def save_user_session(self, user_id, subject_id, questions, current_question, answers, score, total_questions):
        questions_json = json.dumps(questions, ensure_ascii=False)
        answers_json = json.dumps(answers, ensure_ascii=False)
        
        self.conn.execute('''
            INSERT OR REPLACE INTO user_sessions 
            (user_id, subject_id, questions, current_question, answers, score, total_questions)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, subject_id, questions_json, current_question, answers_json, score, total_questions))
        self.conn.commit()
    
    def get_user_session(self, user_id, subject_id):
        cursor = self.conn.execute('''
            SELECT questions, current_question, answers, score, total_questions 
            FROM user_sessions WHERE user_id = ? AND subject_id = ?
        ''', (user_id, subject_id))
        row = cursor.fetchone()
        if row:
            return {
                'questions': json.loads(row[0]),
                'current_question': row[1],
                'answers': json.loads(row[2]),
                'score': row[3],
                'total_questions': row[4]
            }
        return None
    
    def delete_user_session(self, user_id, subject_id):
        self.conn.execute('DELETE FROM user_sessions WHERE user_id = ? AND subject_id = ?', (user_id, subject_id))
        self.conn.commit()
    
    def save_result(self, user_id, user_name, subject_id, score, total_questions, percentage):
        self.conn.execute('''
            INSERT INTO results (user_id, user_name, subject_id, score, total_questions, percentage)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, user_name, subject_id, score, total_questions, percentage))
        self.conn.commit()