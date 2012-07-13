import sys
import copy

CAVE_EMPTY = ' '
CAVE_DIRT = '.'
CAVE_WALL = '#'
CAVE_ROCK = '*'
CAVE_LAMBDA = '\\'
CAVE_ROBOT = 'R'
CAVE_CLOSED_LIFT = 'L'
CAVE_OPEN_LIFT = 'O'

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

class Cave(object):
    def __init__(self):
        self._cave = None
        self._robot_pos = None
        self._lift_pos = None
        self._lift_open = False
        self._lambda_count = 0
        self._lambda_collected = 0
        self._completed = False

    def __str__(self):
        return '\n'.join([''.join(row) for row in reversed(self._cave)])

    def state_str(self):
        s = []
        s.append('Robot position:    %s' % str(self._robot_pos))
        s.append('Lift position:     %s' % str(self._lift_pos))
        s.append('Lift state:        %s' % ('Open' if self._lift_open else 'Closed'))
        s.append('Number of lambdas: %d' % self._lambda_count)
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
        lines = [line.strip('\n') for line in f.readlines()]
        cave_width = max([len(line) for line in lines])
        self._cave = [list(line.ljust(cave_width)) for line in reversed(lines)]
        self.analyze()

    def clone(self):
        return copy.deepcopy(self)

    def move(self, move):
        next = self.clone()
        dx, dy = DPOS[move]
        x, y = self._robot_pos
        new_x = x + dx
        new_y = y + dy
        target_content = self.at(new_x, new_y)
        if target_content in (CAVE_EMPTY, CAVE_DIRT):
            next._robot_pos = (new_x, new_y)
            next._cave[y][x] = CAVE_EMPTY
        elif target_content == CAVE_OPEN_LIFT:
            next._robot_pos = (new_x, new_y)
            next._cave[y][x] = CAVE_EMPTY
            next._completed = True
        elif target_content == CAVE_LAMBDA:
            next._robot_pos = (new_x, new_y)
            next._cave[y][x] = CAVE_EMPTY
            next._lambda_collected += 1
            next._lambda_count -= 1
            if next._lambda_count == 0:
                self._lift_open = True
        elif target_content == CAVE_ROCK and dy == 0:
            if self.at(x + 2 * dx, y) == CAVE_EMPTY:
                next._robot_pos = (new_x, new_y)
                next._cave[y][x] = CAVE_EMPTY
                next._cave[y][x + 2 * dx] = CAVE_ROCK
        return next.update()

    def update(self):
        next = self.clone()
        size_x, size_y = self.size
        for y in range(size_y):
            for x in range(size_x):
                if self.at(x, y) == CAVE_ROCK and self.at(x, y - 1) == CAVE_EMPTY:
                    next._cave[y][x] = CAVE_EMPTY
                    next._cave[y - 1][x] = CAVE_ROCK
                elif self.at(x, y) == CAVE_ROCK and self.at(x, y - 1) == CAVE_ROCK and self.at(x + 1, y) == CAVE_EMPTY and self.at(x + 1, y - 1) == CAVE_EMPTY:
                    next._cave[y][x] = CAVE_EMPTY
                    next._cave[y - 1][x + 1] = CAVE_ROCK
                elif self.at(x, y) == CAVE_ROCK and self.at(x, y - 1) == CAVE_ROCK and self.at(x - 1, y) == CAVE_EMPTY and self.at(x - 1, y - 1) == CAVE_EMPTY:
                    next._cave[y][x] = CAVE_EMPTY
                    next._cave[y - 1][x - 1] = CAVE_ROCK
                elif self.at(x, y) == CAVE_ROCK and self.at(x, y - 1) == CAVE_LAMBDA and self.at(x + 1, y) == CAVE_EMPTY and self.at(x + 1, y - 1) == CAVE_EMPTY:
                    next._cave[y][x] = CAVE_EMPTY
                    next._cave[y - 1][x + 1] = CAVE_ROCK
                elif self.at(x, y) == CAVE_CLOSED_LIFT and self._lift_open:
                    next._cave[y][x] = CAVE_OPEN_LIFT
        return next

if __name__ == '__main__':
    cave = Cave()
    cave.load_file(sys.stdin)
    print cave
    print
    print cave.state_str()
