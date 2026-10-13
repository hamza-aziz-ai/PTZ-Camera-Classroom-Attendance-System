import os
import sys
from pathlib import Path
import numpy as np

import torch

FILE = Path(__file__).resolve()
ROOT = FILE.parents[0]  # YOLO root directory
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))  # add ROOT to PATH
ROOT = Path(os.path.relpath(ROOT, Path.cwd()))  # relative

from models.common import DetectMultiBackend
from utils.general import non_max_suppression
from utils.torch_utils import select_device


def person_detection(
        weights='yolov9-e-converted.pt',  # model path or triton URL
        frames=None,  # list of NumPy arrays for the batch of frames
        data=ROOT / 'data/coco.yaml',  # dataset.yaml path
        conf_thres=0.25,  # confidence threshold
        iou_thres=0.45,  # NMS IOU threshold
        max_det=100,  # maximum detections per image
        model_device='',  # cuda device, i.e. 0 or 0,1,2,3 or cpu
        classes=0,  # filter by class: --class 0, or --class 0 2 3
        agnostic_nms=False,  # class-agnostic NMS
        augment=False,  # augmented inference
        visualize=False,  # visualize features
        dnn=False,  # use OpenCV DNN for ONNX inference
        half=True  # use FP16 half-precision inference
):
    if frames is None or len(frames) == 0:
        raise ValueError("Input frames list cannot be empty")

    count = 0

    # Load model
    if torch.cuda.is_available():
        model_device = '0'
    else:
        model_device = 'cpu'

    device = select_device(model_device)
    model = DetectMultiBackend(weights, device=device, dnn=dnn, data=data, fp16=half, fuse=False)
    _, names, pt = model.stride, model.names, model.pt

    # Process each frame in the batch
    for im0s in frames:
        if not isinstance(im0s, np.ndarray):
            raise ValueError("Input frames must be NumPy arrays")

        # Transpose dimensions to have channels last
        im0s = np.transpose(im0s, (2, 0, 1))
        # print(im0s.shape)

        # Convert to tensor
        im0s = torch.from_numpy(im0s).float().to(device)  # Add method for GPU (CUDA Device)
        im0s /= 255.0  # Normalize to [0,1]

        # Add batch dimension
        im0s = im0s.unsqueeze(0)
        # print(im0s.shape)

        # Inference
        with torch.no_grad():
            pred = model(im0s, augment=augment, visualize=visualize)

        # NMS
        pred = non_max_suppression(pred[0], conf_thres, iou_thres, classes, agnostic_nms, max_det=max_det)

        # Count detections
        for det in pred:
            if det is not None:
                for *xyxy, conf, cls in det:
                    count += 1

    # print(batch_count)
    return count
