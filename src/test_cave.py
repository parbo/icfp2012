import unittest

import cave

ROUTE = 'DDDLLLLLLURRRRRRRRRRRRDDDDDDDLLLLLLLLLLLDDDRRRRRRRRRRRD'

class TestCave(unittest.TestCase):
    def setUp(self):
        self.cave = cave.Cave()
        cave_map = open('../maps/task_desc.map', 'r')
        self.cave.load_file(cave_map)
        cave_map.seek(0)
        self.cave_str = cave_map.read().strip('\n')
        cave_map.close()
        
    def test_load(self):
        self.assertEqual(str(self.cave), self.cave_str)
        
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
        
if __name__ == '__main__':
    #unittest.main()
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCave)
    unittest.TextTestRunner(verbosity=2).run(suite)
    