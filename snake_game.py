import random
import pygame
from pygame.math import Vector2
from typing import Set, Tuple


class Snake:
    def __init__(self):
        self.body = [Vector2(5, 10), Vector2(4, 10), Vector2(3, 10)]
        self.direction = Vector2(0, 0)
        self.new_block = False

        # Graphics
        self.head_up = pygame.image.load('photos/head_up.png').convert_alpha()
        self.head_down = pygame.image.load('photos/head_down.png').convert_alpha()
        self.head_right = pygame.image.load('photos/head_right.png').convert_alpha()
        self.head_left = pygame.image.load('photos/head_left.png').convert_alpha()

        self.tail_up = pygame.image.load('photos/tail_up.png').convert_alpha()
        self.tail_down = pygame.image.load('photos/tail_down.png').convert_alpha()
        self.tail_right = pygame.image.load('photos/tail_right.png').convert_alpha()
        self.tail_left = pygame.image.load('photos/tail_left.png').convert_alpha()

        self.body_vertical = pygame.image.load('photos/body_vertical.png').convert_alpha()
        self.body_horizontal = pygame.image.load('photos/body_horizontal.png').convert_alpha()

        self.body_tr = pygame.image.load('photos/body_tr.png').convert_alpha()
        self.body_tl = pygame.image.load('photos/body_tl.png').convert_alpha()
        self.body_br = pygame.image.load('photos/body_br.png').convert_alpha()
        self.body_bl = pygame.image.load('photos/body_bl.png').convert_alpha()

        # Sound
        self.crunch_sound = pygame.mixer.Sound('Sound/nyam.wav')

        # Defaults
        self.head = self.head_right
        self.tail = self.tail_left

    def reset(self):
        self.body = [Vector2(5, 10), Vector2(4, 10), Vector2(3, 10)]
        self.direction = Vector2(0, 0)
        self.new_block = False

    def play_crunch_sound(self):
        self.crunch_sound.play()

    def add_block(self):
        self.new_block = True

    def move(self):
        # Important: do not move until player chooses direction
        if self.direction == Vector2(0, 0):
            return

        if self.new_block:
            body_copy = self.body[:]
            body_copy.insert(0, body_copy[0] + self.direction)
            self.body = body_copy
            self.new_block = False
        else:
            body_copy = self.body[:-1]
            body_copy.insert(0, body_copy[0] + self.direction)
            self.body = body_copy

    def draw(self, screen, cell_size):
        self._update_head_graphics()
        self._update_tail_graphics()

        for index, block in enumerate(self.body):
            x_pos = int(block.x * cell_size)
            y_pos = int(block.y * cell_size)
            block_rect = pygame.Rect(x_pos, y_pos, cell_size, cell_size)

            if index == 0:
                screen.blit(self.head, block_rect)
            elif index == len(self.body) - 1:
                screen.blit(self.tail, block_rect)
            else:
                previous_block = self.body[index + 1] - block
                next_block = self.body[index - 1] - block
                if previous_block.x == next_block.x:
                    screen.blit(self.body_vertical, block_rect)
                elif previous_block.y == next_block.y:
                    screen.blit(self.body_horizontal, block_rect)
                else:
                    if (previous_block.x == -1 and next_block.y == -1) or (previous_block.y == -1 and next_block.x == -1):
                        screen.blit(self.body_tl, block_rect)
                    elif (previous_block.x == -1 and next_block.y == 1) or (previous_block.y == 1 and next_block.x == -1):
                        screen.blit(self.body_bl, block_rect)
                    elif (previous_block.x == 1 and next_block.y == -1) or (previous_block.y == -1 and next_block.x == 1):
                        screen.blit(self.body_tr, block_rect)
                    elif (previous_block.x == 1 and next_block.y == 1) or (previous_block.y == 1 and next_block.x == 1):
                        screen.blit(self.body_br, block_rect)

    def _update_head_graphics(self):
        head_relation = self.body[1] - self.body[0]
        if head_relation == Vector2(1, 0):
            self.head = self.head_left
        elif head_relation == Vector2(-1, 0):
            self.head = self.head_right
        elif head_relation == Vector2(0, 1):
            self.head = self.head_up
        elif head_relation == Vector2(0, -1):
            self.head = self.head_down

    def _update_tail_graphics(self):
        tail_relation = self.body[-2] - self.body[-1]
        if tail_relation == Vector2(1, 0):
            self.tail = self.tail_left
        elif tail_relation == Vector2(-1, 0):
            self.tail = self.tail_right
        elif tail_relation == Vector2(0, 1):
            self.tail = self.tail_up
        elif tail_relation == Vector2(0, -1):
            self.tail = self.tail_down


class Fruit:
    def __init__(self, cell_number: int):
        self.cell_number = cell_number
        self.pos = Vector2(0, 0)

    def spawn(self, occupied: Set[Tuple[int, int]]):
        max_attempts = self.cell_number * self.cell_number + 200
        for _ in range(max_attempts):
            x = random.randint(0, self.cell_number - 1)
            y = random.randint(0, self.cell_number - 1)
            if (x, y) not in occupied:
                self.pos = Vector2(x, y)
                return

    def draw(self, screen, cell_size, apple_surface):
        rect = pygame.Rect(int(self.pos.x * cell_size), int(self.pos.y * cell_size), cell_size, cell_size)
        screen.blit(apple_surface, rect)


class SnakeGame:
    """
    - Multiple fruits on field
    - After eating: fruit disappears immediately, replacement spawns on next update
    - Game over sets flag (no auto reset)
    """
    def __init__(self, cell_number: int, fruits_count: int = 5):
        self.cell_number = cell_number
        self.fruits_count = max(1, int(fruits_count))

        self.snake = Snake()
        self.fruits = []
        self.pending_spawns = 0
        self.game_over = False

        self._spawn_initial_fruits()

    def reset(self):
        self.snake.reset()
        self.fruits.clear()
        self.pending_spawns = 0
        self.game_over = False
        self._spawn_initial_fruits()

    def is_game_over(self) -> bool:
        return self.game_over

    def get_score(self) -> int:
        return max(0, len(self.snake.body) - 3)

    def update(self):
        if self.game_over:
            return

        self.snake.move()
        self._check_eat()
        self._check_fail()
        self._process_pending_spawns(max_per_update=1)

    def handle_key(self, key):
        if self.game_over:
            return

        if key == pygame.K_UP and self.snake.direction.y != 1:
            self.snake.direction = Vector2(0, -1)
        elif key == pygame.K_RIGHT and self.snake.direction.x != -1:
            self.snake.direction = Vector2(1, 0)
        elif key == pygame.K_DOWN and self.snake.direction.y != -1:
            self.snake.direction = Vector2(0, 1)
        elif key == pygame.K_LEFT and self.snake.direction.x != 1:
            self.snake.direction = Vector2(-1, 0)

    def draw(self, screen, cell_size, apple_surface, game_font):
        self._draw_grass(screen, cell_size)

        for fruit in self.fruits:
            fruit.draw(screen, cell_size, apple_surface)

        self.snake.draw(screen, cell_size)
        self._draw_score(screen, cell_size, apple_surface, game_font)

    # ---- fruits ----

    def _occupied_cells(self) -> Set[Tuple[int, int]]:
        occupied: Set[Tuple[int, int]] = set()
        for block in self.snake.body:
            occupied.add((int(block.x), int(block.y)))
        for fruit in self.fruits:
            occupied.add((int(fruit.pos.x), int(fruit.pos.y)))
        return occupied

    def _spawn_initial_fruits(self):
        for _ in range(self.fruits_count):
            self._spawn_one_fruit()

    def _spawn_one_fruit(self):
        fruit = Fruit(self.cell_number)
        fruit.spawn(self._occupied_cells())
        self.fruits.append(fruit)

    def _check_eat(self):
        head = self.snake.body[0]

        eaten_index = None
        for i, fruit in enumerate(self.fruits):
            if fruit.pos == head:
                eaten_index = i
                break

        if eaten_index is not None:
            self.fruits.pop(eaten_index)
            self.snake.add_block()
            self.snake.play_crunch_sound()
            self.pending_spawns += 1

    def _process_pending_spawns(self, max_per_update: int = 1):
        if self.pending_spawns <= 0:
            return

        created = 0
        while (
            created < max_per_update
            and self.pending_spawns > 0
            and len(self.fruits) < self.fruits_count
        ):
            self._spawn_one_fruit()
            self.pending_spawns -= 1
            created += 1

        if len(self.fruits) >= self.fruits_count:
            self.pending_spawns = 0

    # ---- fail ----

    def _check_fail(self):
        head = self.snake.body[0]

        if not (0 <= head.x < self.cell_number and 0 <= head.y < self.cell_number):
            self.game_over = True
            return

        for block in self.snake.body[1:]:
            if block == head:
                self.game_over = True
                return

    # ---- draw helpers ----

    def _draw_grass(self, screen, cell_size):
        grass_color = (167, 209, 61)
        for row in range(self.cell_number):
            for col in range(self.cell_number):
                if (row + col) % 2 == 0:
                    rect = pygame.Rect(col * cell_size, row * cell_size, cell_size, cell_size)
                    pygame.draw.rect(screen, grass_color, rect)

    def _draw_score(self, screen, cell_size, apple_surface, game_font):
        score_text = str(self.get_score())
        score_surface = game_font.render(score_text, True, (56, 74, 12))
        score_x = int(cell_size * self.cell_number - 60)
        score_y = int(cell_size * self.cell_number - 40)
        score_rect = score_surface.get_rect(center=(score_x, score_y))
        apple_rect = apple_surface.get_rect(midright=(score_rect.left, score_rect.centery))
        bg_rect = pygame.Rect(
            apple_rect.left,
            apple_rect.top,
            apple_rect.width + score_rect.width + 6,
            apple_rect.height
        )

        pygame.draw.rect(screen, (167, 209, 61), bg_rect)
        screen.blit(score_surface, score_rect)
        screen.blit(apple_surface, apple_rect)
        pygame.draw.rect(screen, (56, 74, 12), bg_rect, 2)
