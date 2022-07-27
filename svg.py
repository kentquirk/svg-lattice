# By Kent Quirk, April 2018
# SVG writer; outputs lines and text

# Although SVG is an XML-based language, XML manipulation is annoyingly complicated for what we need
# to do here, so we're just going to treat set things up with a template and embed strings.

# This system exists generate SVG files -- in particular to use with the Glowforge laser cutter. One thing that
# makes using the Glowforge UI work better is for SVGs to use closed paths rather than a semi-random selection of
# lines. Consequently, what this driver does is collect all of the line commands and record them; on the
# save call it concatenates them together into a set of paths.

from string import Template
import sys


def _sc(v):
    "converts from mm to pixels as a numeric string"
    return "{:.1f}".format(v)  # * 96 / 25.4)


def _col(color):
    "generates a CSS color from an ascii color"
    if color in colors:
        return "#" + colors[color]
    return color


tmpl_svg = Template(
    """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<svg width="${pixel_width}px" height="${pixel_height}px" version="1.1"
    xmlns="http://www.w3.org/2000/svg"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xml:space="preserve"
    xmlns:serif="http://www.serif.com/"
    style="fill-rule:evenodd;clip-rule:evenodd;stroke-linecap:round;stroke-linejoin:round;stroke-miterlimit:1.5;">
${contents}
</svg>
"""
)

tmpl_path = Template(
    """        <path d="${path}" style="fill:${fill_color};stroke:${stroke_color};stroke-width:${stroke_pixels}px;"/>
"""
)

tmpl_rect = Template(
    """        <rect x="${x}" y="${y}" style="fill:none;stroke:${stroke_color};stroke-width:${stroke_pixels}px;" width="${w}" height="${h}"/>
"""
)

colors = {
    "black": "000000",
    "red": "FF0000",
    "green": "00FF00",
    "blue": "0000FF",
    "white": "FFFFFF",
}


class Element(object):
    def __init__(self, pt):
        self.path = [f"M{_sc(pt.x)},{_sc(pt.y)}"]
        self.lastpt = pt

    def add_lineto(self, pt):
        self.path.append(f"L{_sc(pt.x)},{_sc(pt.y)}")
        self.lastpt = pt

    def add_arcto(self, pt):
        # we need to make 2 control points, and we know the arc curves to the right
        # from its starting direction.
        # We find a center point that lives at the intersection
        # of the two desired tangents.
        # Control points are both tweened between the points and the center
        # point with the same tween factor.
        ctr = pt.clone()
        if self.lastpt.x < pt.x and self.lastpt.y < pt.y:
            ctr.y = self.lastpt.y
        elif self.lastpt.x > pt.x and self.lastpt.y > pt.y:
            ctr.y = self.lastpt.y
        elif self.lastpt.x < pt.x and self.lastpt.y > pt.y:
            ctr.x = self.lastpt.x
        elif self.lastpt.x > pt.x and self.lastpt.y < pt.y:
            ctr.x = self.lastpt.x
        else:
            print(f"failed! {self.lastpt} {pt}")
            sys.exit(1)

        self.add_arc_ctr(pt, ctr)

    def add_arc_ctr(self, pt, ctr):
        # Control points are both tweened between the points and the center
        # point with the same tween factor.
        tween_factor = 0.5
        ctr = ctr.clone()

        ctrl1 = self.lastpt.tween(ctr, tween_factor)
        ctrl2 = pt.tween(ctr, tween_factor)

        self.path.append(
            f"C{_sc(ctrl1.x)},{_sc(ctrl1.y)} {_sc(ctrl2.x)},{_sc(ctrl2.y)} {_sc(pt.x)},{_sc(pt.y)}"
        )
        self.lastpt = pt

    def close_path(self):
        self.path.append("Z")

    def get_path(self):
        return " ".join(self.path)


class SVGDoc(object):
    def __init__(self, filename):
        self.comments = []
        self.elements = []
        self.paths = []
        self.firsts = set()
        self.filename = filename
        self.strokeColor = "black"
        self.fillColor = "none"
        self.lineWidth = 0.5  # default is mm so we need to convert
        self.pageSize = [0, 0]
        self.author = ""

    def setPageSize(self, pageSize):
        self.pageSize = pageSize

    def setAuthor(self, author):
        self.author = author

    def setStrokeColor(self, col):
        self.strokeColor = col

    def setFillColor(self, col):
        self.fillColor = col

    def setLineWidth(self, lw):
        self.lineWidth = lw

    def drawString(self, x, y, st):
        # String must be free of metacharacters
        self.comments.append((x, y, st))

    def draw_rect(self, x, y, w, h):
        self.elements.append(
            tmpl_rect.substitute(
                dict(
                    x=_sc(x),
                    y=_sc(y),
                    w=_sc(w),
                    h=_sc(h),
                    stroke_color=_col(self.strokeColor),
                    stroke_pixels=_sc(self.lineWidth),
                )
            )
        )

    # expects a list of points as tuples
    def draw_closed_linear_path(self, p):
        s = "M{},{}".format(_sc(p[0][0]), _sc(p[0][1]))
        s += "".join(["L{},{}".format(_sc(pt[0]), _sc(pt[1])) for pt in p[1:-1]])
        s += "Z"
        self.elements.append(
            tmpl_path.substitute(
                dict(
                    path=s,
                    fill_color=_col(self.fillColor),
                    stroke_color=_col(self.strokeColor),
                    stroke_pixels=_sc(self.lineWidth),
                )
            )
        )

    # expects a list of points as tuples
    def draw_open_linear_path(self, p):
        s = "M{},{}".format(_sc(p[0][0]), _sc(p[0][1]))
        s += "".join(["L{},{}".format(_sc(pt[0]), _sc(pt[1])) for pt in p[1:]])
        self.elements.append(
            tmpl_path.substitute(
                dict(
                    path=s,
                    stroke_color=_col(self.strokeColor),
                    stroke_pixels=_sc(self.lineWidth),
                )
            )
        )

    def draw_closed_linear_path(self, p):
        s = "M{},{}".format(_sc(p[0][0]), _sc(p[0][1]))
        s += "".join(["L{},{}".format(_sc(pt[0]), _sc(pt[1])) for pt in p[1:-1]])
        s += "Z"
        self.elements.append(
            tmpl_path.substitute(
                dict(
                    path=s,
                    stroke_color=_col(self.strokeColor),
                    stroke_pixels=_sc(self.lineWidth),
                )
            )
        )

    def draw_element(self, elt):
        self.elements.append(
            tmpl_path.substitute(
                dict(
                    path=elt,
                    fill_color=_col(self.fillColor),
                    stroke_color=_col(self.strokeColor),
                    stroke_pixels=_sc(self.lineWidth),
                )
            )
        )

    def save(self):
        s = "".join([e for e in self.elements])
        pgw, pgh = _sc(self.pageSize[0]), _sc(self.pageSize[1])
        svg = tmpl_svg.substitute(dict(pixel_width=pgw, pixel_height=pgh, contents=s))
        ofh = open(self.filename, "w")
        ofh.write(svg)
        ofh.close()
