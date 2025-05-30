import streamlit as st
import numpy as np
import random
import json
from PIL import Image, ImageDraw, ImageFont
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
SEASON_OPTIONS = ["spring", "summer", "fall", "winter"]
DAY_NIGHT_OPTIONS = ["day", "night"]

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

    def update(self, creatures, energy_sources, weather, season, day_night):
        # Weather stress impact
        if weather == "sunny":
            self.stress -= 0.01
        elif weather == "cloudy":
            pass
        elif weather == "rainy":
            self.stress += 0.01
        elif weather == "stormy":
            self.stress += 0.03

        # Seasonal stress/relief
        if season == "winter":
            self.stress += 0.02
        elif season == "summer":
            self.stress -= 0.01

        # Day/Night energy drain/boost
        if day_night == "night":
            self.energy -= 0.02
        else:
            self.energy += 0.01

        # Clamp stress
        self.stress = min(1.0, max(0.0, self.stress))
        self.energy = min(MAX_ENERGY, max(0.0, self.energy))

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

def draw_grid(creatures, energy_sources, weather, season, day_night):
    base_color = (30, 30, 30)

    if weather == "sunny":
        base_color = (255, 255, 200)
    elif weather == "cloudy":
        base_color = (180, 180, 200)
    elif weather == "rainy":
        base_color = (100, 100, 150)
    elif weather == "stormy":
        base_color = (50, 50, 80)

    # Apply seasonal tint
    if season == "spring":
        base_color = tuple(min(255, c + 30) for c in base_color)
    elif season == "autumn" or season == "fall":
        base_color = (base_color[0] + 30, base_color[1], base_color[2])
    elif season == "winter":
        base_color = tuple(min(255, int(c * 0.9)) for c in base_color)

    if day_night == "night":
        base_color = tuple(max(0, int(c * 0.4)) for c in base_color)

    img = Image.new("RGB", (GRID_WIDTH * CELL_SIZE, GRID_HEIGHT * CELL_SIZE), base_color)
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

st.set_page_config(page_title="Mind Sim", layout="wide")

if "sim_params" not in st.session_state:
    st.session_state.sim_params = {
        "habituation_rate": 0.95,
        "inhibition": 0.3,
        "initial_creature_count": 12,
        "energy_source_count": 20,
    }

if "weather" not in st.session_state:
    st.session_state.weather = "sunny"
if "season" not in st.session_state:
    st.session_state.season = "spring"
if "day_night" not in st.session_state:
    st.session_state.day_night = "day"
if "creatures" not in st.session_state:
    st.session_state.creatures = [Creature(random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1), random.choice(list(SPECIES_DATA.keys())))
                                  for _ in range(st.session_state.sim_params["initial_creature_count"])]
if "energy_sources" not in st.session_state:
    energy_sources = set()
    while len(energy_sources) < st.session_state.sim_params["energy_source_count"]:
        energy_sources.add((random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1)))
    st.session_state.energy_sources = list(energy_sources)
if "running" not in st.session_state:
    st.session_state.running = False

# --- Sidebar UI ---
with st.sidebar:
    st.header("WEATHER")
    st.session_state.weather = st.selectbox("Current Condition", WEATHER_OPTIONS, index=WEATHER_OPTIONS.index(st.session_state.weather))

    st.subheader("SEASON")
    st.session_state.season = st.selectbox("Current Season", SEASON_OPTIONS, index=SEASON_OPTIONS.index(st.session_state.season))

    st.subheader("DAY / NIGHT")
    st.session_state.day_night = st.selectbox("Day or Night", DAY_NIGHT_OPTIONS, index=DAY_NIGHT_OPTIONS.index(st.session_state.day_night))

    st.subheader("SIMULATION")
    if st.button("Reset"):
        st.session_state.creatures = [Creature(random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1), random.choice(list(SPECIES_DATA.keys())))
                                      for _ in range(st.session_state.sim_params["initial_creature_count"])]
        energy_sources = set()
        while len(energy_sources) < st.session_state.sim_params["energy_source_count"]:
            energy_sources.add((random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1)))
        st.session_state.energy_sources = list(energy_sources)
        st.session_state.running = False
        st.experimental_rerun()
    if st.session_state.running:
        if st.button("Pause"):
            st.session_state.running = False
    else:
        if st.button("Play"):
            st.session_state.running = True

# --- Main Simulation ---
if st.session_state.running:
    st_autorefresh(interval=500, key="refresh")

creatures = st.session_state.creatures
energy_sources = st.session_state.energy_sources
weather = st.session_state.weather
season = st.session_state.season
day_night = st.session_state.day_night

for c in creatures:
    c.update(creatures, energy_sources, weather, season, day_night)

img = draw_grid(creatures, energy_sources, weather, season, day_night)
st.image(img, width=GRID_WIDTH * CELL_SIZE)

st.subheader("CREATURE STATS")
for c in creatures:
    st.markdown(
        f"**CREATURE {c.id}** SPECIES: {c.species} MOOD: {c.mood} ENERGY: {c.energy:.1f} STRESS: {c.stress:.2f} {MOOD_DATA[c.mood]['emoji']}"
    )
