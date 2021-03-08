import numpy as np
import cv2 as cv
import os

annotation_file_paths = "/mnt/c/Users/Rufus Vijayaratnam/yolov5/runs/detect/exp2/labels/"

label_files = os.listdir(annotation_file_paths)

image = cv.imread("/mnt/c/Users/Rufus Vijayaratnam/Driverless/Blender/Resources/Renders/train/images/track5-Right_Cam-Render-16.png")
size_x = np.shape(image)[1]
size_y = np.shape(image)[0]
f = open(annotation_file_paths + label_files[0], "r")
#YOLO format: <class> <x_center / res x> <y_center / res y> <width / res x> <height / res y>
bounding_boxes_string = f.readlines()

blue_lower=np.array([100,100,100],np.uint8)
blue_upper=np.array([140,255,255],np.uint8)
blue = (255, 0, 0)

yellow_lower = np.array([20, 100, 100])
yellow_upper = np.array([30, 255, 255])
yellow = (0, 255, 255)

ambiguous = (0, 0, 255)
none = (0, 0, 0)

def yolo_annotation_to_pixel(boxes, res_x, res_y):
    pixel_bounds = np.ndarray(len(boxes), dtype=(tuple, 2))
    for i, box in enumerate(boxes):
        data = [float(val) for val in box.split()]
        data = data[1:]
        width = data[2] * res_x
        height = data[3] * res_y
        x1 = int(data[0] * res_x - width / 2)
        y1 = int(data[1] * res_y - height / 2)
        x2 = int(data[0] * res_x + width / 2)
        y2 = int(data[1] * res_y + height / 2)
        pixel_bounds[i] = ((x1, y1), (x2, y2))

    return pixel_bounds

def remove_noise(image):
    refinement_resolution = 5
    for y in range(int(np.shape(image)[0] / refinement_resolution)):
        for x in range(int(np.shape(image)[1] / refinement_resolution)):
            x1 = x * refinement_resolution
            y1 = y * refinement_resolution
            x2 = (x + 1) * refinement_resolution
            y2 = (y + 1) * refinement_resolution
            sub = image[y1:y2, x1:x2]
            avg = cv.mean(sub)
            if avg[0] <= 150:
                image[y1:y2, x1:x2] = 0
            else:
                image[y1:y2, x1:x2] = 255
    return image

def test_cone_colour(mask):

    num_labels, labels, stats, centroids = cv.connectedComponentsWithStats(mask, connectivity=4)
    centroids = [[int(point[0]), int(point[1])] for point in centroids]
    bg_area = stats[0][cv.CC_STAT_AREA]
    valid_components = [] #Array of indidices representing the stats arrays that meet the conditions
    for i in range(1, num_labels):
        area = stats[i][cv.CC_STAT_AREA]
        if area / bg_area * 100 >= 5:
            valid_components.append(i)

    centroids = [centroids[i] for i in valid_components] #Now excludes background
    stats = [stats[i] for i in valid_components] #Now excludes background
    labels = [labels[i] for i in valid_components] #Now excludes background
    found_colour = np.zeros(len(stats), dtype=bool)

    if len(centroids) == 2:
        return True 
    else:
        return False
        

def estimate_colour(image):
    hsv_image = cv.cvtColor(image, cv.COLOR_BGR2HSV)
    blue_mask = cv.inRange(hsv_image, blue_lower, blue_upper)
    yellow_mask = cv.inRange(hsv_image, yellow_lower, yellow_upper)
    found_blue = test_cone_colour(blue_mask)
    found_yellow = test_cone_colour(yellow_mask)

    if np.logical_and(found_blue, found_yellow):
        colour = ambiguous
        print("ambiguous")
    elif np.logical_xor(found_yellow, found_blue):
        if found_blue:
            colour = blue
            print("blue")
        else:
            colour = yellow
            print("yellow")
    elif not np.logical_or(found_blue, found_yellow):
        colour = none #Just to test, can be removed later probably and replace with "ambiguous"
        print("none")
    
    """ p1 = (stats[i][cv.CC_STAT_LEFT], stats[i][cv.CC_STAT_TOP])
    p2 = (stats[i][cv.CC_STAT_LEFT] + stats[i][cv.CC_STAT_WIDTH], stats[1][cv.CC_STAT_TOP] + stats[1][cv.CC_STAT_HEIGHT]) """

    return colour
        
bounding_boxes = yolo_annotation_to_pixel(bounding_boxes_string, size_x, size_y)

#for detected_cone in bounding_boxes:
#detected_cone = bounding_boxes[3]

for detected_cone in bounding_boxes:
    x1 = detected_cone[0][0]
    y1 = detected_cone[0][1]
    x2 = detected_cone[1][0]
    y2 = detected_cone[1][1]
    print("detected cone:", detected_cone)
    sub_image = image[y1:y2, x1:x2]
    colour = estimate_colour(sub_image)
    cv.rectangle(image, (x1, y1), (x2, y2), colour)

cv.imshow("hi", image)

""" white = np.ndarray(sub_image.shape, dtype=np.uint8)
white[:] = (255, 255, 255)
mask = estimate_colour(sub_image)
mask_inv = cv.bitwise_not(mask)
img_bg = cv.bitwise_and(sub_image, sub_image, mask = mask_inv)
img_fg = cv.bitwise_and(white, white, mask = mask)
final = cv.add(img_bg, img_fg)
image[y1:y2, x1:x2] = final
cv.imshow("hi", image) """

    


cv.waitKey(0)
cv.destroyAllWindows()