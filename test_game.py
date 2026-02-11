
# -*- coding: utf-8 -*-
"""
test_game.py

Юнит-тесты для ключевой логики проекта:
- ScoreDB: сохранение/чтение last_score и best_score
- SnakeGame: движение, рост, счёт, game_over (стены)
- Fruit: корректный спавн в свободной клетке

Тесты не открывают окно и не требуют реальных ассетов:
- pygame.image.load и pygame.mixer.Sound подменяются заглушками.

Запуск:
    python -m unittest -v test_game.py
"""

import os
import unittest
import tempfile

import pygame
from pygame.math import Vector2

from score_db import ScoreDB
from snake_game import SnakeGame


class _DummySurface:
    """Заглушка Surface, чтобы методы загрузки ассетов не падали в тестах."""
    def convert_alpha(self):
        return self


class _DummySound:
    """Заглушка Sound, чтобы вызов play() не падал в тестах."""
    def play(self):
        return None


def _patch_pygame_assets():
    """
    Подменяет загрузку картинок и звуков на заглушки.

    Зачем:
    - тесты должны работать без файлов Graphics/* и Sound/*
    - не должен открываться video mode (окно) ради convert_alpha()
    """
    pygame.image.load = lambda *args, **kwargs: _DummySurface()
    pygame.mixer.Sound = lambda *args, **kwargs: _DummySound()


class TestScoreDB(unittest.TestCase):
    """Тесты слоя хранения результатов (SQLite)."""

    def test_get_default_when_absent(self):
        """Если ключа нет в БД — get() возвращает default."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "scores.db")
            db = ScoreDB(db_path)

            self.assertEqual(db.get("last_score", 0), 0)
            self.assertEqual(db.get("best_score", 123), 123)

    def test_set_and_get(self):
        """set() сохраняет значения, get() возвращает сохранённые."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "scores.db")
            db = ScoreDB(db_path)

            db.set("last_score", 7)
            db.set("best_score", 11)

            self.assertEqual(db.get("last_score", 0), 7)
            self.assertEqual(db.get("best_score", 0), 11)

    def test_upsert_overwrites(self):
        """Повторный set() по тому же ключу должен обновлять значение (upsert)."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "scores.db")
            db = ScoreDB(db_path)

            db.set("best_score", 10)
            db.set("best_score", 15)

            self.assertEqual(db.get("best_score", 0), 15)


class TestSnakeGameCore(unittest.TestCase):
    """Тесты ключевой логики SnakeGame без UI (без окна)."""

    @classmethod
    def setUpClass(cls):
        """Единожды инициализируем pygame и ставим заглушки ассетов."""
        pygame.init()
        _patch_pygame_assets()

    def make_game(self, n=10, fruits=1):
        """Утилита: создаёт игру с заданным размером поля и кол-вом фруктов."""
        g = SnakeGame(cell_number=n, fruits_count=fruits)
        g.reset()
        return g

    def test_initial_state_not_game_over(self):
        """После reset() игра не должна быть в состоянии game_over и счёт = 0."""
        g = self.make_game()
        self.assertFalse(g.is_game_over())
        self.assertEqual(g.get_score(), 0)

    def test_no_move_when_direction_zero(self):
        """Если направление (0,0), update() не должен двигать змейку."""
        g = self.make_game()
        start_head = g.snake.body[0].copy()

        g.update()

        self.assertEqual(g.snake.body[0], start_head)

    def test_move_one_step_changes_head(self):
        """При направлении вправо голова должна сдвинуться на +1 по X за один update()."""
        g = self.make_game()
        g.snake.direction = Vector2(1, 0)
        start_head = g.snake.body[0].copy()

        g.update()

        self.assertEqual(g.snake.body[0], start_head + Vector2(1, 0))

    def test_add_block_grows_on_next_move(self):
        """После add_block() длина должна увеличиться на 1 на следующем update()."""
        g = self.make_game()
        g.snake.direction = Vector2(1, 0)

        start_len = len(g.snake.body)
        g.snake.add_block()
        g.update()

        self.assertEqual(len(g.snake.body), start_len + 1)
        self.assertEqual(g.get_score(), 1)

    def test_wall_collision_sets_game_over(self):
        """Выход головы за границы поля должен выставлять game_over=True."""
        g = self.make_game(n=5, fruits=1)

        # Голова на правой границе, шаг вправо => выход за поле
        g.snake.body = [Vector2(4, 2), Vector2(3, 2), Vector2(2, 2)]
        g.snake.direction = Vector2(1, 0)

        g.update()

        self.assertTrue(g.is_game_over())

    def test_spawned_fruit_not_on_snake(self):
        """Fruit.spawn() не должен ставить фрукт на клетку, занятую змейкой."""
        g = self.make_game(n=10, fruits=1)

        g.snake.body = [Vector2(1, 1), Vector2(1, 2), Vector2(1, 3), Vector2(1, 4)]
        occupied = {(int(b.x), int(b.y)) for b in g.snake.body}

        g.fruits[0].spawn(occupied)

        self.assertNotIn((int(g.fruits[0].pos.x), int(g.fruits[0].pos.y)), occupied)


if __name__ == "__main__":
    """Локальный запуск тестов напрямую (без python -m unittest)."""
    unittest.main(verbosity=2)
