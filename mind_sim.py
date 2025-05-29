import streamlit as st
import numpy as np
import random

# Grid & simulation parameters
GRID_WIDTH, GRID_HEIGHT = 40, 30
NUM_CREATURES = 10
PIXEL_SIZE = 15  # for display

# Colors
BG_COLOR = np.array([0, 0, 0], dtype=np.uint8)
CREATURE_COLOR = np.array([0, 200, 200], dtype=np.uint8)
STRESSED_COLOR = np.array([200, 0, 0], dtype=np.uint8)

# --- Streamlit App ---
st.set_page_config(page_title="Mind Grid Simulation", layout="wide")
st.title("🧠 Creature Mind Grid Simulation")

# Initialize session state
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
            # Sense nearby creatures
            neighbors = sum(
                1 for c in creatures
                if c is not self and abs(c.x - self.x) <= 1 and abs(c.y - self.y) <= 1
            )
            self.stress = min(1.0, self.stress + neighbors * 0.05)
            self.arousal = 0.6 * self.stress + random.uniform(0, 0.2)
            self.energy = max(0.0, self.energy - self.stress * 0.01)

            # Disinhibition logic
            self.disinhibited = self.arousal > 0.8 and self.energy < 0.3
            if self.disinhibited:
                self.energy = 1.0  # reset on burst

            # Movement logic
            dx, dy = random.choice([(0, 1), (1, 0), (-1, 0), (0, -1)])
            self.x = max(0, min(GRID_WIDTH - 1, self.x + dx))
            self.y = max(0, min(GRID_HEIGHT - 1, self.y + dy))

    st.session_state.creatures = [Creature() for _ in range(NUM_CREATURES)]

# Update simulation
for creature in st.session_state.creatures:
    creature.update(st.session_state.creatures)

# Draw grid as RGB image
grid = np.zeros((GRID_HEIGHT, GRID_WIDTH, 3), dtype=np.uint8)
for c in st.session_state.creatures:
    color = STRESSED_COLOR if c.stress > 0.5 else CREATURE_COLOR
    grid[c.y, c.x] = color

# Upscale grid for display
grid_display = np.kron(grid, np.ones((PIXEL_SIZE, PIXEL_SIZE, 1)))

# Show the grid
st.image(grid_display, caption="Creature Grid", use_column_width=False)

# Step button
if st.button("Step Simulation"):
    st.rerun()
