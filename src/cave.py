#!/usr/bin/python
import sys
import copy
import re

CAVE_EMPTY = ' '
CAVE_DIRT = '.'
CAVE_WALL = '#'
CAVE_ROCK = '*'
CAVE_LAMBDA = '\\'
CAVE_ROBOT = 'R'
CAVE_CLOSED_LIFT = 'L'
CAVE_OPEN_LIFT = 'O'
CAVE_BEARD = 'W'
CAVE_RAZOR = '!'

CAVE_TRAMPOLINE_CHARS = 'ABCDEFGHI'
CAVE_TARGET_CHARS = '123456789'

CAVE_CHARS = set([CAVE_EMPTY, CAVE_DIRT, CAVE_WALL, CAVE_ROCK, CAVE_LAMBDA, CAVE_ROBOT, CAVE_CLOSED_LIFT, CAVE_OPEN_LIFT, CAVE_BEARD, CAVE_RAZOR])
CAVE_CHARS.update(CAVE_TRAMPOLINE_CHARS)
CAVE_CHARS.update(CAVE_TARGET_CHARS)

MOVE_LEFT = 'L'
MOVE_RIGHT = 'R'
MOVE_UP = 'U'
MOVE_DOWN = 'D'
MOVE_SHAVE = 'S'
MOVE_WAIT = 'W'
MOVE_ABORT = 'A'

DPOS = {
    MOVE_LEFT: (-1, 0),
    MOVE_RIGHT: (1, 0),
    MOVE_UP: (0, 1),
    MOVE_DOWN: (0, -1),
    MOVE_SHAVE: (0, 0),
    MOVE_WAIT: (0, 0),
    MOVE_ABORT: (0, 0)
}

SCORE_MOVE = -1
SCORE_LAMBDA_COLLECT = 25
SCORE_LAMBDA_ABORT = 25
SCORE_LAMBDA_LIFT = 50

END_STATE_WIN = 'Win'
END_STATE_LOSE = 'Lose'
END_STATE_ABORT = 'Abort'

DEFAULT_WATER_LEVEL = -1
DEFAULT_FLOOD_RATE = 0
DEFAULT_WATER_RESISTANCE = 10
DEFAULT_BEARD_GROWTH_RATE = 25

RE_WATER_LEVEL = re.compile(r'Water (\d+)')
RE_FLOOD_RATE = re.compile(r'Flooding (\d+)')
RE_WATER_RESISTANCE = re.compile(r'Waterproof (\d+)')
RE_TRAMPOLINE = re.compile(r'Trampoline ([A-I]) targets (\d)')
RE_BEARD_GROWTH = re.compile(r'Growth (\d+)')
RE_RAZORS = re.compile(r'Razors (\d+)')

def is_trampoline(content):
    return content in CAVE_TRAMPOLINE_CHARS

def is_target(content):
    return content in CAVE_TARGET_CHARS

def surrounding_squares(x, y):
    for ys in range(y - 1, y + 2):
        for xs in range(x - 1, x + 2):
            if xs != x or ys != y:
                yield (xs, ys)

class RobotDestroyed(Exception):
    pass

class Cave(object):
    def __init__(self):
        # Public attributes
        self.score = 0
        self.end_state = None
        self.water_resistance = DEFAULT_WATER_RESISTANCE
        self.water_level = DEFAULT_WATER_LEVEL
        self.flood_rate = DEFAULT_FLOOD_RATE
        # Counter for next increase of water level.
        self.flood_steps = 0
        # Number of moves under water.
        self.water_steps = 0
        # Indicates whether at least one rock moved during the last update.
        self.rock_movement = False
        self._robot_pos = None
        self._lift_pos = None
        self._lift_open = False
        self._lambda_count = 0
        self._lambda_collected = 0
        self.lambdas = set()
        # Beard parameters.
        self.beard_growth_rate = DEFAULT_BEARD_GROWTH_RATE
        self.beard_growth = self.beard_growth_rate - 1
        # Number of razors carried by the robot.
        self.razors_carried = 0

        # Private attributes
        self._cave = None

    def __str__(self):
        return '\n'.join([''.join(row) for row in reversed(self._cave)])

    def state_str(self):
        s = []
        s.append('Robot position:    %s' % str(self._robot_pos))
        s.append('Lift position:     %s' % str(self._lift_pos))
        s.append('Lift state:        %s' % ('Open' if self._lift_open else 'Closed'))
        s.append('Number of lambdas: %d' % self._lambda_count)
        s.append('Water resistance:  %d' % self.water_resistance)
        s.append('Water level:       %d' % self.water_level)
        s.append('Flood rate:        %d' % self.flood_rate)
        s.append('Beard growth rate: %d' % self.beard_growth_rate)
        s.append('Initial razors:    %d' % self.razors_carried)
        return '\n'.join(s)

    @property
    def size(self):
        return (len(self._cave[0]), len(self._cave))

    def at(self, x, y):
        try:
            if x < 0 or y < 0:
                raise IndexError()
            return self._cave[y][x]
        except IndexError:
            return CAVE_WALL
            
    def set(self, x, y, content):
        try:
            if x < 0 or y < 0:
                raise IndexError()
            self._cave[y][x] = content
        except IndexError:
            pass
        
    def set_robot(self, x, y):
        self._robot_pos = (x, y)
        self.set(x, y, CAVE_ROBOT)
        
    def set_rock(self, x, y):
        self.set(x, y, CAVE_ROCK)
        self.rock_movement = True
        if self.at(x, y - 1) == CAVE_ROBOT:
            raise RobotDestroyed()
        
    @property
    def completed(self):
        return self.end_state is not None
    
    @property
    def is_drowning(self):
        return self.water_steps >= self.water_resistance

    def analyze(self):
        self._lambda_count = 0
        for row_ix, row in enumerate(self._cave):
            for col_ix, col in enumerate(row):
                if col == CAVE_LAMBDA:
                    self.lambdas.add((col_ix, row_ix))
            self._lambda_count += row.count(CAVE_LAMBDA)
            try:
                robot_col = row.index(CAVE_ROBOT)
            except ValueError:
                pass
            else:
                self._robot_pos = (robot_col, row_ix)
            try:
                lift_col = row.index(CAVE_CLOSED_LIFT)
            except ValueError:
                pass
            else:
                self._lift_pos = (lift_col, row_ix)
                self._lift_open = False
            try:
                lift_col = row.index(CAVE_OPEN_LIFT)
            except ValueError:
                pass
            else:
                self._lift_pos = (lift_col, row_ix)
                self._lift_open = True

    def load_file(self, f):
        cave_lines = []
        for line in f.readlines():
            line = line.strip('\n\r')
            if self.is_cave_str(line):
                cave_lines.append(line)
            else:
                m = RE_WATER_RESISTANCE.match(line)
                if m:
                    self.water_resistance = int(m.group(1))
                    continue
                m = RE_WATER_LEVEL.match(line)
                if m:
                    self.water_level = int(m.group(1)) - 1
                    continue
                m = RE_FLOOD_RATE.match(line)
                if m:
                    self.flood_rate = int(m.group(1))
                    continue
                m = RE_TRAMPOLINE.match(line)
                if m:
                    #self.flood_rate = int(m.group(1))
                    continue
                m = RE_BEARD_GROWTH.match(line)
                if m:
                    self.beard_growth_rate = int(m.group(1))
                    self.beard_growth = self.beard_growth_rate - 1
                    continue
                m = RE_RAZORS.match(line)
                if m:
                    self.razors_carried = int(m.group(1))
                    continue
        cave_width = max([len(line) for line in cave_lines])
        self._cave = [list(line.ljust(cave_width)) for line in reversed(cave_lines)]
        self.analyze()
        
    def is_cave_str(self, s):
        return len(s) > 0 and frozenset(s) <= CAVE_CHARS

    def clone(self):
        return copy.deepcopy(self)
        
    def get_move_state(self):
        """ Save the state before robot movement. """
        robot_x, robot_y = self._robot_pos
        saved_positions = [(x, robot_y) for x in range(robot_x - 2, robot_x + 3)]
        saved_positions.extend([(robot_x, robot_y - 1), (robot_x, robot_y + 1)])
        squares = dict([(pos, self.at(*pos)) for pos in saved_positions])
        return (squares, self.score, self.end_state, self.rock_movement, self._robot_pos, self._lift_open, self._lambda_count, self._lambda_collected, self.razors_carried)

    def restore_move_state(self, state):
        """ Restore the state as it was before robot movement. """
        squares, score, end_state, rock_movement, robot_pos, lift_open, lambda_count, lambda_collected, razors_carried = state
        self.score = score
        self.end_state = end_state
        self.rock_movement = rock_movement
        self._robot_pos = robot_pos
        self._lift_open = lift_open
        self._lambda_count = lambda_count
        self._lambda_collected = lambda_collected
        self.razors_carried = razors_carried
        for pos, content in squares.iteritems():
            self.set(pos[0], pos[1], content)

    def move(self, move):
        if self.completed:
            return self
        if move == MOVE_ABORT:
            next = self.clone()
            next.end_state = END_STATE_ABORT
            next.score += self._lambda_collected * SCORE_LAMBDA_ABORT
            return next
        state = self.get_move_state()
        self.score += SCORE_MOVE
        dx, dy = DPOS[move]
        x, y = self._robot_pos
        new_x = x + dx
        new_y = y + dy
        target_content = self.at(new_x, new_y)
        if target_content == CAVE_OPEN_LIFT:
            next = self.clone()
            next.set_robot(new_x, new_y)
            next.set(x, y, CAVE_EMPTY)
            next.end_state = END_STATE_WIN
            next.score += self._lambda_collected * SCORE_LAMBDA_LIFT
            return next
        self.rock_movement = False
        if target_content in (CAVE_EMPTY, CAVE_DIRT):
            self.set_robot(new_x, new_y)
            self.set(x, y, CAVE_EMPTY)
        elif target_content == CAVE_LAMBDA:
            self.set_robot(new_x, new_y)
            self.set(x, y, CAVE_EMPTY)
            self._lambda_collected += 1
            self._lambda_count -= 1
            self.lambdas.remove((new_x, new_y))
            if self._lambda_count == 0:
                self._lift_open = True
            self.score += SCORE_LAMBDA_COLLECT
        elif target_content == CAVE_RAZOR:
            self.set_robot(new_x, new_y)
            self.set(x, y, CAVE_EMPTY)
            self.razors_carried += 1
        elif target_content == CAVE_ROCK and dy == 0:
            if self.at(x + 2 * dx, y) == CAVE_EMPTY:
                self.set_robot(new_x, new_y)
                self.set(x, y, CAVE_EMPTY)
                self.set_rock(x + 2 * dx, y)
        if move == MOVE_SHAVE and self.razors_carried > 0:
            self.razors_carried -= 1
            for x, y in surrounding_squares(new_x, new_y):
                if self.at(x, y) == CAVE_BEARD:
                    self.set(x, y, CAVE_EMPTY)
        assert self.at(*self._robot_pos) == CAVE_ROBOT
        next = self.update()
        self.restore_move_state(state)
        return next

    def update(self):
        next = self.clone()
        beard_growth = False
        if next.beard_growth == 0:
            beard_growth = True
            next.beard_growth = self.beard_growth_rate - 1
        else:
            next.beard_growth -= 1
        try:
            next.update_water()
            size_x, size_y = self.size
            for y in range(size_y):
                for x in range(size_x):
                    if self.at(x, y) == CAVE_ROCK and self.at(x, y - 1) == CAVE_EMPTY:
                        next.set(x, y, CAVE_EMPTY)
                        next.set_rock(x, y - 1)
                    elif self.at(x, y) == CAVE_ROCK and self.at(x, y - 1) == CAVE_ROCK and self.at(x + 1, y) == CAVE_EMPTY and self.at(x + 1, y - 1) == CAVE_EMPTY:
                        next.set(x, y, CAVE_EMPTY)
                        next.set_rock(x + 1, y - 1)
                    elif self.at(x, y) == CAVE_ROCK and self.at(x, y - 1) == CAVE_ROCK and self.at(x - 1, y) == CAVE_EMPTY and self.at(x - 1, y - 1) == CAVE_EMPTY:
                        next.set(x, y, CAVE_EMPTY)
                        next.set_rock(x - 1, y - 1)
                    elif self.at(x, y) == CAVE_ROCK and self.at(x, y - 1) == CAVE_LAMBDA and self.at(x + 1, y) == CAVE_EMPTY and self.at(x + 1, y - 1) == CAVE_EMPTY:
                        next.set(x, y, CAVE_EMPTY)
                        next.set_rock(x + 1, y - 1)
                    elif self.at(x, y) == CAVE_CLOSED_LIFT and self._lift_open:
                        next.set(x, y, CAVE_OPEN_LIFT)
                    elif self.at(x, y) == CAVE_BEARD and beard_growth:
                        next.grow_beard(x, y)
        except RobotDestroyed:
            next.end_state = END_STATE_LOSE
        return next
    
    def update_water(self):
        robot_x, robot_y = self._robot_pos
        # The robot may have left the water during robot movement.
        if robot_y > self.water_level:
            self.water_steps = 0
        if self.flood_rate > 0:
            self.flood_steps += 1
            if self.flood_steps >= self.flood_rate:
                self.flood_steps = 0
                self.water_level += 1
        if robot_y <= self.water_level:
            self.water_steps += 1
        if self.water_steps > self.water_resistance:
            raise RobotDestroyed()
            
    def grow_beard(self, beard_x, beard_y):
        for x, y in surrounding_squares(beard_x, beard_y):
            if self.at(x, y) == CAVE_EMPTY:
                self.set(x, y, CAVE_BEARD)
            
    def next_stable(self):
        """
        Step forward to a stable cave state, i.e. a state where no rocks have moved.
        The function returns a tuple with the stable cave instance and the number of
        iterations needed to get there: (stable_cave, iteration_number)
        """
        cave = self
        moves = 0
        while cave.rock_movement and not cave.completed:
            cave = cave.move(MOVE_WAIT)
            moves += 1
        return (cave, moves)

if __name__ == '__main__':
    cave = Cave()
    cave.load_file(sys.stdin)
    print cave
    print
    print cave.state_str()
