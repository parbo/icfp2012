import heapq

class PriorityQueue(object):
    def __init__(self):
        self.queue = []

    def push(self, prio, v):
        heapq.heappush(self.queue, (prio, v))

    def pop(self):
        return heapq.heappop(self.queue)

    def __contains__(self, val):
        for p, v in self.queue:
            if v == val:
                return True
        return False

    def __len__(self):
        return len(self.queue)

def astar(start, goal, g_fcn, h_fcn, find_neighbours_fcn):
    def reconstruct_path(came_from, current_node):
        if current_node in came_from:
            p = reconstruct_path(came_from, came_from[current_node])
            return p + (current_node,)
        else:
            return (current_node,)

    closed_list = set()
    open_list = PriorityQueue()
    open_list.push(h_fcn(start), start)
    g_score = {start : 0.0}
    came_from = {}
    while open_list:
        f, node = open_list.pop()
        if node == goal:
            return reconstruct_path(came_from, goal)
        closed_list.add(node)
        neighbours = find_neighbours_fcn(node)
        for neighbour in neighbours:
            if neighbour in closed_list:
                continue
            new_g = g_score[node] + g_fcn(node, neighbour)

            new_is_better = False
            if neighbour not in open_list:
                f = new_g + h_fcn(neighbour)
                open_list.push(f, neighbour)
                new_is_better = True
            elif new_g < g_score[neighbour]:
                new_is_better = True
            else:
                new_is_better = False

            if new_is_better:
                came_from[neighbour] = node
                g_score[neighbour] = new_g

    return tuple()


if __name__=="__main__":
    import math
    def testworld(world):
        world = [list(s) for s in world]
        def g(n1, n2):
            return 1
        def nf(w):
            def neighbours(n):
                x, y = n
                nb = []
                for dx, dy in [(-1, 0), (0, 1), (1, 0), (0, -1)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= ny < len(w) and 0 <= nx < len(w[0]):
                        if w[ny][nx] != "*":
                            nb.append((nx, ny))
                return nb
            return neighbours
        def hf(goal):
            def h(n):
                x, y = n
                gx, gy = goal
                return math.sqrt((x - gx)**2 + (y - gy)**2)
            return h
        def find(w, sym):
            for y, row in enumerate(w):
                for x , col in enumerate(row):
                    if col == sym:
                        return x, y
        start = find(world, "s")
        goal = find(world, "g")
        p = astar(start, goal, g, hf(goal), nf(world))
        for x, y in p[1:-1]:
            world[y][x] = "+"
        print "\n".join(["".join(row) for row in world])

    testworld(["**************************",
               "*                        *",
               "*                     s  *",
               "*                        *",
               "*     ********************",
               "*                        *",
               "*                        *",
               "***********   ************",
               "* g                      *",
               "*                        *",
               "**************************"])
    testworld(["**************************",
               "*                 s      *",
               "*                        *",
               "*                        *",
               "*     ********************",
               "*                        *",
               "*                        *",
               "***********   ************",
               "* g                      *",
               "*                        *",
               "**************************"])
    testworld(["**************************",
               "* s                      *",
               "*                        *",
               "*                        *",
               "*     ********************",
               "*                        *",
               "*                        *",
               "***********   ************",
               "*                        *",
               "*                   g    *",
               "**************************"])
