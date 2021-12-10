import math
import random

import os
import pickle
import numpy as np
import sympy
import logging
from typing import Tuple
from shapely.geometry import Polygon, Point, LineString
from time import time
import math
import matplotlib.pyplot as plt


def line_in_polygon(point_a, point_b, polygon):
    segment_land = LineString([point_a, point_b])
    if_encloses = polygon.contains(segment_land)
    return if_encloses


def is_roll_in_polygon(point_a, distance, angle, polygon):
    curr_point = Point(point_a.x + distance * np.cos(angle),
                       point_a.y + distance * np.sin(angle))
    final_point = Point(
        point_a.x + (1.1) * distance * np.cos(angle),
        point_a.y + (1.1) * distance * np.sin(angle))

    start = time()
    if_encloses = line_in_polygon(curr_point, final_point, polygon)
    end = time()
    # print("line-time", end - start)
    #
    # start = time()
    # curr_point.within(polygon)
    # final_point.within(polygon)
    # end = time()
    # print("points", end-start)
    return if_encloses


def convert_sympy_shapely(point):
    return Point(point.x, point.y)


def direct_distance_angle(curr_loc, target, skill):
    required_dist = curr_loc.distance(target)
    roll_factor = 1.1
    if required_dist < 20:
        roll_factor = 1.0
    max_dist_traveled = 200 + skill
    distance = min(max_dist_traveled, required_dist / roll_factor)
    angle = math.atan2(target.y - curr_loc.y, target.x - curr_loc.x)

    return distance, angle

def is_going_back(previous_angle, new_angle):
    if not previous_angle:
        return (False, (0,0))
    window = np.pi/4 # check if one angle within 90 deg of the other angle
    opposite_angle = np.pi - previous_angle if previous_angle >= np.pi else np.pi + previous_angle # flipping the direction 180 deg
    opposite_angle = opposite_angle if opposite_angle >= 0 else (2 * np.pi) + opposite_angle
    new_angle = new_angle if new_angle >= 0 else (2 * np.pi) + new_angle
    a_min , a_max = opposite_angle - window, opposite_angle + window
    if new_angle >= opposite_angle - window and new_angle <= opposite_angle + window:
        return (True, (a_min, a_max))
    return (False, (0,0))


def generate_points(curr_loc, target, polygon, skill, increment=25, search_angle=np.pi, backtracking=False, angle_range=None):
    distance, angle = direct_distance_angle(curr_loc, target, skill)
    angle = angle-np.pi if backtracking else angle
    theta_min, theta_max = 0, 0
    if angle_range:
        angle = angle + np.pi
        theta_min, theta_max = angle_range

    if distance < 20 and line_in_polygon(curr_loc, target, polygon):
        return [LandingPoint(target, distance, angle, curr_loc, target)]

    points = []
    r = distance
    while r > 0:
        semicircle_length = search_angle * r
        num_sector = int(semicircle_length / increment)  # divide the semicircle into equally sized sectors
        num_sector = num_sector if num_sector % 2 == 0 else num_sector + 1
        if num_sector == 0:
            r -= increment
            continue
        arc_length = semicircle_length / num_sector
        angle_increment = search_angle / num_sector
        for i in range(0, int(num_sector) + 1):
            new_angle = float(angle + (i * angle_increment))
            if new_angle <= theta_max and new_angle >= theta_min:
                continue
            point = Point(curr_loc.x + r * np.cos(new_angle),
                          curr_loc.y + r * np.sin(new_angle))

            if LandingPoint.is_on_land(point, polygon):
                lp = LandingPoint(point, r, new_angle, curr_loc, target, backtracking=backtracking)
                points.append(lp)
            if i > 0:
                new_angle = float(angle - (i * angle_increment))
                if new_angle <= theta_max and new_angle >= theta_min:
                    continue
                point = Point(curr_loc.x + r * np.cos(new_angle),
                              curr_loc.y + r * np.sin(new_angle))

                if LandingPoint.is_on_land(point, polygon):
                    lp = LandingPoint(point, r, new_angle, curr_loc, target, backtracking=backtracking)
                    points.append(lp)
        r -= increment

    return points


def search_landing_points(points, polygon, skill, rng):
    largest_point = None
    largest_point_score = -1 * float('inf')
    for point in points:
        start = time()
        score = point.score(polygon, skill, rng)
        end = time()
        # print("time: ", end-start)
        if score > largest_point_score:
            largest_point = point
            largest_point_score = score

    return largest_point


class LandingPoint(object):
    def __init__(self, point, distance_from_origin, angle_from_origin, start_point, hole_point, backtracking=False):
        # distance_from_origin is the distance from our curr_location to the landing point

        self.point = point
        self.distance_from_origin = distance_from_origin
        self.angle_from_origin = angle_from_origin
        self.hole = hole_point
        self.score_threshold = 95
        self.trials = 20
        self.start_point = start_point
        self.backtracking = backtracking


    @staticmethod
    def is_on_land(point, polygon):
        return point.within(polygon)

    def confidence(self, polygon, skill, rng):
        try:
            return self.shot_confidence
        except AttributeError:
            intended_distance = self.distance_from_origin
            intended_angle = self.angle_from_origin
            successful = 0
            for t in range(0, self.trials):
                actual_distance = rng.normal(intended_distance, intended_distance / skill)
                actual_angle = rng.normal(intended_angle, 1 / (2 * skill))
                if is_roll_in_polygon(self.start_point, actual_distance, actual_angle, polygon):
                    successful += 1
            self.shot_confidence = successful / self.trials
            return self.shot_confidence

    def heuristic(self):
        try:
            return self.distance_to_hole
        except AttributeError:
            self.distance_to_hole = self.point.distance(self.hole) if self.backtracking else -self.point.distance(self.hole)
            return self.distance_to_hole

    def score(self, polygon, skill, rng):
        # uses confidence and heuristic
        return self.heuristic() + (self.confidence(polygon, skill, rng) * 100)

class MultipleLandingPoints:

    def __init__(self, start_lp, backtracking=False):
        self.path = [start_lp]
        self.backtracking = backtracking


    def heuristic(self):
        return self.path[-1].heuristic()

    def confidence(self, polygon, skill, rng):
        total = 1
        for lp in self.path:
            total *= lp.confidence(polygon, skill, rng)
        return total

    def score(self, polygon, skill, rng):
        return (self.heuristic() + (self.confidence(polygon, skill, rng) * 100))/len(self.path)

    def add_point(self, polygon, skill, rng):
        last_point = self.path[-1]

        landing_points = generate_points(last_point.point, last_point.hole, polygon, skill, backtracking=self.backtracking)
        next_point = search_landing_points(landing_points, polygon, skill, rng)
        if next_point:
            self.path.append(next_point)

    def distance_to_hole(self):
        last_point = self.path[-1]
        return last_point.point.distance(last_point.hole)


class Player:
    def __init__(self, skill: int, rng: np.random.Generator, logger: logging.Logger, golf_map: sympy.Polygon, start: sympy.geometry.Point2D, target: sympy.geometry.Point2D, map_path: str, precomp_dir: str) -> None:
        """Initialise the player with given skill.

        Args:
            skill (int): skill of your player
            rng (np.random.Generator): numpy random number generator, use this for same player behvior across run
            logger (logging.Logger): logger use this like logger.info("message")
            golf_map (sympy.Polygon): Golf Map polygon
            start (sympy.geometry.Point2D): Start location
            target (sympy.geometry.Point2D): Target location
            map_path (str): File path to map
            precomp_dir (str): Directory path to store/load precomputation
        """
        # # if depends on skill
        # precomp_path = os.path.join(precomp_dir, "{}_skill-{}.pkl".format(map_path, skill))
        # # if doesn't depend on skill
        # precomp_path = os.path.join(precomp_dir, "{}.pkl".format(map_path))
        
        # # precompute check
        # if os.path.isfile(precomp_path):
        #     # Getting back the objects:
        #     with open(precomp_path, "rb") as f:
        #         self.obj0, self.obj1, self.obj2 = pickle.load(f)
        # else:
        #     # Compute objects to store
        #     self.obj0, self.obj1, self.obj2 = _

        #     # Dump the objects
        #     with open(precomp_path, 'wb') as f:
        #         pickle.dump([self.obj0, self.obj1, self.obj2], f)
        self.skill = skill
        self.rng = rng
        self.logger = logger
        self.previous_angle = None


    def play(self, score: int, golf_map: sympy.Polygon, target: sympy.geometry.Point2D,
             curr_loc: sympy.geometry.Point2D, prev_loc: sympy.geometry.Point2D,
             prev_landing_point: sympy.geometry.Point2D, prev_admissible: bool) -> Tuple[float, float]:
        """Function which based n current game state returns the distance and angle, the shot must be played 

        Args:
            score (int): Your total score including current turn
            golf_map (sympy.Polygon): Golf Map polygon
            target (sympy.geometry.Point2D): Target location
            curr_loc (sympy.geometry.Point2D): Your current location
            prev_loc (sympy.geometry.Point2D): Your previous location. If you haven't played previously then None
            prev_landing_point (sympy.geometry.Point2D): Your previous shot landing location. If you haven't played previously then None
            prev_admissible (bool): Boolean stating if your previous shot was within the polygon limits. If you haven't played previously then None

        Returns:
            Tuple[float, float]: Return a tuple of distance and angle in radians to play the shot
        """

        if score == 1:
            self.shapely_polygon = Polygon([(p.x, p.y) for p in golf_map.vertices])

        curr_loc = convert_sympy_shapely(curr_loc)
        target = convert_sympy_shapely(target)

        _, direct_angel = direct_distance_angle(curr_loc, target, self.skill)
        going_back, angle_range = is_going_back(self.previous_angle, direct_angel)
        if going_back:
            landing_points = generate_points(curr_loc, target, self.shapely_polygon, self.skill, backtracking=True, angle_range=angle_range)
            paths = [MultipleLandingPoints(lp, backtracking=True) for lp in landing_points]
            for path in paths:
                if path.distance_to_hole() > 20:
                    path.add_point(self.shapely_polygon, self.skill, self.rng)
            largest_point = search_landing_points(paths, self.shapely_polygon, self.skill, self.rng)
        else:
            landing_points = generate_points(curr_loc, target, self.shapely_polygon, self.skill)

            paths = [MultipleLandingPoints(lp) for lp in landing_points]
            for path in paths:
                if path.distance_to_hole() > 20:
                    path.add_point(self.shapely_polygon, self.skill, self.rng)
            largest_point = search_landing_points(paths, self.shapely_polygon, self.skill, self.rng)
            # In theory, we can reach 200+skill in one shot, using 200 to go even lower
            if sum([p.distance_from_origin for p in largest_point.path]) < 200 and len(largest_point.path) > 1:
                landing_points = generate_points(curr_loc, target, self.shapely_polygon, self.skill, backtracking=True)
                paths = [MultipleLandingPoints(lp, backtracking=True) for lp in landing_points]
                for path in paths:
                    if path.distance_to_hole() > 20:
                        path.add_point(self.shapely_polygon, self.skill, self.rng)
                largest_point = search_landing_points(paths, self.shapely_polygon, self.skill, self.rng)

        distance, angle = largest_point.path[0].distance_from_origin, largest_point.path[0].angle_from_origin
        self.previous_angle = angle
        print("curr_loc")
        print("x: "+str(curr_loc.x)+" ,y: "+str(curr_loc.y))
        print("path")
        pp = ["x: "+str(p.point.x)+" ,y: "+str(p.point.y) for p in largest_point.path]
        print("\n".join(pp))
        return (distance, angle)