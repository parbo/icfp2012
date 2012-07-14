#!/usr/bin/python
import unittest

import cave

ROUTE = 'DDDLLLLLLURRRRRRRRRRRRDDDDDDDLLLLLLLLLLLDDDRRRRRRRRRRRD'
R = cave.MOVE_RIGHT
L = cave.MOVE_LEFT
U = cave.MOVE_UP
D = cave.MOVE_DOWN

class TestCave(unittest.TestCase):
    def setUp(self):
        self.cave = cave.Cave()
        cave_map = open('../maps/task_desc.map', 'r')
        self.cave.load_file(cave_map)
        cave_map.seek(0)
        self.cave_str = cave_map.read().strip('\n')
        cave_map.close()
        self.water_cave = cave.Cave()
        cave_map = open('../maps/flood1.map', 'r')
        self.water_cave.load_file(cave_map)
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
        cv = self.cave
        for m in move:
            cv = cv.move(m)
        self.assertTrue(cv.rock_movement)
        stable_cave, n = cv.next_stable()
        self.assertEqual(n, 0)
        # Test normal case.
        cv = self.cave
        move = [D, D, D, D, D, D, R, R, R, R, U, U, U, R]
        for m in move:
            cv = cv.move(m)
        self.assertTrue(cv.rock_movement)
        stable_cave, n = cv.next_stable()
        self.assertEqual(n, 4)
        
    def test_route(self):
        for move in ROUTE[:-1]:
            self.cave = self.cave.move(move)
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
        
if __name__ == '__main__':
    #unittest.main()
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCave)
    unittest.TextTestRunner(verbosity=2).run(suite)
    