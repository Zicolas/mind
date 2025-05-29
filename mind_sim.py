import streamlit as st
import numpy as np
import random
import uuid
from streamlit_autorefresh import st_autorefresh

GRID_WIDTH, GRID_HEIGHT = 30, 20
PIXEL_SIZE = 20

COLOR_NORMAL = np.array([0, 180, 255], dtype=np.uint8)
COLOR_STRESSED = np.array([255, 80, 80], dtype=np.uint8)
COLOR_HAPPY = np.array([80, 255, 120], dtype=np.uint8)

def get_mood_emoji(stress, energy, disinhibited):
    if disinhibited:
        return "🌀"
    if stress > 0.7:
        return "😡"
    elif energy > 0.8:
        return "😊"
    else:
        return "😐"

class Creature:
    def __init__(self, name=None):
        self.id = str(uuid.uuid4())[:4]
        self.x = random.randint(0, GRID_WIDTH - 1)
        self.y = random.randint(0, GRID_HEIGHT - 1)
        self.energy = random.uniform(0.5, 1.0)
        self.stress = 0.0
        self.arousal = 0.0
        self.name = name or f"C-{self.id}"
        self.disinhibited = False

    def update(self, others):
        neighbors = sum(
            1
            for c in others
            if c is not self and abs(c.x - self.x) <= 1 and abs(c.y - self.y) <= 1
        )
        self.stress = min(1.0, self.stress + neighbors * 0.02)
        self.arousal = 0.6 * self.stress + random.uniform(0, 0.2)
        self.energy = max(0.0, self.energy - 0.005)

        self.disinhibited = self.arousal > 0.7 and self.energy < 0.3
        if self.disinhibited:
            self.energy = 1.0

        dx, dy = random.choice([(0, 1), (1, 0), (-1, 0), (0, -1)])
        self.x = max(0, min(GRID_WIDTH - 1, self.x + dx))
        self.y = max(0, min(GRID_HEIGHT - 1, self.y + dy))

    def color(self):
        if self.stress > 0.7:
            return COLOR_STRESSED
        elif self.energy > 0.8:
            return COLOR_HAPPY
        else:
            return COLOR_NORMAL

st.set_page_config(layout="wide")
st.title("🧠 Mind Grid V2 – Real-Time Simulation")

# Initialize session state
if "creatures" not in st.session_state:
    st.session_state.creatures = [Creature() for _ in range(10)]
if "running" not in st.session_state:
    st.session_state.running = False

# Controls
col1, col2 = st.columns([1, 3])
with col1:
    if st.button("▶️ Play" if not st.session_state.running else "⏸ Pause"):
        st.session_state.running = not st.session_state.running

    if st.button("➕ Add Creature"):
        st.session_state.creatures.append(Creature())

    if st.button("🔁 Reset"):
        st.session_state.creatures = [Creature() for _ in range(10)]
        st.session_state.running = False

with col2:
    display = st.empty()
    stats = st.empty()

# Auto-refresh only if running
if st.session_state.running:
    st_autorefresh(interval=500, limit=None, key="refresh")  # refresh every 0.5 sec

# Update simulation one step per rerun when running
if st.session_state.running:
    for c in st.session_state.creatures:
        c.update(st.session_state.creatures)

# Draw grid
grid = np.zeros((GRID_HEIGHT, GRID_WIDTH, 3), dtype=np.uint8)
for c in st.session_state.creatures:
    grid[c.y, c.x] = c.color()

display_img = np.kron(grid, np.ones((PIXEL_SIZE, PIXEL_SIZE, 1), dtype=np.uint8))
display.image(display_img, use_container_width=False, caption="Creature Mood Grid")

mood_lines = [
    f"{get_mood_emoji(c.stress, c.energy, c.disinhibited)} {c.name}: ⚡ {c.energy:.2f}, 😰 {c.stress:.2f}"
    for c in st.session_state.creatures[:10]
]
stats.markdown("**Moods**\n" + "\n".join(mood_lines))
