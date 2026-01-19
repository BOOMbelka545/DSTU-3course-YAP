# score_db.py
"""
score_db.py

Минимальный слой хранения результатов.
Хранит:
- last_score: результат последней завершённой игры
- best_score: лучший результат за всё время
"""

import sqlite3


class ScoreDB:
    """Обёртка над SQLite для чтения/записи пар 'ключ-значение' (int)."""

    def __init__(self, path: str = "scores.db"):
        """
        Создаёт экземпляр БД и инициализирует таблицы при необходимости.

        """
        self.path = path
        self._init()

    def _init(self) -> None:
        """Создаёт таблицу stats, если она ещё не существует."""
        with sqlite3.connect(self.path) as con:
            con.execute(
                "CREATE TABLE IF NOT EXISTS stats ("
                "key TEXT PRIMARY KEY, "
                "value INTEGER NOT NULL)"
            )
            con.commit()

    def get(self, key: str, default: int = 0) -> int:
        """
        Возвращает значение по ключу.
        """
        with sqlite3.connect(self.path) as con:
            cur = con.execute("SELECT value FROM stats WHERE key = ?", (key,))
            row = cur.fetchone()
            return int(row[0]) if row is not None else int(default)

    def set(self, key: str, value: int) -> None:
        """
        Записывает значение по ключу.
        """
        with sqlite3.connect(self.path) as con:
            con.execute(
                "INSERT INTO stats(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, int(value)),
            )
            con.commit()
