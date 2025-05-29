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
MAX_ENERGY = 10.0
MAX_HISTORY = 50  # For stats tracking history length

# Species data (two species with distinct colors)
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
        self.energy = random.uniform(4, 7)
        self.stress = 0.0
        self.habituation_rate = st.session_state.sim_params['habituation_rate']
        self.inhibition = st.session_state.sim_params['inhibition']
        self.disinhibited = False
        self.constricted = False
        self.response = 1.0
        self.mood = "neutral"

        # Stats history (energy and stress)
        self.energy_history = deque(maxlen=MAX_HISTORY)
        self.stress_history = deque(maxlen=MAX_HISTORY)

    def update(self, creatures, energy_sources):
        self.habituation_rate = st.session_state.sim_params['habituation_rate']
        self.inhibition = st.session_state.sim_params['inhibition']

        # Habituation and inhibition
        self.response *= self.habituation_rate
        if not self.disinhibited:
            self.response -= self.inhibition

        # Stress contagion from neighbors
        neighbors = [c for c in creatures if abs(c.x - self.x) <= 1 and abs(c.y - self.y) <= 1 and c.id != self.id]
        if neighbors:
            avg_neighbor_stress = sum(n.stress for n in neighbors) / len(neighbors)
            self.stress += (avg_neighbor_stress - self.stress) * 0.05

        # Small random stress fluctuation
        stress_change = (random.random() - 0.5) * 0.05
        self.stress = min(1.0, max(0.0, self.stress + stress_change))

        self.constricted = self.stress > 0.7
        if random.random() < 0.05:
            self.disinhibited = not self.disinhibited

        self.energy -= 0.12

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
                self.energy = min(MAX_ENERGY, self.energy + 5)
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
            self.energy = random.uniform(4, 7)
            self.stress = 0.0
            self.response = 1.0
            self.disinhibited = False

        # Mood update
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

def serialize_creatures(creatures):
    return json.dumps([{
        "id": c.id,
        "x": c.x,
        "y": c.y,
        "species": c.species,
        "energy": c.energy,
        "stress": c.stress,
        "disinhibited": c.disinhibited,
        "response": c.response,
        "mood": c.mood,
    } for c in creatures], indent=2)

def deserialize_creatures(json_str):
    data = json.loads(json_str)
    creatures = []
    Creature._id_counter = 0
    for cdata in data:
        c = Creature(cdata["x"], cdata["y"], cdata["species"])
        c.energy = cdata["energy"]
        c.stress = cdata["stress"]
        c.disinhibited = cdata["disinhibited"]
        c.response = cdata["response"]
        c.mood = cdata["mood"]
        c.id = cdata["id"]
        if c.id >= Creature._id_counter:
            Creature._id_counter = c.id + 1
        creatures.append(c)
    return creatures

def serialize_energy_sources(sources):
    return json.dumps(sources, indent=2)

def deserialize_energy_sources(json_str):
    return json.loads(json_str)

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

if "running" not in st.session_state:
    st.session_state.running = False

# --- Sidebar ---

with st.sidebar:
    st.header("Controls")

    st.subheader("Simulation Settings")
    # Use local variables for slider values to avoid instant overwrite issues
    hab_rate = st.slider("Habituation Rate", 0.7, 1.0, st.session_state.sim_params['habituation_rate'], 0.01)
    inhibition = st.slider("Inhibition", 0.0, 1.0, st.session_state.sim_params['inhibition'], 0.01)
    initial_creatures = st.number_input("Initial Creature Count", 1, 50, st.session_state.sim_params['initial_creature_count'], 1)
    energy_sources_count = st.number_input("Energy Source Count", 0, 100, st.session_state.sim_params['energy_source_count'], 1)

    # Update session state only after input
    st.session_state.sim_params['habituation_rate'] = hab_rate
    st.session_state.sim_params['inhibition'] = inhibition
    st.session_state.sim_params['initial_creature_count'] = initial_creatures
    st.session_state.sim_params['energy_source_count'] = energy_sources_count

    if st.button("Reset Creatures and Energy"):
        # Reset creatures
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

        # Reset energy sources
        energy_sources = set()
        attempts = 0
        while len(energy_sources) < st.session_state.sim_params["energy_source_count"] and attempts < 300:
            ex = random.randint(0, GRID_WIDTH - 1)
            ey = random.randint(0, GRID_HEIGHT - 1)
            if not any(c.x == ex and c.y == ey for c in st.session_state.creatures) and (ex, ey) not in energy_sources:
                energy_sources.add((ex, ey))
            attempts += 1
        st.session_state.energy_sources = list(energy_sources)

        st.session_state.running = False
        st.experimental_rerun()

    if st.session_state.running:
        if st.button("Pause"):
            st.session_state.running = False
    else:
        if st.button("Play"):
            st.session_state.running = True

    st.markdown("---")

    if st.button("Add Creature"):
        attempts = 0
        while attempts < 100:
            x = random.randint(0, GRID_WIDTH - 1)
            y = random.randint(0, GRID_HEIGHT - 1)
            species = random.choice(list(SPECIES_DATA.keys()))
            if not any(c.x == x and c.y == y for c in st.session_state.creatures):
                st.session_state.creatures.append(Creature(x, y, species))
                break
            attempts += 1

    st.subheader("Save / Load Simulation")
    saved_creatures = serialize_creatures(st.session_state.creatures)
    saved_energy = serialize_energy_sources(st.session_state.energy_sources)

    creatures_json = st.text_area("Creatures JSON", saved_creatures, height=180, key="save_creatures_area")
    energy_json = st.text_area("Energy Sources JSON", saved_energy, height=80, key="save_energy_area")

    if st.button("Load Simulation from JSON"):
        try:
            loaded_creatures = deserialize_creatures(creatures_json)
            loaded_energy = deserialize_energy_sources(energy_json)
            st.session_state.creatures = loaded_creatures
            st.session_state.energy_sources = loaded_energy
            st.success("Simulation loaded successfully!")
        except Exception as e:
            st.error(f"Failed to load simulation: {e}")

    st.markdown("---")

    st.subheader("Creature Profiles")
    creature_ids = [c.id for c in st.session_state.creatures]
    if creature_ids:
        selected_id = st.selectbox("Select Creature by ID", options=creature_ids)
        selected_creature = next((c for c in st.session_state.creatures if c.id == selected_id), None)
        if selected_creature:
            st.write(f"**ID:** {selected_creature.id}")
            st.write(f"**Species:** {selected_creature.species}")
            st.write(f"**Position:** ({selected_creature.x}, {selected_creature.y})")
            st.write(f"**Mood:** {selected_creature.mood} {MOOD_DATA[selected_creature.mood]['emoji']}")
            st.write(f"**Energy:** {selected_creature.energy:.2f}")
            st.write(f"**Stress:** {selected_creature.stress:.2f}")
            st.write(f"**Disinhibited:** {selected_creature.disinhibited}")

            # Show energy and stress history chart
            import pandas as pd
            df = pd.DataFrame({
                "Energy": list(selected_creature.energy_history),
                "Stress": list(selected_creature.stress_history),
            })
            st.line_chart(df)

# --- Main Simulation Loop ---

if st.session_state.running:
    # Autorefresh page every 500 ms for animation effect
    st_autorefresh(interval=500, limit=None, key="autorefresh")

    # Update all creatures
    for c in st.session_state.creatures:
        c.update(st.session_state.creatures, st.session_state.energy_sources)

# Draw the grid and creatures
grid_img = draw_grid(st.session_state.creatures, st.session_state.energy_sources)
st.image(grid_img, caption="Simulation Grid", use_container_width=True)
