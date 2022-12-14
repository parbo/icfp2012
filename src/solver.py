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
    def __init__(self, pos, obj, path):
        self.pos = pos
        self.obj = obj
        self.path = path

    def __str__(self):
        return "pos: %s, obj: %s, path: %s"%(self.pos, self.obj, self.path)

class Solver(object):
    def _signal_handler(self, signal, frame):
        raise SolverInterrupted()

    def __init__(self):
        self.interrupted = False
        signal.signal(signal.SIGINT, self._signal_handler)

    def solve(self, cave):
        """Returns a route"""

def get_lambda_comparer(cave_, rpos, lpos, from_below):
    rpx, rpy = rpos
    lpx, lpy = lpos
    def compare(p1, p2):
        dx1 = abs(rpx - p1[0])
        dy1 = abs(rpy - p1[1])
        dx2 = abs(rpx - p2[0])
        dy2 = abs(rpy - p2[1])
        if from_below:
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

class AStarSolver(Solver):
    def __init__(self, from_below):
        Solver.__init__(self)
        self._from_below = from_below
        self._failed_targets = set()
        self._bad_rocks = None
        self.visited = {}

    def find_movable_rocks(self, cave_, pos=None):
        w, h = cave_.size
        rocks = self.find_stuff(cave_, cave.CAVE_ROCK)
        rocks.extend(self.find_stuff(cave_, cave.CAVE_LAMBDA_ROCK))
        movable_rocks = []
        for x, y in rocks:
            def movable(rx, ry):
                return (cave_.at(rx-1, ry) in (cave.CAVE_DIRT, cave.CAVE_RAZOR, cave.CAVE_EMPTY) or cave_.at(rx+1, ry) in (cave.CAVE_DIRT, cave.CAVE_RAZOR, cave.CAVE_EMPTY))
            possible = movable(x, y) or (cave_.at(x, y-1) in (cave.CAVE_DIRT, cave.CAVE_RAZOR) and movable(x, y-1))
            if possible:
                movable_rocks.append((x, y))
        if pos is None:
            pos = cave_._robot_pos
        rpx, rpy = pos
        movable_rocks.sort(get_lambda_comparer(cave_, pos, cave_._lift_pos, self._from_below))
        return movable_rocks

    def find_path_intersecting_rocks(self, cave_, lambdas):
        c = cave_.clone()
        w, h = c.size
        # remove rocks
        for y in range(h):
            for x in range(w):
                if c.at(x, y) in cave.CAVE_ANY_ROCK:
                    c.set(x, y, cave.CAVE_EMPTY)
        # find path
        intersecting = {}
        for lmb in lambdas:
            f, path = c.find_path(lmb)
            # walk path to see if there is a rock in the way
            for pos in path:
                if cave_.at(*pos) in cave.CAVE_ANY_ROCK:
                    intersecting.setdefault(lmb, []).append(pos)
        return intersecting

    def find_lambdas(self, cave_, pos=None):
        w, h = cave_.size
        lambdas = []
        for x, y in cave_.lambdas:
            lambdas.append((x, y))
        if pos is None:
            pos = cave_._robot_pos
        rpx, rpy = pos
        lambdas.sort(get_lambda_comparer(cave_, pos, cave_._lift_pos, self._from_below))
        return lambdas

    def find_lambda_rocks(self, cave_, pos=None):
        w, h = cave_.size
        lambdas = []
        for x, y in cave_.lambda_rocks:
            possible = (cave_.at(x, y - 1) in (cave.CAVE_DIRT, cave.CAVE_RAZOR) and (cave_.at(x-1, y - 1) in (cave.CAVE_DIRT, cave.CAVE_RAZOR, cave.CAVE_EMPTY) or cave_.at(x+1, y - 1) in (cave.CAVE_DIRT, cave.CAVE_RAZOR, cave.CAVE_EMPTY)))
            if possible:
                lambdas.append((x, y))
        if pos is None:
            pos = cave_._robot_pos
        rpx, rpy = pos
        lambdas.sort(get_lambda_comparer(cave_, pos, cave_._lift_pos, self._from_below))
        return lambdas

    def move_success(self, cave_, expected):
        trampoline_id = cave_.trampoline_from_pos(expected)
        if trampoline_id is not None and trampoline_id in cave.CAVE_TRAMPOLINE_CHARS:
            expected = cave_.trampoline_target_pos(trampoline_id)
        return cave_._robot_pos == expected

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
                # do we need to shave?
                dx, dy = cave.DPOS[move]
                if cave_.at(rpx+dx, rpy+dy) == cave.CAVE_BEARD:
                    logging.debug("shave needed at %s", (rpx+dx, rpy+dy))
                    cave_, moves, step_success, step_replan = self.move(cave_, moves, cave.MOVE_SHAVE)
                    if step_replan:
                        replan = True
                        break

                # execute wanted move
                cave_, moves, step_success, step_replan = self.move(cave_, moves, move)
                if step_replan:
                    replan = True
                    break

            if cave_.completed:
                break
        success = self.move_success(cave_, p[-1])
        return cave_, moves, success, replan

    def move(self, cave_, moves, move):
        new_cave = cave_.move(move)
        dx, dy = cave.DPOS[move]
        rpx, rpy = cave_._robot_pos
        move_to = (rpx+dx, rpy+dy)
        success = False
        if move == cave.MOVE_SHAVE:
            shave_ok = False
            for x, y in cave.surrounding_squares(*move_to):
                if cave_.at(x, y) == cave.CAVE_BEARD:
                    shave_ok = True
                    break
            if shave_ok:
                success = True
        else:
            success = self.move_success(new_cave, (rpx+dx, rpy+dy))
        if success:
            return new_cave, moves + move, success, new_cave.rock_movement
        else:
            return cave_, moves, success, cave_.rock_movement

    def exit_blocked(self, cave_, pos):
        return len(cave_.get_possible_robot_moves(pos)) == 0

    def move_rock_sideways(self, c, x, y):
        needed_pos = []
        # move to left
        if c.at(x-1, y) == cave.CAVE_EMPTY:
            needed_pos.append([(x+1, y), (x, y)])
        elif c.at(x-1, y+1) in (cave.CAVE_DIRT, cave.CAVE_RAZOR):
            needed_pos.append([(x-1, y), (x+1, y), (x, y)])
        # move to right
        if c.at(x+1, y) == cave.CAVE_EMPTY:
            needed_pos.append([(x-1, y), (x, y)])
        elif c.at(x+1, y) in (cave.CAVE_DIRT, cave.CAVE_RAZOR):
            needed_pos.append([(x+1, y), (x-1, y), (x, y)])
        return needed_pos

    def move_rock(self, c, x, y):
        # drop first?
        if c.at(x-1, y) in cave.CAVE_SOLID_CHARS and c.at(x+1, y) in cave.CAVE_SOLID_CHARS:
            needed_pos = []
            needed_move_pos = self.move_rock_sideways(c, x, y-1)
            for mp in needed_move_pos:
                needed_pos.append([(x, y-1)] + mp)
            return needed_pos
        else:
            return self.move_rock_sideways(c, x, y)

    def find_stuff(self, cave_, stuff):
        w, h = cave_.size
        stuffs = []
        for y in range(h):
            for x in range(w):
                if cave_.at(x, y) in stuff:
                    stuffs.append((x, y))
        return stuffs

    def assemble_target_list(self, cave_, curr, positions):
        tentative = []
        for pos in positions:
            if pos in self._failed_targets:
                logging.debug("pos %s has failed before, skipping", pos)
                return []
            f, p = cave_.find_path(pos, curr)
            if p:
                tentative.append(Target(pos, cave_.at(*pos), p))
                logging.debug("found path %s -> %s", curr, pos)
                curr = pos
            else:
                logging.debug("no path %s -> %s", curr, pos)
                break
        if len(tentative) == len(positions):
            return tentative
        return []

    def find_target_list(self, cave_):
        logging.debug("find new target(s)")
        # find some lambdas
        lambdas = self.find_lambdas(cave_)
        lambdas = lambdas[:10]

        # sort on path cost (lower is better)
        path_cost = {}
        for lmb in lambdas:
            f, p = cave_.find_path(lmb)
            if p:
                path_cost[lmb] = int(f)
            else:
                path_cost[lmb] = 10000000
        def lcmp(p1, p2):
            pl1 = path_cost[p1]
            pl2 = path_cost[p2]
            diff = pl1 - pl2
            # if same path length, take the one closest in y
            if diff == 0:
                rpx, rpy = cave_._robot_pos
                diff = abs(rpy - p1[1]) - abs(rpy - p2[1])
            return diff
        lambdas.sort(lcmp)

        # find stuff we have to clear to make an exit from those lambdas
        # throw away the ones we can't exit from
        unblockable = {}
        movable = {}
        maybe_movable = {}
        blocked = set()
        movable_rocks = self.find_movable_rocks(cave_)
        logging.debug("movable rocks: %s", movable_rocks)
        intersecting = self.find_path_intersecting_rocks(cave_, lambdas)
        logging.debug("intersecting lambda paths: %s", intersecting)
        for lmb in lambdas:
            x, y = lmb
            c = cave_
            if self.exit_blocked(c, (x, y)):
                if c.at(x-1, y) == cave.CAVE_ROCK and c.at(x-2, y) in cave.CAVE_REMOVABLE_CHARS:
                    unblockable[(x,y)] = (x-2, y)
                elif c.at(x+1, y) == cave.CAVE_ROCK and c.at(x+2, y) in cave.CAVE_REMOVABLE_CHARS:
                    unblockable[(x,y)] = (x+2, y)
                elif (cave_.at(x, y + 1) in cave.CAVE_ANY_ROCK and cave_.at(x - 1, y) in cave.CAVE_SOLID_CHARS and cave_.at(x + 1, y) in cave.CAVE_SOLID_CHARS):
                    if (x,y+1) in movable_rocks:
                        logging.debug("there is a movable rock at %s, figure out how to move it!", (x, y+1))
                        needed_pos = self.move_rock(c, x, y+1)
                        movable[(x,y)] = needed_pos
                elif lmb in intersecting:
                    # if a single rock is blocking, move as above
                    rocks = intersecting[lmb]
                    logging.debug("intersecting rocks for path to %s", lmb)
                    if len(rocks) == 1:
                        if rocks[0] in movable_rocks:
                            rx, ry = rocks[0]
                            needed_pos = self.move_rock(c, rx, ry)
                            movable[(x,y)] = needed_pos
                            logging.debug("intersecting rock is movable: %s", needed_pos)
                    else:
                        blocked.add((x, y))
                else:
                    blocked.add((x, y))
            else:
                if lmb in intersecting:
                    # if a single rock is blocking, move as above
                    rocks = intersecting[lmb]
                    logging.debug("intersecting rocks for path to %s", lmb)
                    for rock in rocks:
                        if rock in movable_rocks:
                            rx, ry = rock
                            rock_can_fall_from_left_above = c.at(rx-1, ry+1) in cave.CAVE_ANY_ROCK and c.at(rx-1, ry) in cave.CAVE_ANY_ROCK and c.at(rx, ry+1) == cave.CAVE_EMPTY
                            rock_can_fall_from_right_above = c.at(rx+1, ry+1) in cave.CAVE_ANY_ROCK and c.at(rx+1, ry) in cave.CAVE_ANY_ROCK and c.at(rx, ry+1) == cave.CAVE_EMPTY
                            rock_can_fall_from_straight_above = c.at(rx, ry+1) in cave.CAVE_ANY_ROCK
                            if not (rock_can_fall_from_straight_above or rock_can_fall_from_right_above or rock_can_fall_from_left_above):
                                needed_pos = self.move_rock(c, rx, ry)
                                maybe_movable[(x,y)] = needed_pos
                                logging.debug("intersecting rock is movable: %s", needed_pos)
                elif (x, y+1) in self._bad_rocks and c.at(x, y-1) == cave.CAVE_EMPTY:
                    logging.debug("there is a bad rock at %s, figure out how to move it!", (x, y+1))
                    needed_pos = self.move_rock(c, x, y+1)
                    movable[(x,y)] = needed_pos

        # assemble a list of targets with paths
        target_list = []
        for lmb in lambdas:
            if lmb in blocked:
                logging.debug("lambda %s is blocked, skipping", lmb)
                continue
            if lmb in self._failed_targets:
                logging.debug("lambda %s has failed before, skipping", lmb)
                continue
            # try to unblock
            if lmb in unblockable:
                positions = []
                positions.append(unblockable[lmb])
                positions.append(lmb)
                curr = cave_._robot_pos
                target_list = self.assemble_target_list(cave_, curr, positions)
                if target_list:
                    break
            # try to move
            if lmb in movable:
                possibly_movable = movable[lmb]
                for pm in possibly_movable:
                    # if we can't reach, don't add the lambda
                    if lmb not in intersecting:
                        pm.append(lmb)
                    curr = cave_._robot_pos
                    logging.debug("possible positions to move rock: %s", pm)
                    target_list = self.assemble_target_list(cave_, curr, pm)
                    if target_list:
                        logging.debug("rock can likely be moved")
                        break
                # also break out of outer loop
                if target_list:
                    break
            # just go to it
            positions = []
            positions.append(lmb)
            curr = cave_._robot_pos
            target_list = self.assemble_target_list(cave_, curr, positions)
            if target_list:
                break
            # try to move
            if lmb in maybe_movable:
                possibly_movable = maybe_movable[lmb]
                for pm in possibly_movable:
                    # if we can't reach, don't add the lambda
                    if lmb not in intersecting:
                        pm.append(lmb)
                    curr = cave_._robot_pos
                    logging.debug("possible positions to move rock: %s", pm)
                    target_list = self.assemble_target_list(cave_, curr, pm)
                    if target_list:
                        logging.debug("rock can likely be moved")
                        break
                # also break out of outer loop
                if target_list:
                    break

        if target_list:
            return target_list

        # try to get some lambda rocks
        lambda_rocks = self.find_lambda_rocks(cave_)
        lambda_rocks = lambda_rocks[:10]
        lrocktoremove = {}
        lrockendpos = []
        blocked = set()
        for rx, ry in lambda_rocks:
            for x, y in [(rx-1, ry-1), (rx+1, ry-1)]:
                c = cave_
                if not self.exit_blocked(c, (x, y)):
                    lrocktoremove[(x,y)] = (rx, ry-1)
                    lrockendpos.append((x, y))
                    break

        logging.debug("found %d possible lambda rocks", len(lrockendpos))

        # assemble a list of targets with paths
        target_list = []
        for lrk in lrockendpos:
            if lrk in blocked:
                logging.debug("lambda rock %s is blocked, skipping", lmb)
                continue
            if lrk in self._failed_targets:
                logging.debug("lambda rock %s has failed before, skipping", lmb)
                continue
            positions = []
            try:
                positions.append(lrocktoremove[lrk])
            except KeyError:
                pass
            positions.append(lrk)
            curr = cave_._robot_pos
            target_list = self.assemble_target_list(cave_, curr, positions)
            if target_list:
                break

        if target_list:
            return target_list

        # If no targets, wait until stable
        if cave_.rock_movement:
            logging.debug("no targets, wait until stable")
            return [Target(cave_._robot_pos, cave.CAVE_ROBOT, tuple())]

        # no suitable targets, try a trampoline
        targets = self.find_stuff(cave_, cave.CAVE_TARGET_CHARS)
        for t in targets:
            lambdas = self.find_lambdas(cave_, t)
            for l in lambdas:
                f, path = cave_.find_path(l, t)
                if path:
                    logging.debug("found path from target to lambda")
                    trampolines = cave_.target_trampolines(cave_.at(*t))
                    logging.debug("trampolines: %s", trampolines)
                    for tr in [cave_._trampoline_pos[tramp] for tramp in trampolines]:
                        if tr in self._failed_targets:
                            logging.debug("trampoline %s has failed before, skipping", tr)
                            continue
                        f, path = cave_.find_path(tr)
                        if path:
                            logging.debug("found a trampoline, taking it!")
                            return [Target(tr, cave_.at(*tr), path)]

        # no lambdas, find open lift
        if cave_.at(*cave_._lift_pos) == cave.CAVE_OPEN_LIFT:
            if cave_._lift_pos in self._failed_targets:
                logging.debug("lift %s failed before, skipping", cave_._lift_pos)
                return []
            f, p = cave_.find_path(cave_._lift_pos)
            if p:
                logging.debug("go to open lift")
                return [Target(cave_._lift_pos, cave_.at(*cave_._lift_pos), p)]
            else:
                logging.debug("no path to open lift")
        else:
            logging.debug("lift not open")
        # no path
        return []

    def solve(self, cave_):
        moves = ""
        panic_moves = [cave.MOVE_UP, cave.MOVE_LEFT, cave.MOVE_RIGHT, cave.MOVE_DOWN, cave.MOVE_SHAVE]
        panic_count = 0
        self._bad_rocks = cave_.find_bad_rocks()
        try:
            while not cave_.completed:
                logging.debug("lambdas left: %d", cave_._lambda_count)
                if cave_.is_drowning:
                    return self.move(cave_, moves, cave.MOVE_ABORT)
                # find target list to traverse
                target_list = self.find_target_list(cave_)
                if not target_list:
                    logging.debug("no target list, aborting")
                    return self.move(cave_, moves, cave.MOVE_ABORT)
                for target in target_list:
                    if target.pos == cave_._robot_pos:
                        logging.debug("no move, just wait")
                        cave_, moves, success, replan = self.move(cave_, moves, cave.MOVE_WAIT)
                        continue
                    # reset panic count for new targets
                    self.panic_count = 0
                    target_done = False
                    target_fail = False
                    need_panic = False
                    path = target.path
                    replans = 0
                    while not target_done:
                        logging.debug("trying to get from %s to target %s, %s", cave_._robot_pos, target.pos, target.obj)
                        if path:
                            logging.debug("path: %s", path)
                            # move to it
                            new_cave, new_moves, success, replan = self.follow_path(cave_, moves, path)
                            if success and new_cave.end_state != cave.END_STATE_LOSE:
                                logging.debug("successfully followed path to %s", new_cave._robot_pos)
                                cave_ = new_cave
                                moves = new_moves
                                target_done = True
                            elif replan and new_cave.end_state != cave.END_STATE_LOSE and replans < 10:
                                logging.debug("something changed, replanning")
                                cave_ = new_cave
                                moves = new_moves
                                logging.debug("find path: %s -> %s", cave_._robot_pos, target.pos)
                                f, path = cave_.find_path(target.pos)
                                logging.debug("found path: %s", path)
                                replans += 1
                            else:
                                need_panic = True
                        else:
                            need_panic = True

                        if need_panic:
                            # no strategy works, just move a step and see what happens
                            for m in panic_moves[panic_count:]:
                                panic_count += 1
                                if cave_.robot_move_cost(m) < 0:
                                    continue
                                logging.debug("making panic move: %s", m)
                                rpx, rpy = cave_._robot_pos
                                new_cave, new_moves, success, replan = self.move(cave_, moves, m)
                                logging.debug("panic move: %s, %s", success, replan)
                                if (success or replan) and not new_cave.end_state == cave.END_STATE_LOSE:
                                    cave_ = new_cave
                                    moves = new_moves
                                    f, path = cave_.find_path(target.pos)
                                    break
                            else:
                                # replan on a higher level
                                logging.debug("panic didn't work, skipping target list")
                                target_fail = True
                                target_done = True
                    # if a target fails, we break out of the target_list loop
                    if target_fail:
                        logging.debug("add %s to failed targets", target.pos)
                        self._failed_targets.add(target.pos)
                        break
        except SolverInterrupted:
            logging.debug("solver interrupted, abort")
            self.interrupted = True
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
    solvers = [AStarSolver(False), AStarSolver(True)]
    solutions = []
    for s in solvers:
        logging.debug("starting solver..")
        new_c, route, success, replan = s.solve(c)
        solutions.append((new_c.score, new_c, route))
        if s.interrupted:
            logging.debug("abort calculations!")
            break

    solutions.sort(reverse=True)
    if solutions:
        print solutions[0][2],
    for s in solutions:
        score, new_c, route = s
        logging.info("score: %d", score)
        logging.info("end state: %s", new_c.end_state)


if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-f", "--file", dest="filename",
                      help="load map from FILE", metavar="FILE")
    parser.add_option("-l", "--log", dest="loglevel", type="int",
                      help="logging level", default=1000)
    options, args = parser.parse_args()
    main(options, args)
