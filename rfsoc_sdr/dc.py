# All my funciton for the Data Converter Settings
# Some are redefined as methods of the SdrOVerlay class !

# MATH AND PLOT
import numpy as np
import matplotlib.pyplot as plt
import commpy as cp
from scipy.io import savemat
import scipy.signal as sig

# PYNQ
from pynq import Overlay
from pynq import MMIO
from pynq import allocate
import xrfclk
import xrfdc

# Utility 
from time import sleep
import os

def print_lmx_lmk():
    """ Show the available lmx and lmk clock available on the board """
    files = sorted(os.listdir(os.path.dirname(xrfclk.__file__)))
    for file in files:
        if 'LMK' in file or 'LMX' in file:
            print(file)

# def block_Freq(block: xrfdc.RFdcDacBlock, Freq):
#     """ Set the frequency of a block, Freq in MHz"""
#     # https://github.com/Xilinx/PYNQ/tree/master/sdbuild/packages/xrfdc/package
#     block.MixerSettings['Freq'] = Freq
#     block.UpdateEvent(xrfdc.EVENT_MIXER)
    
# def set_interpolation(rfdc, tile, interpolation_factor, dacs_index = [0,1,2]):
#     """
#     Set the Interpolation fot the entire tile dacs, following the procedure pg269 v2.6 p292
    
#     Parameters
#     ----------
    
#     tile : int
#         0 or 1.
    
#     interpolation_factor : int
#         2, 4 or 8.
        
#     dacs_index : 1-D ndarray (int)
#         An array fill with the active DAC indexes
    
#     Example
#     -------
    
#     If you have DAC 00 and DAC 01 active : tile = 0 dac_index = [0,1]
    
#     """
#     tile_valid = {0,1}
#     interpolation_valid = {2,4,8}
#     if tile not in tile_valid:
#         raise ValueError(f"valid tile values: {tile_valid}")
#     if interpolation_factor not in interpolation_valid:
#         raise ValueError(f"valid interpolation values: {interpolation_valid}")

#     rfdc.dac_tiles[tile].SetupFIFO(False)
#     if (interpolation_factor == 2):
#         rfdc.dac_tiles[tile].FabClkOutDiv = 2
#     elif (interpolation_factor == 4):
#         rfdc.dac_tiles[tile].FabClkOutDiv = 3
#     else: # 8
#         rfdc.dac_tiles[tile].FabClkOutDiv = 4
        
#     rfdc.dac_tiles[tile].InterpolationFactor = interpolation_factor
#     for dac_index in dacs_index:
#         rfdc.dac_tiles[tile].blocks[dac_index].InterpolationFactor = interpolation_factor
#     for dac_index in dacs_index:
#         rfdc.adc_tiles[tile].blocks[dac_index].IntrClr = 4294967295     
#     rfdc.dac_tiles[tile].SetupFIFO(True)

    
### MMIO READ WRITE ###

# Write :

def dac_bram_write(bram_mmio, bram_data):
    """ Write the content of a 1-D ndarray into a PL Ram (BRAM or Uram)"""
    # FIFO 1024 to 256
    bram_word_size = int(1024)
    ratio = int(bram_word_size/32)
    for n in range(int(bram_data.size // (ratio))):
        bram_mmio.write(n*ratio*4 + 8*3*4 + 0*4, int(bram_data[n*ratio + 0] )& 0xFFFFFFFF)
        bram_mmio.write(n*ratio*4 + 8*3*4 + 1*4, int(bram_data[n*ratio + 1] )& 0xFFFFFFFF)
        bram_mmio.write(n*ratio*4 + 8*3*4 + 2*4, int(bram_data[n*ratio + 2] )& 0xFFFFFFFF)
        bram_mmio.write(n*ratio*4 + 8*3*4 + 3*4, int(bram_data[n*ratio + 3] )& 0xFFFFFFFF)
        bram_mmio.write(n*ratio*4 + 8*3*4 + 4*4, int(bram_data[n*ratio + 4] )& 0xFFFFFFFF)
        bram_mmio.write(n*ratio*4 + 8*3*4 + 5*4, int(bram_data[n*ratio + 5] )& 0xFFFFFFFF)
        bram_mmio.write(n*ratio*4 + 8*3*4 + 6*4, int(bram_data[n*ratio + 6] )& 0xFFFFFFFF)
        bram_mmio.write(n*ratio*4 + 8*3*4 + 7*4, int(bram_data[n*ratio + 7] )& 0xFFFFFFFF)
        
        bram_mmio.write(n*ratio*4 + 8*2*4 + 0*4, int(bram_data[n*ratio + 8] )& 0xFFFFFFFF)
        bram_mmio.write(n*ratio*4 + 8*2*4 + 1*4, int(bram_data[n*ratio + 9] )& 0xFFFFFFFF)
        bram_mmio.write(n*ratio*4 + 8*2*4 + 2*4, int(bram_data[n*ratio + 10]) & 0xFFFFFFFF)
        bram_mmio.write(n*ratio*4 + 8*2*4 + 3*4, int(bram_data[n*ratio + 11]) & 0xFFFFFFFF)
        bram_mmio.write(n*ratio*4 + 8*2*4 + 4*4, int(bram_data[n*ratio + 12]) & 0xFFFFFFFF)
        bram_mmio.write(n*ratio*4 + 8*2*4 + 5*4, int(bram_data[n*ratio + 13]) & 0xFFFFFFFF)
        bram_mmio.write(n*ratio*4 + 8*2*4 + 6*4, int(bram_data[n*ratio + 14]) & 0xFFFFFFFF)
        bram_mmio.write(n*ratio*4 + 8*2*4 + 7*4, int(bram_data[n*ratio + 15]) & 0xFFFFFFFF)

        bram_mmio.write(n*ratio*4 + 8*1*4 + 0*4, int(bram_data[n*ratio + 16]) & 0xFFFFFFFF)
        bram_mmio.write(n*ratio*4 + 8*1*4 + 1*4, int(bram_data[n*ratio + 17]) & 0xFFFFFFFF)
        bram_mmio.write(n*ratio*4 + 8*1*4 + 2*4, int(bram_data[n*ratio + 18]) & 0xFFFFFFFF)
        bram_mmio.write(n*ratio*4 + 8*1*4 + 3*4, int(bram_data[n*ratio + 19]) & 0xFFFFFFFF)
        bram_mmio.write(n*ratio*4 + 8*1*4 + 4*4, int(bram_data[n*ratio + 20]) & 0xFFFFFFFF)
        bram_mmio.write(n*ratio*4 + 8*1*4 + 5*4, int(bram_data[n*ratio + 21]) & 0xFFFFFFFF)
        bram_mmio.write(n*ratio*4 + 8*1*4 + 6*4, int(bram_data[n*ratio + 22]) & 0xFFFFFFFF)
        bram_mmio.write(n*ratio*4 + 8*1*4 + 7*4, int(bram_data[n*ratio + 23]) & 0xFFFFFFFF)
        
        bram_mmio.write(n*ratio*4 + 0*4, int(bram_data[n*ratio + 24]) & 0xFFFFFFFF)
        bram_mmio.write(n*ratio*4 + 1*4, int(bram_data[n*ratio + 25]) & 0xFFFFFFFF)
        bram_mmio.write(n*ratio*4 + 2*4, int(bram_data[n*ratio + 26]) & 0xFFFFFFFF)
        bram_mmio.write(n*ratio*4 + 3*4, int(bram_data[n*ratio + 27]) & 0xFFFFFFFF)
        bram_mmio.write(n*ratio*4 + 4*4, int(bram_data[n*ratio + 28]) & 0xFFFFFFFF)
        bram_mmio.write(n*ratio*4 + 5*4, int(bram_data[n*ratio + 29]) & 0xFFFFFFFF)
        bram_mmio.write(n*ratio*4 + 6*4, int(bram_data[n*ratio + 30]) & 0xFFFFFFFF)
        bram_mmio.write(n*ratio*4 + 7*4, int(bram_data[n*ratio + 31]) & 0xFFFFFFFF)

def ddr4_write(ddr4_mmio, data):
    # FIFO 512 to 256
    for n in range(int(data.size/16)):
        ddr4_mmio.write(n*16*4 + 4*0, int(data[n*16 +8]))
        ddr4_mmio.write(n*16*4 + 4*1, int(data[n*16 +9]))
        ddr4_mmio.write(n*16*4 + 4*2, int(data[n*16 +10]))
        ddr4_mmio.write(n*16*4 + 4*3, int(data[n*16 +11]))
        ddr4_mmio.write(n*16*4 + 4*4, int(data[n*16 +12]))
        ddr4_mmio.write(n*16*4 + 4*5, int(data[n*16 +13]))
        ddr4_mmio.write(n*16*4 + 4*6, int(data[n*16 +14]))
        ddr4_mmio.write(n*16*4 + 4*7, int(data[n*16 +15]))

        ddr4_mmio.write(n*16*4 + 4*8, int(data[n*16 +0]))
        ddr4_mmio.write(n*16*4 + 4*9, int(data[n*16 +1]))
        ddr4_mmio.write(n*16*4 + 4*10, int(data[n*16 +2]))
        ddr4_mmio.write(n*16*4 + 4*11, int(data[n*16 +3]))
        ddr4_mmio.write(n*16*4 + 4*12, int(data[n*16 +4]))
        ddr4_mmio.write(n*16*4 + 4*13, int(data[n*16 +5]))
        ddr4_mmio.write(n*16*4 + 4*14, int(data[n*16 +6]))
        ddr4_mmio.write(n*16*4 + 4*15, int(data[n*16 +7]))

# Read

# def set_bram_adc_capture_maximum(counter_mmio, max):
#     counter_mmio.write(0x00, int(max))
    
# def start_bram_adc_capture(counter_mmio):
#     counter_mmio.write(0x04, 0x0)
#     sleep(0.5)
#     counter_mmio.write(0x04, 0x1)
#     sleep(0.5)

# def adc_bram_refresh(counter_mmio, max):
#     """Set the maximum of the Bram ADC Capture block and restart the capture """
#     set_bram_adc_capture_maximum(counter_mmio, max)
#     start_bram_adc_capture(counter_mmio)

def adc_bram_read(bram_mmio, number_of_32_bits_samples):
    """ Only for REAL DATA """
    number_of_16_bits_samples = 2 * number_of_32_bits_samples
    adc_data_read = np.zeros(number_of_16_bits_samples, np.int16)

    for i in range(0, int(number_of_16_bits_samples//2)):
        current_data = bram_mmio.read(i*4) & 0xFFFFFFFF
        current_data = bram_mmio.read(i*4) & 0xFFFFFFFF
        low = current_data & 0x0000_FFFF
        high = (current_data >> 16) & 0x0000_FFFF
        adc_data_read[i*2 + 0] = np.int16(low)
        adc_data_read[i*2 + 1] = np.int16(high)
    return adc_data_read

def adc_bram_read_IQ(bram_mmio, number_of_32_bits_samples):
    size = number_of_32_bits_samples
    I = np.zeros(size, dtype = np.int16)
    Q = np.zeros(size, dtype = np.int16)
    for i in range(0, size//8):
        for k in range(4):
            current_data = bram_mmio.read((i*8+k)*4) & 0xFFFFFFFF
            current_data = bram_mmio.read((i*8+k)*4) & 0xFFFFFFFF
            I[8*i + 2*k] = current_data & 0x0000_FFFF
            I[8*i + 2*k+1] = (current_data >> 16) & 0x0000_FFFF
        for k in range(4):
            current_data = bram_mmio.read((i*8+k+4)*4) & 0xFFFFFFFF
            current_data = bram_mmio.read((i*8+k+4)*4) & 0xFFFFFFFF
            Q[8*i + 2*k] = current_data & 0x0000_FFFF
            Q[8*i + 2*k+1] = (current_data >> 16) & 0x0000_FFFF
    return I + 1j * Q
        

### Controller (counter) :

def set_bram_dac_counter(mmio, number_of_32bits_samples):
    # STEP = 1
    max_counter_value = int(number_of_32bits_samples * (32/1024) - 1)
    mmio.write(0x00, max_counter_value)
    
def set_uram_dac_counter(mmio, number_of_32bits_samples):
    max_counter_value = int(number_of_32bits_samples * (32/1024) - 1)
    max_offset = 0x00
    step_offset = 0x04
    step = int(1024/8) 
    mmio.write(max_offset, int(max_counter_value*step))
    mmio.write(step_offset, step)

def set_ddr4_controller(mmio, number_of_32bits_samples):
    # init_addr_offset = 0x00; # slv_reg0
    num_samples_offset = 0x04; # slv_reg1
    axi_txn_offset = 0x0c; # slv_reg3
    # Set the number of sample in the DDR4
    mmio.write(num_samples_offset, int(number_of_32bits_samples * 32/512 - 1)) ### DON'T Forget -1 !!
    # Start looping in the DDR4
    mmio.write(axi_txn_offset, 1)
