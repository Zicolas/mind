import streamlit as st
import numpy as np
import random
from streamlit_autorefresh import st_autorefresh

GRID_WIDTH, GRID_HEIGHT = 30, 20
PIXEL_SIZE = 15
DEFAULT_NUM_CREATURES = 10
MAX_ENERGY = 10

class Creature:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.energy = random.uniform(4, 7)
        self.stress = 0.0
        self.mood = "😊"
        self.response = 1.0
        self.habituation_rate = 0.95
        self.inhibition = 0.3
        self.disinhibited = False
        self.constricted = False

    def sense_nutrients(self, nutrient_grid):
        # Simple 3x3 neighborhood sensing nutrient level, weighted by proximity
        total = 0
        count = 0
        for dx in [-1,0,1]:
            for dy in [-1,0,1]:
                nx, ny = self.x+dx, self.y+dy
                if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                    weight = 1.0 if dx==0 and dy==0 else 0.5
                    total += nutrient_grid[ny,nx] * weight
                    count += weight
        return total / count if count > 0 else 0

    def move(self, nutrient_grid, creatures):
        if self.constricted:
            # Move away from crowded spots if stressed
            dx, dy = 0,0
            min_crowd = float('inf')
            for mx in [-1,0,1]:
                for my in [-1,0,1]:
                    nx, ny = self.x+mx, self.y+my
                    if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                        crowd = sum(1 for c in creatures if abs(c.x-nx)<=0 and abs(c.y-ny)<=0)
                        if crowd < min_crowd:
                            min_crowd = crowd
                            dx, dy = mx, my
            new_x = max(0, min(GRID_WIDTH-1, self.x + dx))
            new_y = max(0, min(GRID_HEIGHT-1, self.y + dy))
            self.x, self.y = new_x, new_y
            self.energy -= 0.5
            return

        # Chemotaxis: move toward higher nutrients + slight social attraction to others
        best_score = -float('inf')
        best_pos = (self.x, self.y)
        for dx in [-1,0,1]:
            for dy in [-1,0,1]:
                nx, ny = self.x + dx, self.y + dy
                if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                    nutrient_val = nutrient_grid[ny, nx]
                    # Social attraction score
                    social = sum(1 for c in creatures if abs(c.x - nx) <= 1 and abs(c.y - ny) <= 1)
                    score = nutrient_val * 2 + social * 0.5
                    if score > best_score:
                        best_score = score
                        best_pos = (nx, ny)
        if best_pos != (self.x, self.y):
            self.x, self.y = best_pos
            self.energy -= 0.3  # moving costs energy

    def update(self, nutrient_grid, creatures):
        # Habituation reduces response over time
        self.response *= self.habituation_rate

        # Inhibition reduces response unless disinhibited
        if not self.disinhibited:
            self.response -= self.inhibition
            self.response = max(0, self.response)

        # Stress is based on nearby creature density
        nearby = sum(1 for c in creatures if abs(c.x - self.x) <= 1 and abs(c.y - self.y) <= 1 and c != self)
        self.stress = min(1.0, nearby / 5)

        # Constriction if stress high
        self.constricted = self.stress > 0.6
        self.mood = "😡" if self.constricted else "😊"

        # Disinhibition event randomly resets inhibition
        if random.random() < 0.03:
            self.disinhibited = True
            self.inhibition = 0.0
        elif self.disinhibited:
            self.inhibition += 0.05
            if self.inhibition >= 0.3:
                self.inhibition = 0.3
                self.disinhibited = False

        # Gain energy by "eating" nutrient at current position
        gained = nutrient_grid[self.y, self.x]
        self.energy += gained
        nutrient_grid[self.y, self.x] = max(0, nutrient_grid[self.y, self.x] - gained)

        # Move (cost energy)
        self.move(nutrient_grid, creatures)

        # Lose small energy each update for metabolism
        self.energy -= 0.1

    def can_reproduce(self):
        return self.energy > 8

    def reproduce(self):
        self.energy /= 2
        # New creature nearby
        dx = random.choice([-1,0,1])
        dy = random.choice([-1,0,1])
        nx = max(0, min(GRID_WIDTH-1, self.x + dx))
        ny = max(0, min(GRID_HEIGHT-1, self.y + dy))
        return Creature(nx, ny)


def create_creatures(num):
    return [Creature(random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1)) for _ in range(num)]

def create_nutrient_grid():
    # Random nutrients scattered around
    grid = np.random.rand(GRID_HEIGHT, GRID_WIDTH) * 0.5
    # Add some nutrient hotspots
    for _ in range(5):
        cx = random.randint(5, GRID_WIDTH-6)
        cy = random.randint(5, GRID_HEIGHT-6)
        for dx in range(-3,4):
            for dy in range(-3,4):
                x,y = cx+dx, cy+dy
                if 0 <= x < GRID_WIDTH and 0 <= y < GRID_HEIGHT:
                    dist = abs(dx)+abs(dy)
                    grid[y,x] += max(0, 1 - dist*0.3)
    return np.clip(grid, 0, 1)


if "running" not in st.session_state:
    st.session_state.running = False
if "creatures" not in st.session_state:
    st.session_state.creatures = create_creatures(DEFAULT_NUM_CREATURES)
if "nutrients" not in st.session_state:
    st.session_state.nutrients = create_nutrient_grid()

st.title("Primitive Organism Behavior Simulator 🧬")

# Controls
col1, col2, col3, col4 = st.columns([1,1,1,4])
with col1:
    if st.button("▶️ Play" if not st.session_state.running else "⏸ Pause"):
        st.session_state.running = not st.session_state.running
with col2:
    if st.button("➕ Add Creature"):
        st.session_state.creatures.append(Creature(random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1)))
with col3:
    if st.button("🔄 Reset"):
        st.session_state.creatures = create_creatures(DEFAULT_NUM_CREATURES)
        st.session_state.nutrients = create_nutrient_grid()
with col4:
    st.write("Play/Pause simulation; Add or Reset creatures anytime.")

# Auto refresh every 500ms if running
if st.session_state.running:
    st_autorefresh(interval=500, limit=None, key="refresh")

# Update simulation if running
if st.session_state.running:
    new_creatures = []
    for c in st.session_state.creatures:
        c.update(st.session_state.nutrients, st.session_state.creatures)
        if c.can_reproduce():
            new_creatures.append(c.reproduce())
    st.session_state.creatures.extend(new_creatures)
    # Remove dead creatures (energy <= 0)
    st.session_state.creatures = [c for c in st.session_state.creatures if c.energy > 0]

# Build RGB grid for display: nutrient = blue, creatures = green/red
grid = np.zeros((GRID_HEIGHT, GRID_WIDTH, 3), dtype=np.uint8)

# Nutrient layer - blue intensity
blue_intensity = (st.session_state.nutrients * 255).astype(np.uint8)
grid[:,:,2] = blue_intensity

# Creature layer - green if calm, red if stressed, with brightness based on energy
for c in st.session_state.creatures:
    brightness = int(100 + 155 * min(1.0, c.energy / MAX_ENERGY))
    if c.constricted:
        color = [brightness, 0, 0]  # red tone
    else:
        color = [0, brightness, 0]  # green tone
    grid[c.y, c.x] = color

# Upscale for display
display_img = np.kron(grid, np.ones((PIXEL_SIZE, PIXEL_SIZE, 1), dtype=np.uint8))

# Mood panel with emojis + counts
happy_count = sum(1 for c in st.session_state.creatures if not c.constricted)
angry_count = len(st.session_state.creatures) - happy_count
st.markdown(f"### Mood: 😊 {happy_count}    😡 {angry_count}    Creatures: {len(st.session_state.creatures)}")

# Show grid
st.image(display_img, caption="Nutrient + Creatures Grid", use_container_width=False)
