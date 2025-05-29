import streamlit as st
import numpy as np
import random
import time

GRID_WIDTH, GRID_HEIGHT = 40, 30
NUM_CREATURES = 10
PIXEL_SIZE = 15

BG_COLOR = np.array([0, 0, 0], dtype=np.uint8)
CREATURE_COLOR = np.array([0, 200, 200], dtype=np.uint8)
STRESSED_COLOR = np.array([200, 0, 0], dtype=np.uint8)

st.set_page_config(page_title="Mind Grid Simulation", layout="wide")
st.title("🧠 Creature Mind Grid Simulation")

# Initialize state only once
if "creatures" not in st.session_state:
    class Creature:
        def __init__(self):
            self.x = random.randint(0, GRID_WIDTH - 1)
            self.y = random.randint(0, GRID_HEIGHT - 1)
            self.stress = 0.0
            self.energy = 1.0
            self.arousal = 0.0
            self.disinhibited = False

        def update(self, creatures):
            neighbors = sum(
                1 for c in creatures
                if c is not self and abs(c.x - self.x) <= 1 and abs(c.y - self.y) <= 1
            )
            self.stress = min(1.0, self.stress + neighbors * 0.05)
            self.arousal = 0.6 * self.stress + random.uniform(0, 0.2)
            self.energy = max(0.0, self.energy - self.stress * 0.01)

            self.disinhibited = self.arousal > 0.8 and self.energy < 0.3
            if self.disinhibited:
                self.energy = 1.0

            dx, dy = random.choice([(0, 1), (1, 0), (-1, 0), (0, -1)])
            self.x = max(0, min(GRID_WIDTH - 1, self.x + dx))
            self.y = max(0, min(GRID_HEIGHT - 1, self.y + dy))

    st.session_state.creatures = [Creature() for _ in range(NUM_CREATURES)]
    st.session_state.running = False

# Play/Pause toggle
if st.button("▶️ Play" if not st.session_state.running else "⏸ Pause"):
    st.session_state.running = not st.session_state.running

# Container for animation
display = st.empty()

# Simulation loop (run up to N frames)
if st.session_state.running:
    for _ in range(200):  # limit loop to avoid freezing UI
        # Update creatures
        for c in st.session_state.creatures:
            c.update(st.session_state.creatures)

        # Draw grid
        grid = np.zeros((GRID_HEIGHT, GRID_WIDTH, 3), dtype=np.uint8)
        for c in st.session_state.creatures:
            color = STRESSED_COLOR if c.stress > 0.5 else CREATURE_COLOR
            grid[c.y, c.x] = color

        grid_display = np.kron(grid, np.ones((PIXEL_SIZE, PIXEL_SIZE, 1), dtype=np.uint8))
        display.image(grid_display, caption="Creature Grid", use_container_width=False)

        time.sleep(0.3)

    st.session_state.running = False
