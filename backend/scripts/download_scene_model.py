#!/usr/bin/env python3
"""
Download Places365 scene classification model for MemoLens.

This script downloads:
1. ResNet18 weights trained on Places365
2. Places365 category labels

Run with: python scripts/download_scene_model.py
"""

import os
import sys
import urllib.request
from pathlib import Path

# URLs for Places365 resources
# Using the official MIT Places365 weights
PLACES365_RESNET18_URL = "http://places2.csail.mit.edu/models_places365/resnet18_places365.pth.tar"
PLACES365_CATEGORIES_URL = "https://raw.githubusercontent.com/CSAILVision/places365/master/categories_places365.txt"

# Alternative: Simplified indoor scene categories
INDOOR_CATEGORIES = """
kitchen
bedroom
bathroom
living_room
dining_room
office
hallway
entrance
garage
laundry_room
""".strip()


def download_file(url: str, dest_path: Path, desc: str = "file") -> bool:
    """Download a file with progress indicator."""
    print(f"Downloading {desc}...")
    print(f"  URL: {url}")
    print(f"  Destination: {dest_path}")
    
    try:
        def report_progress(block_num, block_size, total_size):
            if total_size > 0:
                downloaded = block_num * block_size
                percent = min(100, downloaded * 100 / total_size)
                mb_downloaded = downloaded / (1024 * 1024)
                mb_total = total_size / (1024 * 1024)
                print(f"\r  Progress: {percent:.1f}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)", end="", flush=True)
        
        urllib.request.urlretrieve(url, dest_path, reporthook=report_progress)
        print("\n  Done!")
        return True
    except Exception as e:
        print(f"\n  Failed: {e}")
        return False


def setup_models_directory() -> Path:
    """Ensure the models directory exists."""
    # Go up from scripts/ to backend/, then into models/
    script_dir = Path(__file__).parent
    models_dir = script_dir.parent / "models"
    models_dir.mkdir(exist_ok=True)
    return models_dir


def convert_places365_weights(tar_path: Path, output_path: Path) -> bool:
    """Convert Places365 tar weights to standard PyTorch format."""
    try:
        import torch
        
        print(f"Converting weights to standard format...")
        
        # Load the tar checkpoint
        checkpoint = torch.load(tar_path, map_location="cpu")
        
        # Extract state dict (Places365 uses 'state_dict' key)
        if "state_dict" in checkpoint:
            state_dict = checkpoint["state_dict"]
        else:
            state_dict = checkpoint
        
        # Remove 'module.' prefix if present (from DataParallel)
        new_state_dict = {}
        for k, v in state_dict.items():
            name = k.replace("module.", "")
            new_state_dict[name] = v
        
        # Save in standard format
        torch.save(new_state_dict, output_path)
        print(f"  Saved to: {output_path}")
        
        # Remove original tar file
        tar_path.unlink()
        print(f"  Removed temporary file: {tar_path}")
        
        return True
    except Exception as e:
        print(f"  Conversion failed: {e}")
        return False


def download_places365_model(models_dir: Path) -> bool:
    """Download and set up Places365 ResNet18 model."""
    output_path = models_dir / "scene_resnet18_places365.pth"
    
    if output_path.exists():
        print(f"Model already exists: {output_path}")
        return True
    
    # Download to temporary tar file
    tar_path = models_dir / "resnet18_places365.pth.tar"
    
    if not download_file(PLACES365_RESNET18_URL, tar_path, "Places365 ResNet18 weights"):
        print("\nFailed to download Places365 model.")
        print("The system will fall back to ImageNet-based heuristics.")
        return False
    
    # Convert to standard format
    return convert_places365_weights(tar_path, output_path)


def download_categories(models_dir: Path) -> bool:
    """Download Places365 category labels."""
    output_path = models_dir / "places365_categories.txt"
    
    if output_path.exists():
        print(f"Categories file already exists: {output_path}")
        return True
    
    if not download_file(PLACES365_CATEGORIES_URL, output_path, "Places365 categories"):
        print("\nFailed to download categories. Creating simplified version...")
        # Create simplified indoor categories as fallback
        output_path.write_text(INDOOR_CATEGORIES)
        print(f"  Created simplified categories: {output_path}")
    
    return True


def main():
    print("=" * 60)
    print("MemoLens Scene Classification Model Setup")
    print("=" * 60)
    print()
    
    # Check for PyTorch
    try:
        import torch
        print(f"PyTorch version: {torch.__version__}")
    except ImportError:
        print("ERROR: PyTorch is not installed.")
        print("Install with: pip install torch torchvision")
        sys.exit(1)
    
    models_dir = setup_models_directory()
    print(f"Models directory: {models_dir}")
    print()
    
    # Download model
    print("-" * 40)
    print("Step 1: Download scene classification model")
    print("-" * 40)
    model_ok = download_places365_model(models_dir)
    print()
    
    # Download categories
    print("-" * 40)
    print("Step 2: Download category labels")
    print("-" * 40)
    categories_ok = download_categories(models_dir)
    print()
    
    # Summary
    print("=" * 60)
    print("Setup Summary")
    print("=" * 60)
    print(f"  Model downloaded: {'Yes' if model_ok else 'No (will use ImageNet fallback)'}")
    print(f"  Categories file:  {'Yes' if categories_ok else 'No'}")
    print()
    
    if model_ok and categories_ok:
        print("Scene classification is ready!")
        print("Detected items will now be tagged with room locations.")
    else:
        print("Scene classification will use ImageNet-based heuristics.")
        print("For better accuracy, ensure the model download completes.")
    
    return 0 if model_ok else 1


if __name__ == "__main__":
    sys.exit(main())
