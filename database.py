import sqlite3

def init_db():
    conn = sqlite3.connect('ideas.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ideas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            category TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_idea(content, category="General"):
    conn = sqlite3.connect('ideas.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO ideas (content, category) VALUES (?, ?)', (content, category))
    conn.commit()
    conn.close()

def get_all_ideas():
    conn = sqlite3.connect('ideas.db')
    cursor = conn.cursor()
    cursor.execute('SELECT content, category FROM ideas ORDER BY timestamp DESC')
    ideas = cursor.fetchall()
    conn.close()
    return ideas

def get_ideas():
    conn = sqlite3.connect('smartlife.db')
    cursor = conn.cursor()
    # ID ni ham olish shart!
    cursor.execute("SELECT id, content, category, date FROM ideas ORDER BY id DESC")
    ideas = cursor.fetchall()
    conn.close()
    return ideas

    

def delete_idea(idea_id):
    conn = sqlite3.connect('smartlife.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ideas WHERE id = ?", (idea_id,))
    conn.commit()
    conn.close()
