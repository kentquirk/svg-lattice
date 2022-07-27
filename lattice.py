import random
import sys
import argparse
from svg import Element, SVGDoc

DEBUG = False


class Direction(object):
    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y

    def invert(self):
        return Direction(x=-self.x, y=-self.y)

    def __eq__(self, __o: object) -> bool:
        return self.x == __o.x and self.y == __o.y

    def __str__(self):
        return f"({self.x}, {self.y})"

    def __repr__(self):
        return self.__str__()


# our grid is either 4 lines or 6 per square (changes the ratio of figure to ground)
# SIZE = 4
GRID = 12
S = GRID
SIZE = GRID
# "FAT", "THIN", "MEDIUM"
ASPECT = "MEDIUM"
if ASPECT == "THIN":
    A = 0
    B = 4
    C = 6
    D = 8
if ASPECT == "MEDIUM":
    A = 0
    B = 3
    C = 6
    D = 9
if ASPECT == "FAT":
    A = 0
    B = 2
    C = 6
    D = 10


NORTH = Direction(x=0, y=-1)
EAST = Direction(x=1, y=0)
SOUTH = Direction(x=0, y=1)
WEST = Direction(x=-1, y=0)

# the order of these matters later
directions = [NORTH, SOUTH, EAST, WEST]

# A map of these shortcut coordinates
# makes it easier to see how things work.
#
#    N1    N2
# W2 NW NC NE E1
#    WC    EC
# W1 SW SC SE E2
#    S2    S1

N1 = (B, A)
N2 = (D, A)
E1 = (S, B)
E2 = (S, D)
S1 = (D, S)
S2 = (B, S)
W1 = (A, D)
W2 = (A, B)
NC = (C, B)
EC = (D, C)
SC = (C, D)
WC = (B, C)
NW = (B, B)
NE = (D, B)
SW = (B, D)
SE = (D, D)


class Point(object):
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __hash__(self):
        return self.x << 16 + self.y

    def __eq__(self, __o: object) -> bool:
        return self.x == __o.x and self.y == __o.y

    def __str__(self):
        return f"({self.x}, {self.y})"

    def __repr__(self):
        return self.__str__()

    def clone(self):
        return Point(self.x, self.y)

    def scaled(self, scale, offset):
        return Point(self.x * scale + offset.x, self.y * scale + offset.y)

    def tween(self, other, frac):
        return Point(
            self.x + frac * (other.x - self.x),
            self.y + frac * (other.y - self.y),
        )


class Segment(object):
    def __init__(self, op="", fr=Point(0, 0), to=Point(0, 0), ctr=None):
        self.op = op
        self.fr = fr
        self.to = to
        self.ctr = ctr

    def __str__(self):
        return f"<{self.op} {self.fr}->{self.to}>"

    def __repr__(self):
        return self.__str__()


# strokes must be constructed in clockwise order so that they can be joined
class Stroke(object):
    def __init__(self, x, y):
        self.x = x * S
        self.y = y * S
        self.segments = []

    def __str__(self):
        return f"Stroke:({self.segments})"

    def __repr__(self):
        return self.__str__()

    def add_element(self, elt, start, end, ctr=None):
        self.segments.append(Segment(op=elt, fr=start, to=end, ctr=ctr))

    # expect start and end to be simple pairs here, and add them to our xy
    def add(self, elt, start, end, ctr=None):
        if ctr is not None:
            self.add_element(
                elt,
                start=Point(start[0] + self.x, start[1] + self.y),
                end=Point(end[0] + self.x, end[1] + self.y),
                ctr=Point(ctr[0] + self.x, ctr[1] + self.y),
            )
        else:
            self.add_element(
                elt,
                start=Point(start[0] + self.x, start[1] + self.y),
                end=Point(end[0] + self.x, end[1] + self.y),
            )
        return self

    def fr(self):
        if len(self.segments) == 0:
            return None
        return self.segments[0].fr

    def to(self):
        if len(self.segments) == 0:
            return None
        return self.segments[-1].to

    def generate_path(self, scale, offset):
        e = Element(self.fr().scaled(scale, offset))
        for s in self.segments:
            to = s.to.scaled(scale, offset)
            if s.op == "line":
                e.add_lineto(to)
            elif s.op == "arc":
                # e.add_lineto(to)
                # e.add_arcto(to)
                e.add_arc_ctr(to, s.ctr.scaled(scale, offset))
            else:
                print(f"unknown element type {s.op}")
                sys.exit(1)
        if self.fr() == self.to():
            e.close_path()
        return e.get_path()


def optimize_strokes(input):
    # we make a map of the from point of strokes to the strokes themselves
    # then we iterate the list of strokes, building a list of strokes where the
    # from point is the same as the to point; these are the closed strokes.
    # when all strokes are closed, we're done.
    strokes = dict([(s.fr(), s) for s in input])
    closed = []
    st2 = dict()
    # take out the already-closed ones first
    for fr, s in strokes.items():
        if s.to() == fr:
            closed.append(s)
        else:
            st2[fr] = s

    # now everything left in st2 should connect to something, so just repeat
    # until we find them all
    while len(st2) > 0:
        # pop one item out of the list
        fr, s = st2.popitem()
        # find what it connects to
        if s.to() not in st2:
            print(f"ERROR! couldn't find {s.to()} in {st2.keys()}")
            sys.exit(1)
        s_to = st2.pop(s.to())
        # join them
        s.segments.extend(s_to.segments)
        if s_to.to() == fr:
            # if it's closed now, move it to the closed list
            if DEBUG:
                print("adding", s)
            closed.append(s)
        else:
            # put it back
            if DEBUG:
                print("extended", s)
            st2[fr] = s

    return closed


class ClosedLoop(object):
    def __init__(self):
        self.segments = []


class Square(object):
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.occupied = False
        self.connections = []
        self.strokes = []

    # returns a sorted string for the set of connections
    def conns(self):
        c = ""
        if NORTH in self.connections:
            c += "N"
        if SOUTH in self.connections:
            c += "S"
        if EAST in self.connections:
            c += "E"
        if WEST in self.connections:
            c += "W"
        return c

    def __str__(self):
        return f"({self.x}, {self.y}) [{self.conns()}]"

    def connect_0(self):
        if DEBUG:
            (f"connect_0({self.x}, {self.y})")
        s = Stroke(self.x, self.y)
        s.add("arc", NC, EC, NE)
        s.add("arc", EC, SC, SE)
        s.add("arc", SC, WC, SW)
        s.add("arc", WC, NC, NW)
        self.strokes = [s]

    # creates an endcap that connects in the given direction
    # (so NORTH connects to the square that is north of here)
    def connect_1(self):
        if DEBUG:
            print(f"connect_1({self.x}, {self.y})")
        conns = self.conns()
        s = Stroke(self.x, self.y)
        if conns == "N":
            s.add("line", N1, WC)
            s.add("arc", WC, SC, SW)
            s.add("arc", SC, EC, SE)
            s.add("line", EC, N2)
        elif conns == "S":
            s.add("line", S1, EC)
            s.add("arc", EC, NC, NE)
            s.add("arc", NC, WC, NW)
            s.add("line", WC, S2)
        elif conns == "E":
            s.add("line", E1, NC)
            s.add("arc", NC, WC, NW)
            s.add("arc", WC, SC, SW)
            s.add("line", SC, E2)
        elif conns == "W":
            s.add("line", W1, SC)
            s.add("arc", SC, EC, SE)
            s.add("arc", EC, NC, NE)
            s.add("line", NC, W2)

        self.strokes = [s]

    # draws a square with 2 connections
    def connect_2(self):
        if DEBUG:
            print(f"connect_2({self.x}, {self.y})")
        self.strokes = []
        # if we sort them we can handle many fewer cases
        conns = self.conns()
        if conns == "NS":
            # straight up/down
            self.strokes = [
                Stroke(self.x, self.y).add("line", N1, S2),
                Stroke(self.x, self.y).add("line", S1, N2),
            ]
        elif conns == "NE":
            # outer arc from N to E
            s = Stroke(self.x, self.y)
            s.add("line", N1, WC)
            s.add("arc", WC, SC, SW)
            s.add("line", SC, E2)
            self.strokes.append(s)
            # inner arc from E to N
            self.strokes.append(Stroke(self.x, self.y).add("arc", E1, N2, NE))
        elif conns == "NW":
            # inner arc from N to W
            self.strokes.append(Stroke(self.x, self.y).add("arc", N1, W2, NW))
            # outer arc from W to N
            s = Stroke(self.x, self.y)
            s.add("line", W1, SC)
            s.add("arc", SC, EC, SE)
            s.add("line", EC, N2)
            self.strokes.append(s)
        elif conns == "SW":
            # outer arc from S to W
            s = Stroke(self.x, self.y)
            s.add("line", S1, EC)
            s.add("arc", EC, NC, NE)
            s.add("line", NC, W2)
            self.strokes.append(s)
            # inner arc from W to S
            self.strokes.append(Stroke(self.x, self.y).add("arc", W1, S2, SW))
        elif conns == "SE":
            # inner arc from S to E
            self.strokes.append(Stroke(self.x, self.y).add("arc", S1, E2, SE))
            # outer arc from E to S
            s = Stroke(self.x, self.y)
            s.add("line", E1, NC)
            s.add("arc", NC, WC, NW)
            s.add("line", WC, S2)
            self.strokes.append(s)
        elif conns == "EW":
            # all that's left is an east-west line
            self.strokes.append(Stroke(self.x, self.y).add("line", E1, W2))
            self.strokes.append(Stroke(self.x, self.y).add("line", W1, E2))
        else:
            print(f"invalid conns in connect_2, {conns}")
            sys.exit(1)

    # draws a square with 3 connections
    def connect_3(self):
        if DEBUG:
            print(f"connect_3({self.x}, {self.y})")
        self.strokes = []
        # this is sorted so we can handle many fewer cases
        conns = self.conns()
        if conns == "NSE":
            # straight NS on the W
            self.strokes.append(Stroke(self.x, self.y).add("line", N1, S2))
            # inner arc from E to N
            self.strokes.append(Stroke(self.x, self.y).add("arc", E1, N2, NE))
            # inner arc from S to E
            self.strokes.append(Stroke(self.x, self.y).add("arc", S1, E2, SE))
        elif conns == "NSW":
            # straight up/down on the E
            self.strokes.append(Stroke(self.x, self.y).add("line", S1, N2))
            # inner arc from N to W
            self.strokes.append(Stroke(self.x, self.y).add("arc", N1, W2, NW))
            # inner arc from W to S
            self.strokes.append(Stroke(self.x, self.y).add("arc", W1, S2, SW))
        elif conns == "NEW":
            # straight EW on the S side
            self.strokes.append(Stroke(self.x, self.y).add("line", W1, E2))
            # inner arc from N to W
            self.strokes.append(Stroke(self.x, self.y).add("arc", N1, W2, NW))
            # inner arc from E to N
            self.strokes.append(Stroke(self.x, self.y).add("arc", E1, N2, NE))
        elif conns == "SEW":
            # straight EW on the N side
            self.strokes.append(Stroke(self.x, self.y).add("line", E1, W2))
            # inner arc from W to S
            self.strokes.append(Stroke(self.x, self.y).add("arc", W1, S2, SW))
            # inner arc from S to E
            self.strokes.append(Stroke(self.x, self.y).add("arc", S1, E2, SE))
        else:
            print(f"invalid conns in connect_3, {conns}")
            sys.exit(1)

    # draws a square with 4 connections
    def connect_4(self):
        if DEBUG:
            print(f"connect_4({self.x}, {self.y})")
        self.strokes = []
        # just 4 arcs
        # inner arc from N to W
        self.strokes.append(Stroke(self.x, self.y).add("arc", N1, W2, NW))
        # inner arc from W to S
        self.strokes.append(Stroke(self.x, self.y).add("arc", W1, S2, SW))
        # inner arc from S to W
        self.strokes.append(Stroke(self.x, self.y).add("arc", S1, E2, SE))
        # inner arc from W to N
        self.strokes.append(Stroke(self.x, self.y).add("arc", E1, N2, NE))

    def get_strokes(self):
        n = len(self.connections)
        if n == 0:
            # 0 - draw a circle
            self.connect_0()
        elif n == 1:
            # 1 - endcap, 1 line
            self.connect_1()
        elif n == 2:
            # 2 - corner -- 1 large curve, 1 small
            # 2 - straight -- 2 straight lines
            self.connect_2()
        elif n == 3:
            # 3 - tee -- 1 straight, 2 small curved lines
            self.connect_3()
        elif n == 4:
            # 4 - cross -- 4 small curved lines
            self.connect_4()
        if DEBUG:
            print(self.strokes)
        return self.strokes


class Board(object):
    def __init__(self, width=20, height=20, neighborhoods=0):
        self.width = width
        self.height = height
        self.num_filled = 0
        if neighborhoods == 0:
            self.neighborhoods = int(self.width * self.height / 5)
        else:
            self.neighborhoods = neighborhoods
        self.empty_board()

    def density(self):
        return self.num_filled / (self.width * self.height)

    def empty_board(self):
        self.board = []
        for y in range(self.height):
            self.board.append([])
            for x in range(self.width):
                self.board[y].append(Square(x, y))

    def generate_lattice(self):
        self.empty_board()

        while self.num_filled < self.neighborhoods:
            x = random.randint(0, self.width - 1)
            y = random.randint(0, self.height - 1)
            if not self.board[y][x].occupied:
                self.board[y][x].occupied = True
                self.num_filled += 1

    def can_connect(self, x, y, dir):
        nx = x + dir.x
        ny = y + dir.y
        if nx < 0 or nx >= self.width:
            return False
        if ny < 0 or ny >= self.height:
            return False
        if not self.board[ny][nx].occupied:
            return False
        return True

    def connect(self, x, y, dir):
        # print(
        #     f"connecting ({x}, {y}) to ({x + dir.x}, {y + dir.y}) D{dir} I{dir.invert()}"
        # )
        self.board[y][x].occupied = True
        self.board[y][x].connections.append(dir)
        self.board[y + dir.y][x + dir.x].occupied = True
        self.board[y + dir.y][x + dir.x].connections.append(dir.invert())
        self.num_filled += 1

    # Given a coordinate of an empty square, tries to connect it to a
    # randomly-selected neighboring filled square.
    # Returns true if it succeeds.
    def try_connect(self, x, y):
        trial_order = sorted(directions, key=lambda a: random.random())
        for dir in trial_order:
            if self.can_connect(x, y, dir):
                assert self.board[y][x].occupied == False
                assert dir not in self.board[y][x].connections
                assert dir.invert() not in self.board[y + dir.y][x + dir.x].connections
                self.connect(x, y, dir)
                return True
        return False

    def fill_board_randomly(self):
        failures = 0
        while self.density() < 0.9 or failures < 10:
            x = random.randint(0, self.width - 1)
            y = random.randint(0, self.height - 1)
            if self.board[y][x].occupied:
                failures += 1
                continue
            if not self.try_connect(x, y):
                failures += 1
                continue
            failures = 0

    def erase_solo_squares(self):
        for y in range(self.height):
            for x in range(self.width):
                if len(self.board[y][x].connections) == 0:
                    self.board[y][x].occupied = 0

    def fill_board_iteratively(self):
        done = False
        while not done:
            done = True
            for y in range(self.height):
                for x in range(self.width):
                    if self.board[y][x].occupied:
                        continue
                    if not self.try_connect(x, y):
                        done = False

    def print_board(self):
        for y in range(self.height):
            squares = [self.board[y][x] for x in range(self.width)]
            for sq in squares:
                print(f" {NORTH in sq.connections and '|' or ' '} ", end="")
            print()
            for sq in squares:
                print(
                    f"{WEST in sq.connections and '-' or ' '}{sq.occupied and '+' or ' '}{EAST in sq.connections and '-' or ' '}",
                    end="",
                )
            print()
            for sq in squares:
                print(f" {SOUTH in sq.connections and '|' or ' '} ", end="")
            print()

    def print_cells(self):
        for y in range(self.height):
            for x in range(self.width):
                sq = self.board[y][x]
                if sq.occupied:
                    print(sq)

    def drawCell(self, x, y):
        # possible cells by the edges they connect with:
        # N, S, E, W,
        pass

    def generate_strokes(self):
        all_strokes = []
        for y in range(self.height):
            for x in range(self.width):
                sq = self.board[y][x]
                all_strokes.extend(sq.get_strokes())
        closed = optimize_strokes(all_strokes)
        return closed

    def save_svg(self, filename, cellsize, width, height, bordersize, fillcolor):
        print(
            f"writing {width}x{height} grid to "
            f"{filename} with "
            f"cellsize {cellsize} and border {bordersize}"
        )
        strokes = self.generate_strokes()
        doc = SVGDoc(filename)
        size = cellsize * SIZE
        pagewidth = size * width + 2 * bordersize + 2
        pageheight = size * height + 2 * bordersize + 2
        doc.setPageSize([pagewidth, pageheight])
        doc.setAuthor("Lattice Generator")
        doc.setFillColor(fillcolor)
        doc.draw_rect(1, 1, pagewidth - 2, pageheight - 2)
        for s in strokes:
            if DEBUG:
                print("  S:", s)
            path = s.generate_path(cellsize, Point(bordersize + 1, bordersize + 1))
            if DEBUG:
                print("  P:", path)
            doc.draw_element(path)
        doc.save()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a lattice.")
    parser.add_argument(
        "--width",
        dest="width",
        type=int,
        default=10,
        help="the number of lattice cells horizontally",
    )
    parser.add_argument(
        "--height",
        dest="height",
        type=int,
        default=15,
        help="the number of lattice cells vertically",
    )
    parser.add_argument(
        "--cellsize",
        dest="cellsize",
        type=int,
        default=12,
        help="the size of each cell in mm",
    )
    parser.add_argument(
        "--bordersize",
        dest="bordersize",
        type=int,
        default=10,
        help="the size of the border in mm",
    )
    parser.add_argument(
        "--n",
        dest="n",
        type=int,
        default=0,
        help="the number of neighborhoods to use (default is area/5)",
    )
    parser.add_argument(
        "--seed",
        dest="seed",
        type=int,
        default=0,
        help="a seed for randomness (default time.now)",
    )
    parser.add_argument(
        "--printboard",
        dest="printboard",
        default=False,
        action="store_true",
        help="ascii-print the board after generation",
    )
    parser.add_argument(
        "--filename",
        dest="filename",
        default="lattice.svg",
        help="filename in which to store the resulting svg (lattice.svg)",
    )
    parser.add_argument(
        "--fillcolor",
        dest="fillcolor",
        type=str,
        default="none",
        help="fill color of the strokes (none)",
    )
    parser.add_argument(
        "--nosolo",
        dest="nosolo",
        default=False,
        action="store_true",
        help="don't allow neighborhoods of only one cell",
    )

    args = parser.parse_args()

    if args.seed != 0:
        random.seed(args.seed)
    drawing = Board(width=args.width, height=args.height, neighborhoods=args.n)
    drawing.generate_lattice()
    drawing.fill_board_randomly()
    if args.nosolo:
        drawing.erase_solo_squares()
    drawing.fill_board_iteratively()
    if args.printboard:
        drawing.print_board()
    # drawing.print_cells()

    # strokes = drawing.generate_strokes()
    # for s in strokes:
    #     print("  :", s)

    drawing.save_svg(
        args.filename,
        args.cellsize,
        args.width,
        args.height,
        args.bordersize,
        args.fillcolor,
    )
