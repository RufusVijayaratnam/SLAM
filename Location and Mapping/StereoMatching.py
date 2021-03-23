import numpy as np
import cv2 as cv
import ColourEstimation as ce
from Constants import *
from Detections import DetectedCone, Detections
from Colour import Colour

class Matcher():
    def __init__(self, train, query):
        self.train = train
        self.query = query
        self.matches = []

    def in_range(self, test, lower, upper):
        if test <= upper and test >= lower:
            return True
        else:
            return False

    def match_hash(self, hash, array):
        hashes = np.array([q.uid for q in array])
        index = np.where(hashes == hash)[0][0]
        return index

    def __match_keypoints(self, train_im, query_im):
        print("Attempting to find matching points")
        train_im = np.array(train_im)
        query_im = np.array(query_im)
        orb = cv.ORB_create(nfeatures=20)
        kp_query = orb.detect(query_im, None)
        kp_train = orb.detect(train_im, None)

        kp_query, des_query = orb.compute(query_im, kp_query)
        kp_train, des_train = orb.compute(train_im, kp_train)

        point_matcher = cv.BFMatcher(cv.NORM_HAMMING, crossCheck=True)
        point_matches = point_matcher.match(des_query, des_train)
        point_matches = sorted(point_matches, key=lambda x:x.distance)
        

        """ cv.imshow("train", train_im)
        cv.imshow("query", query_im)
        img3 = cv.drawMatches(train_im,kp_train,query_im,kp_query,point_matches[:10],None,flags=cv.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)
        cv.imshow("matches", img3)
        cv.waitKey(0)
        cv.destroyAllWindows() """

        return point_matches

    def deriveDepth(key_points):    
        depths = []
        for key_point in key_points:
            imgWidth = QueryCam.shape[1]
            focalLength_pixels = (focalLength_mm / sensorWidth_mm) * imgWidth
            tidx = key_point.trainIdx
            qidx = key_point.queryIdx
            imIdx = key_point.imgIdx
            Q_x = kpQuery[qidx].pt[0]
            T_x = kpTrain[tidx].pt[0]
            disparity = abs(Q_x - T_x)
            print("tidx: {}, qidx: {}".format(tidx, qidx))
            depth = baseline_mm * focalLength_pixels / disparity
            depths.append(depth)

        return depths

    def center_depth(self, cx1, cx2):
        disparity = abs(cx1 - cx2)
        focalLength_pixels = (focalLength_mm / sensorWidth_mm) * self.train[0].im_width
        depth = baseline_mm * focalLength_pixels / disparity
        return depth / 1000

    def __key_points_to_image_coords(self):
        #the matching function returns key points with their coords in the sub image
        #These must be transformed back into the original image coords
        return 0

    def get_located(self):
        train_matched = [self.train[val[0]] for val in self.matches]
        query_matched = [self.query[val[1]] for val in self.matches]
        train_located = Detections(train_matched, self.train.image)
        query_located = Detections(query_matched, self.query.image)
        return train_located, query_located

        print("depths", depths)
        no_matches = np.where(depths == -1)
        if len(no_matches) != 0:
            for val in no_matches[0]:
                del self.matches[val]
        depths = np.delete(depths, no_matches)
            

class StereoMatcher(Matcher):
    def __init__(self, train, query):
        super().__init__(train, query)

    def __find_match(self, train, query_original):
        for i, t in enumerate(train):
            query = query_original
            tcx = t.cx
            tcy = t.cy
            hash = t.uid
            _, disp_lower, disp_upper = t.monocular_distance_estimate()
            dists = np.array([abs(q.cx - tcx) for q in query])
            in_range = np.array([self.in_range(d, disp_lower, disp_upper) for d in dists])
            out_range = np.where(in_range == False)
            query = np.delete(query, out_range)
            train_index = self.match_hash(hash, self.train)

            if len(query) != 0:
                cy_dists = np.array([abs(q.cy - tcy) for q in query])
                min_cy_dist = np.min(cy_dists)
                match_idx = np.where(cy_dists == min_cy_dist)[0][0]
                match_hash = query[match_idx].uid
                query_index = self.match_hash(match_hash, self.query)
                self.matches.append((train_index, query_index))
            else:
                self.matches.append((train_index, -1))
        
    def find_stereo_matches(self):
        colours = np.array([c.colour.name for c in self.query])
        not_yellow_indices = np.where(colours != "yellow")
        not_blue_indices = np.where(colours != "blue")
        query_yellow = np.delete(self.query, not_yellow_indices)
        query_blue = np.delete(self.query, not_blue_indices)

        colours = np.array([c.colour.name for c in self.train])
        not_yellow_indices = np.where(colours != "yellow")
        not_blue_indices = np.where(colours != "blue")
        train_yellow = np.delete(self.train, not_yellow_indices)
        train_blue = np.delete(self.train, not_blue_indices)

        self.__find_match(train_blue, query_blue)
        self.__find_match(train_yellow, query_yellow)

    def calculate_depth(self):
        depths = np.ndarray(len(self.matches))
        print("what up dog")
        train_im = np.array(self.train.image)
        query_im = np.array(self.query.image)
        for i, match in enumerate(self.matches):
            train_idx = match[0]
            query_idx = match[1]
            if train_idx != -1 and query_idx != -1:
            #if match != None:
                """ train_sub_im = np.array(self.train[train_idx].get_sub_image(train_im))
                query_sub_im = np.array(self.query[query_idx].get_sub_image(query_im))
                point_matches.append(self.__match_keypoints(train_sub_im, query_sub_im)) """
                cx_train = self.train[train_idx].cx
                cx_query = self.query[query_idx].cx
                depth = self.center_depth(cx_train, cx_query)
                self.train[train_idx].depth = depth
                self.query[query_idx].depth = depth
                depths[i] = depth
            else:
                depths[i] = -1