import streamlit as st
import numpy as np
import random
import time
from PIL import Image, ImageDraw

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

    def update(self, creatures):
        self.response *= self.habituation_rate
        if not self.disinhibited:
            self.response -= self.inhibition
        stress_factor = random.random() * 0.2
        self.stress = min(1.0, self.stress + stress_factor * (1 - self.stress))
        self.constricted = self.stress > 0.7
        if random.random() < 0.05:
            self.disinhibited = not self.disinhibited
            self.inhibition = 0.0 if self.disinhibited else 0.3
        self.energy -= 0.1
        if self.energy <= 0:
            self.energy = random.uniform(4, 7)
            self.stress = 0.0
            self.response = 1.0
            self.disinhibited = False
            self.inhibition = 0.3
        if self.stress < 0.3 and self.energy > 6:
            self.mood = "happy"
        elif self.stress > 0.7:
            self.mood = "angry"
        elif self.stress > 0.4:
            self.mood = "stressed"
        else:
            self.mood = "neutral"
        if not self.constricted:
            dx = random.choice([-1, 0, 1])
            dy = random.choice([-1, 0, 1])
            new_x = min(max(self.x + dx, 0), GRID_WIDTH - 1)
            new_y = min(max(self.y + dy, 0), GRID_HEIGHT - 1)
            if not any(c.x == new_x and c.y == new_y for c in creatures):
                self.x = new_x
                self.y = new_y

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

def get_creature_info(c):
    return (
        f"Position: ({c.x},{c.y})\n"
        f"Energy: {c.energy:.2f}\n"
        f"Stress: {c.stress:.2f}\n"
        f"Response: {c.response:.2f}\n"
        f"Mood: {MOOD_DATA[c.mood]['emoji']} {c.mood.capitalize()}\n"
        f"Disinhibited: {c.disinhibited}\n"
        f"Constricted: {c.constricted}"
    )

st.set_page_config(page_title="Mind Simulation Grid", layout="wide")
st.title("🧠 Mind Simulation Sandbox")

if "creatures" not in st.session_state:
    st.session_state.creatures = [Creature(random.randint(0, GRID_WIDTH-1), random.randint(0, GRID_HEIGHT-1)) for _ in range(10)]
if "running" not in st.session_state:
    st.session_state.running = False
if "last_update" not in st.session_state:
    st.session_state.last_update = time.time()

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
        st.session_state.creatures = [Creature(random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1)) for _ in range(10)]

    if st.session_state.running:
        if st.button("Pause"):
            st.session_state.running = False
    else:
        if st.button("Play"):
            st.session_state.running = True

st.markdown("---")
img = draw_grid(st.session_state.creatures)
st.image(img, width=GRID_WIDTH * CELL_SIZE)

if st.session_state.running:
    now = time.time()
    if now - st.session_state.last_update > 0.5:
        for c in st.session_state.creatures:
            c.update(st.session_state.creatures)
        st.session_state.last_update = now
        # Instead of st.experimental_rerun(), just use st.experimental_set_query_params to force refresh
        st.experimental_set_query_params(rerun=str(time.time()))
        # Note: This triggers a soft rerun by changing query params.

# Display creature info on click (manual hack)
if st.button("Show Creature Info at (15,15)"):
    # Example: Show info for creature at pos (15,15)
    for c in st.session_state.creatures:
        if c.x == 15 and c.y == 15:
            st.info(get_creature_info(c))
            break
