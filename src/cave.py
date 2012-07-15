#!/usr/bin/python
import sys
import copy
import re
import array
from collections import defaultdict

import astar

CAVE_EMPTY = ' '
CAVE_DIRT = '.'
CAVE_WALL = '#'
CAVE_ROCK = '*'
CAVE_LAMBDA = '\\'
CAVE_LAMBDA_ROCK = '@'
CAVE_ROBOT = 'R'
CAVE_CLOSED_LIFT = 'L'
CAVE_OPEN_LIFT = 'O'
CAVE_BEARD = 'W'
CAVE_RAZOR = '!'

CAVE_ANY_ROCK = (CAVE_ROCK, CAVE_LAMBDA_ROCK)

CAVE_TRAMPOLINE_CHARS = 'ABCDEFGHI'
CAVE_TARGET_CHARS = '123456789'

CAVE_CHARS = set([CAVE_EMPTY, CAVE_DIRT, CAVE_WALL, CAVE_ROCK, CAVE_LAMBDA, CAVE_LAMBDA_ROCK, CAVE_ROBOT, CAVE_CLOSED_LIFT, CAVE_OPEN_LIFT, CAVE_BEARD, CAVE_RAZOR])
CAVE_CHARS.update(CAVE_TRAMPOLINE_CHARS)
CAVE_CHARS.update(CAVE_TARGET_CHARS)

CAVE_REMOVABLE_CHARS = set([CAVE_DIRT, CAVE_LAMBDA, CAVE_RAZOR])
CAVE_OCCUPIABLE_CHARS = set([CAVE_EMPTY, CAVE_DIRT, CAVE_OPEN_LIFT, CAVE_LAMBDA, CAVE_RAZOR])
CAVE_SOLID_CHARS = CAVE_CHARS - CAVE_OCCUPIABLE_CHARS

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

RDPOS = {
    (-1, 0): MOVE_LEFT,
    (1, 0): MOVE_RIGHT,
    (0, 1): MOVE_UP,
    (0, -1): MOVE_DOWN,
    (0, 0): MOVE_WAIT,
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

def is_occupiable(content):
    return content in CAVE_OCCUPIABLE_CHARS

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
        self.lambda_rock_count = 0
        self._lambda_collected = 0
        self.lambdas = set()
        self.lambda_rocks = set()
        self.razors = set()
        # Beard parameters.
        self.beard_growth_rate = DEFAULT_BEARD_GROWTH_RATE
        self.beard_growth = self.beard_growth_rate - 1
        # Number of razors carried by the robot.
        self.razors_carried = 0
        # Trampoline/target mapping (trampoline -> target).
        self._trampoline = {}
        # Inverse trampoline/target mapping (target -> list of trampolines).
        self._target_trampoline = defaultdict(list)
        # Trampoline/target postions.
        self._trampoline_pos = {}
        self._trampoline_target_pos = {}

        self._cave = None

    def __str__(self):
        return '\n'.join([''.join(row) for row in reversed(self._cave)])

    def state_str(self):
        s = []
        s.append('Robot position:    %s' % str(self._robot_pos))
        s.append('Lift position:     %s' % str(self._lift_pos))
        s.append('Lift state:        %s' % ('Open' if self._lift_open else 'Closed'))
        s.append('Number of lambdas: %d' % self._lambda_count)
        s.append('Lambda rocks:      %d' % self.lambda_rock_count)
        s.append('Water resistance:  %d' % self.water_resistance)
        s.append('Water level:       %d' % self.water_level)
        s.append('Flood rate:        %d' % self.flood_rate)
        s.append('Beard growth rate: %d' % self.beard_growth_rate)
        s.append('Initial razors:    %d' % self.razors_carried)
        if len(self._trampoline) > 0:
            s.append('Trampolines:       %s' % ', '.join(['%s->%s' % (tr, tg) for tr, tg in sorted(self._trampoline.iteritems())]))
            s.append('Positions:         %s' % ', '.join(['%s->(%d,%d)' % (tr, p[0], p[1]) for tr, p in sorted(self._trampoline_pos.iteritems())]))
            s.append('Targets:           %s' % ', '.join(['%s->%s' % (tg, trl) for tg, trl in sorted(self._target_trampoline.iteritems())]))
            s.append('Positions:         %s' % ', '.join(['%s->(%d,%d)' % (tg, p[0], p[1]) for tg, p in sorted(self._trampoline_target_pos.iteritems())]))
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
        
    def set_rock(self, new_pos, old_pos):
        x, y = new_pos
        self.set(x, y, CAVE_ROCK)
        self.rock_movement = True
        if self.at(x, y - 1) == CAVE_ROBOT:
            raise RobotDestroyed()
            
    def set_lambda_rock(self, new_pos, prev_pos):
        nx, ny = new_pos
        px, py = prev_pos
        falling = ny < py
        self.lambda_rocks.remove(prev_pos)
        if falling and self.at(nx, ny - 1) != CAVE_EMPTY:
            self.lambdas.add(new_pos)
            self.lambda_rock_count -= 1
            self._lambda_count += 1
            self.set(nx, ny, CAVE_LAMBDA)
        else:
            self.lambda_rocks.add(new_pos)
            self.set(nx, ny, CAVE_LAMBDA_ROCK)
        #self.rock_movement = True
        if self.at(nx, ny - 1) == CAVE_ROBOT:
            raise RobotDestroyed()
        
    @property
    def completed(self):
        return self.end_state is not None
    
    @property
    def is_drowning(self):
        return self.water_steps >= self.water_resistance
    
    def trampoline_target(self, trampoline):
        """ Get the target ID of a given trampoline. """
        return self._trampoline.get(trampoline)
    
    def trampoline_target_pos(self, trampoline):
        """ Get the target position of a given trampoline. """
        return self._trampoline_target_pos[self._trampoline[trampoline]]
        
    def target_trampolines(self, target):
        """ Get a list of trampolines that can reach a given target. """
        return self._target_trampoline.get(target, [])

    def analyze(self):
        self._lambda_count = 0
        for y, row in enumerate(self._cave):
            for x, content in enumerate(row):
                if content == CAVE_LAMBDA:
                    self._lambda_count += 1
                    self.lambdas.add((x, y))
                elif content == CAVE_LAMBDA_ROCK:
                    self.lambda_rock_count += 1
                    self.lambda_rocks.add((x, y))
                elif content == CAVE_RAZOR:
                    self.razors.add((x, y))
                elif content == CAVE_ROBOT:
                    self._robot_pos = (x, y)
                elif content == CAVE_CLOSED_LIFT:
                    self._lift_pos = (x, y)
                    self._lift_open = False
                elif content == CAVE_OPEN_LIFT:
                    self._lift_pos = (x, y)
                    self._lift_open = True
                elif content in CAVE_TARGET_CHARS:
                    self._trampoline_target_pos[content] = (x, y)
                elif content in CAVE_TRAMPOLINE_CHARS:
                    self._trampoline_pos[content] = (x, y)

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
                    trampoline = m.group(1)
                    target = m.group(2)
                    self._trampoline[trampoline] = target
                    self._target_trampoline[target].append(trampoline)
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
        self._cave = [array.array('c', line.ljust(cave_width)) for line in reversed(cave_lines)]
        self.analyze()

    def is_cave_str(self, s):
        return len(s) > 0 and set(s) <= CAVE_CHARS

    def robot_move_cost(self, move, pos=None):
        """This returns the cost of the move, or -1 if impossible"""
        if pos is None:
            pos = self._robot_pos
        rpx, rpy = pos
        if move in (MOVE_WAIT, MOVE_ABORT):
            return 0
        # don't go down when a rock is above
        if move == MOVE_DOWN:
            if self.at(rpx, rpy+1) in CAVE_ANY_ROCK:
                return -1
        dx, dy = DPOS[move]
        obj = self.at(rpx+dx, rpy+dy)
        # rocks can be pushed, but not to block the lift
        if move in (MOVE_RIGHT, MOVE_LEFT):
            if obj in CAVE_ANY_ROCK and self.at(rpx+2*dx, rpy) == CAVE_EMPTY:
                if self.at(rpx+3*dx, rpy) in (CAVE_OPEN_LIFT, CAVE_CLOSED_LIFT):
                    return 1000 # really high, but not impossible
                return 3
        # it's possible to go to any occupiable object
        if is_occupiable(obj):
            return 1

    def get_possible_robot_moves(self, pos=None):
        if pos is None:
            pos = self._robot_pos
        return [m for m in [MOVE_UP, MOVE_DOWN, MOVE_RIGHT, MOVE_LEFT] if self.robot_move_cost(m, pos) >= 0]

    def find_path(self, goal, pos=None):
        def gf(c):
            def g(n1, n2):
                dx = n2[0] - n1[0]
                dy = n2[1] - n1[1]
                try:
                    m = RDPOS[(dx, dy)]
                    return c.robot_move_cost(m, n1)
                except KeyError:
                    pass
                return 1
            return g
        def nf(c):
            def neighbours(n):
                x, y = n
                nb = []
                w, h = c.size
                for m in [MOVE_UP, MOVE_DOWN, MOVE_RIGHT, MOVE_LEFT]:
                    if c.robot_move_cost(m, (x, y)) >= 0:
                        dx, dy = DPOS[m]
                        nb.append((x+dx, y+dy))
                return nb
            return neighbours
        def hf(goal):
            def h(n):
                x, y = n
                gx, gy = goal
                return abs(x - gx) + abs(y - gy)
            return h
        if pos is None:
            pos = self._robot_pos
        return astar.astar(pos, goal, gf(self), hf(goal), nf(self))

    def clone(self):
        return copy.deepcopy(self)

    def move(self, move):
        if self.completed:
            return self
        next = self.clone()
        if move == MOVE_ABORT:
            next.end_state = END_STATE_ABORT
            next.score += self._lambda_collected * SCORE_LAMBDA_ABORT
            return next
        next.score += SCORE_MOVE
        dx, dy = DPOS[move]
        x, y = next._robot_pos
        new_x = x + dx
        new_y = y + dy
        target_content = next.at(new_x, new_y)
        if target_content == CAVE_OPEN_LIFT:
            next.set_robot(new_x, new_y)
            next.set(x, y, CAVE_EMPTY)
            next.end_state = END_STATE_WIN
            next.score += self._lambda_collected * SCORE_LAMBDA_LIFT
            return next
        next.rock_movement = False
        if target_content in (CAVE_EMPTY, CAVE_DIRT):
            next.set_robot(new_x, new_y)
            next.set(x, y, CAVE_EMPTY)
        elif target_content == CAVE_LAMBDA:
            next.set_robot(new_x, new_y)
            next.set(x, y, CAVE_EMPTY)
            next._lambda_collected += 1
            next._lambda_count -= 1
            next.lambdas.remove((new_x, new_y))
            if next._lambda_count + next.lambda_rock_count == 0:
                next._lift_open = True
            next.score += SCORE_LAMBDA_COLLECT
        elif target_content == CAVE_RAZOR:
            next.set_robot(new_x, new_y)
            next.set(x, y, CAVE_EMPTY)
            next.razors_carried += 1
            next.razors.remove((new_x, new_y))
        elif target_content in CAVE_TRAMPOLINE_CHARS:
            target = next._trampoline[target_content]
            target_pos = next._trampoline_target_pos[target]
            next.set_robot(*target_pos)
            next.set(x, y, CAVE_EMPTY)
            for trampoline, pos in next._trampoline_pos.iteritems():
                if next._trampoline[trampoline] == target:
                    next.set(pos[0], pos[1], CAVE_EMPTY)
        elif target_content == CAVE_ROCK and dy == 0:
            if next.at(x + 2 * dx, y) == CAVE_EMPTY:
                next.set_robot(new_x, new_y)
                next.set(x, y, CAVE_EMPTY)
                next.set_rock((x + 2 * dx, y), (x + dx, y))
        elif target_content == CAVE_LAMBDA_ROCK and dy == 0:
            if next.at(x + 2 * dx, y) == CAVE_EMPTY:
                next.set_robot(new_x, new_y)
                next.set(x, y, CAVE_EMPTY)
                next.set_lambda_rock((x + 2 * dx, y), (x + dx, y))
        if move == MOVE_SHAVE and next.razors_carried > 0:
            next.razors_carried -= 1
            for x, y in surrounding_squares(new_x, new_y):
                if next.at(x, y) == CAVE_BEARD:
                    next.set(x, y, CAVE_EMPTY)
        assert next.at(*next._robot_pos) == CAVE_ROBOT
        return next.update()

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
                    content = self.at(x, y)
                    if content == CAVE_CLOSED_LIFT and self._lift_open:
                        next.set(x, y, CAVE_OPEN_LIFT)
                    elif content == CAVE_BEARD and beard_growth:
                        next.grow_beard(x, y)
                    elif content in CAVE_ANY_ROCK:
                        next.update_rock(self, x, y, content)                    
        except RobotDestroyed:
            next.end_state = END_STATE_LOSE
        return next
    
    def update_rock(self, previous_cave, x, y, rock_type):
        new_pos = None
        if previous_cave.at(x, y - 1) == CAVE_EMPTY:
            new_pos = (x, y - 1)
        elif previous_cave.at(x, y - 1) in CAVE_ANY_ROCK and previous_cave.at(x + 1, y) == CAVE_EMPTY and previous_cave.at(x + 1, y - 1) == CAVE_EMPTY:
            new_pos = (x + 1, y - 1)
        elif previous_cave.at(x, y - 1) in CAVE_ANY_ROCK and previous_cave.at(x - 1, y) == CAVE_EMPTY and previous_cave.at(x - 1, y - 1) == CAVE_EMPTY:
            new_pos = (x - 1, y - 1)
        elif previous_cave.at(x, y - 1) == CAVE_LAMBDA and previous_cave.at(x + 1, y) == CAVE_EMPTY and previous_cave.at(x + 1, y - 1) == CAVE_EMPTY:
            new_pos = (x + 1, y - 1)
        if new_pos is not None:
            self.set(x, y, CAVE_EMPTY)
            if rock_type == CAVE_ROCK:
                self.set_rock(new_pos, (x, y))
            else:
                self.set_lambda_rock(new_pos, (x, y))
    
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
        
    def find_unmovable_rocks(self):
        """ Get a set of rocks (positions) that can't be moved. """
        cave = {}
        size_x, size_y = self.size
        for y in range(size_y):
            for x in range(size_x):
                content = self.at(x, y)
                if content == CAVE_ROCK:
                    cave[x, y] = (x, y)
                elif content in (CAVE_WALL, CAVE_CLOSED_LIFT, CAVE_OPEN_LIFT):
                    cave[x, y] = content
                else:
                    cave[x, y] = CAVE_EMPTY
        other_than_rock = (CAVE_EMPTY, CAVE_WALL, CAVE_CLOSED_LIFT, CAVE_OPEN_LIFT)
        # Find rocks that can be pushed.
        movable = set()
        for y in range(size_y):
            for x in range(size_x):
                if cave[x, y] not in other_than_rock and cave[x - 1, y] == CAVE_EMPTY and cave[x + 1, y] == CAVE_EMPTY:
                    movable.add((x, y))
        movement = True
        while movement:
            movement = False
            next = copy.copy(cave)
            for y in range(size_y):
                for x in range(size_x):
                    content = cave[x, y]
                    if content not in other_than_rock:
                        new_pos = None
                        if cave[x, y - 1] == CAVE_EMPTY:
                            new_pos = (x, y - 1)
                        elif cave[x, y - 1] not in other_than_rock and cave[x + 1, y] == CAVE_EMPTY and cave[x + 1, y - 1] == CAVE_EMPTY:
                            new_pos = (x + 1, y - 1)
                        elif cave[x, y - 1] not in other_than_rock and cave[x - 1, y] == CAVE_EMPTY and cave[x - 1, y - 1] == CAVE_EMPTY:
                            new_pos = (x - 1, y - 1)
                        if new_pos is not None:
                            next[x, y] = CAVE_EMPTY
                            next[new_pos] = content
                            movement = True
            cave = next
        unmovable = set()
        for y in range(size_y):
            for x in range(size_x):
                if cave[x, y] == (x, y):
                    unmovable.add((x, y))
        unmovable -= movable
        return unmovable

if __name__ == '__main__':
    cave = Cave()
    cave.load_file(sys.stdin)
    print cave
    print
    print cave.state_str()
