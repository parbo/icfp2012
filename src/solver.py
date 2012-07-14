#!/usr/bin/env python
#from __future__ import with_statement
import astar
import cave
import logging
import math
import signal
import sys
from optparse import OptionParser

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
                return abs(x - gx) + abs(y - gy)
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
                    possible = not (cave_.at(x, y + 1) == cave.CAVE_ROCK and cave_.at(x - 1, y) in (cave.CAVE_WALL, cave.CAVE_ROCK) and cave_.at(x + 1, y) in (cave.CAVE_WALL, cave.CAVE_ROCK))
                    if possible:
                        lambdas.append((x, y))
        rpx, rpy = cave_._robot_pos
        lambdas.sort(lambda pos1, pos2: (abs(rpx - pos1[0]) + abs(rpy - pos1[1])) - (abs(rpx - pos2[0]) + abs(rpy - pos2[1])))
        return lambdas

    def follow_path(self, cave_, moves, p):
        success = True
        for x, y in p[1:]:
            rpx, rpy = cave_._robot_pos
            move = ""
            if x > rpx:
                move = cave.MOVE_RIGHT
            elif x < rpx:
                move = cave.MOVE_LEFT
            elif y > rpy:
                move = cave.MOVE_UP
            elif y < rpy:
                move = cave.MOVE_DOWN
            else:
                move = cave.MOVE_WAIT

            if move:
                cave_, moves, step_success = self.move(cave_, moves, move)
                if not step_success:
                    success = False

            if cave_.completed:
                if cave_.end_state == cave.END_STATE_LOSE:
                    success = False
                break
        return cave_, moves, success

    def move(self, cave_, moves, move):
        new_cave = cave_.move(move)
        if move != cave.MOVE_WAIT:
            success = new_cave._robot_pos != cave_._robot_pos
        else:
            success = True
        return new_cave, moves + move, success

    def solve_recursive(self, cave_, moves):
        pass

    def solve(self, cave_):
        moves = ""
        try:
            while not cave_.completed:
                # find all the lambdas
                lambdas = self.find_lambdas(cave_)
                logging.debug("lambdas left: %d", len(lambdas))
                lambdas = lambdas[:20]
                # just bail for now
                if len(lambdas) == 0:
                    # Take the shortest path
                    paths = self.find_paths(cave_._robot_pos, [cave_._lift_pos], cave_)
                    if len(paths) == 0:
                        logging.debug("no path to lift, abort")
                        return self.move(cave_, moves, cave.MOVE_ABORT)
                    logging.debug("no more lambdas, go to lift")
                    return self.follow_path(cave_, moves, paths[0])
                else:
                    # Take the shortest path
                    paths = self.find_paths(cave_._robot_pos, lambdas, cave_)
                    if len(paths) == 0:
                        logging.debug("no path to lambdas, go to lift")
                        paths = self.find_paths(cave_._robot_pos, [cave_._lift_pos], cave_)
                        if len(paths) == 0:
                            logging.debug("no path to lift, abort")
                            return self.move(cave_, moves, cave.MOVE_ABORT)
                        return self.follow_path(cave_, moves, paths[0])
                    taken = None
                    for p in paths:
                        # move to it
                        new_cave, new_moves, success = self.follow_path(cave_, moves, p)
                        if success:
                            taken = new_cave, new_moves
                            break
                    if taken:
                        cave_ = taken[0]
                        moves = taken[1]
                    else:
                        logging.debug("no succesful path to lambdas, abort")
                        return self.move(cave_, moves, cave.MOVE_ABORT)
        except SolverInterrupted:
            logging.debug("solver interrupted, abort")
            return self.move(cave_, moves, cave.MOVE_ABORT)
        return cave_, moves


def main(options, args):
    logging.basicConfig(level=options.loglevel)
    c = cave.Cave()
    if options.filename:
        logging.info("filename: %s", options.filename)
        with open(options.filename) as f:
            c.load_file(f)
    else:
        c.load_file(sys.stdin)
    s = AStarSolver()
    new_c, route, success = s.solve(c)
    print route
    logging.info("score: %d", new_c.score)


if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-f", "--file", dest="filename",
                      help="load map from FILE", metavar="FILE")
    parser.add_option("-l", "--log", dest="loglevel", type="int",
                      help="logging level", default=1000)
    options, args = parser.parse_args()
    main(options, args)
