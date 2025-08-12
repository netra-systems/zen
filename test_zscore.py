import numpy as np

values = [10, 10, 10, 10, 10, 10, 10, 10, 10, 51]
arr = np.array(values)
mean = np.mean(arr)
std = np.std(arr)
print(f'Mean: {mean}, Std: {std}')
z = abs((51 - mean) / std) if std != 0 else 0
print(f'Z-score for 51: {z}')
print(f'Threshold is 3, detected: {z > 3}')