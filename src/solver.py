#!/usr/bin/env python
#from __future__ import with_statement
import cave
import logging
import math
import signal
import string
import sys
from optparse import OptionParser

class SolverInterrupted(Exception):
    pass

class Target(object):
    def __init__(self, pos, obj):
        self.pos = pos
        self.obj = obj

class Solver(object):
    def _signal_handler(self, signal, frame):
        raise SolverInterrupted()

    def __init__(self):
        signal.signal(signal.SIGINT, self._signal_handler)

    def solve(self, cave):
        """Returns a route"""

class AStarSolver(Solver):
    def __init__(self, from_below):
        Solver.__init__(self)
        self._from_below = from_below
        self.visited = {}

    def find_lambdas(self, cave_, pos=None):
        def get_lambda_comparer(cave_, rpos, lpos):
            rpx, rpy = rpos
            lpx, lpy = lpos
            def compare(p1, p2):
                dx1 = abs(rpx - p1[0])
                dy1 = abs(rpy - p1[1])
                dx2 = abs(rpx - p2[0])
                dy2 = abs(rpy - p2[1])
                if self._from_below:
                    diff = p1[1] - p2[1]
                    if diff == 0:
                        diff = dx1 - dx2
                else:
                    diff = (dx1+dy1) - (dx2+dy2)
                    if diff == 0:
                        diff = dy1 - dy2
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
        if pos is None:
            pos = cave_._robot_pos
        rpx, rpy = pos
        lambdas.sort(get_lambda_comparer(cave_, pos, cave_._lift_pos))
        return lambdas

    def follow_path(self, cave_, moves, p):
        replan = False
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
                cave_, moves, step_success, step_replan = self.move(cave_, moves, move)
                if step_replan:
                    replan = True
                    break

            if cave_.completed:
                break
        return cave_, moves, cave_._robot_pos == p[-1], replan

    def move(self, cave_, moves, move):
        new_cave = cave_.move(move)
        dx, dy = cave.DPOS[move]
        rpx, rpy = cave_._robot_pos
        success = new_cave._robot_pos == (rpx+dx, rpy+dy)
        return new_cave, moves + move, success, new_cave.rock_movement

    def exit_blocked(self, cave_, pos):
        return len(cave_.get_possible_robot_moves(pos)) == 0

    def find_stuff(self, cave_, stuff):
        w, h = cave_.size
        stuffs = []
        for y in range(h):
            for x in range(w):
                if cave_.at(x, y) in stuff:
                    stuffs.append((x, y))
        return stuffs

    def find_target_list(self, cave_):
        # find some lambdas
        lambdas = self.find_lambdas(cave_)
        lambdas = lambdas[:20]

        # find stuff we have to clear to make an exit from those lambdas
        # throw away the ones we can't exit from
        unblockable = {}
        blocked = set()
        for x, y in lambdas:
            c = cave_.clone()
            c.set(x, y, cave.CAVE_EMPTY)
            c, iters = c.next_stable()
            if self.exit_blocked(c, (x, y)):
                if c.at(x-1, y) == cave.CAVE_ROCK and c.at(x-2, y) in cave.CAVE_REMOVABLE_CHARS:
                    unblockable[(x,y)] = (x-2, y)
                elif c.at(x+1, y) == cave.CAVE_ROCK and c.at(x+2, y) in cave.CAVE_REMOVABLE_CHARS:
                    unblockable[(x,y)] = (x+2, y)
                else:
                    blocked.add((x, y))

        # assemble a list of targets
        target_list = []
        for lmb in lambdas:
            if lmb in blocked:
                continue
            try:
                unblocker = unblockable[lmb]
                target_list.append(Target(unblocker, cave_.at(*unblocker)))
            except KeyError:
                pass
            target_list.append(Target(lmb, cave_.at(*lmb)))
            break

        if target_list:
            return target_list

        # trampolines = self.find_stuff(cave_, cave.CAVE_TRAMPOLINE_CHARS)
        # targets = self.find_stuff(cave_, cave.CAVE_TARGET_CHARS)
        # for t in target:
        #     lambdas = find_lambdas(cave_, t)
        #     print lambdas
        #     for l in lambdas:
        #         path = cave_.find_path(l, t)
        #         if len(path) > 0:
        #             for tr in trampolines:
        #                 if 
        #                 path = cave_.find_path(tr)
        #                 if len(path) > 0:
        #                     return [tr]

        # no lambdas, find open lift
        if cave_.at(*cave_._lift_pos) == cave.CAVE_OPEN_LIFT:
            logging.debug("go to open lift")
            return [Target(cave_._lift_pos, cave_.at(*cave_._lift_pos))]
        else:
            logging.debug("lift not open")
        # no path
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
                # find target list to traverse
                target_list = self.find_target_list(cave_)
                if not target_list:
                    return self.move(cave_, moves, cave.MOVE_ABORT)
                for target in target_list:
                    # reset panic count for new targets
                    self.panic_count = 0
                    target_done = False
                    need_panic = False
                    while not target_done:
                        logging.debug("trying to get to target '%s' at %s", target.obj, target.pos)
                        path = cave_.find_path(target.pos)
                        if path:
                            logging.debug("found path")
                            # move to it
                            new_cave, new_moves, success, replan = self.follow_path(cave_, moves, path)
                            if success and new_cave.end_state != cave.END_STATE_LOSE:
                                logging.debug("successfully followed path %s", path)
                                cave_ = new_cave
                                moves = new_moves
                                target_done = True
                            elif replan and new_cave.end_state != cave.END_STATE_LOSE:
                                logging.debug("something changed, replanning")
                                cave_ = new_cave
                                moves = new_moves
                            else:
                                need_panic = True
                        else:
                            need_panic = True

                        if need_panic:
                            # no strategy works, just move a step and see what happens
                            for m in panic_moves[panic_count:]:
                                logging.debug("making panic move: %s", m)
                                panic_count += 1
                                rpx, rpy = cave_._robot_pos
                                new_cave, new_moves, success, replan = self.move(cave_, moves, m)
                                if (success or replan) and not new_cave.end_state == cave.END_STATE_LOSE:
                                    cave_ = new_cave
                                    moves = new_moves
                                    break
                            else:
                                # TODO: replan on a higher level
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
    s = AStarSolver(False)
    c1, route1, success, replan = s.solve(c)
    s = AStarSolver(True)
    c2, route2, success, replan = s.solve(c)
    if c1.score > c2.score:
        print route1
    else:
        print route2
    logging.info("scores: %d", c1.score)
    logging.info("end state 1: %s", c1.end_state)
    logging.info("score 2: %d", c2.score)
    logging.info("end state 2: %s", c2.end_state)

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
