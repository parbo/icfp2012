import unittest

import cave

class TestCave(unittest.TestCase):
    def setUp(self):
        self.cave = cave.Cave()
        cave_map = open('../maps/contest10.map', 'r')
        self.cave.load_file(cave_map)
        cave_map.seek(0)
        self.cave_str = cave_map.read().strip('\n')
        cave_map.close()
        
    def test_load(self):
        self.assertEqual(str(self.cave), self.cave_str)
        
    def test_size(self):
        self.assertEqual(self.cave.size, (29, 24))
        
    def test_at(self):
        self.assertEqual(self.cave.at(0, 0), cave.CAVE_WALL)
        self.assertEqual(self.cave.at(1, 1), cave.CAVE_DIRT)
        self.assertEqual(self.cave.at(27, 1), cave.CAVE_ROBOT)
        self.assertEqual(self.cave.at(27, 0), cave.CAVE_CLOSED_LIFT)
        self.assertEqual(self.cave.at(9, 1), cave.CAVE_EMPTY)
        self.assertEqual(self.cave.at(5, 4), cave.CAVE_LAMBDA)
        self.assertEqual(self.cave.at(-1, -1), cave.CAVE_WALL)
        self.assertEqual(self.cave.at(*self.cave.size), cave.CAVE_WALL)
        
    def test_move(self):
        next = [self.cave.move(cave.MOVE_WAIT)]
        self.assertEqual(str(self.cave), str(next[0]))
        next.append(next[0].move(cave.MOVE_UP))
        self.assertEqual(str(self.cave), str(next[0]))
        self.assertEqual(next[-1]._robot_pos, (27, 2))
        self.assertEqual(next[-1].at(27, 1), cave.CAVE_EMPTY)
        
if __name__ == '__main__':
    #unittest.main()
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCave)
    unittest.TextTestRunner(verbosity=2).run(suite)
    