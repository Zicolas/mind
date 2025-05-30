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

# Weather options
WEATHER_OPTIONS = ["sunny", "cloudy", "rainy", "stormy"]

# Species data
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
        self.habituation_rate = st.session_state.sim_params.get("habituation_rate", 0.95)
        self.inhibition = st.session_state.sim_params.get("inhibition", 0.2)
        self.disinhibited = False
        self.constricted = False
        self.response = 1.0
        self.mood = "neutral"

        self.energy_history = deque(maxlen=MAX_HISTORY)
        self.stress_history = deque(maxlen=MAX_HISTORY)

    def update(self, creatures, energy_sources, weather):
        # Weather stress impact
        if weather == "sunny":
            self.stress -= 0.01
        elif weather == "cloudy":
            pass
        elif weather == "rainy":
            self.stress += 0.01
        elif weather == "stormy":
            self.stress += 0.03

        # Clamp stress
        self.stress = min(1.0, max(0.0, self.stress))

        self.response *= self.habituation_rate
        if not self.disinhibited:
            self.response -= self.inhibition

        neighbors = [c for c in creatures if abs(c.x - self.x) <= 1 and abs(c.y - self.y) <= 1 and c.id != self.id]
        if neighbors:
            avg_neighbor_stress = sum(n.stress for n in neighbors) / len(neighbors)
            self.stress += (avg_neighbor_stress - self.stress) * 0.05

        stress_change = (random.random() - 0.5) * 0.05
        self.stress = min(1.0, max(0.0, self.stress + stress_change))

        self.constricted = self.stress > 0.7
        if random.random() < 0.05:
            self.disinhibited = not self.disinhibited

        self.energy -= 0.06

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

        if self.energy <= 0:
            self.energy = random.uniform(6, 10)
            self.stress = 0.0
            self.response = 1.0
            self.disinhibited = False

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

    for c in creatures:
        mood_color = SPECIES_DATA[c.species]["mood_colors"][c.mood]
        brightness = int(100 + 155 * min(1.0, c.energy / MAX_ENERGY))
        color = tuple(min(255, int(brightness * (v / 255))) for v in mood_color)
        top_left = (c.x * CELL_SIZE + 2, c.y * CELL_SIZE + 2)
        bottom_right = ((c.x + 1) * CELL_SIZE - 2, (c.y + 1) * CELL_SIZE - 2)
        draw.rectangle([top_left, bottom_right], fill=color)

    return img

# --- Streamlit Setup ---

st.set_page_config(page_title="Eco Sim Route", layout="wide")
st.title("🌱 Eco Simulation Grid - Real-Time Weather")

if "sim_params" not in st.session_state:
    st.session_state.sim_params = {
        "habituation_rate": 0.95,
        "inhibition": 0.3,
        "initial_creature_count": 12,
        "energy_source_count": 20,
    }

if "weather" not in st.session_state:
    st.session_state.weather = "sunny"

if "creatures" not in st.session_state:
    creatures = []
    for _ in range(st.session_state.sim_params["initial_creature_count"]):
        x = random.randint(0, GRID_WIDTH - 1)
        y = random.randint(0, GRID_HEIGHT - 1)
        species = random.choice(list(SPECIES_DATA.keys()))
        creatures.append(Creature(x, y, species))
    st.session_state.creatures = creatures

if "energy_sources" not in st.session_state:
    energy_sources = set()
    while len(energy_sources) < st.session_state.sim_params["energy_source_count"]:
        ex = random.randint(0, GRID_WIDTH - 1)
        ey = random.randint(0, GRID_HEIGHT - 1)
        energy_sources.add((ex, ey))
    st.session_state.energy_sources = list(energy_sources)

if "running" not in st.session_state:
    st.session_state.running = False

# --- Sidebar UI ---

with st.sidebar:
    st.header("WEATHER")
    st.session_state.weather = st.selectbox(
        "Current Conition", WEATHER_OPTIONS, index=WEATHER_OPTIONS.index(st.session_state.weather)
    )

    st.subheader("Simulation Settings")

    if st.button("Reset Creatures and Energy"):
        st.session_state.creatures = []
        for _ in range(st.session_state.sim_params["initial_creature_count"]):
            x = random.randint(0, GRID_WIDTH - 1)
            y = random.randint(0, GRID_HEIGHT - 1)
            species = random.choice(list(SPECIES_DATA.keys()))
            st.session_state.creatures.append(Creature(x, y, species))

        energy_sources = set()
        while len(energy_sources) < st.session_state.sim_params["energy_source_count"]:
            ex = random.randint(0, GRID_WIDTH - 1)
            ey = random.randint(0, GRID_HEIGHT - 1)
            energy_sources.add((ex, ey))
        st.session_state.energy_sources = list(energy_sources)

        st.session_state.running = False
        st.experimental_rerun()

    if st.session_state.running:
        if st.button("Pause"):
            st.session_state.running = False
    else:
        if st.button("Play"):
            st.session_state.running = True


# --- Simulation Loop ---

if st.session_state.running:
    st_autorefresh(interval=500, key="refresh")

creatures = st.session_state.creatures
energy_sources = st.session_state.energy_sources
weather = st.session_state.weather

for c in creatures:
    c.update(creatures, energy_sources, weather)

img = draw_grid(creatures, energy_sources)
st.image(img, width=GRID_WIDTH * CELL_SIZE)

st.subheader("Creature Status")
for c in creatures:
    st.markdown(
        f"**Creature {c.id}** Species: {c.species} Mood: {c.mood} Energy: {c.energy:.1f} Stress: {c.stress:.2f} {MOOD_DATA[c.mood]['emoji']}"
    )
