import astar
import cave
import math
import signal
import sys

class SolverInterrupted(Exception):
    pass

class Solver(object):
    def _signal_handler(self, signal, frame):
        raise SolverInterrupted()

    def __init__(self):
        signal.signal(signal.SIGINT, self._signal_handler)

    def solve(self, cave):
        """Returns a route"""

class AStarSolver(Solver):
    def __init__(self):
        Solver.__init__(self)

    def find_path(self, start, goal, cave_):
        def g(n1, n2):
            return 1
        def nf(c):
            def neighbours(n):
                x, y = n
                nb = []
                w, h = c.size
                for dx, dy in [(-1, 0), (0, 1), (1, 0), (0, -1)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= ny < h and 0 <= nx < w:
                        rock_above = (ny < y and c.at(x, y+1) == cave.CAVE_ROCK)
                        if not rock_above and c.at(nx, ny) in (cave.CAVE_EMPTY, cave.CAVE_DIRT, cave.CAVE_OPEN_LIFT, cave.CAVE_LAMBDA):
                            nb.append((nx, ny))
                return nb
            return neighbours
        def hf(goal):
            def h(n):
                x, y = n
                gx, gy = goal
                return math.sqrt((x - gx)**2 + (y - gy)**2)
            return h
        return astar.astar(start, goal, g, hf(goal), nf(cave_))

    def shortest_path(self, start, goals, cave_):
        paths = []
        for g in goals:
            p = self.find_path(start, g, cave_)
            paths.append(p)
        paths.sort(lambda x, y: len(x) - len(y))
        return paths[0]

    def find_lambdas(self, cave_):
        w, h = cave_.size
        lambdas = []
        for y in range(h):
            for x in range(w):
                if cave_.at(x, y) == cave.CAVE_LAMBDA:
                    lambdas.append((x, y))
        return lambdas

    def follow_path(self, cave_, p, moves):
        for x, y in p[1:]:
            rpx, rpy = cave_._robot_pos
            if x > rpx:
                moves.append(cave.MOVE_RIGHT)
                cave_ = cave_.move(cave.MOVE_RIGHT)
            elif x < rpx:
                moves.append(cave.MOVE_LEFT)
                cave_ = cave_.move(cave.MOVE_LEFT)
            elif y > rpy:
                moves.append(cave.MOVE_UP)
                cave_ = cave_.move(cave.MOVE_UP)
            elif y < rpy:
                moves.append(cave.MOVE_DOWN)
                cave_ = cave_.move(cave.MOVE_DOWN)
            else:
                moves.append(cave.MOVE_WAIT)
                cave_ = cave_.move(cave.MOVE_WAIT)
            if cave_.completed:
                break
        return cave_, moves

    def solve(self, cave_):
        moves = []
        try:
            while not cave_.completed:
                # find all the lambdas
                lambdas = self.find_lambdas(cave_)
                # just bail for now
                if len(lambdas) == 0:
                    # Take the shortest path
                    p = self.shortest_path(cave_._robot_pos, [cave_._lift_pos], cave_)
                    # move to it
                    cave_, moves = self.follow_path(cave_, p, moves)
                    return ''.join(moves)
                else:
                    # Take the shortest path
                    p = self.shortest_path(cave_._robot_pos, lambdas, cave_)
                    # move to it
                    cave_, moves = self.follow_path(cave_, p, moves)
        except SolverInterrupted:
            moves.append(cave.MOVE_ABORT)
            return ''.join(moves)
        return ''.join(moves)


if __name__ == "__main__":
    c = cave.Cave()
    f = open(sys.argv[1])
    c.load_file(f)
    f.close()
    s = AStarSolver()
    print s.solve(c)
