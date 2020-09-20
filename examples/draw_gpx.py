#!/usr/bin/env python

# py-staticmaps
# Copyright (c) 2020 Florian Pigorsch; see /LICENSE for licensing information

import sys

import gpxpy  # type: ignore
import staticmaps

context = staticmaps.Context()
context.set_tile_provider(staticmaps.tile_provider_ArcGISWorldImagery)

with open(sys.argv[1], "r") as file:
    gpx = gpxpy.parse(file)

for track in gpx.tracks:
    for segment in track.segments:
        line = [staticmaps.create_latlng(p.latitude, p.longitude) for p in segment.points]
        context.add_object(staticmaps.Line(line))

# render png
image = context.render_cairo(800, 500)
image.write_to_png("running.png")

# render svg
svg_image = context.render_svg(800, 500)
with open("running.svg", "w", encoding="utf-8") as f:
    svg_image.write(f, pretty=True)
