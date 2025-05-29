import streamlit as st
import numpy as np
import random
import time
import uuid

# Grid and simulation constants
GRID_WIDTH, GRID_HEIGHT = 40, 30
PIXEL_SIZE = 15
MAX_CREATURES = 50

# Colors for emotion states
BG_COLOR = np.array([0, 0, 0], dtype=np.uint8)
COLOR_NORMAL = np.array([0, 200, 200], dtype=np.uint8)
COLOR_STRESSED = np.array([255, 100, 100], dtype=np.uint8)
COLOR_HAPPY = np.array([100, 255, 100], dtype=np.uint8)

st.set_page_config(page_title="Mind Grid", layout="wide")
st.title("🧠 Mind Grid Simulator")

# Creature class with emotion logic
class Creature:
    def __init__(self, name=None):
        self.id = str(uuid.uuid4())[:4]
        self.x = random.randint(0, GRID_WIDTH - 1)
        self.y = random.randint(0, GRID_HEIGHT - 1)
        self.energy = random.uniform(0.5, 1.0)
        self.stress = 0.0
        self.arousal = 0.0
        self.name = name or f"Creature-{random.randint(1000, 9999)}"
        self.disinhibited = False

    def update(self, others):
        neighbors = sum(
            1 for c in others if c is not self and abs(c.x - self.x) <= 1 and abs(c.y - self.y) <= 1
        )
        self.stress = min(1.0, self.stress + neighbors * 0.03)
        self.arousal = 0.7 * self.stress + random.uniform(0, 0.3)
        self.energy = max(0.0, self.energy - self.stress * 0.01)

        self.disinhibited = self.arousal > 0.7 and self.energy < 0.3
        if self.disinhibited:
            self.energy = 1.0  # recovery burst

        dx, dy = random.choice([(0, 1), (1, 0), (-1, 0), (0, -1)])
        self.x = max(0, min(GRID_WIDTH - 1, self.x + dx))
        self.y = max(0, min(GRID_HEIGHT - 1, self.y + dy))

    def color(self):
        if self.stress > 0.6:
            return COLOR_STRESSED
        elif self.energy > 0.8:
            return COLOR_HAPPY
        else:
            return COLOR_NORMAL

# Initialize session state
if "creatures" not in st.session_state:
    st.session_state.creatures = [Creature() for _ in range(10)]
    st.session_state.running = False

# Controls
col1, col2 = st.columns([1, 3])

with col1:
    if st.button("▶️ Play" if not st.session_state.running else "⏸ Pause"):
        st.session_state.running = not st.session_state.running

    if st.button("➕ Spawn Creature"):
        if len(st.session_state.creatures) < MAX_CREATURES:
            st.session_state.creatures.append(Creature())
        else:
            st.warning("Maximum creatures reached.")

    if st.button("💾 Save State"):
        st.session_state.saved = [
            (c.x, c.y, c.energy, c.stress, c.name) for c in st.session_state.creatures
        ]
        st.success("State saved!")

    if st.button("📂 Load State"):
        if "saved" in st.session_state:
            st.session_state.creatures = []
            for x, y, energy, stress, name in st.session_state.saved:
                c = Creature(name)
                c.x, c.y, c.energy, c.stress = x, y, energy, stress
                st.session_state.creatures.append(c)
            st.success("State loaded!")

    if st.button("🧹 Reset State (dev use)"):
        for key in ["creatures", "saved", "running"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

# Main display
with col2:
    display = st.empty()
    stats_area = st.empty()

# Simulation loop
if st.session_state.running:
    for _ in range(200):  # cap to prevent infinite running
        for c in st.session_state.creatures:
            c.update(st.session_state.creatures)

        grid = np.zeros((GRID_HEIGHT, GRID_WIDTH, 3), dtype=np.uint8)
        for c in st.session_state.creatures:
            grid[c.y, c.x] = c.color()

        # Upscale grid
        grid_display = np.kron(grid, np.ones((PIXEL_SIZE, PIXEL_SIZE, 1), dtype=np.uint8))
        display.image(grid_display, caption="Creature Grid", use_container_width=False)

        # Stats
        stat_lines = [
            f"{c.name}: ⚡ {c.energy:.2f} | 😰 {c.stress:.2f} {'🔥' if c.disinhibited else ''}"
            for c in st.session_state.creatures[:10]
        ]
        stats_area.markdown("**Stats (first 10):**\n" + "\n".join(stat_lines))

        time.sleep(0.35)

    st.session_state.running = False
else:
    # Static view
    grid = np.zeros((GRID_HEIGHT, GRID_WIDTH, 3), dtype=np.uint8)
    for c in st.session_state.creatures:
        grid[c.y, c.x] = c.color()
    grid_display = np.kron(grid, np.ones((PIXEL_SIZE, PIXEL_SIZE, 1), dtype=np.uint8))
    display.image(grid_display, caption="Creature Grid", use_container_width=False)

    stat_lines = [
        f"{c.name}: ⚡ {c.energy:.2f} | 😰 {c.stress:.2f} {'🔥' if c.disinhibited else ''}"
        for c in st.session_state.creatures[:10]
    ]
    stats_area.markdown("**Stats (first 10):**\n" + "\n".join(stat_lines))
