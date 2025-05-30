import streamlit as st
import numpy as np
import random
import json
from PIL import Image, ImageDraw
from streamlit_autorefresh import st_autorefresh
from collections import deque

# Constants
GRID_WIDTH = 30
GRID_HEIGHT = 30
CELL_SIZE = 20
MAX_ENERGY = 15.0
MAX_HISTORY = 50

WEATHER_TYPES = ["calm", "hot", "cold", "storm"]
WEATHER_EFFECTS = {
    "calm": {"energy_drain": 0.06, "stress_modifier": 0.0},
    "hot": {"energy_drain": 0.1, "stress_modifier": 0.1},
    "cold": {"energy_drain": 0.08, "stress_modifier": 0.05},
    "storm": {"energy_drain": 0.12, "stress_modifier": 0.2},
}

SPECIES_DATA = {
    "A": {"base_color": (0, 200, 0), "mood_colors": {
        "happy": (0, 255, 0),
        "neutral": (150, 200, 0),
        "stressed": (150, 100, 0),
        "angry": (150, 0, 0),
    }},
    "B": {"base_color": (0, 0, 200), "mood_colors": {
        "happy": (0, 0, 255),
        "neutral": (0, 150, 200),
        "stressed": (0, 100, 150),
        "angry": (0, 0, 150),
    }},
}

MOOD_DATA = {
    "happy": {"emoji": "😊"},
    "neutral": {"emoji": "😐"},
    "stressed": {"emoji": "😰"},
    "angry": {"emoji": "😡"},
}

class Creature:
    _id_counter = 0

    def __init__(self, x, y, species):
        self.id = Creature._id_counter
        Creature._id_counter += 1
        self.x = x
        self.y = y
        self.species = species
        self.energy = random.uniform(6, 10)
        self.stress = 0.0
        self.habituation_rate = st.session_state.sim_params['habituation_rate']
        self.inhibition = st.session_state.sim_params['inhibition']
        self.disinhibited = False
        self.constricted = False
        self.response = 1.0
        self.mood = "neutral"
        self.energy_history = deque(maxlen=MAX_HISTORY)
        self.stress_history = deque(maxlen=MAX_HISTORY)

    def update(self, creatures, energy_sources):
        self.habituation_rate = st.session_state.sim_params['habituation_rate']
        self.inhibition = st.session_state.sim_params['inhibition']

        self.response *= self.habituation_rate
        if not self.disinhibited:
            self.response -= self.inhibition

        neighbors = [c for c in creatures if abs(c.x - self.x) <= 1 and abs(c.y - self.y) <= 1 and c.id != self.id]
        if neighbors:
            avg_neighbor_stress = sum(n.stress for n in neighbors) / len(neighbors)
            self.stress += (avg_neighbor_stress - self.stress) * 0.05

        self.stress = min(1.0, max(0.0, self.stress + (random.random() - 0.5) * 0.05))

        self.constricted = self.stress > 0.7
        if random.random() < 0.05:
            self.disinhibited = not self.disinhibited

        # Weather effect (improved stress logic)
        weather = st.session_state.weather
        effect = WEATHER_EFFECTS[weather]
        self.energy -= effect["energy_drain"]

        # Adaptive stress: only push toward a weather-specific target stress level
        weather_target_stress = {
            "calm": 0.2,
            "hot": 0.4,
            "cold": 0.35,
            "storm": 0.6,
        }
        target = weather_target_stress[weather]
        self.stress += (target - self.stress) * 0.02  # Gentle adjustment
        self.stress = max(0.0, min(1.0, self.stress))

        if self.energy < 3 and energy_sources:
            closest = min(energy_sources, key=lambda e: abs(e[0]-self.x)+abs(e[1]-self.y))
            dx = np.sign(closest[0] - self.x)
            dy = np.sign(closest[1] - self.y)
            new_x = min(max(self.x + int(dx), 0), GRID_WIDTH - 1)
            new_y = min(max(self.y + int(dy), 0), GRID_HEIGHT - 1)
            if not any(c.x == new_x and c.y == new_y for c in creatures):
                self.x = new_x
                self.y = new_y
            if (self.x, self.y) == closest:
                self.energy = min(MAX_ENERGY, self.energy + 8)
                energy_sources.remove(closest)
        else:
            if not self.constricted:
                dx = random.choice([-1, 0, 1])
                dy = random.choice([-1, 0, 1])
                new_x = min(max(self.x + dx, 0), GRID_WIDTH - 1)
                new_y = min(max(self.y + dy, 0), GRID_HEIGHT - 1)
                if not any(c.x == new_x and c.y == new_y for c in creatures):
                    self.x = new_x
                    self.y = new_y

        # Regeneration zones
        if (self.x, self.y) in st.session_state.regen_zones and self.energy < MAX_ENERGY:
            self.energy = min(MAX_ENERGY, self.energy + 0.1)

        # Reproduction
        if self.energy > 13 and self.stress < 0.3 and random.random() < 0.01:
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    nx, ny = self.x + dx, self.y + dy
                    if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT and not any(c.x == nx and c.y == ny for c in creatures):
                        child = Creature(nx, ny, self.species)
                        child.energy = self.energy / 2
                        self.energy /= 2
                        st.session_state.new_creatures.append(child)
                        break

        if self.energy <= 0:
            self.energy = 0

        if self.stress < 0.3 and self.energy > 6:
            self.mood = "happy"
        elif self.stress > 0.7:
            self.mood = "angry"
        elif self.stress > 0.4:
            self.mood = "stressed"
        else:
            self.mood = "neutral"

        self.energy_history.append(self.energy)
        self.stress_history.append(self.stress)

def draw_grid(creatures, energy_sources):
    img = Image.new("RGB", (GRID_WIDTH * CELL_SIZE, GRID_HEIGHT * CELL_SIZE), (30, 30, 30))
    draw = ImageDraw.Draw(img)

    for x in range(GRID_WIDTH + 1):
        draw.line([(x * CELL_SIZE, 0), (x * CELL_SIZE, GRID_HEIGHT * CELL_SIZE)], fill=(50, 50, 50))
    for y in range(GRID_HEIGHT + 1):
        draw.line([(0, y * CELL_SIZE), (GRID_WIDTH * CELL_SIZE, y * CELL_SIZE)], fill=(50, 50, 50))

    for ex, ey in energy_sources:
        top_left = (ex * CELL_SIZE + 4, ey * CELL_SIZE + 4)
        bottom_right = ((ex + 1) * CELL_SIZE - 4, (ey + 1) * CELL_SIZE - 4)
        draw.rectangle([top_left, bottom_right], fill=(255, 255, 0))

    for rx, ry in st.session_state.regen_zones:
        top_left = (rx * CELL_SIZE + 6, ry * CELL_SIZE + 6)
        bottom_right = ((rx + 1) * CELL_SIZE - 6, (ry + 1) * CELL_SIZE - 6)
        draw.rectangle([top_left, bottom_right], fill=(0, 100, 255))

    for c in creatures:
        mood_color = SPECIES_DATA[c.species]["mood_colors"][c.mood]
        brightness = int(100 + 155 * min(1.0, c.energy / MAX_ENERGY))
        color = tuple(min(255, int(brightness * (v / 255))) for v in mood_color)
        top_left = (c.x * CELL_SIZE + 2, c.y * CELL_SIZE + 2)
        bottom_right = ((c.x + 1) * CELL_SIZE - 2, (c.y + 1) * CELL_SIZE - 2)
        draw.rectangle([top_left, bottom_right], fill=color)

    return img

# --- Streamlit UI and main loop ---

st.set_page_config(page_title="Mind Simulation Grid v2", layout="wide")
st.title("🧠 Mind Simulation Sandbox - v2 with Species & Energy")

if "sim_params" not in st.session_state:
    st.session_state.sim_params = {
        "habituation_rate": 0.95,
        "inhibition": 0.3,
        "initial_creature_count": 12,
        "energy_source_count": 20,
    }

if "creatures" not in st.session_state:
    creatures = []
    attempts = 0
    while len(creatures) < st.session_state.sim_params["initial_creature_count"] and attempts < 200:
        x = random.randint(0, GRID_WIDTH - 1)
        y = random.randint(0, GRID_HEIGHT - 1)
        species = random.choice(list(SPECIES_DATA.keys()))
        if not any(c.x == x and c.y == y for c in creatures):
            creatures.append(Creature(x, y, species))
        attempts += 1
    st.session_state.creatures = creatures

if "energy_sources" not in st.session_state:
    energy_sources = set()
    attempts = 0
    while len(energy_sources) < st.session_state.sim_params["energy_source_count"] and attempts < 300:
        ex = random.randint(0, GRID_WIDTH - 1)
        ey = random.randint(0, GRID_HEIGHT - 1)
        if not any(c.x == ex and c.y == ey for c in st.session_state.creatures) and (ex, ey) not in energy_sources:
            energy_sources.add((ex, ey))
        attempts += 1
    st.session_state.energy_sources = list(energy_sources)

if "regen_zones" not in st.session_state:
    regen_zones = set()
    while len(regen_zones) < 10:
        x = random.randint(0, GRID_WIDTH - 1)
        y = random.randint(0, GRID_HEIGHT - 1)
        regen_zones.add((x, y))
    st.session_state.regen_zones = list(regen_zones)

if "running" not in st.session_state:
    st.session_state.running = False

if "weather" not in st.session_state:
    st.session_state.weather = random.choice(WEATHER_TYPES)
    st.session_state.weather_ticks = 0

with st.sidebar:
    st.header("Controls")

    st.subheader("Simulation Settings")
    hab_rate = st.slider("Habituation Rate", 0.7, 1.0, st.session_state.sim_params['habituation_rate'], 0.01)
    inhibition = st.slider("Inhibition", 0.0, 1.0, st.session_state.sim_params['inhibition'], 0.01)
    initial_creatures = st.number_input("Initial Creature Count", 1, 50, st.session_state.sim_params['initial_creature_count'], 1)
    energy_sources_count = st.number_input("Energy Source Count", 0, 100, st.session_state.sim_params['energy_source_count'], 1)

    st.session_state.sim_params['habituation_rate'] = hab_rate
    st.session_state.sim_params['inhibition'] = inhibition
    st.session_state.sim_params['initial_creature_count'] = initial_creatures
    st.session_state.sim_params['energy_source_count'] = energy_sources_count

    if st.button("Reset Creatures and Energy"):
        st.session_state.creatures = []
        st.session_state.energy_sources = []
        st.session_state.regen_zones = []
        st.session_state.running = False
        st.rerun()

    if st.session_state.running:
        if st.button("Pause"):
            st.session_state.running = False
    else:
        if st.button("Play"):
            st.session_state.running = True

    st.markdown("---")
    st.write("Adjust parameters and reset to apply.")

if st.session_state.running:
    st_autorefresh(interval=500, key="auto_refresh")

st.session_state.weather_ticks += 1
if st.session_state.weather_ticks > 20:
    st.session_state.weather = random.choice(WEATHER_TYPES)
    st.session_state.weather_ticks = 0

st.markdown(f"### Current Weather: `{st.session_state.weather.upper()}`")

st.session_state.new_creatures = []
creatures = st.session_state.creatures
energy_sources = st.session_state.energy_sources

for c in creatures:
    c.update(creatures, energy_sources)

creatures = [c for c in creatures if c.energy > 0]
creatures.extend(st.session_state.new_creatures)
st.session_state.creatures = creatures

img = draw_grid(creatures, energy_sources)
st.image(img, width=GRID_WIDTH * CELL_SIZE)

st.subheader("Creature Status")
for c in creatures:
    st.markdown(f"**Creature {c.id}** Species: {c.species} Mood: {c.mood} Energy: {c.energy:.1f} Stress: {c.stress:.2f} {MOOD_DATA[c.mood]['emoji']}")
