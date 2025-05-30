import streamlit as st
import numpy as np
import random
import json
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from streamlit_autorefresh import st_autorefresh
from collections import deque

# Constants
GRID_WIDTH = 30
GRID_HEIGHT = 30
CELL_SIZE = 20
MAX_ENERGY = 15.0
MAX_HISTORY = 50

TRAIL_FADE_STEPS = 10

# Weather options
WEATHER_OPTIONS = ["sunny", "cloudy", "rainy", "stormy"]
SEASON_OPTIONS = ["spring", "summer", "fall", "winter"]
DAY_NIGHT_OPTIONS = ["day", "night"]

# Color mapping for seasons and overlays
SEASON_GROUND_COLORS = {
    "spring": "#799548",
    "summer": "#A2B86C",
    "fall": "#A79548",
    "winter": "#799548",
}

# Environmental zones - added for water, obstacles, temperature zones
# Each cell in grid can be: 'normal', 'water', 'obstacle', 'cold_zone', 'hot_zone'
# We'll generate them once on reset, store in session_state
ZONE_TYPES = ['normal', 'water', 'obstacle', 'cold_zone', 'hot_zone']

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

# ---- CREATURE CLASS UPDATED ----

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

        # --- NEW: Aging & lifecycle ---
        self.age = 0
        self.lifespan = random.randint(80, 120)  # lifespan in update cycles
        self.alive = True

        # --- NEW: Memory of energy locations ---
        self.memory = set()  # set of (x, y) energy locations seen before

        # --- NEW: Mutation due to stress ---
        self.mutated = False
        self.mutation_counter = 0  # counts updates of prolonged stress
        self.mutation_threshold = 50  # after this many stressed cycles, mutate

    def update(self, creatures, energy_sources, weather, season, day_night, zones):
        if not self.alive:
            return  # dead creatures do nothing

        # Aging
        self.age += 1
        if self.age > self.lifespan or self.energy <= 0:
            self.alive = False
            return

        # Environmental zone effects
        current_zone = zones[self.x][self.y]
        if current_zone == "water":
            # Energy drain if in water and species B (just an example)
            if self.species == "B":
                self.energy -= 0.05  # water drains energy for B
            else:
                self.energy += 0.02  # species A gains small energy in water (maybe hydration)
        elif current_zone == "obstacle":
            # Can't move here; handled by movement checks later
            self.stress += 0.02  # stress increased by obstacle contact
        elif current_zone == "cold_zone":
            self.stress += 0.01
        elif current_zone == "hot_zone":
            self.stress += 0.01

        # Weather stress influence (unchanged)
        if weather == "sunny":
            self.stress -= 0.01
        elif weather == "cloudy":
            pass
        elif weather == "rainy":
            self.stress += 0.01
        elif weather == "stormy":
            self.stress += 0.03

        self.stress = min(1.0, max(0.0, self.stress))
        self.response *= self.habituation_rate
        if not self.disinhibited:
            self.response -= self.inhibition

        # --- SOCIAL BEHAVIOR / COMMUNICATION (stress signaling neighbors) ---
        neighbors = [c for c in creatures if abs(c.x - self.x) <= 1 and abs(c.y - self.y) <= 1 and c.id != self.id and c.alive]
        if neighbors:
            avg_neighbor_stress = sum(n.stress for n in neighbors) / len(neighbors)
            # Stress moves toward neighbors' stress (stress contagion)
            self.stress += (avg_neighbor_stress - self.stress) * 0.05

        self.stress = min(1.0, max(0.0, self.stress + (random.random() - 0.5) * 0.05))
        self.constricted = self.stress > 0.7
        if random.random() < 0.05:
            self.disinhibited = not self.disinhibited

        # Energy decay each step
        self.energy -= 0.06

        # Movement & energy source seeking
        if self.energy < 3 and energy_sources:
            # Prefer locations remembered if still valid
            remembered_sources = [pos for pos in self.memory if pos in energy_sources]
            if remembered_sources:
                closest = min(remembered_sources, key=lambda e: abs(e[0]-self.x)+abs(e[1]-self.y))
            else:
                closest = min(energy_sources, key=lambda e: abs(e[0]-self.x)+abs(e[1]-self.y))

            dx = np.sign(closest[0] - self.x)
            dy = np.sign(closest[1] - self.y)
            new_x = min(max(self.x + int(dx), 0), GRID_WIDTH - 1)
            new_y = min(max(self.y + int(dy), 0), GRID_HEIGHT - 1)

            # Check if new position is obstacle
            if zones[new_x][new_y] != "obstacle" and not any(c.x == new_x and c.y == new_y and c.alive for c in creatures):
                self.x = new_x
                self.y = new_y

            # If reached energy source
            if (self.x, self.y) == closest:
                self.energy = min(MAX_ENERGY, self.energy + 8)
                energy_sources.remove(closest)
                # Add to memory (learning)
                self.memory.add(closest)

        else:
            # Random move if not constrained and no urgent energy need
            if not self.constricted:
                for _ in range(5):  # try up to 5 random moves to avoid obstacles
                    dx = random.choice([-1, 0, 1])
                    dy = random.choice([-1, 0, 1])
                    new_x = min(max(self.x + dx, 0), GRID_WIDTH - 1)
                    new_y = min(max(self.y + dy, 0), GRID_HEIGHT - 1)
                    if zones[new_x][new_y] != "obstacle" and not any(c.x == new_x and c.y == new_y and c.alive for c in creatures):
                        self.x = new_x
                        self.y = new_y
                        break

        # Mood calculation (unchanged)
        if self.stress < 0.3 and self.energy > 6:
            self.mood = "happy"
        elif self.stress > 0.7:
            self.mood = "angry"
        elif self.stress > 0.4:
            self.mood = "stressed"
        else:
            self.mood = "neutral"

        # --- REPRODUCTION (new) ---
        # If energy high, stress low, and chance, reproduce a new creature nearby if space
        if self.energy > 10 and self.stress < 0.4:
            empty_neighbors = [(self.x + dx, self.y + dy) for dx in [-1,0,1] for dy in [-1,0,1]
                               if 0 <= self.x+dx < GRID_WIDTH and 0 <= self.y+dy < GRID_HEIGHT]
            empty_neighbors = [pos for pos in empty_neighbors if
                               not any(c.x == pos[0] and c.y == pos[1] and c.alive for c in creatures)
                               and zones[pos[0]][pos[1]] != "obstacle"]
            if empty_neighbors and random.random() < 0.02:  # low chance per update
                nx, ny = random.choice(empty_neighbors)
                # Spawn new creature of same species
                offspring = Creature(nx, ny, self.species)
                offspring.energy = self.energy / 2
                offspring.stress = self.stress / 2
                self.energy /= 2
                creatures.append(offspring)

        # --- STRESS-DRIVEN MUTATION ---
        if self.stress > 0.7:
            self.mutation_counter += 1
            if self.mutation_counter > self.mutation_threshold and not self.mutated:
                self.mutated = True
                # Mutation changes inhibition or habituation_rate slightly
                self.inhibition = max(0, min(1, self.inhibition + random.uniform(-0.1, 0.1)))
                self.habituation_rate = max(0.8, min(1, self.habituation_rate + random.uniform(-0.05, 0.05)))
        else:
            # Reset mutation counter if stress low
            self.mutation_counter = max(0, self.mutation_counter - 2)

        # Append histories for plotting or info
        self.energy_history.append(self.energy)
        self.stress_history.append(self.stress)

# --- Draw grid updated with zones visualization ---
def draw_grid(creatures, energy_sources, weather, season, day_night, zones):
    ground_color = "#799548" if season == "winter" else SEASON_GROUND_COLORS.get(season, "#799548")
    img = Image.new("RGB", (GRID_WIDTH * CELL_SIZE, GRID_HEIGHT * CELL_SIZE), ground_color)
    draw = ImageDraw.Draw(img)

    for x in range(GRID_WIDTH + 1):
        draw.line([(x * CELL_SIZE, 0), (x * CELL_SIZE, GRID_HEIGHT * CELL_SIZE)], fill=(50, 50, 50))
    for y in range(GRID_HEIGHT + 1):
        draw.line([(0, y * CELL_SIZE), (GRID_WIDTH * CELL_SIZE, y * CELL_SIZE)], fill=(50, 50, 50))

    # Draw environmental zones
    for x in range(GRID_WIDTH):
        for y in range(GRID_HEIGHT):
            zone = zones[x][y]
            top_left = (x * CELL_SIZE, y * CELL_SIZE)
            bottom_right = ((x + 1) * CELL_SIZE, (y + 1) * CELL_SIZE)

            if zone == "water":
                draw.rectangle([top_left, bottom_right], fill=(64, 164, 223))  # blueish
            elif zone == "obstacle":
                draw.rectangle([top_left, bottom_right], fill=(80, 80, 80))  # gray
            elif zone == "cold_zone":
                draw.rectangle([top_left, bottom_right], fill=(173, 216, 230))  # light blue
            elif zone == "hot_zone":
                draw.rectangle([top_left, bottom_right], fill=(255, 160, 122))  # light red-orange

    for ex, ey in energy_sources:
        top_left = (ex * CELL_SIZE + 4, ey * CELL_SIZE + 4)
        bottom_right = ((ex + 1) * CELL_SIZE - 4, (ey + 1) * CELL_SIZE - 4)
        draw.rectangle([top_left, bottom_right], fill=(255, 255, 0))

    # Draw fading trails
    trail_map = st.session_state.creature_trail_map
    for (tx, ty), intensity in trail_map.items():
        fade_color = (100, 100, 100, int(255 * (intensity / TRAIL_FADE_STEPS)))
        trail_overlay = Image.new("RGBA", (CELL_SIZE, CELL_SIZE), fade_color)
        img.paste(trail_overlay, (tx * CELL_SIZE, ty * CELL_SIZE), trail_overlay)
    
    for c in creatures:
        if not c.alive:
            continue  # skip dead creatures
        mood_color = SPECIES_DATA[c.species]["mood_colors"][c.mood]
        brightness = int(100 + 155 * min(1.0, c.energy / MAX_ENERGY))
        color = tuple(min(255, int(brightness * (v / 255))) for v in mood_color)
        top_left = (c.x * CELL_SIZE + 2, c.y * CELL_SIZE + 2)
        bottom_right = ((c.x + 1) * CELL_SIZE - 2, (c.y + 1) * CELL_SIZE - 2)
        draw.rectangle([top_left, bottom_right], fill=color)

        # Draw a small border if mutated
        if c.mutated:
            draw.rectangle([top_left, bottom_right], outline=(255, 0, 255), width=2)

    # Weather and season visuals
    weather_icons = {"sunny": "☀️", "cloudy": "☁️", "rainy": "🌧️", "stormy": "⛈️"}
    font = ImageFont.load_default()
    draw.text((5, 5), weather_icons.get(weather, ""), fill="white", font=font)
    draw.rectangle([5, 25, 90, 40], fill=(255, 255, 255))
    draw.text((10, 27), season.capitalize(), fill="black", font=font)
    draw.text((10, 42), day_night.capitalize(), fill="black", font=font)

    return img

# --- Initialize or reset zones on reset ---
def init_zones():
    zones = []
    for x in range(GRID_WIDTH):
        col = []
        for y in range(GRID_HEIGHT):
            # Propose zone type with preference for normal
            zone_type = "normal"
            r = random.random()

            # To increase spacing of water:
            # We'll only add water if no neighbor is water already
            def has_water_neighbor(xi, yi):
                for dx in [-1,0,1]:
                    for dy in [-1,0,1]:
                        nx, ny = xi+dx, yi+dy
                        if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                            if zones[nx][ny] == "water":
                                return True
                return False

            if r < 0.05:
                # Only set water if no neighbor water
                if not has_water_neighbor(x, y):
                    zone_type = "water"
                else:
                    zone_type = "normal"
            elif r < 0.1:
                zone_type = "obstacle"
            elif r < 0.15:
                zone_type = "cold_zone"
            elif r < 0.2:
                zone_type = "hot_zone"
            else:
                zone_type = "normal"

            col.append(zone_type)
        zones.append(col)
    return zones

# --- Main Streamlit interface ---

def main():
    if st.session_state.play_sim:
    st_autorefresh(interval=200, limit=None, key="simulation_autorefresh")

    st.title("Extended Creature Simulation with Aging, Memory, and Social Behavior")

    if "creatures" not in st.session_state:
        st.session_state.creatures = []
    if "energy_sources" not in st.session_state:
        st.session_state.energy_sources = []
    if "creature_trail_map" not in st.session_state:
        st.session_state.creature_trail_map = {}
    if "weather" not in st.session_state:
        st.session_state.weather = "sunny"
    if "season" not in st.session_state:
        st.session_state.season = "summer"
    if "day_night" not in st.session_state:
        st.session_state.day_night = "day"
    if "zones" not in st.session_state:
        st.session_state.zones = init_zones()
    if "sim_params" not in st.session_state:
        st.session_state.sim_params = {
            "habituation_rate": 0.95,
            "inhibition": 0.2,
        }

    # UI Controls
    with st.sidebar:
        st.header("Simulation Parameters")
        st.session_state.sim_params["habituation_rate"] = st.slider("Habituation rate", 0.8, 1.0, 0.95)
        st.session_state.sim_params["inhibition"] = st.slider("Inhibition", 0.0, 0.5, 0.2)
        st.session_state.weather = st.selectbox("Weather", WEATHER_OPTIONS, index=WEATHER_OPTIONS.index(st.session_state.weather))
        st.session_state.season = st.selectbox("Season", SEASON_OPTIONS, index=SEASON_OPTIONS.index(st.session_state.season))
        st.session_state.day_night = st.selectbox("Day/Night", DAY_NIGHT_OPTIONS, index=DAY_NIGHT_OPTIONS.index(st.session_state.day_night))

        if "play_sim" not in st.session_state:
        st.session_state.play_sim = False

        st.session_state.play_sim = st.checkbox("Play simulation", value=st.session_state.play_sim)
        
        if st.button("Reset Simulation"):
            st.session_state.creatures = []
            st.session_state.energy_sources = []
            st.session_state.creature_trail_map = {}
            st.session_state.zones = init_zones()

        if st.button("Add Species A"):
            for _ in range(5):
                x, y = random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1)
                if st.session_state.zones[x][y] != "obstacle":
                    st.session_state.creatures.append(Creature(x, y, "A"))

        if st.button("Add Species B"):
            for _ in range(5):
                x, y = random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1)
                if st.session_state.zones[x][y] != "obstacle":
                    st.session_state.creatures.append(Creature(x, y, "B"))

        if st.button("Add Energy Sources"):
            for _ in range(15):
                x, y = random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1)
                if st.session_state.zones[x][y] != "obstacle":
                    st.session_state.energy_sources.append((x, y))

    if st.session_state.play_sim:
    for c in st.session_state.creatures:
        c.update(st.session_state.creatures, st.session_state.energy_sources,
                 st.session_state.weather, st.session_state.season,
                 st.session_state.day_night, st.session_state.zones)

    # Remove dead creatures
    st.session_state.creatures = [c for c in st.session_state.creatures if c.alive]

    # Update trail map for fading trails
    new_trail_map = {}
    for c in st.session_state.creatures:
        key = (c.x, c.y)
        new_trail_map[key] = TRAIL_FADE_STEPS

    # Decrease trail intensity on old trails
    for key, val in st.session_state.creature_trail_map.items():
        new_val = val - 1
        if new_val > 0:
            if key in new_trail_map:
                new_trail_map[key] = max(new_trail_map[key], new_val)
            else:
                new_trail_map[key] = new_val

    st.session_state.creature_trail_map = new_trail_map

    img = draw_grid(st.session_state.creatures, st.session_state.energy_sources,
                    st.session_state.weather, st.session_state.season,
                    st.session_state.day_night, st.session_state.zones)

    st.image(img, width=GRID_WIDTH * CELL_SIZE)

    # Show creature info on hover or selected? (simplified, show summary)
    st.write(f"Creatures count: {len(st.session_state.creatures)}")
    # Show average age, mutation count
    if st.session_state.creatures:
        avg_age = sum(c.age for c in st.session_state.creatures) / len(st.session_state.creatures)
        mutated_count = sum(1 for c in st.session_state.creatures if c.mutated)
        st.write(f"Average creature age: {avg_age:.1f}")
        st.write(f"Creatures mutated: {mutated_count}")

if __name__ == "__main__":
    main()
