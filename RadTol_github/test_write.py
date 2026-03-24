import numpy as np

data = np.array([1, 2, 3])
header = ['Test1', 'Test2', 'Test3']

np.savetxt(f'ProbeStation/DG028/test.csv', data, delimiter=",", header=",".join(header), comments='')
