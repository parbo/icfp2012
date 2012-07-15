#!/usr/bin/python
import unittest

import cave

ROUTE = 'DDDLLLLLLURRRRRRRRRRRRDDDDDDDLLLLLLLLLLLDDDRRRRRRRRRRRD'
R = cave.MOVE_RIGHT
L = cave.MOVE_LEFT
U = cave.MOVE_UP
D = cave.MOVE_DOWN

def apply_moves(cave, moves):
    c = cave
    for move in moves:
        c = c.move(move)
    return c

class TestCave(unittest.TestCase):
    def setUp(self):
        self.cave = cave.Cave()
        cave_map = open('../maps/task_desc.map', 'r')
        self.cave.load_file(cave_map)
        cave_map.seek(0)
        self.cave_str = cave_map.read().strip('\n\r')
        cave_map.close()
        self.water_cave = cave.Cave()
        cave_map = open('../maps/flood1.map', 'r')
        self.water_cave.load_file(cave_map)
        cave_map.close()
        self.beard_cave = cave.Cave()
        cave_map = open('../maps/beard1.map', 'r')
        self.beard_cave.load_file(cave_map)
        cave_map.close()
        self.trampoline_cave = cave.Cave()
        cave_map = open('../maps/trampoline1.map', 'r')
        self.trampoline_cave.load_file(cave_map)
        cave_map.close()
        self.horock_cave = cave.Cave()
        cave_map = open('../maps/horock1.map', 'r')
        self.horock_cave.load_file(cave_map)
        cave_map.close()
        self.unmovable_rock_cave = cave.Cave()
        cave_map = open('../maps/test_unmovable_rocks.map', 'r')
        self.unmovable_rock_cave.load_file(cave_map)
        cave_map.close()
        
    def test_load(self):
        self.assertEqual(str(self.cave), self.cave_str)
        self.assertEqual(self.cave.water_resistance, cave.DEFAULT_WATER_RESISTANCE)
        self.assertEqual(self.cave.water_level, cave.DEFAULT_WATER_LEVEL)
        self.assertEqual(self.cave.flood_rate, cave.DEFAULT_FLOOD_RATE)
        self.assertEqual(self.water_cave.water_resistance, 5)
        self.assertEqual(self.water_cave.water_level, 0)
        self.assertEqual(self.water_cave.flood_rate, 8)
        
    def test_size(self):
        self.assertEqual(self.cave.size, (15, 15))
        
    def test_at(self):
        self.assertEqual(self.cave.at(0, 0), cave.CAVE_WALL)
        self.assertEqual(self.cave.at(1, 1), cave.CAVE_DIRT)
        self.assertEqual(self.cave.at(7, 13), cave.CAVE_ROBOT)
        self.assertEqual(self.cave.at(13, 0), cave.CAVE_CLOSED_LIFT)
        self.assertEqual(self.cave.at(10, 1), cave.CAVE_EMPTY)
        self.assertEqual(self.cave.at(2, 3), cave.CAVE_LAMBDA)
        self.assertEqual(self.cave.at(-1, -1), cave.CAVE_WALL)
        self.assertEqual(self.cave.at(*self.cave.size), cave.CAVE_WALL)
        
    def test_move(self):
        next = [self.cave.move(cave.MOVE_WAIT)]
        self.assertEqual(str(self.cave), str(next[0]))
        next.append(next[0].move(cave.MOVE_DOWN))
        self.assertEqual(str(self.cave), str(next[0]))
        self.assertEqual(next[-1]._robot_pos, (7, 12))
        self.assertEqual(next[-1].at(7, 13), cave.CAVE_EMPTY)
        
    def test_rock_movement(self):
        move = [L, L, L, D, R, D, L, L, L, L]
        rock = [0, 0, 0, 0, 1, 0, 0, 1, 1, 1]
        for m, r in zip(move, rock):
            self.cave = self.cave.move(m)
            self.assertEqual(bool(r), self.cave.rock_movement)
            
    def test_next_stable(self):
        # Test that function returns when cave is completed.
        move = [L, L, L, D, D]
        cv = apply_moves(self.cave, move)
        self.assertTrue(cv.rock_movement)
        stable_cave, n = cv.next_stable()
        self.assertEqual(n, 0)
        # Test normal case.
        move = [D, D, D, D, D, D, R, R, R, R, U, U, U, R]
        cv = apply_moves(self.cave, move)
        self.assertTrue(cv.rock_movement)
        stable_cave, n = cv.next_stable()
        self.assertEqual(n, 4)
        
    def test_route(self):
        self.cave = apply_moves(self.cave, ROUTE[:-1])
        self.assertEqual(self.cave._lambda_count, 0)
        self.assertTrue(self.cave._lift_open)
        self.assertEqual(self.cave.at(13, 1), cave.CAVE_ROBOT)
        self.assertEqual(self.cave.at(13, 0), cave.CAVE_OPEN_LIFT)
        self.cave = self.cave.move(ROUTE[-1])
        self.assertEqual(self.cave.at(13, 0), cave.CAVE_ROBOT)
        self.assertTrue(self.cave.completed)
        self.assertEqual(self.cave.end_state, cave.END_STATE_WIN)
        self.assertEqual(self.cave.water_level, cave.DEFAULT_WATER_LEVEL)
        
    def test_flooding(self):
        initial_level = self.water_cave.water_level
        for i in range(self.water_cave.flood_rate - 1):
            self.water_cave = self.water_cave.move(cave.MOVE_WAIT)
            self.assertEqual(self.water_cave.water_level, initial_level)
        self.water_cave = self.water_cave.move(cave.MOVE_WAIT)
        self.assertEqual(self.water_cave.water_level, initial_level + 1)
        
    def test_drowning(self):
        while self.water_cave._robot_pos[1] > self.water_cave.water_level:
            self.water_cave = self.water_cave.move(cave.MOVE_WAIT)
        for i in range(self.water_cave.water_resistance - 1):
            self.water_cave = self.water_cave.move(cave.MOVE_WAIT)
        self.assertFalse(self.water_cave.completed)
        self.water_cave = self.water_cave.move(cave.MOVE_WAIT)
        self.assertTrue(self.water_cave.completed)
        self.assertEqual(self.water_cave.end_state, cave.END_STATE_LOSE)
        
    def test_collect_razor(self):
        self.assertEqual(self.beard_cave.razors_carried, 0)
        move = [R, D, L, L, D]
        cv = apply_moves(self.beard_cave, move)
        self.assertEqual(cv.razors_carried, 1)
        
    def test_beard_growth(self):
        self.assertEqual(self.beard_cave.at(4, 2), cave.CAVE_BEARD)
        self.assertEqual(self.beard_cave.at(4, 1), cave.CAVE_EMPTY)
        self.assertEqual(self.beard_cave.at(5, 1), cave.CAVE_EMPTY)
        cv = apply_moves(self.beard_cave, (self.beard_cave.beard_growth_rate - 1) * cave.MOVE_WAIT)
        self.assertEqual(cv.at(4, 2), cave.CAVE_BEARD)
        self.assertEqual(cv.at(4, 1), cave.CAVE_EMPTY)
        self.assertEqual(cv.at(5, 1), cave.CAVE_EMPTY)
        cv = cv.move(cave.MOVE_WAIT)
        self.assertEqual(cv.at(4, 2), cave.CAVE_BEARD)
        self.assertEqual(cv.at(4, 1), cave.CAVE_BEARD)
        self.assertEqual(cv.at(5, 1), cave.CAVE_BEARD)
        
    def test_shave(self):
        move = [R, R, D, D, D, D, R, D]
        cv = apply_moves(self.beard_cave, move)
        cv = apply_moves(cv, (self.beard_cave.beard_growth_rate) * cave.MOVE_WAIT)
        self.assertEqual(cv.at(5, 2), cave.CAVE_ROBOT)
        self.assertEqual(cv.at(4, 3), cave.CAVE_BEARD)
        self.assertEqual(cv.at(5, 3), cave.CAVE_BEARD)
        self.assertEqual(cv.at(4, 2), cave.CAVE_BEARD)
        self.assertEqual(cv.at(4, 1), cave.CAVE_BEARD)
        self.assertEqual(cv.at(5, 1), cave.CAVE_BEARD)
        cv = cv.move(cave.MOVE_SHAVE)
        # No razor -> shave will fail.
        self.assertEqual(cv.at(5, 2), cave.CAVE_ROBOT)
        self.assertEqual(cv.at(4, 3), cave.CAVE_BEARD)
        self.assertEqual(cv.at(5, 3), cave.CAVE_BEARD)
        self.assertEqual(cv.at(4, 2), cave.CAVE_BEARD)
        self.assertEqual(cv.at(4, 1), cave.CAVE_BEARD)
        self.assertEqual(cv.at(5, 1), cave.CAVE_BEARD)
        cv.razors_carried = 1
        cv = cv.move(cave.MOVE_SHAVE)
        self.assertEqual(cv.at(5, 2), cave.CAVE_ROBOT)
        self.assertEqual(cv.at(4, 3), cave.CAVE_EMPTY)
        self.assertEqual(cv.at(5, 3), cave.CAVE_EMPTY)
        self.assertEqual(cv.at(4, 2), cave.CAVE_EMPTY)
        self.assertEqual(cv.at(4, 1), cave.CAVE_EMPTY)
        self.assertEqual(cv.at(5, 1), cave.CAVE_EMPTY)
        
    def test_trampoline(self):
        self.assertEqual(self.trampoline_cave.at(3, 3), 'A')
        self.assertEqual(self.trampoline_cave.at(8, 3), 'B')
        self.assertEqual(self.trampoline_cave.at(15, 2), 'C')
        self.assertEqual(self.trampoline_cave.at(15, 1), '1')
        self.assertEqual(self.trampoline_cave.at(5, 2), '2')
        move = [D, L, L]
        cv = apply_moves(self.trampoline_cave, move)
        self.assertEqual(cv.at(3, 3), cave.CAVE_ROCK)
        self.assertEqual(cv.at(8, 3), cave.CAVE_ROCK)
        self.assertEqual(cv.at(15, 2), 'C')
        self.assertEqual(cv.at(15, 1), cave.CAVE_ROBOT)
        self.assertEqual(cv.at(5, 2), '2')
        
    def test_lambda_rock(self):
        self.assertEqual(self.horock_cave.at(4, 3), cave.CAVE_DIRT)
        move = [R, R, R, R, R, U, U, R, R, L]
        cv = apply_moves(self.horock_cave, move)
        self.assertEqual(cv.at(4, 3), cave.CAVE_LAMBDA)
        
    def test_unmovable_rocks(self):
        unmovable = self.unmovable_rock_cave.find_unmovable_rocks()
        self.assertEqual(len(unmovable), 3)
        self.assertTrue((7, 1) in unmovable)
        self.assertTrue((8, 1) in unmovable)
        self.assertTrue((13, 6) in unmovable)
                
if __name__ == '__main__':
    #unittest.main()
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCave)
    unittest.TextTestRunner(verbosity=2).run(suite)
    