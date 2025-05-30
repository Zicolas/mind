import streamlit as st
import numpy as np
import random
from PIL import Image, ImageDraw, ImageFont
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

ZONE_TYPES = ['normal', 'water', 'obstacle', 'cold_zone', 'hot_zone']

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

    # Fixed constants replacing sliders:
    HABITUATION_RATE = 0.95
    INHIBITION = 0.2

    def __init__(self, x, y, species):
        self.id = Creature._id_counter
        Creature._id_counter += 1

        self.x = x
        self.y = y
        self.species = species
        self.energy = random.uniform(6, 10)
        self.stress = 0.0
        self.habituation_rate = Creature.HABITUATION_RATE
        self.inhibition = Creature.INHIBITION
        self.disinhibited = False
        self.constricted = False
        self.response = 1.0
        self.mood = "neutral"

        self.energy_history = deque(maxlen=MAX_HISTORY)
        self.stress_history = deque(maxlen=MAX_HISTORY)

        self.age = 0
        self.lifespan = random.randint(80, 120)
        self.alive = True

        self.memory = set()

        self.mutated = False
        self.mutation_counter = 0
        self.mutation_threshold = 50

    def update(self, creatures, energy_sources, weather, season, day_night, zones):
        if not self.alive:
            return

        self.age += 1
        if self.age > self.lifespan or self.energy <= 0:
            self.alive = False
            return

        current_zone = zones[self.x][self.y]
        if current_zone == "water":
            if self.species == "B":
                self.energy -= 0.05
            else:
                self.energy += 0.02
        elif current_zone == "obstacle":
            self.stress += 0.02
        elif current_zone == "cold_zone":
            self.stress += 0.01
        elif current_zone == "hot_zone":
            self.stress += 0.01

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

        neighbors = [c for c in creatures if abs(c.x - self.x) <= 1 and abs(c.y - self.y) <= 1 and c.id != self.id and c.alive]
        if neighbors:
            avg_neighbor_stress = sum(n.stress for n in neighbors) / len(neighbors)
            self.stress += (avg_neighbor_stress - self.stress) * 0.05

        self.stress = min(1.0, max(0.0, self.stress + (random.random() - 0.5) * 0.05))
        self.constricted = self.stress > 0.7
        if random.random() < 0.05:
            self.disinhibited = not self.disinhibited

        self.energy -= 0.06

        if self.energy < 3 and energy_sources:
            remembered_sources = [pos for pos in self.memory if pos in energy_sources]
            if remembered_sources:
                closest = min(remembered_sources, key=lambda e: abs(e[0]-self.x)+abs(e[1]-self.y))
            else:
                closest = min(energy_sources, key=lambda e: abs(e[0]-self.x)+abs(e[1]-self.y))

            dx = np.sign(closest[0] - self.x)
            dy = np.sign(closest[1] - self.y)
            new_x = min(max(self.x + int(dx), 0), GRID_WIDTH - 1)
            new_y = min(max(self.y + int(dy), 0), GRID_HEIGHT - 1)

            if zones[new_x][new_y] != "obstacle" and not any(c.x == new_x and c.y == new_y and c.alive for c in creatures):
                self.x = new_x
                self.y = new_y

            if (self.x, self.y) == closest:
                self.energy = min(MAX_ENERGY, self.energy + 8)
                energy_sources.remove(closest)
                self.memory.add(closest)
        else:
            if not self.constricted:
                for _ in range(5):
                    dx = random.choice([-1, 0, 1])
                    dy = random.choice([-1, 0, 1])
                    new_x = min(max(self.x + dx, 0), GRID_WIDTH - 1)
                    new_y = min(max(self.y + dy, 0), GRID_HEIGHT - 1)
                    if zones[new_x][new_y] != "obstacle" and not any(c.x == new_x and c.y == new_y and c.alive for c in creatures):
                        self.x = new_x
                        self.y = new_y
                        break

        if self.stress < 0.3 and self.energy > 6:
            self.mood = "happy"
        elif self.stress > 0.7:
            self.mood = "angry"
        elif self.stress > 0.4:
            self.mood = "stressed"
        else:
            self.mood = "neutral"

        if self.energy > 10 and self.stress < 0.4:
            empty_neighbors = [(self.x + dx, self.y + dy) for dx in [-1,0,1] for dy in [-1,0,1]
                               if 0 <= self.x+dx < GRID_WIDTH and 0 <= self.y+dy < GRID_HEIGHT]
            empty_neighbors = [pos for pos in empty_neighbors if
                               not any(c.x == pos[0] and c.y == pos[1] and c.alive for c in creatures)
                               and zones[pos[0]][pos[1]] != "obstacle"]
            if empty_neighbors and random.random() < 0.02:
                nx, ny = random.choice(empty_neighbors)
                offspring = Creature(nx, ny, self.species)
                offspring.energy = self.energy / 2
                offspring.stress = self.stress / 2
                self.energy /= 2
                creatures.append(offspring)

        if self.stress > 0.7:
            self.mutation_counter += 1
            if self.mutation_counter > self.mutation_threshold and not self.mutated:
                self.mutated = True
                self.inhibition = max(0, min(1, self.inhibition + random.uniform(-0.1, 0.1)))
                self.habituation_rate = max(0.8, min(1, self.habituation_rate + random.uniform(-0.05, 0.05)))
        else:
            self.mutation_counter = max(0, self.mutation_counter - 2)

        self.energy_history.append(self.energy)
        self.stress_history.append(self.stress)


def draw_grid(creatures, energy_sources, weather, season, day_night, zones):
    ground_color = SEASON_GROUND_COLORS.get(season, "#799548")
    img = Image.new("RGB", (GRID_WIDTH * CELL_SIZE, GRID_HEIGHT * CELL_SIZE), ground_color)
    draw = ImageDraw.Draw(img)

    for x in range(GRID_WIDTH + 1):
        draw.line([(x * CELL_SIZE, 0), (x * CELL_SIZE, GRID_HEIGHT * CELL_SIZE)], fill=(50, 50, 50))
    for y in range(GRID_HEIGHT + 1):
        draw.line([(0, y * CELL_SIZE), (GRID_WIDTH * CELL_SIZE, y * CELL_SIZE)], fill=(50, 50, 50))

    for x in range(GRID_WIDTH):
        for y in range(GRID_HEIGHT):
            zone = zones[x][y]
            top_left = (x * CELL_SIZE, y * CELL_SIZE)
            bottom_right = ((x + 1) * CELL_SIZE, (y + 1) * CELL_SIZE)

            if zone == "water":
                draw.rectangle([top_left, bottom_right], fill=(64, 164, 223))
            elif zone == "obstacle":
                draw.rectangle([top_left, bottom_right], fill=(80, 80, 80))
            elif zone == "cold_zone":
                draw.rectangle([top_left, bottom_right], fill=(173, 216, 230))
            elif zone == "hot_zone":
                draw.rectangle([top_left, bottom_right], fill=(255, 160, 122))

    for ex, ey in energy_sources:
        top_left = (ex * CELL_SIZE + 4, ey * CELL_SIZE + 4)
        bottom_right = ((ex + 1) * CELL_SIZE - 4, (ey + 1) * CELL_SIZE - 4)
        draw.rectangle([top_left, bottom_right], fill=(255, 215, 0))

    for creature in creatures:
        if not creature.alive:
            continue
        cx = creature.x * CELL_SIZE + CELL_SIZE // 2
        cy = creature.y * CELL_SIZE + CELL_SIZE // 2

        base = SPECIES_DATA[creature.species]["base_color"]
        mood_color = SPECIES_DATA[creature.species]["mood_colors"].get(creature.mood, base)

        color = tuple(
            int((mood_color[i] + base[i]) / 2) if not creature.disinhibited else 255
            for i in range(3)
        )

        radius = CELL_SIZE // 3
        if creature.constricted:
            radius = CELL_SIZE // 5

        draw.ellipse([(cx - radius, cy - radius), (cx + radius, cy + radius)], fill=color, outline=(0,0,0))

        if creature.mutated:
            draw.line([(cx - radius, cy), (cx + radius, cy)], fill=(255, 0, 255), width=2)
            draw.line([(cx, cy - radius), (cx, cy + radius)], fill=(255, 0, 255), width=2)

        mood_emoji = MOOD_DATA[creature.mood]["emoji"]
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", CELL_SIZE - 4)
        except:
            font = ImageFont.load_default()
        w, h = draw.textsize(mood_emoji, font=font)
        draw.text((cx - w // 2, cy - h // 2), mood_emoji, fill=(0, 0, 0), font=font)

    if day_night == "night":
        overlay = Image.new("RGBA", img.size, (0, 0, 30, 120))
        img = Image.alpha_composite(img.convert("RGBA"), overlay)

    return img

def create_zones():
    zones = [["normal" for _ in range(GRID_HEIGHT)] for _ in range(GRID_WIDTH)]
    for _ in range(50):
        x = random.randint(0, GRID_WIDTH - 1)
        y = random.randint(0, GRID_HEIGHT - 1)
        zones[x][y] = random.choice(["water", "obstacle", "cold_zone", "hot_zone"])
    return zones

def main():
    st.title("Creature Simulation")

    if "sim_params" not in st.session_state:
        st.session_state.sim_params = {
            "num_creatures": 40,
            "weather": "sunny",
            "season": "spring",
            "day_night": "day",
            "show_trails": True,
            "mutate_creatures": True,
            "zones": create_zones(),
        }

    params = st.session_state.sim_params

    col1, col2 = st.columns([1, 3])

    with col1:
        params["num_creatures"] = st.slider("Number of Creatures", 10, 100, params["num_creatures"])
        params["weather"] = st.selectbox("Weather", WEATHER_OPTIONS, index=WEATHER_OPTIONS.index(params["weather"]))
        params["season"] = st.selectbox("Season", SEASON_OPTIONS, index=SEASON_OPTIONS.index(params["season"]))
        params["day_night"] = st.selectbox("Day/Night", DAY_NIGHT_OPTIONS, index=DAY_NIGHT_OPTIONS.index(params["day_night"]))
        params["show_trails"] = st.checkbox("Show Trails", params["show_trails"])
        params["mutate_creatures"] = st.checkbox("Allow Mutation", params["mutate_creatures"])

        if st.button("Reset Zones"):
            params["zones"] = create_zones()

    if "creatures" not in st.session_state:
        creatures = []
        for _ in range(params["num_creatures"]):
            x = random.randint(0, GRID_WIDTH - 1)
            y = random.randint(0, GRID_HEIGHT - 1)
            species = random.choice(["A", "B"])
            creatures.append(Creature(x, y, species))
        st.session_state.creatures = creatures

    if len(st.session_state.creatures) != params["num_creatures"]:
        current = st.session_state.creatures
        if len(current) < params["num_creatures"]:
            for _ in range(params["num_creatures"] - len(current)):
                x = random.randint(0, GRID_WIDTH - 1)
                y = random.randint(0, GRID_HEIGHT - 1)
                species = random.choice(["A", "B"])
                current.append(Creature(x, y, species))
        else:
            st.session_state.creatures = current[:params["num_creatures"]]

    energy_sources = set()
    for _ in range(15):
        ex = random.randint(0, GRID_WIDTH - 1)
        ey = random.randint(0, GRID_HEIGHT - 1)
        if params["zones"][ex][ey] != "obstacle":
            energy_sources.add((ex, ey))

    for creature in st.session_state.creatures:
        creature.update(st.session_state.creatures, energy_sources, params["weather"], params["season"], params["day_night"], params["zones"])

    img = draw_grid(st.session_state.creatures, energy_sources, params["weather"], params["season"], params["day_night"], params["zones"])

    st.image(img, use_column_width=True)

    alive_count = sum(1 for c in st.session_state.creatures if c.alive)
    st.write(f"Creatures alive: {alive_count}")

if __name__ == "__main__":
    main()
