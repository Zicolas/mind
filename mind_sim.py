# Constants
GRID_WIDTH = 30
GRID_HEIGHT = 30
CELL_SIZE = 20
MAX_ENERGY = 15.0  # increased max energy
MAX_HISTORY = 50  # For stats tracking history length

# ... rest of your code unchanged ...

class Creature:
    _id_counter = 0

    def __init__(self, x, y, species):
        self.id = Creature._id_counter
        Creature._id_counter += 1

        self.x = x
        self.y = y
        self.species = species
        self.energy = random.uniform(6, 10)  # increased initial energy range
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

        self.energy -= 0.06  # slower energy depletion

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
                self.energy = min(MAX_ENERGY, self.energy + 8)  # bigger recharge
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
            self.energy = random.uniform(6, 10)  # reset with higher initial energy
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
