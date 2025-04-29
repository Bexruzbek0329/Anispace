import aiosqlite
import asyncio
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("database.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_name):
        self.db_name = db_name

    async def init(self):
        """Initialize database - FIXED to not drop tables on every init"""
        try:
            async with aiosqlite.connect(self.db_name) as db:
                await db.execute('PRAGMA foreign_keys = ON')
                
                # Create tables if they don't exist instead of dropping them
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER UNIQUE NOT NULL,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        is_admin INTEGER DEFAULT 0,
                        is_vip INTEGER DEFAULT 0,
                        joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                await db.execute('''
                    CREATE TABLE IF NOT EXISTS animes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        season INTEGER NOT NULL,
                        episodes INTEGER NOT NULL,
                        genre TEXT,
                        language TEXT,
                        thumbnail TEXT,
                        views INTEGER DEFAULT 0,
                        added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                await db.execute('''
                    CREATE TABLE IF NOT EXISTS episodes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        anime_id INTEGER NOT NULL,
                        episode_number INTEGER NOT NULL,
                        video_file_id TEXT NOT NULL,
                        title TEXT,
                        views INTEGER DEFAULT 0,
                        added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (anime_id) REFERENCES animes (id) ON DELETE CASCADE
                    )
                ''')

                await db.commit()
                logger.info("Database initialization completed successfully")
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            raise

    # --- USER FUNCTIONS ---

    async def add_user(self, user_id, username, first_name, last_name=None):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                await db.execute(
                    'INSERT OR IGNORE INTO users (user_id, username, first_name, last_name) VALUES (?, ?, ?, ?)',
                    (user_id, username, first_name, last_name)
                )
                await db.commit()
                logger.info(f"User added or updated: {user_id}")
        except Exception as e:
            logger.error(f"Error adding user {user_id}: {e}")

    async def get_user(self, user_id):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                async with db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)) as cursor:
                    return await cursor.fetchone()
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None

    async def get_vip_status(self, user_id):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                async with db.execute('SELECT is_vip FROM users WHERE user_id = ?', (user_id,)) as cursor:
                    result = await cursor.fetchone()
                    return bool(result[0]) if result else False
        except Exception as e:
            logger.error(f"Error getting VIP status for user {user_id}: {e}")
            return False

    async def set_vip_status(self, user_id, status):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                await db.execute('UPDATE users SET is_vip = ? WHERE user_id = ?', (int(status), user_id))
                await db.commit()
                logger.info(f"VIP status updated for user {user_id}: {status}")
        except Exception as e:
            logger.error(f"Error setting VIP status for user {user_id}: {e}")

    async def get_all_users(self):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                async with db.execute('SELECT * FROM users ORDER BY joined_date DESC') as cursor:
                    return await cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []

    async def get_users_count(self):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                async with db.execute('SELECT COUNT(*) FROM users') as cursor:
                    result = await cursor.fetchone()
                    return result[0] if result else 0
        except Exception as e:
            logger.error(f"Error getting users count: {e}")
            return 0

    async def get_today_users_count(self):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                async with db.execute('SELECT COUNT(*) FROM users WHERE date(joined_date) = date("now")') as cursor:
                    result = await cursor.fetchone()
                    return result[0] if result else 0
        except Exception as e:
            logger.error(f"Error getting today's users count: {e}")
            return 0

    async def get_vip_users_count(self):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                async with db.execute('SELECT COUNT(*) FROM users WHERE is_vip = 1') as cursor:
                    result = await cursor.fetchone()
                    return result[0] if result else 0
        except Exception as e:
            logger.error(f"Error getting VIP users count: {e}")
            return 0

    # --- ANIME FUNCTIONS ---

    async def add_anime(self, name, season, episodes, genre, language, thumbnail):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                await db.execute(
                    'INSERT INTO animes (name, season, episodes, genre, language, thumbnail) VALUES (?, ?, ?, ?, ?, ?)',
                    (name, season, episodes, genre, language, thumbnail)
                )
                await db.commit()
                logger.info(f"Anime added: {name}, Season {season}")
                
                # Get the id of the inserted anime
                async with db.execute("SELECT last_insert_rowid()") as cursor:
                    result = await cursor.fetchone()
                    return result[0] if result else None
        except Exception as e:
            logger.error(f"Error adding anime {name}: {e}")
            return None

    async def get_all_anime(self):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                async with db.execute('SELECT * FROM animes ORDER BY added_date DESC') as cursor:
                    return await cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting all anime: {e}")
            return []

    async def get_anime(self, anime_id):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                async with db.execute('SELECT * FROM animes WHERE id = ?', (anime_id,)) as cursor:
                    return await cursor.fetchone()
        except Exception as e:
            logger.error(f"Error getting anime {anime_id}: {e}")
            return None

    async def update_anime(self, anime_id, name, season, episodes, genre, language, thumbnail):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                await db.execute('''
                    UPDATE animes
                    SET name = ?, season = ?, episodes = ?, genre = ?, language = ?, thumbnail = ?
                    WHERE id = ?
                ''', (name, season, episodes, genre, language, thumbnail, anime_id))
                await db.commit()
                logger.info(f"Anime updated: ID {anime_id}")
        except Exception as e:
            logger.error(f"Error updating anime {anime_id}: {e}")

    async def delete_anime(self, anime_id):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                await db.execute('DELETE FROM animes WHERE id = ?', (anime_id,))
                await db.commit()
                logger.info(f"Anime deleted: ID {anime_id}")
        except Exception as e:
            logger.error(f"Error deleting anime {anime_id}: {e}")

    async def get_anime_count(self):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                async with db.execute('SELECT COUNT(*) FROM animes') as cursor:
                    result = await cursor.fetchone()
                    return result[0] if result else 0
        except Exception as e:
            logger.error(f"Error getting anime count: {e}")
            return 0

    async def increment_anime_views(self, anime_id):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                await db.execute('UPDATE animes SET views = views + 1 WHERE id = ?', (anime_id,))
                await db.commit()
                logger.info(f"Anime views incremented: ID {anime_id}")
        except Exception as e:
            logger.error(f"Error incrementing views for anime {anime_id}: {e}")

    async def search_anime(self, query):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                pattern = f"%{query.lower()}%"
                async with db.execute('SELECT * FROM animes WHERE LOWER(name) LIKE ?', (pattern,)) as cursor:
                    return await cursor.fetchall()
        except Exception as e:
            logger.error(f"Error searching anime with query '{query}': {e}")
            return []

    async def get_top_animes(self, limit=10):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                async with db.execute('SELECT * FROM animes ORDER BY views DESC LIMIT ?', (limit,)) as cursor:
                    return await cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting top {limit} animes: {e}")
            return []

    async def get_latest_animes(self, limit=10):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                async with db.execute('SELECT * FROM animes ORDER BY added_date DESC LIMIT ?', (limit,)) as cursor:
                    return await cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting latest {limit} animes: {e}")
            return []

    async def get_random_anime(self):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                async with db.execute('SELECT * FROM animes ORDER BY RANDOM() LIMIT 1') as cursor:
                    return await cursor.fetchone()
        except Exception as e:
            logger.error(f"Error getting random anime: {e}")
            return None

    # --- EPISODE FUNCTIONS ---

    async def add_episode(self, anime_id, episode_number, video_id, title):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                await db.execute(
                    'INSERT INTO episodes (anime_id, episode_number, video_file_id, title) VALUES (?, ?, ?, ?)',
                    (anime_id, episode_number, video_id, title)
                )
                await db.commit()
                logger.info(f"Episode added: Anime ID {anime_id}, Episode {episode_number}")
        except Exception as e:
            logger.error(f"Error adding episode {episode_number} for anime {anime_id}: {e}")

    async def get_episodes(self, anime_id):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                async with db.execute('SELECT * FROM episodes WHERE anime_id = ? ORDER BY episode_number', (anime_id,)) as cursor:
                    return await cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting episodes for anime {anime_id}: {e}")
            return []

    async def get_episode(self, episode_id):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                async with db.execute('SELECT * FROM episodes WHERE id = ?', (episode_id,)) as cursor:
                    return await cursor.fetchone()
        except Exception as e:
            logger.error(f"Error getting episode {episode_id}: {e}")
            return None

    async def get_episode_by_number(self, anime_id, episode_number):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                async with db.execute('SELECT * FROM episodes WHERE anime_id = ? AND episode_number = ?', (anime_id, episode_number)) as cursor:
                    return await cursor.fetchone()
        except Exception as e:
            logger.error(f"Error getting episode {episode_number} for anime {anime_id}: {e}")
            return None

    async def get_episodes_count(self):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                async with db.execute('SELECT COUNT(*) FROM episodes') as cursor:
                    result = await cursor.fetchone()
                    return result[0] if result else 0
        except Exception as e:
            logger.error(f"Error getting episodes count: {e}")
            return 0

    async def increment_episode_views(self, episode_id):
        try:
            async with aiosqlite.connect(self.db_name) as db:
                await db.execute('UPDATE episodes SET views = views + 1 WHERE id = ?', (episode_id,))
                await db.commit()
                logger.info(f"Episode views incremented: ID {episode_id}")
        except Exception as e:
            logger.error(f"Error incrementing views for episode {episode_id}: {e}")

# Initialize database
def main():
    db = Database("anime_bot.db")
    asyncio.run(db.init())
    print("Database yaratildi va tayyor!")

if __name__ == "__main__":
    main()