import pygame
import random
import math

# Constants
GRID_SIZE = 20
WORLD_WIDTH = 40
WORLD_HEIGHT = 30
CREATURE_COUNT = 10
CELL_SIZE = 20
WINDOW_WIDTH = WORLD_WIDTH * CELL_SIZE
WINDOW_HEIGHT = WORLD_HEIGHT * CELL_SIZE

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
CREATURE_COLOR = (0, 200, 200)
STRESSED_COLOR = (200, 0, 0)

# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Mind Creatures Simulation")
clock = pygame.time.Clock()

class Creature:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.stress = 0.0
        self.arousal = 0.0
        self.energy = 1.0
        self.habituation = {}
        self.inhibited = False
        self.response = 1.0
        self.constricted = False
        self.disinhibited = False

    def sense_others(self, creatures):
        nearby = 0
        for c in creatures:
            if c is self: continue
            if abs(c.x - self.x) <= 2 and abs(c.y - self.y) <= 2:
                nearby += 1
        return nearby

    def update_mind(self, creatures):
        stimulus = self.sense_others(creatures)
        self.habituation['others'] = self.habituation.get('others', 0) + 1
        habituation_decay = 0.85 ** self.habituation['others']
        self.response = 1.0 * habituation_decay

        # Increase stress over time
        self.stress = min(1.0, self.stress + 0.01 * stimulus)
        self.arousal = min(1.0, 0.6 * self.stress + random.uniform(0, 0.2))

        # Inhibition logic
        inhibition = max(0.0, (1.0 - self.arousal) - (1.0 - self.energy))
        self.response *= inhibition

        # Constriction
        self.constricted = self.stress > 0.6 or self.energy < 0.3

        # Disinhibition
        self.disinhibited = self.arousal > 0.8 and self.energy < 0.2
        if self.disinhibited:
            self.response += 0.5
            self.energy = 1.0  # crash recovery

        # Energy drain
        self.energy = max(0.0, self.energy - 0.01 * self.stress)

    def move(self):
        if self.constricted:
            dx, dy = random.choice([(0, -1), (0, 1)])  # limited movement
        else:
            dx, dy = random.choice([(0, -1), (0, 1), (-1, 0), (1, 0)])
        self.x = max(0, min(WORLD_WIDTH - 1, self.x + dx))
        self.y = max(0, min(WORLD_HEIGHT - 1, self.y + dy))

    def draw(self, surface):
        color = STRESSED_COLOR if self.stress > 0.5 else CREATURE_COLOR
        pygame.draw.rect(surface, color, pygame.Rect(
            self.x * CELL_SIZE, self.y * CELL_SIZE, CELL_SIZE, CELL_SIZE
        ))

# Create creatures
creatures = [Creature(random.randint(0, WORLD_WIDTH - 1), random.randint(0, WORLD_HEIGHT - 1)) for _ in range(CREATURE_COUNT)]

# Main Loop
running = True
while running:
    screen.fill(BLACK)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    for creature in creatures:
        creature.update_mind(creatures)
        creature.move()
        creature.draw(screen)

    pygame.display.flip()
    clock.tick(5)  # 5 FPS for visible movement

pygame.quit()
