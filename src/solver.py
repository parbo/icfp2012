#!/usr/bin/env python
#from __future__ import with_statement
import astar
import cave
import logging
import math
import signal
import string
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
        self.visited = {}

    def find_path(self, start, goal, cave_):
        def gf(c):
            def g(n1, n2):
                return 1
            return g
        def nf(c):
            def neighbours(n):
                x, y = n
                nb = []
                w, h = c.size
                for dx, dy in [(-1, 0), (0, 1), (1, 0), (0, -1)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= ny < h and 0 <= nx < w:
                        rock_above = (ny < y and c.at(x, y+1) == cave.CAVE_ROCK)
                        if not rock_above:
                            pushable_rock_left = (nx < x and c.at(nx, y) == cave.CAVE_ROCK and c.at(nx-1, y) == cave.CAVE_EMPTY)
                            pushable_rock_right = (nx > x and c.at(nx, y) == cave.CAVE_ROCK and c.at(nx+1, y) == cave.CAVE_EMPTY)
                            if c.at(nx, ny) in (cave.CAVE_EMPTY, cave.CAVE_DIRT, cave.CAVE_OPEN_LIFT, cave.CAVE_LAMBDA):
                                nb.append((nx, ny))
                            elif pushable_rock_right or pushable_rock_right:
                                nb.append((nx, ny))
                return nb
            return neighbours
        def hf(goal):
            def h(n):
                x, y = n
                gx, gy = goal
                return abs(x - gx) + abs(y - gy)
            return h
        return astar.astar(start, goal, gf(cave_), hf(goal), nf(cave_))

    def find_paths(self, start, goals, cave_):
        paths = []
        for g in goals:
            p = self.find_path(start, g, cave_)
            if len(p) > 0:
                paths.append(p)
        paths.sort(lambda x, y: len(x) - len(y))
        return paths

    def find_lambdas(self, cave_):
        def get_lambda_comparer(cave_):
            rpx, rpy = cave_._robot_pos
            lpx, lpy = cave_._lift_pos
            def compare(p1, p2):
                dp1 = abs(rpx - p1[0]) + abs(rpy - p1[1])
                dp2 = abs(rpx - p2[0]) + abs(rpy - p2[1])
                diff = dp1 - dp2
                if diff == 0:
                    # take lambdas close to the lift later
                    return (abs(lpx - p2[0]) + abs(lpy - p2[1])) - (abs(lpx - p1[0]) + abs(lpy - p1[1]))
                return diff
            return compare
        w, h = cave_.size
        lambdas = []
        for x, y in cave_.lambdas:
            if cave_.at(x, y) == cave.CAVE_LAMBDA:
                possible = not (cave_.at(x, y + 1) == cave.CAVE_ROCK and cave_.at(x - 1, y) in (cave.CAVE_WALL,) and cave_.at(x + 1, y) in (cave.CAVE_WALL,))
                if possible:
                    lambdas.append((x, y))
        rpx, rpy = cave_._robot_pos
        lambdas.sort(get_lambda_comparer(cave_))
        return lambdas

    def follow_path(self, cave_, moves, p):
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
                cave_, moves, step_success, replan = self.move(cave_, moves, move)
                if replan:
                    return cave_, moves, cave_._robot_pos == p[-1], replan

            if cave_.completed:
                break
        return cave_, moves, cave_._robot_pos == p[-1], False

    def move(self, cave_, moves, move):
        new_cave = cave_.move(move)
        if move != cave.MOVE_WAIT:
            success = new_cave._robot_pos != cave_._robot_pos
        else:
            success = True
        return new_cave, moves + move, success, new_cave.rock_movement

    def solve_recursive(self, cave_, moves):
        try:
            return self.visited[str(cave_)]
        except KeyError:
            pass
        if cave_.completed:
            return cave_.score, cave_, moves
        goals = self.find_lambdas(cave_)
        goals = goals[:5]
        paths = self.find_paths(cave_._robot_pos, goals, cave_)
        if len(paths) == 0:
            # find lift
            paths = self.find_paths(cave_._robot_pos, [cave_._lift_pos], cave_)
        scores = []
        for p in paths:
            new_cave, new_moves, success, replan = self.follow_path(cave_, moves, p)
            if success or replan:
                scores.append(self.solve_recursive(new_cave, new_moves))
        scores.sort()
        if len(scores) == 0:
            new_cave, new_moves, succes, replan = self.move(cave_, moves, cave.MOVE_ABORT)
            self.visited[str(cave_)] = (new_cave.score, new_cave, new_moves)
            print new_cave.score
            return new_cave.score, new_cave, new_moves
        s, new_cave, new_moves = scores[-1]
        self.visited[str(cave_)] = (new_cave.score, new_cave, new_moves)
        print new_cave.score
        return new_cave.score, new_cave, new_moves

    def find_goals(self, cave_):
        # find some lambdas
        lambdas = self.find_lambdas(cave_)
        lambdas = lambdas[:20]
        if len(lambdas) > 0:
            return lambdas
        # no lambdas, find open lift
        if cave_.at(*cave_._lift_pos) == cave.CAVE_OPEN_LIFT:
            logging.debug("go to open lift")
            return [cave_._lift_pos]
        else:
            logging.debug("lift not open")
        # no goals
        return []

    def solve(self, cave_):
        moves = ""
        panic_moves = [cave.MOVE_UP, cave.MOVE_LEFT, cave.MOVE_RIGHT, cave.MOVE_DOWN]
        panic_count = 0
        try:
            while not cave_.completed:
                logging.debug("lambdas left: %d", cave_._lambda_count)
                if cave_.is_drowning:
                    return self.move(cave_, moves, cave.MOVE_ABORT)
                # find goals
                goals = self.find_goals(cave_)
                if len(goals) == 0:
                    return self.move(cave_, moves, cave.MOVE_ABORT)
                logging.debug("considering %d goals", len(goals))
                # find paths to goals
                paths = self.find_paths(cave_._robot_pos, goals, cave_)
                logging.debug("found %d paths", len(paths))
                if len(paths) > 0:
                    # reset panic count when new paths are found
                    self.panic_count = 0
                taken = None
                to_replan = []
                for p in paths:
                    # move to it
                    new_cave, new_moves, success, replan = self.follow_path(cave_, moves, p)
                    if success and new_cave.end_state != cave.END_STATE_LOSE:
                        logging.debug("successfully followed path")
                        taken = new_cave, new_moves
                        break
                    if replan and new_cave.end_state != cave.END_STATE_LOSE:
                        logging.debug("replan, cave state: %s", new_cave.end_state)
                        to_replan.append((new_cave, new_moves))
                if taken:
                    # a successful move was found
                    cave_ = taken[0]
                    moves = taken[1]
                elif to_replan:
                    # something changed, replanning needed
                    logging.debug("replanning needed!")
                    # grab the first one
                    cave_ = to_replan[0][0]
                    moves = to_replan[0][1]
                else:
                    # no strategy works, just move a step and see what happens
                    ok = False
                    for m in panic_moves[panic_count:]:
                        panic_count += 1
                        rpx, rpy = cave_._robot_pos
                        new_cave, new_moves, success, replan = self.move(cave_, moves, m)
                        if success:
                            cave_ = new_cave
                            moves = new_moves
                            ok = True
                            break
                    if not ok:
                        return self.move(cave_, moves, cave.MOVE_ABORT)
        except SolverInterrupted:
            logging.debug("solver interrupted, abort")
            return self.move(cave_, moves, cave.MOVE_ABORT)
        logging.debug("end state: %s", cave_.end_state)
        return cave_, moves, True, False


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
    new_c, route, success, replan = s.solve(c)
    print route
    logging.info("score: %d", new_c.score)
    logging.info("end state: %s", new_c.end_state)

#    score, c, route = s.solve_recursive(c, "")
#    print route, c.score, c.end_state


if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-f", "--file", dest="filename",
                      help="load map from FILE", metavar="FILE")
    parser.add_option("-l", "--log", dest="loglevel", type="int",
                      help="logging level", default=1000)
    options, args = parser.parse_args()
    main(options, args)
