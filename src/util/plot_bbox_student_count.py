import argparse
import os
import sys
from pathlib import Path

import cv2
import numpy as np
import torch

from generic_utilities import check_for_directory

# FILE = Path(__file__).resolve()
# ROOT = FILE.parents[0]  # YOLO root directory
# if str(ROOT) not in sys.path:
#     sys.path.append(str(ROOT))  # add ROOT to PATH
# ROOT = Path(os.path.relpath(ROOT, Path.cwd()))  # relative

# Ensure the parent directory is on the path for module imports.
current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from parameters import INSTITUTE

FILE = Path(__file__).resolve()
ROOT = FILE.parents[0]  # YOLO root directory
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))  # add ROOT to PATH
ROOT = Path(os.path.relpath(ROOT, Path.cwd()))  # relative

from StudentCount.yolov9.models.common import DetectMultiBackend
from StudentCount.yolov9.utils.general import non_max_suppression
from StudentCount.yolov9.utils.torch_utils import select_device


def count_detections_in_batch(
        date,
        lecture,
        classroom_name,
        weights='yolov9-e-converted.pt',  # model path or triton URL
        frames_with_filenames=None,  # list of tuples (filename, NumPy array)
        data=ROOT / 'data/coco.yaml',  # dataset.yaml path
        conf_thres=0.25,  # confidence threshold
        iou_thres=0.45,  # NMS IOU threshold
        max_det=100,  # maximum detections per image
        classes=0,  # filter by class: --class 0, or --class 0 2 3
        agnostic_nms=False,  # class-agnostic NMS
        augment=False,  # augmented inference
        visualize=False,  # visualize features
        half=False,  # use FP16 half-precision inference
        dnn=False  # use OpenCV DNN for ONNX inference
):
    if frames_with_filenames is None or len(frames_with_filenames) == 0:
        raise ValueError("Input frames list cannot be empty")

    # Sort frames by filenames (timestamps)
    frames_with_filenames.sort(key=lambda x: x[0])

    # Load model
    if torch.cuda.is_available():
        device = '0'
    else:
        device = 'cpu'
    
    device = select_device(device)
    model = DetectMultiBackend(weights, device=device, dnn=dnn, data=data, fp16=half, fuse=False)
    _, names, pt = model.stride, model.names, model.pt

    detection_counts = []

    # Process each frame in the batch
    for filename, im0s in frames_with_filenames:
        frame_count = 0
        if not isinstance(im0s, np.ndarray):
            raise ValueError("Input frames must be NumPy arrays")

        # Transpose dimensions to have channels last
        im0s = cv2.resize(im0s, (2304, 1312))
        im1s = np.transpose(im0s, (2, 0, 1))

        # Convert to tensor
        im1s = torch.from_numpy(im1s).float().to(device)
        im1s /= 255.0  # Normalize to [0,1]

        # Add batch dimension
        im1s = im1s.unsqueeze(0)

        # Inference
        with torch.no_grad():
            predictions = model(im1s, augment=augment, visualize=visualize)

        # NMS
        predictions = non_max_suppression(predictions[0], conf_thres, iou_thres, classes, agnostic_nms, max_det=max_det)

        for det in predictions:
            if det is not None:
                for *xyxy, conf, cls in det:
                    xyxy = [int(x) for x in xyxy]
                    cv2.rectangle(im0s, (xyxy[0], xyxy[1]), (xyxy[2], xyxy[3]), (255, 0, 0), 2)
                    frame_count += 1

        detection_counts.append(frame_count)

        cv2.putText(im0s, f"Students Detected: {frame_count}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 3, cv2.LINE_AA)
        directory_path = f"/workspace/CLASSROOM-ATTENDANCE-TESTING/{date}/Lecture_{lecture}/Classroom_{classroom_name}/CountingFrames/Inferred_Frames"
        check_for_directory(directory_path)
        output_filename = f"/workspace/CLASSROOM-ATTENDANCE-TESTING/{date}/Lecture_{lecture}/Classroom_{classroom_name}/CountingFrames/Inferred_Frames/{os.path.basename(filename)}"
        cv2.imwrite(output_filename, im0s)  # Save image with bounding boxes

    # Pair frames and print the sum of counts
    for i in range(0, len(detection_counts), 2):
        pair_count = detection_counts[i] + (detection_counts[i + 1] if i + 1 < len(detection_counts) else 0)
        print(f"CYCLE {i // 2 + 1:<3}: Total number of Students detected is {pair_count:3}")


def load_images_from_folder(folder):
    images = []
    for filename in os.listdir(folder):
        img_path = os.path.join(folder, filename)
        if os.path.isfile(img_path):
            img = cv2.imread(img_path)
            if img is not None:
                images.append((filename, img))

    return images


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Student Detection")
    parser.add_argument("--date", type=str, help="Date of the lecture")
    parser.add_argument("--lecture", type=int, help="Lecture number")
    parser.add_argument("--classroom", type=str, default="2F-32" if INSTITUTE == "ABESIT" else "AB-1_319", help="Name of the classroom")
    args = parser.parse_args()

    folder_path = f"/workspace/CLASSROOM-ATTENDANCE-TESTING/{args.date}/Lecture_{args.lecture}/Classroom_{args.classroom}/CountingFrames/Raw_Frames"
    images_with_filenames = load_images_from_folder(folder_path)
    count_detections_in_batch(weights='yolov9-e-converted.pt', frames_with_filenames=images_with_filenames, date=args.date, lecture=args.lecture, classroom_name=args.classroom)
