from music21 import *
import numpy as np
from typing import Tuple, List, Dict, Set
from collections import defaultdict

class MusicMatrixRepresentation:
    def __init__(self, key_signature, time_signature, quantization, piano_roll, onset_map, durations_matrix):
        self.key_signature = key_signature
        self.time_signature = time_signature
        self.quantization = quantization
        self.piano_roll = piano_roll
        self.onset_map = onset_map
        self.durations_matrix = durations_matrix

    def reconstruct_piano_roll(self) -> np.ndarray:
        """Reconstruct piano roll from durations matrix."""
        new_piano_roll = np.zeros_like(self.durations_matrix)
        rows, cols = self.durations_matrix.shape

        for r in range(rows):
            c = 0
            while c < cols:
                dur = int(self.durations_matrix[r, c])
                if dur == 0:
                    c += 1
                else:
                    x = c
                    for dx in range(dur):
                        if (x+dx) >= cols:
                            break
                        new_piano_roll[r, x+dx] = 1
                    c += dur

        return new_piano_roll

    def flatten_durations(self) -> Tuple[List[int], Dict[int, List[int]]]:
        """Flatten the durations matrix into a list and create a time-to-pitches mapping."""
        flat = [int(x) for x in self.durations_matrix[0]]
        hashmap = defaultdict(list)

        for ri, ci in np.ndindex(self.durations_matrix.shape):
            if self.durations_matrix[ri, ci] != 0:
                if flat[ci] == 0:
                    flat[ci] = int(self.durations_matrix[ri, ci])
                hashmap[ci].append(ri)

        return flat, hashmap

    def find_duplicate_length_ranges(self, durations_list: List[int]) -> List[Tuple[int, int, int]]:
        """Find ranges of duplicate lengths in the durations list."""
        windows = []
        curr_val_count = 0
        curr_val = -1
        i = 0
        j = 0

        while j < len(durations_list):
            if durations_list[j] > 0:
                if curr_val < 0:
                    curr_val = durations_list[j]
                    curr_val_count += 1
                    i = j
                elif durations_list[j] == curr_val:
                    curr_val_count += 1
                else:
                    if curr_val_count > 1:
                        windows.append((i, j, curr_val_count))
                    curr_val = durations_list[j]
                    curr_val_count = 1
                    i = j
            j += 1

        if curr_val_count > 1:
            windows.append((i, j, curr_val_count))

        return windows 