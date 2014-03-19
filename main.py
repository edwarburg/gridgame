import sys
from game.game import Grid, Game


def pretty_print(grid):
    print str(grid)

dirs = {
    "h" : Grid.LEFT,
    "j" : Grid.DOWN,
    "k" : Grid.UP,
    "l" : Grid.RIGHT,
}

def get_dir(dir_str):
    return dirs.get(dir_str, None)

def main(width=4, height=4, goal=2048, intial_value=2):
    game = Game(int(width), int(height), int(goal), int(intial_value))
    game.start()

    while True:
        try:
            pretty_print(game.grid)

            line = raw_input("> ").strip().lower()

            if line == "q" or line == "quit":
                print "bye"
                return

            dir_ = get_dir(line)

            if dir_ is None:
                print "options: %s, q" % (", ".join(sorted(dirs.keys())))
                continue

            game.slam(dir_)

            if game.is_over():
                pretty_print(game.grid)

                if game.goal_met():
                    print "You won! Yay!"
                else:
                    print "Game over! You suck!"
                return

        except KeyboardInterrupt:
            print
            return

main(*sys.argv[1:])