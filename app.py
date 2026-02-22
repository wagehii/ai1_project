# PART 1: IMPORTS, CONSTANTS, AND ALGORITHMS
import streamlit as st
import random
import time
import heapq
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional, Literal

# --- CONFIGURATION & CONSTANTS ---
GRID_SIZE = 12
FOG_RADIUS = 2
PHANTOM_SENSE_RADIUS = 3
WALL_CHANGE_INTERVAL = 10
MOVES_FOR_BONUS = 40

# Visual Assets
ICON_PLAYER = "👤"
ICON_ROBOT = "🤖"
ICON_PHANTOM = "👻"
ICON_TREASURE = "💎"
ICON_WALL = "🧱"
ICON_EXIT = "🚪"
ICON_EMPTY = "⬜"
ICON_FOG = "☁️"

# CSS Styling
COLOR_FOG = "#1e1e1e"
COLOR_EMPTY = "#f0f2f6"
COLOR_WALL = "#4a4a4a"

# --- DATA STRUCTURES ---
@dataclass(order=True)
class Node:
    priority: float
    x: int = field(compare=False)
    y: int = field(compare=False)

@dataclass
class Position:
    x: int
    y: int

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y
    
    def distance(self, other):
        return abs(self.x - other.x) + abs(self.y - other.y)
    
    def to_tuple(self):
        return (self.x, self.y)

@dataclass
class GameMoveLog:
    turn: int
    player_pos: Tuple[int, int]
    phantom_pos: Tuple[int, int]
    distance_to_treasure: int
    distance_to_phantom: int
    utility: float
    risk_level: float
    timestamp: float

# --- ALGORITHMS ---
class AStarPathfinder:
    """
    Risk-Aware A* Algorithm.
    Calculates path cost based on distance + proximity to threats.
    """
    @staticmethod
    def get_path(start: Position, goal: Position, walls: List[Position], 
                 grid_size: int, danger_zones: Dict[Tuple[int, int], float] = None) -> List[Position]:
        
        frontier = []
        heapq.heappush(frontier, Node(0, start.x, start.y))
        came_from = {}
        cost_so_far = {}
        came_from[start.to_tuple()] = None
        cost_so_far[start.to_tuple()] = 0
        
        wall_set = {w.to_tuple() for w in walls}
        danger_zones = danger_zones if danger_zones else {}

        while frontier:
            current_node = heapq.heappop(frontier)
            current = Position(current_node.x, current_node.y)

            if current == goal:
                break

            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                next_x, next_y = current.x + dx, current.y + dy
                
                if 0 <= next_x < grid_size and 0 <= next_y < grid_size:
                    if (next_x, next_y) in wall_set:
                        continue
                    
                    # Cost Function: 1 (base) + Risk Penalty
                    risk_penalty = danger_zones.get((next_x, next_y), 0)
                    new_cost = cost_so_far[current.to_tuple()] + 1 + risk_penalty
                    
                    if (next_x, next_y) not in cost_so_far or new_cost < cost_so_far[(next_x, next_y)]:
                        cost_so_far[(next_x, next_y)] = new_cost
                        priority = new_cost + AStarPathfinder.heuristic(Position(next_x, next_y), goal)
                        heapq.heappush(frontier, Node(priority, next_x, next_y))
                        came_from[(next_x, next_y)] = current

        # Path Reconstruction
        path = []
        curr_tuple = goal.to_tuple()
        if curr_tuple not in came_from:
            return [] # No path found
            
        while curr_tuple != start.to_tuple():
            path.append(Position(curr_tuple[0], curr_tuple[1]))
            curr_pos = came_from[curr_tuple]
            curr_tuple = curr_pos.to_tuple()
        path.reverse()
        return path

    @staticmethod
    def heuristic(a: Position, b: Position) -> float:
        return abs(a.x - b.x) + abs(a.y - b.y)

class MazeGenerator:
    """
    Handles dynamic environment generation and connectivity verification.
    """
    @staticmethod
    def generate_walls(grid_size: int, density: float, 
                      safe_positions: List[Position]) -> List[Position]:
        walls = []
        safe_set = {p.to_tuple() for p in safe_positions}
        
        for x in range(grid_size):
            for y in range(grid_size):
                if (x, y) not in safe_set:
                    if random.random() < density:
                        walls.append(Position(x, y))
        return walls

    @staticmethod
    def is_solvable(start: Position, goal: Position, walls: List[Position], grid_size: int) -> bool:
        queue = [start]
        visited = {start.to_tuple()}
        wall_set = {w.to_tuple() for w in walls}
        
        while queue:
            curr = queue.pop(0)
            if curr == goal:
                return True
            
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = curr.x + dx, curr.y + dy
                if 0 <= nx < grid_size and 0 <= ny < grid_size:
                    if (nx, ny) not in wall_set and (nx, ny) not in visited:
                        visited.add((nx, ny))
                        queue.append(Position(nx, ny))
        return False
    
# PART 2: AGENTS AND ANALYTICS

class AdventurerAgent:
    """
    The Protagonist.
    Modes:
    - 'AI': Uses A* with risk utility.
    - 'Heuristic': Simulates a decent human player (Greedy Best-First).
    - 'Manual': Controlled by UI.
    """
    def __init__(self, start_pos: Position, mode: str = "AI"):
        self.pos = start_pos
        self.mode = mode
        self.has_treasure = False
        self.utility_score = 0
        self.moves_taken = 0
        self.freeze_charges = 1
        
    def decide_move(self, state, manual_move: Optional[Position] = None) -> Optional[Position]:
        target = state.exit_pos if self.has_treasure else state.treasure_pos
        
        # 1. Manual Mode
        if self.mode == "Manual":
            return manual_move

        # 2. Heuristic Mode (Simulated Human)
        if self.mode == "Heuristic":
            # Greedy approach: Move to neighbor closest to target, avoiding immediate walls
            best_move = self.pos
            min_dist = float('inf')
            valid_moves = []
            
            for dx, dy in [(0,1), (0,-1), (1,0), (-1,0)]:
                nx, ny = self.pos.x + dx, self.pos.y + dy
                if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
                    pos = Position(nx, ny)
                    if pos not in state.walls:
                        valid_moves.append(pos)
                        d = pos.distance(target)
                        # Add slight randomness to simulate human imperfection
                        d += random.uniform(0, 0.5) 
                        if d < min_dist:
                            min_dist = d
                            best_move = pos
            # If trapped, stay still
            return best_move if valid_moves else self.pos

        # 3. AI Mode (Utility-Based A*)
        danger_map = {}
        if self.pos.distance(state.phantom.pos) <= PHANTOM_SENSE_RADIUS:
            px, py = state.phantom.pos.x, state.phantom.pos.y
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    danger_map[(px+dx, py+dy)] = 15.0 # High risk penalty
        
        path = AStarPathfinder.get_path(
            self.pos, target, state.walls, GRID_SIZE, danger_map
        )
        
        if path:
            return path[0]
        
        # Fallback: Maximize distance from phantom
        return self._get_fallback_move(state)

    def _get_fallback_move(self, state) -> Position:
        best_move = self.pos
        max_dist = -1
        for dx, dy in [(0,1), (0,-1), (1,0), (-1,0)]:
            nx, ny = self.pos.x + dx, self.pos.y + dy
            if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
                p = Position(nx, ny)
                if p not in state.walls:
                    d = p.distance(state.phantom.pos)
                    if d > max_dist:
                        max_dist = d
                        best_move = p
        return best_move

class PhantomAgent:
    """Model-Based Interceptor"""
    def __init__(self, start_pos: Position):
        self.pos = start_pos
        self.is_frozen = False
        self.freeze_timer = 0
        
    def decide_move(self, state) -> Position:
        if self.is_frozen:
            self.freeze_timer -= 1
            if self.freeze_timer <= 0: self.is_frozen = False
            return self.pos
            
        target = state.adventurer.pos
        # Intercept logic: Aim for a point ahead of player if far away
        dist = self.pos.distance(target)
        if dist > 4:
            goal_obj = state.exit_pos if state.adventurer.has_treasure else state.treasure_pos
            mid_x = (target.x + goal_obj.x) // 2
            mid_y = (target.y + goal_obj.y) // 2
            target = Position(mid_x, mid_y)
            
        path = AStarPathfinder.get_path(self.pos, target, state.walls, GRID_SIZE)
        return path[0] if path else self.pos

class AnalyticsEngine:
    @staticmethod
    def log_move(state, logs: List[GameMoveLog]):
        adv = state.adventurer
        p_dist = adv.pos.distance(state.phantom.pos)
        t_dist = adv.pos.distance(state.treasure_pos)
        
        # Calculate Risk Score (Inverse of distance to phantom)
        risk = 10.0 / (p_dist + 0.1) if p_dist < 4 else 0
        
        logs.append(GameMoveLog(
            turn=state.turn_count,
            player_pos=adv.pos.to_tuple(),
            phantom_pos=state.phantom.pos.to_tuple(),
            distance_to_treasure=t_dist,
            distance_to_phantom=p_dist,
            utility=adv.utility_score,
            risk_level=risk,
            timestamp=time.time()
        ))

    @staticmethod
    def calculate_efficiency(logs: List[GameMoveLog], start: Position, treasure: Position, exit: Position):
        if not logs: return 0
        actual_steps = len(logs)
        # Optimal = Start->Treasure + Treasure->Exit
        optimal = start.distance(treasure) + treasure.distance(exit)
        return round((optimal / actual_steps) * 100, 2) if actual_steps > 0 else 0

class GameState:
    def __init__(self, mode="AI"):
        self.mode = mode
        self.turn_count = 0
        self.game_over = False
        self.win = False
        self.logs: List[GameMoveLog] = []
        
        # Init Entities
        self.adventurer = AdventurerAgent(Position(0, 0), mode=mode)
        self.phantom = PhantomAgent(Position(GRID_SIZE-1, GRID_SIZE-1))
        self.treasure_pos = Position(random.randint(4, 8), random.randint(4, 8))
        self.exit_pos = Position(GRID_SIZE-1, GRID_SIZE-1)
        self.walls = []
        self._regenerate_walls(force=True)

    def _regenerate_walls(self, force=False):
        safe = [self.adventurer.pos, self.phantom.pos, self.treasure_pos, self.exit_pos]
        for _ in range(10):
            walls = MazeGenerator.generate_walls(GRID_SIZE, 0.25, safe)
            # Connectivity Check
            if (MazeGenerator.is_solvable(self.adventurer.pos, self.treasure_pos, walls, GRID_SIZE) and
                MazeGenerator.is_solvable(self.treasure_pos, self.exit_pos, walls, GRID_SIZE)):
                self.walls = walls
                return
        if force: self.walls = [] # Failsafe

    def step(self, manual_move: Optional[Position] = None):
        if self.game_over: return
        
        # 1. Log State Before Action
        AnalyticsEngine.log_move(self, self.logs)
        self.turn_count += 1
        
        # 2. Dynamic Walls
        if self.turn_count % WALL_CHANGE_INTERVAL == 0:
            self._regenerate_walls()
            
        # 3. Adventurer Move
        prev_dist = self.adventurer.pos.distance(self.treasure_pos)
        new_pos = self.adventurer.decide_move(self, manual_move)
        if new_pos:
            self.adventurer.pos = new_pos
            self.adventurer.moves_taken += 1
            
        # 4. Utility Update
        target = self.exit_pos if self.adventurer.has_treasure else self.treasure_pos
        new_dist = self.adventurer.pos.distance(target)
        self.adventurer.utility_score += 10 if new_dist < prev_dist else -5
        
        # 5. Phantom Move
        self.phantom.pos = self.phantom.decide_move(self)
        
        # 6. Win/Loss Check
        if self.adventurer.pos == self.phantom.pos:
            self.game_over = True; self.win = False
            self.adventurer.utility_score -= 50
        elif self.adventurer.pos == self.treasure_pos:
            self.adventurer.has_treasure = True
            self.adventurer.utility_score += 20
        elif self.adventurer.pos == self.exit_pos and self.adventurer.has_treasure:
            self.game_over = True; self.win = True
            self.adventurer.utility_score += 100

# PART 3: UI, BENCHMARKING, AND MAIN EXECUTION

def run_simulation(mode: str) -> dict:
    """Runs a complete game in logic-only mode (fast) for benchmarking."""
    sim_state = GameState(mode=mode)
    max_turns = 100
    
    while not sim_state.game_over and sim_state.turn_count < max_turns:
        sim_state.step()
    
    efficiency = AnalyticsEngine.calculate_efficiency(
        sim_state.logs, Position(0,0), sim_state.treasure_pos, sim_state.exit_pos
    )
    
    return {
        "mode": mode,
        "win": sim_state.win,
        "score": sim_state.adventurer.utility_score,
        "moves": sim_state.adventurer.moves_taken,
        "efficiency": efficiency,
        "logs": sim_state.logs
    }

def render_analytics(logs: List[GameMoveLog], title="Analytics"):
    if not logs: return
    df = pd.DataFrame([vars(l) for l in logs])
    
    st.subheader(f"📊 {title}")
    
    # 1. Line Chart: Utility & Risk
    st.caption("Utility vs Risk Over Time")
    chart_data = df[['turn', 'utility', 'risk_level']].set_index('turn')
    # Normalize risk for visualization
    chart_data['risk_level'] = chart_data['risk_level'] * 10 
    st.line_chart(chart_data)
    
    # 2. Heatmap Logic
    st.caption("🔥 Risk Heatmap (Phantom Presence)")
    heatmap_grid = np.zeros((GRID_SIZE, GRID_SIZE))
    for log in logs:
        px, py = log.phantom_pos
        heatmap_grid[py][px] += 1
        
    fig, ax = plt.subplots(figsize=(5,5))
    sns.heatmap(heatmap_grid, cmap="Reds", alpha=0.6, cbar=False, linewidths=0.5, linecolor='black')
    ax.invert_yaxis()
    plt.axis('off')
    st.pyplot(fig)

def render_grid(state: GameState):
    """Renders the game board."""
    html = '<div style="display: grid; grid-template-columns: repeat(12, 1fr); gap: 2px; width: 100%; max-width: 450px; margin: auto;">'
    
    for y in range(GRID_SIZE):
        for x in range(GRID_SIZE):
            pos = Position(x, y)
            dist_p = pos.distance(state.adventurer.pos)
            
            # Fog Logic
            visible = dist_p <= FOG_RADIUS or state.game_over
            
            bg = COLOR_EMPTY
            content = ""
            
            if visible:
                if pos in state.walls:
                    bg = COLOR_WALL; content = ICON_WALL
                elif pos == state.adventurer.pos:
                    content = ICON_ROBOT if state.mode == "AI" else ICON_PLAYER
                elif pos == state.phantom.pos:
                    content = ICON_PHANTOM
                elif pos == state.treasure_pos and not state.adventurer.has_treasure:
                    content = ICON_TREASURE
                elif pos == state.exit_pos:
                    content = ICON_EXIT
            else:
                bg = COLOR_FOG; content = ICON_FOG
                
            style = f"background-color: {bg}; height: 30px; display: flex; align-items: center; justify-content: center; font-size: 18px; border-radius: 4px;"
            html += f'<div style="{style}">{content}</div>'
    
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

def main():
    st.set_page_config(page_title="The Cursed Labyrinth", page_icon="👻", layout="wide")
    
    if 'game_state' not in st.session_state:
        st.session_state.game_state = GameState(mode="Manual")
    
    if 'benchmark_results' not in st.session_state:
        st.session_state.benchmark_results = None

    state = st.session_state.game_state

    # --- SIDEBAR ---
    with st.sidebar:
        st.title("👻 Control Panel")
        mode = st.radio("Game Mode", ["Manual Play", "AI Auto-Play"])
        
        if mode == "AI Auto-Play" and state.mode != "AI":
            st.session_state.game_state = GameState(mode="AI")
            st.rerun()
        elif mode == "Manual Play" and state.mode != "Manual":
            st.session_state.game_state = GameState(mode="Manual")
            st.rerun()
            
        st.metric("Score", state.adventurer.utility_score)
        st.metric("Moves", state.adventurer.moves_taken)
        
        if st.button("🔄 Reset Game"):
            st.session_state.game_state = GameState(mode=state.mode)
            st.session_state.benchmark_results = None
            st.rerun()
            
        st.markdown("---")
        st.subheader("🧪 Benchmark Lab")
        if st.button("🚀 Run AI vs Human Sim"):
            with st.spinner("Simulating matches..."):
                ai_res = run_simulation("AI")
                human_res = run_simulation("Heuristic") # Simulates human
                st.session_state.benchmark_results = (ai_res, human_res)

    # --- MAIN LAYOUT ---
    tab1, tab2 = st.tabs(["🎮 Game Arena", "📈 Performance Analytics"])

    with tab1:
        col1, col2 = st.columns([2, 1])
        with col1:
            render_grid(state)
        
        with col2:
            st.write(f"**Status:** {'Game Over' if state.game_over else 'Active'}")
            if state.game_over:
                if state.win: st.success("Victory!")
                else: st.error("Captured!")
            
            # Manual Controls
            if state.mode == "Manual" and not state.game_over:
                cols = st.columns(3)
                move = None
                if cols[1].button("⬆️"): move = Position(state.adventurer.pos.x, state.adventurer.pos.y-1)
                cols = st.columns(3)
                if cols[0].button("⬅️"): move = Position(state.adventurer.pos.x-1, state.adventurer.pos.y)
                if cols[2].button("➡️"): move = Position(state.adventurer.pos.x+1, state.adventurer.pos.y)
                cols = st.columns(3)
                if cols[1].button("⬇️"): move = Position(state.adventurer.pos.x, state.adventurer.pos.y+1)
                
                if move:
                    # Validate bounds/walls before stepping
                    if 0 <= move.x < GRID_SIZE and 0 <= move.y < GRID_SIZE and move not in state.walls:
                        state.step(manual_move=move)
                        st.rerun()

            # AI Auto-Step
            if state.mode == "AI" and not state.game_over:
                if st.button("Step AI"):
                    state.step()
                    st.rerun()

    with tab2:
        # Benchmark Results
        res = st.session_state.benchmark_results
        if res:
            ai, human = res
            st.markdown("### 🏆 Benchmark Report")
            
            # Metrics Comparison
            col_a, col_b, col_c = st.columns(3)
            diff_score = ai['score'] - human['score']
            winner = "AI Agent" if diff_score > 0 else "Human Sim"
            
            col_a.metric("Winner", winner)
            col_b.metric("AI Efficiency", f"{ai['efficiency']}%", delta=f"{ai['efficiency'] - human['efficiency']:.1f}%")
            col_c.metric("Human Efficiency", f"{human['efficiency']}%")
            
            # Visual Comparison
            chart_data = pd.DataFrame({
                "Metric": ["Score", "Moves", "Efficiency"],
                "AI": [ai['score'], ai['moves'], ai['efficiency']],
                "Human": [human['score'], human['moves'], human['efficiency']]
            })
            st.bar_chart(chart_data.set_index("Metric"))
            
            st.markdown("---")
            c1, c2 = st.columns(2)
            with c1: render_analytics(ai['logs'], "AI Analysis")
            with c2: render_analytics(human['logs'], "Human Analysis")
        else:
            st.info("Run the Benchmark from the sidebar to see comparative analytics.")

        # Live Game Analytics
        if state.logs:
            st.markdown("---")
            st.subheader("📍 Current Session Analytics")
            render_analytics(state.logs, "Live Session")

if __name__ == "__main__":
    main()