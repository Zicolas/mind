import streamlit as st
import numpy as np
import random
from streamlit_autorefresh import st_autorefresh

GRID_WIDTH, GRID_HEIGHT = 20, 15
PIXEL_SIZE = 20
DEFAULT_NUM_CREATURES = 5

class Creature:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.response = 1.0
        self.habituation_rate = 0.9
        self.inhibition = 0.5
        self.disinhibited = False
        self.constricted = False
        self.stress_level = 0.0  # 0 to 1
        self.mood = "😊"

    def update(self, others):
        # Habituation
        self.response *= self.habituation_rate

        # Inhibition
        if not self.disinhibited:
            self.response -= self.inhibition
            if self.response < 0:
                self.response = 0

        # Stress increases if many creatures nearby
        nearby = sum(1 for c in others if abs(c.x - self.x) <= 1 and abs(c.y - self.y) <= 1 and c != self)
        self.stress_level = min(1.0, nearby / 4)

        # Constriction logic
        if self.stress_level > 0.7:
            self.constricted = True
            self.mood = "😡"
        else:
            self.constricted = False
            self.mood = "😊"

        # Disinhibition event randomly
        if random.random() < 0.05:
            self.disinhibited = True
            self.inhibition = 0.0
        else:
            # Recover inhibition slowly
            if self.disinhibited:
                self.inhibition += 0.05
                if self.inhibition >= 0.5:
                    self.inhibition = 0.5
                    self.disinhibited = False

        # Movement: if not constricted, move randomly inside grid
        if not self.constricted:
            dx = random.choice([-1, 0, 1])
            dy = random.choice([-1, 0, 1])
            new_x = max(0, min(GRID_WIDTH - 1, self.x + dx))
            new_y = max(0, min(GRID_HEIGHT - 1, self.y + dy))
            self.x, self.y = new_x, new_y


def create_creatures(num):
    return [Creature(random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1)) for _ in range(num)]

# Initialize session state
if "running" not in st.session_state:
    st.session_state.running = False
if "creatures" not in st.session_state:
    st.session_state.creatures = create_creatures(DEFAULT_NUM_CREATURES)

st.title("Creature Mind Simulator 🧠")

# Controls
col1, col2, col3, col4 = st.columns([1,1,1,4])
with col1:
    if st.button("▶️ Play" if not st.session_state.running else "⏸ Pause"):
        st.session_state.running = not st.session_state.running
with col2:
    if st.button("➕ Add Creature"):
        st.session_state.creatures.append(Creature(random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1)))
with col3:
    if st.button("🔄 Reset Creatures"):
        st.session_state.creatures = create_creatures(DEFAULT_NUM_CREATURES)
with col4:
    st.write("Use Play/Pause to run simulation; add or reset creatures anytime.")

# Autorefresh only if running
if st.session_state.running:
    st_autorefresh(interval=500, limit=None, key="refresh")

# Update creatures if running
if st.session_state.running:
    for c in st.session_state.creatures:
        c.update(st.session_state.creatures)

# Create empty grid
grid = np.zeros((GRID_HEIGHT, GRID_WIDTH, 3), dtype=np.uint8)

# Draw creatures on grid with colors based on mood
for c in st.session_state.creatures:
    color = [0, 255, 0] if not c.constricted else [255, 0, 0]  # green if calm, red if stressed
    grid[c.y, c.x] = color

# Scale grid pixels for display
display_img = np.kron(grid, np.ones((PIXEL_SIZE, PIXEL_SIZE, 1), dtype=np.uint8))

# Show mood emoji panel
moods = " ".join([c.mood for c in st.session_state.creatures])
st.markdown(f"### Creature moods: {moods}")

# Show grid image
st.image(display_img, caption="Creature Grid", use_container_width=False)
