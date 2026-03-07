# MemoLens CV Starter

This folder contains local CV helpers for object and face signal generation.

## Quick run

```bash
cd cv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python object_detection/yolo_detector.py --image /path/to/image.jpg --tracked-items keys,phone,wallet
```

If `ultralytics` is unavailable, detector returns an empty list instead of crashing.
