# main.py
"""
main.py

UI-слой игры:
- Управляет окнами/состояниями (меню, настройки, игра, экран проигрыша)
- Обрабатывает ввод (клавиатура/мышь)
- Запускает тики обновления игры (таймер SCREEN_UPDATE)
- Показывает статистику (предыдущий/лучший результат) и сохраняет её в SQLite через ScoreDB

main.py импортирует snake_game.py и score_db.py.
"""

import pygame
import sys

from snake_game import SnakeGame
from score_db import ScoreDB


class Button:
    """Простая UI-кнопка: рисование и проверка клика мышью."""

    def __init__(self, rect, text, font):
        """
        Args:
            rect: (x, y, w, h) кнопки.
            text: Текст на кнопке.
            font: pygame Font для рендера текста.
        """
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self._render()

    def _render(self) -> None:
        """Создаёт текстовую поверхность для кнопки (кэш)."""
        self.text_surf = self.font.render(self.text, True, (56, 74, 12))
        self.text_rect = self.text_surf.get_rect(center=self.rect.center)

    def draw(self, screen, selected: bool = False) -> None:
        """
        Рисует кнопку.

        Args:
            screen: Экран pygame.
            selected: Подсветка (например выбранный размер поля).
        """
        pygame.draw.rect(screen, (167, 209, 61), self.rect, border_radius=14)
        border_w = 5 if selected else 3
        pygame.draw.rect(screen, (56, 74, 12), self.rect, width=border_w, border_radius=14)
        screen.blit(self.text_surf, self.text_rect)

    def is_clicked(self, event) -> bool:
        """
        Проверяет, был ли клик мышью внутри кнопки.

        Args:
            event: pygame event.

        Returns:
            bool: True если ЛКМ нажата и координата внутри rect.
        """
        return (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and self.rect.collidepoint(event.pos)
        )


class GameApp:
    """
    Главный контроллер приложения.

    Содержит state machine:
    - MENU: старт/настройки
    - SETTINGS: выбор размера поля и кол-ва фруктов
    - GAME: игровой процесс
    - GAME_OVER: серый экран "ПОТРАЧЕНО" + кнопки меню/заново

    Также управляет сохранением last/best score через ScoreDB.
    """

    STATE_MENU = "menu"
    STATE_SETTINGS = "settings"
    STATE_GAME = "game"
    STATE_GAME_OVER = "game_over"

    def __init__(self):
        """Инициализация pygame, окна, ассетов, БД и параметров состояния."""
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.init()

        self.cell_size = 40

        # defaults
        self.cell_number = 20
        self.fruits_count = 5

        # Tick event: скорость "шага" змейки
        self.SCREEN_UPDATE = pygame.USEREVENT
        pygame.time.set_timer(self.SCREEN_UPDATE, 150)

        self.clock = pygame.time.Clock()
        self.state = self.STATE_MENU

        self.game = None

        # Важно: set_mode ДО convert_alpha()
        self.apply_window()
        self._load_assets()

        # DB
        self.db = ScoreDB("scores.db")
        self.last_score = self.db.get("last_score", 0)
        self.best_score = self.db.get("best_score", 0)

        # Текущий результат (для экрана GAME_OVER)
        self.current_score = 0

        # Защита от многократного сохранения game_over
        self._saved_game_over = False

        # settings pending (изменяются в SETTINGS до APPLY)
        self.pending_cell_number = self.cell_number
        self.pending_fruits_count = self.fruits_count
        self._sync_fruits_label()

    def apply_window(self) -> None:
        """Создаёт/пересоздаёт окно на основе cell_number и cell_size."""
        self.width = self.cell_number * self.cell_size
        self.height = self.cell_number * self.cell_size
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Snake")

    def _load_assets(self) -> None:
        """Загружает ресурсы (картинки/шрифты) и собирает UI."""
        self.apple = pygame.image.load("photos/apple.png").convert_alpha()

        # Оставляем "старое" решение со шрифтом (как просили)
        self.game_font = pygame.font.Font("font/arialmt.ttf", 25)
        self.title_font = pygame.font.Font("font/arialmt.ttf", 52)

        self._build_menu_ui()
        self._build_settings_ui()
        self._build_game_over_ui()

    def _build_menu_ui(self) -> None:
        """Создаёт кнопки и геометрию для экрана меню."""
        btn_w, btn_h = 280, 70
        btn_x = (self.width - btn_w) // 2
        start_y = (self.height // 2) + 10

        self.start_button = Button((btn_x, start_y, btn_w, btn_h), "НАЧАТЬ", self.game_font)
        self.settings_button = Button((btn_x, start_y + 90, btn_w, btn_h), "НАСТРОЙКИ", self.game_font)

    def _build_settings_ui(self) -> None:
        """Создаёт кнопки и геометрию для экрана настроек."""
        btn_w, btn_h = 220, 60
        btn_x = (self.width - btn_w) // 2
        top_y = (self.height // 2) - 80

        self.size_10_btn = Button((btn_x, top_y, btn_w, btn_h), "10 x 10", self.game_font)
        self.size_15_btn = Button((btn_x, top_y + 70, btn_w, btn_h), "15 x 15", self.game_font)
        self.size_20_btn = Button((btn_x, top_y + 140, btn_w, btn_h), "20 x 20", self.game_font)

        step_y = top_y + 220
        small_w = 70
        mid_w = 160

        self.fruits_minus_btn = Button((btn_x, step_y, small_w, btn_h), "-", self.game_font)
        self.fruits_value_btn = Button((btn_x + small_w + 10, step_y, mid_w, btn_h), "ФРУКТОВ: 5", self.game_font)
        self.fruits_plus_btn = Button((btn_x + small_w + 10 + mid_w + 10, step_y, small_w, btn_h), "+", self.game_font)

        action_y = step_y + 90
        self.apply_btn = Button((btn_x, action_y, btn_w, btn_h), "ПРИНЯТЬ", self.game_font)
        self.back_btn = Button((btn_x, action_y + 80, btn_w, btn_h), "НАЗАД", self.game_font)

    def _build_game_over_ui(self) -> None:
        """Создаёт кнопки и геометрию для экрана проигрыша (ПОТРАЧЕНО)."""
        btn_w, btn_h = 280, 70
        btn_x = (self.width - btn_w) // 2
        y = (self.height // 2) + 30

        self.go_restart_btn = Button((btn_x, y, btn_w, btn_h), "ЗАНОВО", self.game_font)
        self.go_menu_btn = Button((btn_x, y + 90, btn_w, btn_h), "МЕНЮ", self.game_font)

    def _save_run_score(self, score: int) -> None:
        """
        Сохраняет результат завершённой игры в память и БД:
        - last_score всегда обновляется
        - best_score обновляется только при улучшении рекорда
        """
        score = int(score)
        self.current_score = score

        self.last_score = score
        self.db.set("last_score", self.last_score)

        if score > self.best_score:
            self.best_score = score
            self.db.set("best_score", self.best_score)

    def _sync_fruits_label(self) -> None:
        """Обновляет текст на кнопке отображения количества фруктов (SETTINGS)."""
        if hasattr(self, "fruits_value_btn"):
            self.fruits_value_btn.text = f"ФРУКТОВ: {self.pending_fruits_count}"
            self.fruits_value_btn._render()

    def _change_pending_fruits(self, delta: int) -> None:
        """Меняет pending кол-во фруктов в диапазоне 1..10."""
        self.pending_fruits_count = max(1, min(10, self.pending_fruits_count + delta))
        self._sync_fruits_label()

    def start_game(self) -> None:
        """Запускает новую игру с текущими настройками (размер/фрукты)."""
        self._saved_game_over = False
        self.game = SnakeGame(self.cell_number, fruits_count=self.fruits_count)
        self.game.reset()
        self.state = self.STATE_GAME

    def open_settings(self) -> None:
        """Открывает экран настроек и копирует текущие значения в pending."""
        self.pending_cell_number = self.cell_number
        self.pending_fruits_count = self.fruits_count
        self._sync_fruits_label()
        self.state = self.STATE_SETTINGS

    def apply_settings(self) -> None:
        """Применяет настройки: пересоздаёт окно и пересобирает UI."""
        self.cell_number = self.pending_cell_number
        self.fruits_count = self.pending_fruits_count

        self.apply_window()

        # После смены размера окна — пересобираем UI
        self._build_menu_ui()
        self._build_settings_ui()
        self._build_game_over_ui()
        self._sync_fruits_label()

        self.state = self.STATE_MENU

    def handle_game_input(self, event) -> None:
        """Обрабатывает ввод в состоянии GAME (Esc → меню, стрелки → направление)."""
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_ESCAPE:
            self.state = self.STATE_MENU
            return

        self.game.handle_key(event.key)

    def draw_menu(self) -> None:
        """Рисует экран меню."""
        self.screen.fill((175, 215, 70))

        title_surf = self.title_font.render("ЗМЕЙКА", True, (56, 74, 12))
        title_rect = title_surf.get_rect(center=(self.width // 2, self.height // 2 - 120))
        self.screen.blit(title_surf, title_rect)

        hint = self.game_font.render("Enter = начать, Esc в игре -> меню", True, (56, 74, 12))
        hint_rect = hint.get_rect(center=(self.width // 2, self.height // 2 - 60))
        self.screen.blit(hint, hint_rect)

        # Если ты переносил статистику в меню — она обычно отрисовывается здесь.
        # stats = self.game_font.render(
        #     f"Предыдущий: {self.last_score}    Лучший: {self.best_score}",
        #     True, (56, 74, 12)
        # )
        # stats_rect = stats.get_rect(center=(self.width // 2, self.height // 2 - 20))
        # self.screen.blit(stats, stats_rect)

        self.start_button.draw(self.screen)
        self.settings_button.draw(self.screen)

    def draw_settings(self) -> None:
        """Рисует экран настроек."""
        self.screen.fill((175, 215, 70))

        title_surf = self.title_font.render("НАСТРОЙКИ", True, (56, 74, 12))
        title_rect = title_surf.get_rect(center=(self.width // 2, self.height // 2 - 170))
        self.screen.blit(title_surf, title_rect)

        subtitle = self.game_font.render("Выбери размер поля и кол-во фруктов", True, (56, 74, 12))
        subtitle_rect = subtitle.get_rect(center=(self.width // 2, self.height // 2 - 130))
        self.screen.blit(subtitle, subtitle_rect)

        self.size_10_btn.draw(self.screen, selected=(self.pending_cell_number == 10))
        self.size_15_btn.draw(self.screen, selected=(self.pending_cell_number == 15))
        self.size_20_btn.draw(self.screen, selected=(self.pending_cell_number == 20))

        self.fruits_minus_btn.draw(self.screen)
        self.fruits_value_btn.draw(self.screen)
        self.fruits_plus_btn.draw(self.screen)

        self.apply_btn.draw(self.screen)
        self.back_btn.draw(self.screen)

    def draw_game(self) -> None:
        """Рисует игровой процесс (поле + змейка + фрукты + счёт)."""
        self.screen.fill((175, 215, 70))
        self.game.draw(self.screen, self.cell_size, self.apple, self.game_font)

    def draw_game_over(self) -> None:
        """Рисует экран проигрыша: серый фон, текст, статистика и кнопки."""
        self.screen.fill((150, 150, 150))

        text_surf = self.title_font.render("ПОТРАЧЕНО", True, (35, 35, 35))
        text_rect = text_surf.get_rect(center=(self.width // 2, self.height // 2 - 120))
        self.screen.blit(text_surf, text_rect)

        score_line = self.game_font.render(f"Результат: {self.current_score}", True, (35, 35, 35))
        best_line = self.game_font.render(f"Лучший: {self.best_score}", True, (35, 35, 35))
        last_line = self.game_font.render(f"Предыдущий: {self.last_score}", True, (35, 35, 35))

        score_rect = score_line.get_rect(center=(self.width // 2, self.height // 2 - 70))
        best_rect = best_line.get_rect(center=(self.width // 2, self.height // 2 - 40))
        last_rect = last_line.get_rect(center=(self.width // 2, self.height // 2 - 10))

        self.screen.blit(score_line, score_rect)
        self.screen.blit(best_line, best_rect)
        self.screen.blit(last_line, last_rect)

        self.go_restart_btn.draw(self.screen)
        self.go_menu_btn.draw(self.screen)

    def run(self) -> None:
        """
        Главный цикл приложения:
        - читает события
        - обрабатывает их согласно текущему state
        - рисует соответствующий экран
        """
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                if self.state == self.STATE_MENU:
                    if self.start_button.is_clicked(event):
                        self.start_game()
                    if self.settings_button.is_clicked(event):
                        self.open_settings()
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                        self.start_game()

                elif self.state == self.STATE_SETTINGS:
                    if self.size_10_btn.is_clicked(event):
                        self.pending_cell_number = 10
                    elif self.size_15_btn.is_clicked(event):
                        self.pending_cell_number = 15
                    elif self.size_20_btn.is_clicked(event):
                        self.pending_cell_number = 20

                    if self.fruits_minus_btn.is_clicked(event):
                        self._change_pending_fruits(-1)
                    elif self.fruits_plus_btn.is_clicked(event):
                        self._change_pending_fruits(+1)

                    if self.apply_btn.is_clicked(event):
                        self.apply_settings()
                    elif self.back_btn.is_clicked(event):
                        self.state = self.STATE_MENU

                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        self.state = self.STATE_MENU

                elif self.state == self.STATE_GAME:
                    # Тик игры происходит на таймерном событии, а не каждый кадр.
                    if event.type == self.SCREEN_UPDATE:
                        self.game.update()

                        # При проигрыше сохраняем результат ровно один раз.
                        if self.game.is_game_over():
                            if not self._saved_game_over:
                                self._saved_game_over = True
                                self._save_run_score(self.game.get_score())
                            self.state = self.STATE_GAME_OVER

                    self.handle_game_input(event)

                elif self.state == self.STATE_GAME_OVER:
                    if self.go_restart_btn.is_clicked(event):
                        self.start_game()
                    elif self.go_menu_btn.is_clicked(event):
                        self.state = self.STATE_MENU

                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_RETURN:
                            self.start_game()
                        elif event.key == pygame.K_ESCAPE:
                            self.state = self.STATE_MENU

            if self.state == self.STATE_MENU:
                self.draw_menu()
            elif self.state == self.STATE_SETTINGS:
                self.draw_settings()
            elif self.state == self.STATE_GAME_OVER:
                self.draw_game_over()
            else:
                self.draw_game()

            pygame.display.update()
            self.clock.tick(60)


if __name__ == "__main__":
    """Точка входа: создаёт приложение и запускает главный цикл."""
    GameApp().run()
