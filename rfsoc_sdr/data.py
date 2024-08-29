import numpy as np
import matplotlib.pyplot as plt
import commpy as cp
from scipy.io import savemat, loadmat
import scipy.signal as sig

# Utility
from time import sleep
import os


def concat(array16):
    """
    Constructs an int32 array from an int16 array by concatenating pairs of elements.

    Parameters
    ----------
    array16 : 1-D ndarray (int16)
        Array of int16 elements.

    Returns
    -------
    array32 : 1-D ndarray (int32)
        Array containing the concatenation of pairs of 16-bit int elements.
    """

    N = int(array16.size//2)
    array32 = np.zeros(N, dtype=np.int32)
    for n in range(N):
        array32[n] = ((array16[2*n+1] << 16) & 0xFFFF_0000) | ((array16[2*n]) & 0x0000_FFFF)
    return array32

def sin_gen(Fs=1024e6, f=6.4e6, number_of_periods=10, plot=False):
    # if ((Fs/f) % 1 != 0):
    #     print("The number of 16 bits samples in one period must be an integer ! Fs/f = ",  Fs / f)
    N_one_period = int(Fs / f)
    N = int(number_of_periods * Fs / f)
    # print("N = ", N)
    max_val_16bit_signed = 2**13 - 1
    sinus = np.zeros(N, dtype=np.int16)
    for n in range(N):
        value = np.sin(2 * np.pi * f * n / Fs) * max_val_16bit_signed
        sinus[n] = int(value) << 2
    if (plot):
        plt.plot(sinus[:N_one_period])
        plt.show()
    sinus_32bit = np.zeros(N // 2, dtype=np.int32)
    for i in range(0, N, 2):
        high = np.int32(sinus[i + 1]) << 16
        low = np.int32(sinus[i] & 0xFFFF)
        sinus_32bit[i // 2] = high | low
    return sinus_32bit


def LPF(signal, fc, Fs):
    """ Low Pass Filter """
    o = 5  # order of the filter
    fc = np.array([fc])
    wn = 2 * fc / Fs
    [b, a] = sig.butter(o, wn, btype='lowpass')
    [W, h] = sig.freqz(b, a, worN=1024)
    W = Fs * W / (2 * np.pi)
    signal_filt = sig.lfilter(b, a, signal)
    return signal_filt, W, h


# def qam_gen(N=6400, mod_order=16, samples_per_symbol=4, rolloff_factor=0.25, filter_span=20, plot=False):
#     """Generate a 1-D ndarray of np.int32 data of QAM modulation for the DAC insite an RFSOC (Xinlinx FPGA)

#     Args:
#         N (int, optional): Number of symbols. Defaults to 6400.
#         mod_order (int, optional): 16 or 64 or ... . Defaults to 16.
#         samples_per_symbol (int, optional): 4, 8, 16 (4, 8, 16 for the respective interpolation factors 8, 4, 2). Defaults to 4.
#         rolloff_factor (float, optional): rolloff_factor/alpha parameters for the Raised Root Cosine Filter (RRC). Defaults to 0.25.
#         filter_span (int, optional): filter span. Defaults to 20.
#         plot (bool, optional): Plotting option. Defaults to False.

#     Returns:
#         data, rrc_filter, normalization_factor : the 32 bits data array, the rrc filter coeff and the normalization factor
#     """
#     symbol_rate = 1
#     num_taps = filter_span * samples_per_symbol + 1

#     # Generation of bits and QAM symbols
#     bits = np.random.randint(0, 2, int(N * np.log2(mod_order)))
#     QAMModem = cp.modulation.QAMModem(mod_order)
#     symbols = QAMModem.modulate(bits)

#     if (plot):
#         plt.scatter(np.real(symbols), np.imag(symbols))
#         plt.title("QAM Symbol Constellation")
#         plt.show()

#     # Design of the RRC filter
#     time_idx, rrc_filter = cp.filters.rrcosfilter(
#         num_taps, rolloff_factor, samples_per_symbol, symbol_rate)

#     if (plot):
#         plt.plot(time_idx, rrc_filter)
#         plt.title("Raised Cosine Response (RRC) Filter")
#         plt.show()

#     # Upsampling of symbols
#     upsampled_symbols = np.zeros(N * samples_per_symbol, dtype=complex)
#     upsampled_symbols[::samples_per_symbol] = symbols

#     if (plot):
#         plt.scatter(np.real(upsampled_symbols), np.imag(upsampled_symbols))
#         plt.title("Symbols after Upsampling")
#         plt.show()

#     # Filtering the upsampled signal
#     filtered_signal = np.convolve(upsampled_symbols, rrc_filter, 'same')

#     if (plot):
#         print("After convolution: ")
#         plot_fft(filtered_signal, symbol_rate)

#     # Normalization and conversion of signal to int16 format
#     normalization_factor = 32767 / np.max(np.abs(filtered_signal))
#     IQ_signal = filtered_signal * normalization_factor
#     I_signal = IQ_signal.real.astype(np.int16)
#     Q_signal = IQ_signal.imag.astype(np.int16)

#     if (plot):
#         plt.scatter(I_signal, Q_signal)
#         plt.title("Constellation after Convolution with RRC Filter")
#         plt.show()

#     data = np.zeros(int(I_signal.size), dtype=np.int32)
#     for n in range(I_signal.size):
#         data[n] = ((I_signal[n] << 16) & 0xFFFF_0000) | (
#             (Q_signal[n]) & 0x0000_FFFF)

#     return data, rrc_filter, normalization_factor

# def mat_to_numpy(file_path): NOT WORKING PLEASE SEE README
#     """
#     Load a .mat file containing a complex array and convert it to a numpy array.
    
#     Parameters:
#     file_path (str): Path to the .mat file.
    
#     Returns:
#     numpy.ndarray: Numpy array containing the complex data.
#     """
#     # Load the .mat file
#     mat_data = loadmat(file_path)
    
#     complex_array = None
#     for key, value in mat_data.items():
#         if np.iscomplexobj(value):
#             complex_array = np.array(value, dtype=np.complex_)
#             break
    
#     if complex_array is None:
#         raise ValueError("No complex array found in the .mat file.")
    
#     return complex_array


def complex_to_dc_32bits_format(complex_array):
    data = np.zeros(complex_array.size, dtype=np.int32)
    for n in range(complex_array.size):
        data[n] = ((np.real(complex_array[n]) << 16) & 0xFFFF_0000) | ((np.imag(complex_array[n])) & 0x0000_FFFF)
    return data

def mat_to_dc_data(file_path):
    return complex_to_dc_32bits_format(mat_to_numpy(file_path))


def random_bit(N=256):
    return np.random.randint(0, 2, N)


def qam16symbols(N=1024, plot=False):
    # Generate 16-QAM symbols
    qam_scheme = [-3-3j, -3-1j, -3+3j, -3+1j,
                  -1-3j, -1-1j, -1+3j, -1+1j,
                  3-3j,  3-1j,  3+3j,  3+1j,
                  1-3j,  1-1j,  1+3j,  1+1j]
    ints = np.random.randint(0, 16, N)
    qam_symbols = [qam_scheme[i] for i in ints]
    if (plot):
        # Plot the mapped symbols
        plt.figure(figsize=(5, 5))
        plt.scatter(np.real(qam_symbols), np.imag(qam_symbols))
        plt.title('16-QAM constellation diagram')
        plt.xlabel('Channel 1 amplitude')
        plt.ylabel('Channel 2 amplitude')
        plt.grid()
        plt.show()
    return qam_symbols


def complex_noise(N, noise_power):
    complex_noise = np.sqrt(noise_power/2)*(np.random.randn(N) +
                                            np.random.randn(N)*1j)
    return complex_noise


def awgn(signal, snr=20):
    sig_power = np.mean(np.abs(signal)**2)
    sig_power_db = 10 * np.log10(sig_power)

    noise_power_db = sig_power_db - snr
    noise_power = 10**(noise_power_db / 10)

    complex_noise = np.sqrt(noise_power/2)*(np.random.randn(len(signal)) +
                                            np.random.randn(len(signal))*1j)

    return signal + complex_noise


def calculate_evm(symbols_tx, symbols_rx):
    evm_rms = np.sqrt(np.mean(np.abs(symbols_rx - symbols_tx)**2)) / \
        np.sqrt(np.mean(np.abs(symbols_tx)**2))

    return evm_rms*100


def upsampler(Ns, K, symbols):
    up = np.zeros(Ns * K)
    up[::K] = symbols
    return up


def check_storage_capacity(array):
    """ array must be fill with 32 bits data, the return value is in Mbytes"""
    size = array.size * 32 / (8e6)  # Mbytes
    return size


#####################################################################################################################################################

######## PLOT FUNCTIONS ##############

#####################################################################################################################################################

def plot_32bits(bram_data):
    bram_data_16 = np.zeros(int(bram_data.size * 2), np.int16)

    for n in range(int(bram_data.size)):
        bram_data_16[n*2 + 0] = np.int16(bram_data[n] & 0xFFFF)
        bram_data_16[n*2 + 1] = np.int16((bram_data[n] >> 16) & 0xFFFF)

    plt.plot(bram_data_16)
    plt.show()


def plot_fft(signal, Fs=1, M=0, title="FFT", opt="log"):
    if M == 0:
        M = signal.size
    if (opt == "log"):
        y = 10*np.log10(np.abs(np.fft.fftshift(np.fft.fft(signal, M))))
    elif (opt == "lin"):
        y = np.abs(np.fft.fftshift(np.fft.fft(signal, M)))
    else:
        return
    plt.plot(np.linspace(-Fs / 2, Fs / 2, M), y)
    plt.title(title)
    plt.xlabel("f (Hz)")
    plt.ylabel(f"Amplitude ({opt})")
    plt.show()


def plot_scatter(signal, title="constellation"):
    plt.scatter(np.real(signal), np.imag(signal))
    plt.title(title)
    plt.xlabel("I")
    plt.ylabel("Q")
    plt.plot()
    plt.show()


#####################################################################################################################################################

# Write/Read files funcitons

#####################################################################################################################################################


def write_file(file_name, data):
    with open(file_name, "w") as f:
        for value in data:
            f.write(f"{value}\n")


def write_file_signed_hex(file_name, data):
    with open(file_name, "w") as f:
        for value in data:
            f.write(f"{value:08X}\n")


def read_file(file_name):
    with open(file_name, "r") as f:
        data = [int(line.strip()) for line in f]
    return np.array(data, dtype=np.int32)


def read_hex_file_to_numpy_array(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()
    data = [int(line.strip().rstrip(','), 16) for line in lines]
    numpy_array = np.array(data, dtype=np.uint32)

    return numpy_array


def save_numpy_to_mat(filename, array):
    savemat(filename, {'data': array})
