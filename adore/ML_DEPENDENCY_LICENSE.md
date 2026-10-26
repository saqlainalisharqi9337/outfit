# ML dependency license notes

The Adore ML service uses TensorFlow/Keras (Apache-2.0) for the clothing
classifiers. Optional object localisation uses **Ultralytics YOLO**, which is
licensed under **AGPL-3.0**.

## What this means for the FYP

- Ultralytics is used only as a **pretrained COCO detector**. No custom YOLO
  clothing model is trained in this project.
- If you distribute the ML service with Ultralytics included, AGPL-3.0 requires
  you to make the corresponding source of that combined work available under
  AGPL-3.0 (or obtain a commercial license from Ultralytics).
- The detector is **optional at runtime**. If `ultralytics` is not installed, or
  `models/yolov8n.pt` is absent, the service still runs using region proposals
  and MobileNetV2 classification.

This file exists so the AGPL-3.0 dependency is not silent. It is not legal
advice.
