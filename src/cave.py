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
CAVE_CHARS = frozenset([CAVE_EMPTY, CAVE_DIRT, CAVE_WALL, CAVE_ROCK, CAVE_LAMBDA, CAVE_ROBOT, CAVE_CLOSED_LIFT, CAVE_OPEN_LIFT])

MOVE_LEFT = 'L'
MOVE_RIGHT = 'R'
MOVE_UP = 'U'
MOVE_DOWN = 'D'
MOVE_WAIT = 'W'
MOVE_ABORT = 'A'

DPOS = {
    MOVE_LEFT: (-1, 0),
    MOVE_RIGHT: (1, 0),
    MOVE_UP: (0, 1),
    MOVE_DOWN: (0, -1),
    MOVE_WAIT: (0, 0),
    MOVE_ABORT: (0, 0)
}

SCORE_MOVE = -1
SCORE_LAMBDA_COLLECT = 25
SCORE_LAMBDA_ABORT = 25
SCORE_LAMBDA_LIFT = 50

END_STATE_WIN = 'win'
END_STATE_LOSE = 'lose'
END_STATE_ABORT = 'abort'

DEFAULT_WATER_LEVEL = -1
DEFAULT_FLOOD_RATE = 0
DEFAULT_WATER_RESISTANCE = 10

RE_WATER_LEVEL = re.compile(r'Water (\d+)')
RE_FLOOD_RATE = re.compile(r'Flooding (\d+)')
RE_WATER_RESISTANCE = re.compile(r'Waterproof (\d+)')

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
        
        # Private attributes
        self._cave = None
        self._robot_pos = None
        self._lift_pos = None
        self._lift_open = False
        self._lambda_count = 0
        self._lambda_collected = 0

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
            line = line.strip('\n')
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
        return (squares, self.score, self.end_state, self._robot_pos, self._lift_open, self._lambda_count, self._lambda_collected)

    def restore_move_state(self, state):
        """ Restore the state as it was before robot movement. """
        squares, score, end_state, robot_pos, lift_open, lambda_count, lambda_collected = state
        self.score = score
        self.end_state = end_state
        self._robot_pos = robot_pos
        self._lift_open = lift_open
        self._lambda_count = lambda_count
        self._lambda_collected = lambda_collected
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
        if target_content in (CAVE_EMPTY, CAVE_DIRT):
            self.set_robot(new_x, new_y)
            self.set(x, y, CAVE_EMPTY)
        elif target_content == CAVE_OPEN_LIFT:
            next = self.clone()
            next.set_robot(new_x, new_y)
            next.set(x, y, CAVE_EMPTY)
            next.end_state = END_STATE_WIN
            next.score += self._lambda_collected * SCORE_LAMBDA_LIFT
            return next
        elif target_content == CAVE_LAMBDA:
            self.set_robot(new_x, new_y)
            self.set(x, y, CAVE_EMPTY)
            self._lambda_collected += 1
            self._lambda_count -= 1
            if self._lambda_count == 0:
                self._lift_open = True
            self.score += SCORE_LAMBDA_COLLECT
        elif target_content == CAVE_ROCK and dy == 0:
            if self.at(x + 2 * dx, y) == CAVE_EMPTY:
                self.set_robot(new_x, new_y)
                self.set(x, y, CAVE_EMPTY)
                self.set_rock(x + 2 * dx, y)
        assert self.at(*self._robot_pos) == CAVE_ROBOT
        next = self.update()
        self.restore_move_state(state)
        return next

    def update(self):
        next = self.clone()
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
        except RobotDestroyed:
            next.end_state = END_STATE_LOSE
        return next
    
    def update_water(self):
        if self.flood_rate > 0:
            self.flood_steps += 1
            if self.flood_steps >= self.flood_rate:
                self.flood_steps = 0
                self.water_level += 1
        robot_x, robot_y = self._robot_pos
        if robot_y > self.water_level:
            self.water_steps = 0
        else:
            self.water_steps += 1
        if self.water_steps > self.water_resistance:
            raise RobotDestroyed()

if __name__ == '__main__':
    cave = Cave()
    cave.load_file(sys.stdin)
    print cave
    print
    print cave.state_str()
