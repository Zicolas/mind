import streamlit as st
import numpy as np
import random
from PIL import Image, ImageDraw
from streamlit_autorefresh import st_autorefresh

# Constants
GRID_WIDTH = 30
GRID_HEIGHT = 30
CELL_SIZE = 20
MAX_ENERGY = 10.0

MOOD_DATA = {
    "happy": {"color": (0, 200, 0), "emoji": "😊"},
    "neutral": {"color": (200, 200, 0), "emoji": "😐"},
    "stressed": {"color": (200, 100, 0), "emoji": "😰"},
    "angry": {"color": (200, 0, 0), "emoji": "😡"},
}

class Creature:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.energy = random.uniform(4, 7)
        self.stress = 0.0
        self.habituation_rate = 0.95
        self.inhibition = 0.3
        self.disinhibited = False
        self.constricted = False
        self.response = 1.0
        self.mood = "neutral"
        self.memory = []  # new: remember last few positions
        self.age = 0      # new: age for possible reproduction

    def update(self, creatures):
        self.response *= self.habituation_rate
        if not self.disinhibited:
            self.response -= self.inhibition

        # Small random stress fluctuation up/down
        stress_change = (random.random() - 0.5) * 0.1
        self.stress = min(1.0, max(0.0, self.stress + stress_change))

        self.constricted = self.stress > 0.7
        if random.random() < 0.05:
            self.disinhibited = not self.disinhibited
            self.inhibition = 0.0 if self.disinhibited else 0.3

        self.energy -= 0.1
        self.age += 1  # age increments every update

        if self.energy <= 0:
            self.energy = random.uniform(4, 7)
            self.stress = 0.0
            self.response = 1.0
            self.disinhibited = False
            self.inhibition = 0.3

        # Mood logic unchanged
        if self.stress < 0.3 and self.energy > 6:
            self.mood = "happy"
        elif self.stress > 0.7:
            self.mood = "angry"
        elif self.stress > 0.4:
            self.mood = "stressed"
        else:
            self.mood = "neutral"

        # Movement with basic goal: seek low stress zones or energy if low
        if not self.constricted:
            # Look around adjacent cells for least crowded + possibly mate if energy high
            neighbors = []
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    nx, ny = self.x + dx, self.y + dy
                    if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                        neighbors.append((nx, ny))

            # Prefer cells with no creature
            empty_neighbors = [pos for pos in neighbors if not any(c.x == pos[0] and c.y == pos[1] for c in creatures)]

            # Try to move toward "safe" empty cells (simulate seeking low stress)
            if empty_neighbors:
                # Prefer random empty cell (could be improved with real goals)
                new_x, new_y = random.choice(empty_neighbors)

                # Check for possible reproduction if energy high and age sufficient
                if self.energy > 8 and self.age > 30:
                    # Check if mate nearby (another creature in adjacent cells with high energy)
                    mate = next(
                        (c for c in creatures
                         if c != self and abs(c.x - self.x) <= 1 and abs(c.y - self.y) <= 1
                         and c.energy > 8 and c.age > 30),
                        None
                    )
                    if mate:
                        # Reproduce: create new creature near self if space
                        free_spots = [
                            pos for pos in empty_neighbors
                            if pos != (new_x, new_y)  # avoid same spot
                        ]
                        if free_spots:
                            bx, by = random.choice(free_spots)
                            creatures.append(Creature(bx, by))
                            # Energy cost for reproduction
                            self.energy -= 3
                            mate.energy -= 3
                            self.age = 0
                            mate.age = 0

                self.x = new_x
                self.y = new_y

        # Update memory of positions (last 5)
        self.memory.append((self.x, self.y))
        if len(self.memory) > 5:
            self.memory.pop(0)

def draw_grid(creatures):
    img = Image.new("RGB", (GRID_WIDTH * CELL_SIZE, GRID_HEIGHT * CELL_SIZE), (30, 30, 30))
    draw = ImageDraw.Draw(img)
    for x in range(GRID_WIDTH + 1):
        draw.line([(x * CELL_SIZE, 0), (x * CELL_SIZE, GRID_HEIGHT * CELL_SIZE)], fill=(50, 50, 50))
    for y in range(GRID_HEIGHT + 1):
        draw.line([(0, y * CELL_SIZE), (GRID_WIDTH * CELL_SIZE, y * CELL_SIZE)], fill=(50, 50, 50))
    for c in creatures:
        mood_color = MOOD_DATA[c.mood]["color"]
        brightness = int(100 + 155 * min(1.0, c.energy / MAX_ENERGY))
        color = tuple(min(255, int(brightness * (v / 255))) for v in mood_color)
        top_left = (c.x * CELL_SIZE + 2, c.y * CELL_SIZE + 2)
        bottom_right = ((c.x + 1) * CELL_SIZE - 2, (c.y + 1) * CELL_SIZE - 2)
        draw.rectangle([top_left, bottom_right], fill=color)
    return img

st.set_page_config(page_title="Mind Simulation Grid", layout="wide")
st.title("🧠 Mind Simulation Sandbox")

# Initialize session state
if "creatures" not in st.session_state:
    st.session_state.creatures = [
        Creature(random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1))
        for _ in range(10)
    ]
if "running" not in st.session_state:
    st.session_state.running = False

with st.sidebar:
    st.header("Controls")

    if st.button("Add Creature"):
        attempts = 0
        while attempts < 100:
            x = random.randint(0, GRID_WIDTH - 1)
            y = random.randint(0, GRID_HEIGHT - 1)
            if not any(c.x == x and c.y == y for c in st.session_state.creatures):
                st.session_state.creatures.append(Creature(x, y))
                break
            attempts += 1

    if st.button("Reset Creatures"):
        st.session_state.creatures = [
            Creature(random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1))
            for _ in range(10)
        ]

    if st.session_state.running:
        if st.button("Pause"):
            st.session_state.running = False
    else:
        if st.button("Play"):
            st.session_state.running = True

# Auto-refresh and update creatures if running
if st.session_state.running:
    count = st_autorefresh(interval=500, limit=None, key="autorefresh")
    for c in st.session_state.creatures:
        c.update(st.session_state.creatures)

# Draw and display grid
img = draw_grid(st.session_state.creatures)
st.image(img, width=GRID_WIDTH * CELL_SIZE)

# Show moods and stats
st.markdown("### Creatures' Moods")
cols = st.columns(len(st.session_state.creatures))
for idx, c in enumerate(st.session_state.creatures):
    with cols[idx]:
        st.write(f"{MOOD_DATA[c.mood]['emoji']} Energy: {c.energy:.1f}\nStress: {c.stress:.2f}")
