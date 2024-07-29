import numpy as np
from scipy.io import loadmat

def mat_to_numpy32(file_path):
    """
    Load a .mat file containing a complex array and convert it to a numpy array (dtype = np.int32 ready for loading).
    
    Parameters:
    file_path (str): Path to the .mat file.
    
    Returns:
    numpy.ndarray: Numpy array containing the complex data.
    """
    # Load the .mat file
    mat_data = loadmat(file_path)
    
    complex_array = None
    for key, value in mat_data.items():
        if np.iscomplexobj(value):
            complex_array = np.array(value, dtype=np.complex_)
            break
    
    if complex_array is None:
        raise ValueError("No complex array found in the .mat file.")

    data = np.zeros(complex_array.size, dtype=np.int32)
    for n in range(complex_array.size):
        data[n] = ((np.real(complex_array[n]) << 16) & 0xFFFF_0000) | ((np.imag(complex_array[n])) & 0x0000_FFFF)

    return data

