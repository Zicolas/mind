import streamlit as st
import random
import json
import numpy as np

# Constants for grid size
GRID_WIDTH = 20
GRID_HEIGHT = 20

# Creature class with id attribute added
class Creature:
    _id_counter = 0

    def __init__(self, x, y, energy=100):
        self.id = Creature._id_counter
        Creature._id_counter += 1
        self.x = int(x)  # Ensure x is int
        self.y = int(y)  # Ensure y is int
        self.energy = int(energy)  # Ensure energy is int

    def move(self, dx, dy):
        self.x = max(0, min(GRID_WIDTH - 1, self.x + dx))
        self.y = max(0, min(GRID_HEIGHT - 1, self.y + dy))

    def to_dict(self):
        # Return a dict representation, making sure all are JSON serializable (convert numpy int64 to int)
        return {
            "id": int(self.id),
            "x": int(self.x),
            "y": int(self.y),
            "energy": int(self.energy)
        }

# EnergySource class
class EnergySource:
    def __init__(self, x, y, energy=50):
        self.x = int(x)
        self.y = int(y)
        self.energy = int(energy)

    def to_dict(self):
        return {
            "x": int(self.x),
            "y": int(self.y),
            "energy": int(self.energy)
        }

# Serialize creatures: use .to_dict() to ensure JSON compatibility
def serialize_creatures(creatures):
    return json.dumps([c.to_dict() for c in creatures])

# Serialize energy sources similarly
def serialize_energy_sources(energy_sources):
    return json.dumps([e.to_dict() for e in energy_sources])

# Initialize session state if not present
if "creatures" not in st.session_state:
    st.session_state.creatures = [
        Creature(random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1)) for _ in range(10)
    ]

if "energy_sources" not in st.session_state:
    st.session_state.energy_sources = [
        EnergySource(random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1)) for _ in range(5)
    ]

# Running flag
if "running" not in st.session_state:
    st.session_state.running = False

# Streamlit UI and simulation logic
st.title("Creature Simulation")

if st.button("Start"):
    st.session_state.running = True

if st.button("Stop"):
    st.session_state.running = False

if st.session_state.running:
    # Example simulation step: move creatures randomly
    for c in st.session_state.creatures:
        dx = random.choice([-1, 0, 1])
        dy = random.choice([-1, 0, 1])
        c.move(dx, dy)

    st.write("Simulation running...")

# Display creatures and energy sources JSON
st.subheader("Save / Load Simulation")
saved_creatures = serialize_creatures(st.session_state.creatures)
saved_energy = serialize_energy_sources(st.session_state.energy_sources)

st.text_area("Creatures JSON", saved_creatures, height=180, key="saved_creatures_area")
st.text_area("Energy Sources JSON", saved_energy, height=180, key="saved_energy_area")

# Optionally: Load creatures from JSON input
load_creatures_json = st.text_area("Load Creatures JSON", height=180)
if st.button("Load Creatures"):
    try:
        loaded_list = json.loads(load_creatures_json)
        new_creatures = []
        for c_dict in loaded_list:
            # Safely load and convert values to int
            x = int(c_dict.get("x", 0))
            y = int(c_dict.get("y", 0))
            energy = int(c_dict.get("energy", 100))
            creature = Creature(x, y, energy)
            new_creatures.append(creature)
        st.session_state.creatures = new_creatures
        st.success("Creatures loaded successfully!")
    except Exception as e:
        st.error(f"Failed to load creatures: {e}")

# Display creatures on grid (simple visualization)
grid_display = [["." for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
for c in st.session_state.creatures:
    grid_display[c.y][c.x] = "C"
for e in st.session_state.energy_sources:
    # Mark energy sources as E if empty spot or keep C if creature already there
    if grid_display[e.y][e.x] == ".":
        grid_display[e.y][e.x] = "E"

st.subheader("Grid View")
for row in grid_display:
    st.text(" ".join(row))
