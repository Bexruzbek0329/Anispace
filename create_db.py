import sqlite3
import os

def create_database():
    # Remove existing database if it exists
    if os.path.exists('anime_bot.db'):
        os.remove('anime_bot.db')
    
    # Connect to SQLite database (creates new if not exists)
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()

    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            is_vip BOOLEAN DEFAULT FALSE,
            joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create animes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS animes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            season INTEGER,
            episodes INTEGER,
            genre TEXT,
            language TEXT,
            thumbnail TEXT,
            views INTEGER DEFAULT 0,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create episodes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS episodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anime_id INTEGER,
            episode_number INTEGER,
            video_id TEXT,
            title TEXT,
            views INTEGER DEFAULT 0,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (anime_id) REFERENCES animes (id) ON DELETE CASCADE
        )
    ''')

    # Create indices for better performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_animes_added_date ON animes(added_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_episodes_anime_id ON episodes(anime_id)')

    # Commit changes and close connection
    conn.commit()
    conn.close()

if __name__ == '__main__':
    create_database()