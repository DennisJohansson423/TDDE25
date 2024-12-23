import math
import pymunk
from pymunk import Vec2d
import gameobjects
from collections import defaultdict, deque
import maps

# NOTE: use only 'map0' during development!

MIN_ANGLE_DIF = math.radians(3) # 3 degrees, a bit more than we can turn each tick

def angle_between_vectors(vec1, vec2):
    """ 
    Since Vec2d operates in a cartesian coordinate space we have to
    convert the resulting vector to get the correct angle for our space.
    """
    vec = vec1 - vec2 
    vec = vec.perpendicular()
    return vec.angle

def periodic_difference_of_angles(angle1, angle2): 
    return (angle1 % (2*math.pi)) - (angle2 % (2*math.pi))


class Ai:
    """ 
    A simple ai that finds the shortest path to the target using 
    a breadth first search. Also capable of shooting other tanks and or wooden
    boxes. 
    """

    def __init__(self, tank,  game_objects_list, tanks_list, space, currentmap):
        self.tank               = tank
        self.game_objects_list  = game_objects_list
        self.tanks_list         = tanks_list
        self.space              = space
        self.currentmap         = currentmap
        self.flag = None
        self.MAX_X = currentmap.width - 1 
        self.MAX_Y = currentmap.height - 1

        self.allow_metalbox = False
        self.path = deque()
        self.move_cycle = self.move_cycle_gen()
        self.update_grid_pos()

    def update_grid_pos(self):
        """This should only be called in the beginning, or at the end of a move_cycle."""
        self.grid_pos = self.get_tile_of_position(self.tank.body.position)

    def decide(self):
        """ Main decision function that gets called on every tick of the game. """
        self.maybe_shoot()
        next(self.move_cycle)

    def maybe_shoot(self):
        """ 
        Makes a raycast query in front of the tank. If another tank
        or a wooden box is found, then we shoot. 
        """
        # Get the diagonal of the map using pythagorean theroem
        diagonal = ((self.currentmap.width**2) + (self.currentmap.height**2))
        # Start in front of tank
        start = self.tank.body.position[0]+(math.cos(self.tank.body.angle+math.radians(90)))*0.5, \
                self.tank.body.position[1]+(math.sin(self.tank.body.angle+math.radians(90)))*0.5
        # End is the longest possible distance from a tank to a boarder in the map.
        end = self.tank.body.position[0]+(math.cos(self.tank.body.angle+math.radians(90)))* diagonal, \
                self.tank.body.position[1]+(math.sin(self.tank.body.angle+math.radians(90)))* diagonal
        object = self.space.segment_query_first(start, end, 0, pymunk.ShapeFilter())

        if object != None:
            if hasattr(object, 'shape'):
                if hasattr(object.shape, 'parent'):
                    if isinstance(object.shape.parent, gameobjects.Tank):
                        self.tank.shoot(self.space, self.game_objects_list)
                    elif isinstance(object.shape.parent, gameobjects.Box):
                        if object.shape.parent.destructable:
                            self.tank.shoot(self.space, self.game_objects_list)

    def move_cycle_gen(self):
        """ 
        A generator that iteratively goes through all the required steps
        to move to our goal.
        """ 
        while True:
            self.update_grid_pos()
            shortest_path = self.find_shortest_path()
            # If no shortest path is found, allow metal boxes.
            if not shortest_path:
                self.allow_metalbox = True
                yield
                continue # Start from the top of our cycle
            self.allow_metalbox = False
            next_coord = shortest_path.popleft()
            yield
            target_angle = angle_between_vectors(self.tank.body.position, next_coord + Vec2d(0.5, 0.5))
            # Difference between the tanks angle and the target angle.
            diff_angle = periodic_difference_of_angles(self.tank.body.angle, target_angle)

            # Depending on the angle difference, turn the shortest way.
            if diff_angle < -math.pi:
                self.tank.turn_left()
                yield
            elif 0 > diff_angle > -math.pi:
                self.tank.turn_right()
                yield
            elif math.pi > diff_angle > 0:
                self.tank.turn_left()
                yield
            else:
                self.tank.turn_right()
                yield
            
            if abs(diff_angle) >= MIN_ANGLE_DIF:
                self.tank.stop_moving()

            while abs(diff_angle) >= MIN_ANGLE_DIF:
                diff_angle = periodic_difference_of_angles(self.tank.body.angle, target_angle)
                yield
            
            self.tank.stop_turning()
            self.tank.accelerate()
    
            yield
            continue

    move_cycle = move_cycle_gen
    
    def find_shortest_path(self):
        """ 
        A simple Breadth First Search using integer coordinates as our nodes.
        Edges are calculated as we go, using an external function.
        """
        shortest_path = []
        start = self.grid_pos
        queue = deque()
        queue.append(start)
        visited_nodes = set(start.int_tuple)
        node_tree = {}

        while len(queue) > 0:
            node = queue.popleft()
            if node == self.get_target_tile():
                while node != start:
                    shortest_path.append(node)
                    parent = node_tree[node.int_tuple]
                    node = parent
                shortest_path.reverse()
                return deque(shortest_path)
            for neighbour in self.get_tile_neighbors(node):
                if neighbour.int_tuple not in visited_nodes:
                    queue.append(neighbour)
                    node_tree[neighbour.int_tuple] = node
                    visited_nodes.add(neighbour.int_tuple)

        return deque(shortest_path)
            
    def get_target_tile(self):
        """ 
        Returns position of the flag if we don't have it. If we do have the flag,
        return the position of our home base.
        """
        if self.tank.flag != None:
            x, y = self.tank.start_position
        else:
            self.get_flag() # Ensure that we have initialized it.
            x, y = self.flag.x, self.flag.y
        return Vec2d(int(x), int(y))

    def get_flag(self):
        """ 
        This has to be called to get the flag, since we don't know
        where it is when the Ai object is initialized.
        """
        if self.flag is None:
        # Find the flag in the game objects list
            for obj in self.game_objects_list:
                if isinstance(obj, gameobjects.Flag):
                    self.flag = obj
                    break
        return self.flag

    def get_tile_of_position(self, position_vector):
        """Converts and returns the float position of our tank to an integer position."""
        x, y = position_vector
        return Vec2d(int(x), int(y))

    def get_tile_neighbors(self, coord_vec):
        """ 
        Returns all bordering grid squares of the input coordinate.
        A bordering square is only considered accessible if it is grass
        or a wooden box.
        """
        neighbors = []  # Find the coordinates of the tiles' four neighbors
        position = self.get_tile_of_position(coord_vec)
        neighbors.append(position + Vec2d(-1, 0))
        neighbors.append(position + Vec2d(1, 0))
        neighbors.append(position + Vec2d(0, -1))
        neighbors.append(position + Vec2d(0, 1))

        return filter(self.filter_tile_neighbors, neighbors)


    def filter_tile_neighbors (self, coord):
        """
        Filters neighbor tiles. Grass and wooden box always returns true.
        Metalbox only returns true if metalbox is allowed.
        """
        if coord[0] <= self.MAX_X and coord[0] >= 0 and coord[1] <= self.MAX_Y and coord[1] >= 0:
            if self.currentmap.boxAt(int(coord[0]), int(coord[1])) == 0 or self.currentmap.boxAt(int(coord[0]), int(coord[1])) == 2:
                return True
            if self.currentmap.boxAt(int(coord[0]), int(coord[1])) == 3:
                return self.allow_metalbox
            else:
                return False
        
        


SimpleAi = Ai # Legacy
