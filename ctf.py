import pygame 
from pygame.locals import *
from pygame.color import *
import pymunk
import math
from pygame import mixer
import os
import sys

#----- Initialisation -----#

#-- Initialise the display
pygame.init()
pygame.display.set_mode()
pygame.mixer.init()
main_dir = os.path.split(os.path.abspath(__file__))[0]

#-- Initialise the clock
clock = pygame.time.Clock()

#-- Initialise the physics engine
space = pymunk.Space()
space.gravity = (0.0, 0.0)
space.damping = 0.1 # Adds friction to the ground for all objects


#-- Import from the ctf framework
import ai
import images
import gameobjects
import maps

#-- Constants
FRAMERATE = 50

#-- Variables
#   Define the current level
current_map         = maps.map0

#-- Choose type of map
if '--map' in sys.argv:
    if '--json' in sys.argv:
        current_map = maps.create_map_jon(sys.argv[5])

#   List of all game objects
game_objects_list   = []
tanks_list          = []
ai_list             = []

# List/dictionary for win conditions
round_counter       = 0


point_dict          = {}

#-- Resize the screen to the size of the current level
screen = pygame.display.set_mode(current_map.rect().size)

#-- Generate the background
background = pygame.Surface(screen.get_size())

#-- Create and add boarders

space = pymunk.Space()
static_lines = [
    pymunk.Segment(space.static_body, (0,0), (0, current_map.height), 0),
    pymunk.Segment(space.static_body, (0, current_map.height), (current_map.width ,current_map.height), 0),
    pymunk.Segment(space.static_body, (current_map.width ,0), (current_map.width, current_map.height), 0),
    pymunk.Segment(space.static_body, (0,0), (current_map.width,0), 0)
]

for line in static_lines:
    line.elasticity = 1
    line.friction = 1

space.add(*static_lines)

#-- Create collisions
def collision_bullet_nondestr(arb, space, data):
    """Collision with bullet and none destructable object."""
    _bullet = arb.shapes[0]
    space.remove(_bullet, _bullet.body)
    if _bullet.parent in game_objects_list:
        game_objects_list.remove(_bullet.parent)
    return True

def collision_bullet_destr(arb, space, data):
    """Collision with bullet and destructable object."""
    _bullet = arb.shapes[0]
    _box = arb.shapes[1]
    space.remove(_box, _box.body)
    game_objects_list.remove(_box.parent)
    space.remove(_bullet, _bullet.body)
    if _bullet.parent in game_objects_list:
        game_objects_list.remove(_bullet.parent)
    return True
    

def collision_bullet_tank(arb, space, data):
    """Collision with bullet and tank."""
    _bullet = arb.shapes[0]
    _tank = arb.shapes[1]
    _tank.parent.drop_flag(flag)
    index = tanks_list.index(_tank.parent)
    space.remove(_bullet, _bullet.body)
    if _bullet.parent in game_objects_list:
        game_objects_list.remove(_bullet.parent)
    space.remove(_tank, _tank.body)
    game_objects_list.remove(_tank.parent)
    tanks_list.remove(_tank.parent)
    recreate_tank(index) 
    return True

def collision_bullet_bullet(arb, space, data):
    """Collision with bullet and bullet"""
    _bullet = arb.shapes[0]
    space.remove(_bullet, _bullet.body)
    if _bullet.parent in game_objects_list:
        game_objects_list.remove(_bullet.parent)
    return True

def collision_handlers():
    # Collision with tank
    handler = space.add_collision_handler(1,2)
    handler.begin = collision_bullet_tank
    # Collision with destructable box
    handler = space.add_collision_handler(1,4)
    handler.pre_solve = collision_bullet_destr
    # Collision with nondestructable boxes
    handler = space.add_collision_handler(1,3)
    handler.pre_solve = collision_bullet_nondestr
    # Collision with bullet
    handler = space.add_collision_handler(1,1)
    handler.pre_solve = collision_bullet_bullet


def create_background():
    #   Copy the grass tile all over the level area
    for x in range(0, current_map.width):
        for y in range(0,  current_map.height):
            # The call to the function "blit" will copy the image
            # contained in "images.grass" into the "background"
            # image at the coordinates given as the second argument
            background.blit(images.grass,  (x*images.TILE_SIZE, y*images.TILE_SIZE))


def create_boxes():
#-- Create the boxes
    for x in range(0, current_map.width):
        for y in range(0,  current_map.height):
            # Get the type of boxes
            box_type  = current_map.boxAt(x, y)
            # If the box type is not 0 (aka grass tile), create a box
            if(box_type != 0):
                # Create a "Box" using the box_type, aswell as the x,y coordinates,
                # and the pymunk space
                box = gameobjects.get_box_with_type(x, y, box_type, space)
                game_objects_list.append(box)


def create_bases():
    #-- Create the bases
    for i in range(0, len(current_map.start_positions)):
        # The position of bases is the startpositins of the tanks.
        pos = current_map.start_positions[i]
        base = gameobjects.GameVisibleObject(pos[0], pos[1], images.bases[i])
        game_objects_list.append(base)

def create_ai():
    """
    Function to create ai tanks. 
    The amount of ai tanks depends on players and game mode.
    """
    if '--singleplayer' in sys.argv:
        for tank in tanks_list[1:]:
            aitank = ai.Ai(tank, game_objects_list, tanks_list, space, current_map)
            ai_list.append(aitank)
    elif '--multiplayer' in sys.argv:
        for tank in tanks_list[2:]:
            aitank = ai.Ai(tank, game_objects_list, tanks_list, space, current_map)
            ai_list.append(aitank)


def create_tanks():
    #-- Create the tanks
    # Loop over the starting poistion
    for i in range(0, len(current_map.start_positions)):
        # Get the starting position of the tank "i"
        pos = current_map.start_positions[i]
        # Create the tank, images.tanks contains the image representing the tank
        tank = gameobjects.Tank(pos[0], pos[1], pos[2], images.tanks[i], space)
        # Add the tank to the list of tanks
        tanks_list.append(tank)
        game_objects_list.append(tank)
    
        create_ai()

def recreate_tank(index):
    """
    A function to respawn a tank if it has been destroyed.
    """
    # Gets the starting position from tanks index in tanks_list. 
    pos = current_map.start_positions[index]
    tank = gameobjects.Tank(pos[0], pos[1], pos[2], images.tanks[index], space)
    # Insert the tank at the same index as it were before in tanks_list.
    tanks_list.insert(index, tank)
    game_objects_list.append(tank)
    # Make sure all the tanks that are ais still are after respawn.
    create_ai()

#-- Create the flag
def create_flag():
    # Turn flag into global variable
    global flag
    flag = gameobjects.Flag(current_map.flag_position[0], current_map.flag_position[1])
    game_objects_list.append(flag)

def won():
    # If a tank has won remove everything and add it again.
    # -> a new round starts.
    space.remove(space.shapes, space.bodies)
    game_objects_list.clear()
    tanks_list.clear()
    ai_list.clear()
    create_objects()
    

def print_score():
    # Print out a scoreboard
    print("____SCORE____")
    for key in point_dict:
        print(key, ':', point_dict[key])

def print_wincond(timer):
    """ Function to display the wincondition """
    if '--first-to' in sys.argv:
        print('First to 5 points wins!', end = '\r')
    elif '--best-of' in sys.argv:
        print('Rounds left:', 5 - round_counter, end = '\r')
    elif '--time' in sys.argv:
        print('Time left:', (str(timer)).zfill(2), end = '\r')

def print_winner():
    """ Function to print out the winner """
    print("____WINNER____")
    # Get the highest score amongst the players.
    winner = max(point_dict.values())
    # Find the player with that score.
    for key in point_dict:
        if point_dict[key] == winner:
            print(key)

# Function to create all objects.
def create_objects():
    create_bases()
    create_boxes()
    create_tanks()
    create_flag()

# Define controls for player 1 and 2.
def p1_controls(event):
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_UP:
            tanks_list[0].accelerate()
        elif event.key == pygame.K_DOWN:
            tanks_list[0].decelerate()
        elif event.key == pygame.K_LEFT:
            tanks_list[0].turn_left()
        elif event.key == pygame.K_RIGHT:
            tanks_list[0].turn_right()
        elif event.key == pygame.K_RETURN:
            tanks_list[0].shoot(space, game_objects_list)  
    elif event.type == pygame.KEYUP:
        if event.key == pygame.K_UP or pygame.K_DOWN:
            tanks_list[0].stop_moving()
            if event.key == pygame.K_LEFT or pygame.K_RIGHT:
                tanks_list[0].stop_turning()    
        

def p2_controls(event):
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_w:
            tanks_list[1].accelerate()
        elif event.key == pygame.K_s:
            tanks_list[1].decelerate()
        elif event.key == pygame.K_a:
            tanks_list[1].turn_left()
        elif event.key == pygame.K_d:
            tanks_list[1].turn_right()
        elif event.key == pygame.K_SPACE:
            tanks_list[1].shoot(space, game_objects_list)
    elif event.type == pygame.KEYUP:
        if event.key == pygame.K_w or pygame.K_s:
            tanks_list[1].stop_moving()
            if event.key == pygame.K_a or pygame.K_d:
                tanks_list[1].stop_turning()


#----- Main Loop -----#
def main_loop():
#-- Control whether the game run
    running = True

    skip_update = 0
    
    # Time variable used to create timer.
    t1 = 0
    
    # Add 0 to the round counter
    round_counter = 0

    # Add a key and 0 for each tank.
    for ind in range(len(tanks_list)):
        player = 'Player ' + str(ind+1)
        point_dict[player] = 0

    while running:
    #-- Handle the events
        
        # Add 1 to t1
        t1 = t1 + 1
        # Start time
        t2 = 10
        # Create timer
        timer = t2-(t1//FRAMERATE)
        # Print out the wincondition
        print_wincond(timer)

        tanks_list[0].update()
        tanks_list[1].update()
        for event in pygame.event.get():
        # Check if we receive a QUIT event (for instance, if the user press the
        # close button of the window) or if the user press the escape key.
    
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False

            # Depending on game mode, run functions for player controls.
            if '--singleplayer' in sys.argv:
                p1_controls(event)
            elif '--multiplayer' in sys.argv:
                p1_controls(event)
                p2_controls(event)

        for ai in ai_list:
            ai.decide()

        for tank in tanks_list:
        # Reset game if a tank has won and print score
            if tank.has_won():
                index = tanks_list.index(tank)
                won()
                # Add 1 to the round counter
                round_counter = round_counter + 1
                # Give the player that won this round a point.
                point_dict['Player ' + str(index+1)] = point_dict['Player ' + str(index+1)] + 1
                print('')
                print_score()

            # Try to grab flag    
            tank.try_grab_flag(flag)

        # Enable win condition depending on what command is written.
        if '--first-to' in sys.argv:
            for key in point_dict:
                if point_dict[key] == 5:
                    print_winner()
                    running = False
        elif '--best-of' in sys.argv:
            if round_counter == 5:
                print_winner()
                running = False
        elif '--time' in sys.argv:
            if timer == 0:
                print_winner()
                running = False


        #-- Update physics
        if skip_update == 0:
        # Loop over all the game objects and update their speed in function of their
        # acceleration.
            for obj in game_objects_list:
                obj.update()
                skip_update = 2
        else:
            skip_update -= 1

        #   Check collisions and update the objects position
        space.step(1 / FRAMERATE)

        #   Update object that depends on an other object position (for instance a flag)
        for tank in tanks_list:
            tank.post_update()

        for obj in game_objects_list:
            obj.post_update()

        #-- Update Display

        # Display the background on the screen
        screen.blit(background, (0, 0))

        # Update the display of the game objects on the screen
        for obj in game_objects_list:
            obj.update_screen(screen)

        #   Redisplay the entire screen (see double buffer technique)
        pygame.display.flip()

        #   Control the game framerate
        clock.tick(FRAMERATE)

collision_handlers()
create_background()
create_objects()
main_loop()


