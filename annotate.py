#!/usr/local/bin/python
# -*- coding: utf-8 -*-

import sys
import argparse
import csv
import re
import fiona
import shapely.geometry
from shapely.geometry import Point

# A datastructure to hold a shape (neighborhood, beat, etc)
class Shape:
    def __init__(self, feature):
        self.polygon = shapely.geometry.shape(feature['geometry'])
        self.name = feature['properties']['gnocdc_lab']
        self.centroid = self.polygon.centroid

def sort_shapes(shapes, point):
    """
    Sorts the shapes by distance from the shape centroid to the given point
    """
    shapes.sort(key = lambda shape: shape.centroid.distance(point))
    return shapes

def find_neighborhood(shapes, lat, lng):
    """
    Finds the neighborhood given the lat, lng
    """
    point = Point(lng, lat)

    # sorts the shapes by distance from shape centroid the point
    sorted_shapes = sort_shapes(shapes, point)

    # now that shapes are sorted, we should find the
    # boundary shape pretty quick
    for shape in sorted_shapes:
        if shape.polygon.contains(point):
            return shape.name

    return None

lat_lng_rg = re.compile('.*?([+-]?\\d*\\.\\d+)(?![-+0-9\\.]).*?([+-]?\\d*\\.\\d+)(?![-+0-9\\.])')

def parse_lat_lng(lat_lng_string):
    """
    Turns the Location column into (lat, lng) floats
    May look like this "(29.98645605, -90.06910049)"
    May have degree symbol "(29.98645605°,-90.06910049°)"
    """
    m = lat_lng_rg.search(lat_lng_string)

    if m:
        return (float(m.group(1)), float(m.group(2)))
    else:
        return (None, None)

def annotate_csv(in_file, out_file, options):
    """
    Goes row by row through the in_file and
    writes out the row to the out_file with
    the new Neighbhorhood column
    """

    fc = fiona.open(options.shape_file)
    shapes = [Shape(feature) for feature in fc]

    reader = csv.reader(in_file)
    writer = csv.writer(out_file)

    # Write headers first, add new neighborhood column
    headers = reader.next()
    headers.append(options.output_column)

    writer.writerow(headers)

    for row in reader:
        # WGS84 point, "Location" column, is last element
        lat, lng = parse_lat_lng(row[options.loc_column])

        if lat and lng:
            neighborhood = find_neighborhood(shapes, lat, lng)
        else:
            neighborhood = 'N/A'

        row.append(neighborhood)
        writer.writerow(row)

        print("#%s lat: %s lng: %s -> %s" % (reader.line_num, lat, lng, neighborhood))

def main(options):
    if not options.loc_column and (not (options.lat_column and options.lng_column)):
        sys.exit('You must set either --loc-column or both --lat-column and --lng-column')

    with open(options.input_file, 'r') as in_file:
        with open(options.output_file, 'w') as out_file:
            annotate_csv(in_file, out_file, options)

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Annotate csv file with shape tags')
    parser.add_argument('input_file', metavar='input_file', help='the input csv file path')
    parser.add_argument('output_file', metavar='output_file', help='the output csv file path')
    parser.add_argument('output_column', metavar='output_column', help='the name of the column you wish to add')
    parser.add_argument('shape_file', metavar='shape_file', help='the path to the shp file')
    parser.add_argument('--lat-column', type=int, help="the 0-indexed column position for latitude (if in it's own column)")
    parser.add_argument('--lng-column', type=int, help="the 0-indexed column position for longitude (if in it's own column)")
    parser.add_argument('--loc-column', type=int, help="the 0-indexed column position for location (if lat and lng are in one column)")
    main(parser.parse_args())

