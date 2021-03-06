import cv2
import os
import json
import argparse
import tensorflow as tf
from tensorflow.keras.applications import vgg16, mobilenet, mobilenet_v2
import numpy as np
from networks import SSD_VGG16, SSD_MOBILENET, SSD_MOBILENETV2
from utils import inference_utils, textboxes_utils

parser = argparse.ArgumentParser(description='run inference on an input image.')
parser.add_argument('input_image', type=str, help='path to the input image.')
parser.add_argument('label_file', type=str, help='path to the label file.')
parser.add_argument('config', type=str, help='path to config file.')
parser.add_argument('weights', type=str, help='path to the weight file.')
parser.add_argument('--label_maps', type=str, help='path to label maps file.')
parser.add_argument('--confidence_threshold', type=float, help='the confidence score a detection should match in order to be counted.', default=0.9)
parser.add_argument('--num_predictions', type=int, help='the number of detections to be output as final detections', default=10)
parser.add_argument('--show_class_label', type=bool, help='the number of detections to be output as final detections', default=False)
args = parser.parse_args()

assert os.path.exists(args.input_image), "config file does not exist"
assert os.path.exists(args.config), "config file does not exist"
assert args.num_predictions > 0, "num_predictions must be larger than zero"
assert args.confidence_threshold > 0, "confidence_threshold must be larger than zero."
assert args.confidence_threshold <= 1, "confidence_threshold must be smaller than or equal to 1."

with open(args.config, "r") as config_file:
    config = json.load(config_file)

input_size = config["model"]["input_size"]
model_config = config["model"]

if model_config["name"] == "ssd_vgg16":
    model, label_maps, process_input_fn, image, bboxes, classes = inference_utils.inference_ssd_vgg16(config, args)
elif model_config["name"] == "ssd_mobilenetv1":
    model, label_maps, process_input_fn, image, bboxes, classes = inference_utils.inference_ssd_mobilenetv1(config, args)
elif model_config["name"] == "ssd_mobilenetv2":
    model, label_maps, process_input_fn, image, bboxes, classes = inference_utils.inference_ssd_mobilenetv2(config, args)
elif model_config["name"] == "tbpp_vgg16":
    model, label_maps, process_input_fn, image, quads, classes = inference_utils.inference_tbpp_vgg16(config, args)
    bboxes = textboxes_utils.get_bboxes_from_quads(quads)
else:
    print(f"model with name ${model_config['name']} has not been implemented yet")
    exit()

model.load_weights(args.weights)

display_image = image.copy()
image_height, image_width, _ = image.shape
height_scale, width_scale = input_size/image_height, input_size/image_width

image = cv2.resize(image, (input_size, input_size))
image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
image = process_input_fn(image)

image = np.expand_dims(image, axis=0)
y_pred = model.predict(image)

for i, bbox in enumerate(bboxes):
    xmin = int(bbox[0] - (bbox[2] / 2))
    ymin = int(bbox[1] - (bbox[3] / 2))
    xmax = int(bbox[0] + (bbox[2] / 2))
    ymax = int(bbox[1] + (bbox[3] / 2))
    if args.show_class_label:
        cv2.putText(
            display_image,
            classes[i],
            (int(xmin), int(ymin)),
            cv2.FONT_HERSHEY_PLAIN,
            1,
            (100, 100, 255),
            1,
            1
        )

    cv2.rectangle(
        display_image,
        (xmin, ymin),
        (xmax, ymax),
        (0, 0, 255),
        1
    )

for i, pred in enumerate(y_pred[0]):
    classname = label_maps[int(pred[0]) - 1].upper()
    confidence_score = pred[1]

    score = f"{'%.2f' % (confidence_score * 100)}%"
    print(f"-- {classname}: {score}")

    if confidence_score <= 1 and confidence_score > args.confidence_threshold:
        xmin = max(int(pred[2] / width_scale), 1)
        ymin = max(int(pred[3] / height_scale), 1)
        xmax = min(int(pred[4] / width_scale), image_width-1)
        ymax = min(int(pred[5] / height_scale), image_height-1)

        if args.show_class_label:
            cv2.putText(
                display_image,
                classname,
                (int(xmin), int(ymin)),
                cv2.FONT_HERSHEY_PLAIN,
                1,
                (100, 100, 255),
                1, 1)

        cv2.putText(
            display_image,
            score,
            (int(xmin), int(ymin)),
            cv2.FONT_HERSHEY_PLAIN,
            1,
            (100, 100, 255),
            1, 1)
        cv2.rectangle(
            display_image,
            (xmin, ymin),
            (xmax, ymax),
            (0, 255, 0),
            1)

cv2.imshow("image", display_image)
if cv2.waitKey(0) == ord('q'):
    cv2.destroyAllWindows()
