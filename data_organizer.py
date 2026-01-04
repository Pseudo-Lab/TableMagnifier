import os
import re
import random
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple, Optional

class TableDataOrganizer:
    def __init__(self, data_root: str):
        """
        Initialize the organizer with the root data directory.
        Args:
            data_root: Path to the 'data' directory.
        """
        self.data_root = Path(data_root)
        self.grouped_data: Dict[str, List[str]] = defaultdict(list)
        self._organize_data()

    def _organize_data(self):
        """Scans the data directory and groups images by table ID."""
        # Public: P_origin_{group}_{table}_{index}.png or P_origin_{group}_{table}.png
        p_pattern = re.compile(r"P_origin_(\d+)_(\d+)(?:_(\d+))?\.png")
        
        # Insurance: I_table_{table}_{index}.png or I_table_{table}.png
        i_pattern = re.compile(r"I_table_(\d+)(?:_(\d+))?\.png")

        if not self.data_root.exists():
            print(f"Warning: Directory {self.data_root} does not exist.")
            return

        for root, _, files in os.walk(self.data_root):
            for file in files:
                if not file.endswith(".png"):
                    continue
                
                # Check Public pattern
                m_p = p_pattern.match(file)
                if m_p:
                    group_id = m_p.group(1)
                    table_id = m_p.group(2)
                    index = m_p.group(3)
                    
                    idx_val = int(index) if index is not None else -1
                    key = f"P_origin_{group_id}_{table_id}"
                    
                    abs_path = str(Path(root) / file)
                    self.grouped_data[key].append((idx_val, abs_path))
                    continue

                # Check Insurance pattern
                m_i = i_pattern.match(file)
                if m_i:
                    table_id = m_i.group(1)
                    index = m_i.group(2)
                    
                    idx_val = int(index) if index is not None else -1
                    key = f"I_table_{table_id}"
                    
                    abs_path = str(Path(root) / file)
                    self.grouped_data[key].append((idx_val, abs_path))
                    continue

        # Sort each group by index
        for key in self.grouped_data:
            # Sort by index (tuple first element)
            self.grouped_data[key].sort(key=lambda x: x[0])
            # Keep only paths
            self.grouped_data[key] = [item[1] for item in self.grouped_data[key]]

    def get_batches(self, 
                    sampling: bool = False, 
                    min_k: int = 2, 
                    max_k: int = 3, 
                    num_samples: int = 1,
                    pair_mode: bool = False) -> Dict[str, List[List[str]]]:
        """
        Generates batches of images for each table.
        
        Args:
            sampling: If True, randomly samples images. If False, returns all images as one batch.
            min_k: Minimum number of images to sample (inclusive, used if sampling=True).
            max_k: Maximum number of images to sample (inclusive, used if sampling=True).
            num_samples: Number of random batches to generate per table (used if sampling=True).
            pair_mode: If True, returns sequential pairs (e.g. indices 0-1, 2-3) regardless of sampling settings.
            
        Returns:
            A dictionary where keys are table identifiers and values are LISTS of image lists (batches).
            e.g. {
                "P_origin_1_11": [ ["path/to/img0", "path/to/img2"] ]
            }
        """
        results = {}

        for key, images in self.grouped_data.items():
            if pair_mode:
                # Pair mode: strictly sequential pairs [0,1], [2,3], ...
                # images are already sorted by index in _organize_data
                table_batches = []
                for i in range(0, len(images), 2):
                    batch = images[i : i + 2]
                    if batch:
                        table_batches.append(batch)
                results[key] = table_batches
                continue

            if not sampling:
                # Return all images as a single batch
                results[key] = [images]
            else:
                table_batches = []
                n_images = len(images)
                
                # If there are fewer images than min_k, we can't really "sample" between min_k and max_k 
                # strictly unless we allow duplicates or just take what we have.
                # Logic: if n_images < min_k, just use all images once (effectively no sampling choice).
                effective_min = min(n_images, min_k)
                effective_max = min(n_images, max_k)
                
                if n_images == 0:
                     results[key] = []
                     continue

                for _ in range(num_samples):
                    # Randomly choose k size
                    # If effective_min == effective_max, then k is fixed
                    k = random.randint(effective_min, effective_max) if effective_min <= effective_max else n_images
                    
                    # Sample k images
                    # Note: random.sample throws error if k > population
                    # We guarded with min(), so k <= n_images
                    if k > 0:
                        batch = sorted(random.sample(images, k))
                        table_batches.append(batch)
                    else:
                        # Should not happen typically unless file list is empty
                        table_batches.append([])
                
                results[key] = table_batches
                
        return results

    if __name__ == "__main__":
        # Test existing directory
        organizer = TableDataOrganizer("data")
        
        print("=== Default Mode (All Images) ===")
        batches_default = organizer.get_batches(sampling=False)
        # Print first 2 keys
        for k in list(batches_default.keys())[:2]:
            print(f"Table: {k}")
            for batch in batches_default[k]:
                print(f"  Batch size: {len(batch)}")
                # print(batch) # Uncomment to see paths

        print("\n=== Sampling Mode (2-3 images) ===")
        batches_sampled = organizer.get_batches(sampling=True, min_k=2, max_k=3, num_samples=2)
        for k in list(batches_sampled.keys())[:2]:
            print(f"Table: {k}")
            for i, batch in enumerate(batches_sampled[k]):
                print(f"  Sample {i+1}: size {len(batch)}")
                # print(batch) # Uncomment to see paths

        print("\n=== Pair Mode (Sequential 0-1, 2-3) ===")
        batches_pairs = organizer.get_batches(pair_mode=True)
        for k in list(batches_pairs.keys())[:2]:
            print(f"Table: {k}")
            for i, batch in enumerate(batches_pairs[k]):
                print(f"  Pair {i+1}: size {len(batch)}")
                # print(batch)
