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
MAX_HEALTH = 10.0

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
        self.health = MAX_HEALTH
        self.stress = 0.0
        self.habituation_rate = 0.95
        self.inhibition = 0.3
        self.disinhibited = False
        self.constricted = False
        self.response = 1.0
        self.mood = "neutral"
        self.age = 0
        self.memory = []  # stores last positions for trail
        self.signal_strength = 0  # how far mood signals reach

    def learn(self, learning_rate):
        # Simple adaptation: reduce stress slightly based on learning_rate
        self.stress = max(0, self.stress - learning_rate * 0.05)

    def communicate(self, creatures, signal_strength):
        # Affect nearby creatures' stress based on mood and signal strength
        self.signal_strength = signal_strength
        for other in creatures:
            if other is self:
                continue
            dist = abs(self.x - other.x) + abs(self.y - other.y)
            if dist <= self.signal_strength:
                if self.mood == "happy":
                    other.stress = max(0, other.stress - 0.02)
                elif self.mood == "angry":
                    other.stress = min(1, other.stress + 0.05)
                elif self.mood == "stressed":
                    other.stress = min(1, other.stress + 0.03)

    def reproduce(self, creatures, mutation_rate):
        # If energy high enough, create new creature nearby with mutation
        if self.energy > 8:
            directions = [(1,0), (-1,0), (0,1), (0,-1)]
            random.shuffle(directions)
            for dx, dy in directions:
                nx, ny = self.x + dx, self.y + dy
                if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                    if not any(c.x == nx and c.y == ny for c in creatures):
                        # Create mutated offspring
                        child = Creature(nx, ny)
                        # Mutate attributes slightly
                        child.habituation_rate = max(0.8, min(1.0, self.habituation_rate + random.uniform(-mutation_rate, mutation_rate)))
                        child.inhibition = max(0.0, min(0.5, self.inhibition + random.uniform(-mutation_rate, mutation_rate)))
                        child.energy = self.energy / 2
                        self.energy /= 2
                        creatures.append(child)
                        break

    def heal(self, health_decay_rate):
        # Health decays proportionally to stress
        self.health -= health_decay_rate * self.stress
        self.health = max(0, self.health)
        # Low health increases stress
        if self.health < 3:
            self.stress = min(1, self.stress + 0.05)

    def update(self, creatures, settings):
        self.age += 1

        self.response *= self.habituation_rate
        if not self.disinhibited:
            self.response -= self.inhibition

        # Stress fluctuates randomly
        stress_change = (random.random() - 0.5) * 0.1
        self.stress = min(1.0, max(0.0, self.stress + stress_change))

        self.constricted = self.stress > 0.7

        if random.random() < 0.05:
            self.disinhibited = not self.disinhibited
            self.inhibition = 0.0 if self.disinhibited else 0.3

        # Energy loss each update
        self.energy -= 0.1

        # Energy sources logic if enabled
        if settings['goals_enabled'] and settings['energy_sources']:
            # Move towards nearest energy source if low energy
            if self.energy < 6:
                closest_source = None
                closest_dist = 9999
                for (sx, sy) in settings['energy_sources']:
                    dist = abs(self.x - sx) + abs(self.y - sy)
                    if dist < closest_dist:
                        closest_dist = dist
                        closest_source = (sx, sy)
                if closest_source:
                    dx = np.sign(closest_source[0] - self.x)
                    dy = np.sign(closest_source[1] - self.y)
                    new_x = min(max(self.x + dx, 0), GRID_WIDTH - 1)
                    new_y = min(max(self.y + dy, 0), GRID_HEIGHT - 1)
                    if not any(c.x == new_x and c.y == new_y for c in creatures):
                        self.x = new_x
                        self.y = new_y
                    # If reached energy source, recharge
                    if self.x == closest_source[0] and self.y == closest_source[1]:
                        self.energy = min(MAX_ENERGY, self.energy + settings['energy_recharge_rate'])

        # Natural energy decay if not at source
        if self.energy <= 0:
            self.energy = random.uniform(4, 7)
            self.stress = 0.0
            self.response = 1.0
            self.disinhibited = False
            self.inhibition = 0.3
            self.health = MAX_HEALTH  # reset health on "respawn"

        # Mood update logic
        if self.stress < 0.3 and self.energy > 6:
            self.mood = "happy"
        elif self.stress > 0.7:
            self.mood = "angry"
        elif self.stress > 0.4:
            self.mood = "stressed"
        else:
            self.mood = "neutral"

        # Learning if enabled
        if settings['learning_enabled']:
            self.learn(settings['learning_rate'])

        # Communication if enabled
        if settings['communication_enabled']:
            self.communicate(creatures, settings['signal_strength'])

        # Health decay if enabled
        if settings['health_enabled']:
            self.heal(settings['health_decay_rate'])

        # Reproduction if enabled
        if settings['reproduction_enabled']:
            self.reproduce(creatures, settings['mutation_rate'])

        # Movement if not constricted or moving towards energy source
        if not self.constricted and (not settings['goals_enabled'] or self.energy >= 6):
            dx = random.choice([-1, 0, 1])
            dy = random.choice([-1, 0, 1])
            new_x = min(max(self.x + dx, 0), GRID_WIDTH - 1)
            new_y = min(max(self.y + dy, 0), GRID_HEIGHT - 1)
            if not any(c.x == new_x and c.y == new_y for c in creatures):
                self.x = new_x
                self.y = new_y

        # Update memory for trail visualization if enabled
        if settings['memory_enabled']:
            self.memory.append((self.x, self.y))
            if len(self.memory) > settings['memory_trail_length']:
                self.memory.pop(0)
        else:
            self.memory = []

def draw_grid(creatures, energy_sources, settings):
    img = Image.new("RGB", (GRID_WIDTH * CELL_SIZE, GRID_HEIGHT * CELL_SIZE), (30, 30, 30))
    draw = ImageDraw.Draw(img)

    # Draw grid lines
    for x in range(GRID_WIDTH + 1):
        draw.line([(x * CELL_SIZE, 0), (x * CELL_SIZE, GRID_HEIGHT * CELL_SIZE)], fill=(50, 50, 50))
    for y in range(GRID_HEIGHT + 1):
        draw.line([(0, y * CELL_SIZE), (GRID_WIDTH * CELL_SIZE, y * CELL_SIZE)], fill=(50, 50, 50))

    # Draw energy sources if enabled
    if settings['goals_enabled']:
        for (ex, ey) in energy_sources:
            top_left = (ex * CELL_SIZE + 4, ey * CELL_SIZE + 4)
            bottom_right = ((ex + 1) * CELL_SIZE - 4, (ey + 1) * CELL_SIZE - 4)
            draw.ellipse([top_left, bottom_right], fill=(0, 255, 255))

    # Draw creatures and memory trails
    for c in creatures:
        # Draw memory trail if enabled
        if settings['memory_enabled'] and len(c.memory) > 1:
            for i in range(len(c.memory)-1):
                x1, y1 = c.memory[i]
                x2, y2 = c.memory[i+1]
                draw.line(
                    [
                        (x1 * CELL_SIZE + CELL_SIZE//2, y1 * CELL_SIZE + CELL_SIZE//2),
                        (x2 * CELL_SIZE + CELL_SIZE//2, y2 * CELL_SIZE + CELL_SIZE//2),
                    ],
                    fill=(150, 150, 150),
                    width=2,
                )
        mood_color = MOOD_DATA[c.mood]["color"]
        brightness = int(100 + 155 * min(1.0, c.energy / MAX_ENERGY))
        color = tuple(min(255, int(brightness * (v / 255))) for v in mood_color)
        top_left = (c.x * CELL_SIZE + 2, c.y * CELL_SIZE + 2)
        bottom_right = ((c.x + 1) * CELL_SIZE - 2, (c.y + 1) * CELL_SIZE - 2)
        draw.rectangle([top_left, bottom_right], fill=color)

        # Draw health bar above creature if health enabled
        if settings['health_enabled']:
            health_ratio = c.health / MAX_HEALTH
            bar_width = CELL_SIZE - 4
            bar_height = 4
            bar_x1 = c.x * CELL_SIZE + 2
            bar_y1 = c.y * CELL_SIZE
            bar_x2 = bar_x1 + int(bar_width * health_ratio)
            bar_y2 = bar_y1 + bar_height
            draw.rectangle([bar_x1, bar_y1, bar_x2, bar_y2], fill=(0, 255, 0))
            draw.rectangle([bar_x1, bar_y1, bar_x1 + bar_width, bar_y2], outline=(255, 255, 255))

    return img

# Streamlit app setup
st.set_page_config(page_title="Mind Simulation Grid v2", layout="wide")
st.title("🧠 Mind Simulation Sandbox v2 — Customizable")

# Initialize session state
if "creatures" not in st.session_state:
    st.session_state.creatures = [
        Creature(random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1))
        for _ in range(10)
    ]

if "running" not in st.session_state:
    st.session_state.running = False

if "energy_sources" not in st.session_state:
    # Randomly place 5 energy sources
    st.session_state.energy_sources = [
        (random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1)) for _ in range(5)
    ]

# Sidebar: Controls + Simulation Settings
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

    st.markdown("---")
    st.header("Simulation Settings")

    # Learning
    learning_enabled = st.checkbox("Enable Learning/Adaptation", value=True)
    learning_rate = st.slider("Learning Rate", 0.0, 0.2, 0.05, 0.01)

    # Social Interaction (not fully implemented but place-holder)
    social_enabled = st.checkbox("Enable Social Interaction (Mood Effects)", value=True)
    social_influence_radius = st.slider("Social Influence Radius", 0, 5, 2, 1)
    social_stress_factor = st.slider("Social Stress Impact", 0.0, 0.2, 0.05, 0.01)

    # Goals / Energy sources
    goals_enabled = st.checkbox("Enable Energy Sources", value=True)
    energy_source_count = st.slider("Number of Energy Sources", 1, 10, 5)
    energy_recharge_rate = st.slider("Energy Recharge Rate at Sources", 0.1, 1.0, 0.5, 0.1)

    # Communication
    communication_enabled = st.checkbox("Enable Communication (Mood Signals)", value=True)
    signal_strength = st.slider("Signal Strength (Mood Signal Radius)", 0, 10, 3)

    # Evolution / Reproduction
    reproduction_enabled = st.checkbox("Enable Reproduction", value=True)
    energy_threshold_for_reproduction = st.slider("Energy Threshold to Reproduce", 5, 10, 8)
    mutation_rate = st.slider("Mutation Rate", 0.0, 0.2, 0.05, 0.01)

    # Health & Damage
    health_enabled = st.checkbox("Enable Health & Damage", value=True)
    health_decay_rate = st.slider("Health Decay Rate (Stress Impact)", 0.0, 0.2, 0.05, 0.01)

    # Memory Visualization
    memory_enabled = st.checkbox("Show Memory Trails", value=True)
    memory_trail_length = st.slider("Memory Trail Length", 0, 20, 10)

    # Update energy sources if count changed
    if len(st.session_state.energy_sources) != energy_source_count:
        st.session_state.energy_sources = [
            (random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1))
            for _ in range(energy_source_count)
        ]

# Bundle settings into a dict for passing around
settings = {
    'learning_enabled': learning_enabled,
    'learning_rate': learning_rate,
    'social_enabled': social_enabled,
    'social_influence_radius': social_influence_radius,
    'social_stress_factor': social_stress_factor,
    'goals_enabled': goals_enabled,
    'energy_sources': st.session_state.energy_sources if goals_enabled else [],
    'energy_recharge_rate': energy_recharge_rate,
    'communication_enabled': communication_enabled,
    'signal_strength': signal_strength,
    'reproduction_enabled': reproduction_enabled,
    'energy_threshold_for_reproduction': energy_threshold_for_reproduction,
    'mutation_rate': mutation_rate,
    'health_enabled': health_enabled,
    'health_decay_rate': health_decay_rate,
    'memory_enabled': memory_enabled,
    'memory_trail_length': memory_trail_length,
}

# Auto-refresh and update creatures if running
if st.session_state.running:
    count = st_autorefresh(interval=500, limit=None, key="autorefresh")
    for c in st.session_state.creatures:
        c.update(st.session_state.creatures, settings)

# Draw and display grid
img = draw_grid(st.session_state.creatures, settings['energy_sources'], settings)
st.image(img, width=GRID_WIDTH * CELL_SIZE)

# Show creatures' moods and stats
st.markdown("### Creatures' Moods and Stats")
cols = st.columns(min(len(st.session_state.creatures), 20))
for idx, c in enumerate(st.session_state.creatures):
    with cols[idx]:
        st.write(f"{MOOD_DATA[c.mood]['emoji']} Energy: {c.energy:.1f}\nStress: {c.stress:.2f}\nHealth: {c.health:.1f}\nAge: {c.age}")

