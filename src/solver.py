#!/usr/bin/env python
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

    def find_paths(self, start, goals, cave_):
        paths = []
        for g in goals:
            p = self.find_path(start, g, cave_)
            if len(p) > 0:
                paths.append(p)
        paths.sort(lambda x, y: len(x) - len(y))
        return paths

    def find_lambdas(self, cave_):
        w, h = cave_.size
        lambdas = []
        for y in range(h):
            for x in range(w):
                if cave_.at(x, y) == cave.CAVE_LAMBDA:
                    lambdas.append((x, y))
        return lambdas

    def follow_path(self, cave_, p):
        moves = []
        success = True
        for x, y in p[1:]:
            rpx, rpy = cave_._robot_pos
            if x > rpx:
                moves.append(cave.MOVE_RIGHT)
                cave_ = cave_.move(cave.MOVE_RIGHT)
                if cave_._robot_pos == (rpx, rpy):
                    success = False
            elif x < rpx:
                moves.append(cave.MOVE_LEFT)
                cave_ = cave_.move(cave.MOVE_LEFT)
                if cave_._robot_pos == (rpx, rpy):
                    success = False
            elif y > rpy:
                moves.append(cave.MOVE_UP)
                cave_ = cave_.move(cave.MOVE_UP)
                if cave_._robot_pos == (rpx, rpy):
                    success = False
            elif y < rpy:
                moves.append(cave.MOVE_DOWN)
                cave_ = cave_.move(cave.MOVE_DOWN)
                if cave_._robot_pos == (rpx, rpy):
                    success = False
            else:
                moves.append(cave.MOVE_WAIT)
                cave_ = cave_.move(cave.MOVE_WAIT)
                if cave_._robot_pos == (rpx, rpy):
                    success = False
            if cave_.completed:
                if cave_.end_state == cave.END_STATE_LOSE:
                    success = False
                break
        return cave_, moves, success

    def solve(self, cave_):
        moves = []
        try:
            while not cave_.completed:
                # find all the lambdas
                lambdas = self.find_lambdas(cave_)
                # just bail for now
                if len(lambdas) == 0:
                    # Take the shortest path
                    paths = self.find_paths(cave_._robot_pos, [cave_._lift_pos], cave_)
                    if len(paths) == 0:
                        moves.append(cave.MOVE_ABORT)
                        return cave_, ''.join(moves)
                    new_cave_, new_moves, success = self.follow_path(cave_, paths[0])
                    moves.extend(new_moves)
                    return new_cave_, ''.join(moves)
                else:
                    # Take the shortest path
                    paths = self.find_paths(cave_._robot_pos, lambdas, cave_)
                    if len(paths) == 0:
                        paths = self.find_paths(cave_._robot_pos, [cave_._lift_pos], cave_)
                        if len(paths) == 0:
                            moves.append(cave.MOVE_ABORT)
                            return cave_, ''.join(moves)
                        new_cave_, new_moves, success = self.follow_path(cave_, paths[0])
                        moves.extend(new_moves)
                        return new_cave_, ''.join(moves)
                    taken = None
                    for p in paths:
                        # move to it
                        new_cave, new_moves, success = self.follow_path(cave_, p)
                        if success:
                            taken = new_cave, new_moves
                            break
                    if taken:
                        cave_ = taken[0]
                        moves.extend(taken[1])
                    else:
                        moves.append(cave.MOVE_ABORT)
                        return cave_, ''.join(moves)
        except SolverInterrupted:
            moves.append(cave.MOVE_ABORT)
            return cave_, ''.join(moves)
        return cave_, ''.join(moves)


if __name__ == "__main__":
    c = cave.Cave()
    c.load_file(sys.stdin)
    s = AStarSolver()
    new_c, route = s.solve(c)
    print route
    #print new_c.score
