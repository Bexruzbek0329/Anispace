import sqlite3 from 'sqlite3';
import { open } from 'sqlite';

class Database {
  constructor(dbPath) {
    this.dbPath = dbPath;
    this.db = null;
  }

  async init() {
    this.db = await open({
      filename: this.dbPath,
      driver: sqlite3.Database
    });

    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        is_vip BOOLEAN DEFAULT FALSE,
        joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      );

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
      );

      CREATE TABLE IF NOT EXISTS episodes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        anime_id INTEGER,
        episode_number INTEGER,
        video_id TEXT,
        title TEXT,
        views INTEGER DEFAULT 0,
        added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (anime_id) REFERENCES animes (id)
      );
    `);
  }

  async addUser(userId, username, firstName, lastName) {
    return this.db.run(
      'INSERT OR IGNORE INTO users (user_id, username, first_name, last_name) VALUES (?, ?, ?, ?)',
      [userId, username, firstName, lastName]
    );
  }

  async searchAnime(query) {
    return this.db.all(
      'SELECT * FROM animes WHERE name LIKE ?',
      [`%${query}%`]
    );
  }

  async getVipStatus(userId) {
    const result = await this.db.get(
      'SELECT is_vip FROM users WHERE user_id = ?',
      [userId]
    );
    return result ? result.is_vip : false;
  }

  async getAllAnime() {
    return this.db.all('SELECT * FROM animes ORDER BY added_date DESC');
  }
}

export const db = new Database('anime_bot.db');