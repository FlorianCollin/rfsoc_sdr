from pynq import Overlay
from pynq import MMIO
import xrfclk
import xrfdc
import numpy as np
from time import sleep

from dc import dac_bram_write, ddr4_write, set_bram_dac_counter, set_uram_dac_counter, set_ddr4_controller, adc_bram_read_IQ, adc_bram_read
from data import sin_gen

class SdrOverlay(Overlay):
    """The only class (Overlay subclass) in this project, it provides the interface between the design (overlay).

    By default, it configures the DAC and ADC converters in Real-> IQ and IQ->Real mode respectively, with interpolation and decimation at 2 and a sampling frequency of 6144MHz and 4096 MHz. 
    It provides a set of methods to simplify converter parameterization and memory reading and writing.
    """

    def __init__(self, bitstream_path, Fs_dac_tile_0 = 6144, Fs_dac_tile_1 = 6144, Fs_adc_tile_0 = 4096):
        """Construct a new SdrOverlay

        Args:
            bitstream_path (str)
            Fs_dac_tile_0 (int, optional): Sampling Rate of the DAC tile 0 (in MHz). Defaults to 6144.
            Fs_dac_tile_1 (int, optional): Sampling Rate of the DAC tile 1 (in MHz). Defaults to 6144.
            Fs_adc_tile_0 (int, optional): Sampling Rate of the ADC tile 0 (in MHz). Defaults to 4096.
        """
        super().__init__(bitstream_path)

        print("Design loaded (status) : ", self.is_loaded())

        # For better readability, 'rfdc' can be used to configure converters
        self.rfdc = self.usp_rf_data_converter_0

        xrfclk.set_ref_clks()
        self.ref_clock = 409.6 # 409 MHz clock reference for the rfdc PLLs (see the def print_lmx_lmk() function in dc.py)


        # For easier modification of the class in the event of new designs
        self.dacs_tiles = [0, 1]
        self.dacs_tile0 = [0, 1, 2]
        self.dacs_tile1 = [2, 3]

        # For ADCs only the first of tile 0 is used
        self.adcs_tiles = [0]
        self.adcs_tile0 = [0]
        self.adcs_tile1 = []

        # By default everything is set in IQ mode
        # To keeep track of the current tiles configuration
        self.dacs_tiles_mode = ["IQ", "IQ"]
        self.adcs_tiles_mode = ["IQ"]

        # Only One ADC Tile 0 DAC 0 00

#         self.Fs_dac = [409.6, 819.2, 1228.8, 1634.4, 2048, 2457.6, 2867.2, 3276.8, 3686.4, 4096.0, 4505.6, 4915.2, 5324.8, 5734.4, 6144.0]
#         self.Fs_adc = [409.6, 819.2, 1228.8, 1634.4, 2048, 2457.6, 2867.2, 3276.8, 3686.4, 4096]

#         if (Fs_dac_tile_0 not in self.Fs_dac) or (Fs_dac_tile_1 not in self.Fs_dac) or (Fs_adc_tile_0 not in self.Fs_adc):
#             raise ValueError("Fs must be a multiple of 409.6 MHz")

        # PLL Config
        self.rfdc.dac_tiles[0].DynamicPLLConfig(1, self.ref_clock, Fs_dac_tile_0)
        self.rfdc.dac_tiles[1].DynamicPLLConfig(1, self.ref_clock, Fs_dac_tile_1)
        self.rfdc.adc_tiles[0].DynamicPLLConfig(1, self.ref_clock, Fs_adc_tile_0)

        ## WARNING : By default, the configuration is set to arbitrary values. Always start by setting the DAC to the values you need!

        # DACs
        # TILE 0
        for dac in self.dacs_tile0:
            self.rfdc.dac_tiles[0].blocks[dac].MixerSettings = {
                'CoarseMixFreq':  0,
                'EventSource':    2,
                'FineMixerScale': 0,
                'Freq':           -1500,
                'MixerMode':      2,
                'MixerType':      2,
                'PhaseOffset':    0.0
            }
            self.rfdc.dac_tiles[0].blocks[dac].NyquistZone = 2
            self.rfdc.dac_tiles[0].blocks[dac].UpdateEvent(xrfdc.EVENT_MIXER)
        # TILE 1
        for dac in self.dacs_tile1:
            self.rfdc.dac_tiles[1].blocks[dac].MixerSettings = {
                'CoarseMixFreq':  0,
                'EventSource':    2,
                'FineMixerScale': 0,
                'Freq':           -1500,
                'MixerMode':      2,
                'MixerType':      2,
                'PhaseOffset':    0.0
            }
            self.rfdc.dac_tiles[1].blocks[dac].NyquistZone = 2
            self.rfdc.dac_tiles[1].blocks[dac].UpdateEvent(xrfdc.EVENT_MIXER)
        # ADC
        # TILE 0
        for adc in self.adcs_tile0:
            self.rfdc.adc_tiles[0].blocks[adc].MixerSettings = {
                'CoarseMixFreq':  0,
                'EventSource':    2,
                'FineMixerScale': 0,
                'Freq':           1500,
                'MixerMode':      3,
                'MixerType':      2,
                'PhaseOffset':    0.0
            }
            self.rfdc.adc_tiles[0].blocks[adc].NyquistZone = 2
            self.rfdc.adc_tiles[0].blocks[adc].UpdateEvent(xrfdc.EVENT_MIXER)

        ## MMIO init ##
        # Each memory associated with a DAC is named by mem_xx where xx is the DAC number
        self.dac_mem_00 = MMIO(0xA000_0000, 0x000F_FFFF)   # BRAM(0) 1M
        self.dac_mem_01 = MMIO(0xA010_0000, 0x000F_FFFF)   # BRAM(1) 1M
        self.dac_mem_02 = MMIO(0xA120_0000, 0x007F_FFFF)   # URAM(1) 512k
        # self.dac_mem_10 = MMIO(0xA020_0000, 0x000F_FFFF)   # BRAM(2) 1M
        # self.dac_mem_11 = MMIO(0xA128_0000, 0x0007_FFFF)   # BRAM(3) 512K
        self.dac_mem_12 = MMIO(0x4_0000_0000, 0xFFFF_FFFF)  # DDR4(0) 8G
        self.dac_mem_13 = MMIO(0xA100_0000, 0x001F_FFFF)   # URAM(0) 2M
        self.adc_mem_00 = MMIO(0xA020_0000, 0x000F_FFFF) # BRAM(0) 1M


        self.dac_controller_00 = self.bram_dac_driver.bram_dac_driver_0.bram_counter_0
        self.dac_controller_01 = self.bram_dac_driver.bram_dac_driver_1.bram_counter_0
        self.dac_controller_02 = self.uram_dac_driver.uram_dac_driver_0.bram_counter_2_0
        #self.dac_controller_10 = self.bram_dac_driver.bram_dac_driver_2.bram_counter_0
        # self.dac_controller_11 = self.bram_dac_driver.bram_dac_driver_3.bram_counter_0
        self.dac_controller_12 = self.ddr4_dac_driver.ddr_controller_0
        self.dac_controller_13 = self.uram_dac_driver.uram_dac_driver_1.bram_counter_2_0
        self.adc_controller_00 = self.bram_adc_capture.adc_counter_v1_0_0

        

########### Driver and Capture ##################

    def load_data(self, tile, dac, data):
        """Written to the memory associated with a specific DAC numbered by its tile number and its number in that tile.

        Args:
            tile (int)
            dac (int)
            data (numpy.ndarray int32): array numpy already formatted in the correct int32 format
        """
        self._check_if_dac_is_valid(tile, dac)
        self.check_data_width(tile, dac, data.size)
        # The same function is used to fill bram and uram because of the IP AXI BRAM Controller
        if (tile == 0):
            if (dac == 0):
                dac_bram_write(self.dac_mem_00, data)
            elif (dac == 1):
                dac_bram_write(self.dac_mem_01, data)
            elif (dac == 2):
                dac_bram_write(self.dac_mem_02, data)
            else:
                raise ValueError("dac value is imposible")
        elif (tile == 1):
            # if (dac == 0):
                # dac_bram_write(self.mem_10, data)
            # elif (dac == 1):
                # dac_bram_write(self.mem_11, data)
            if (dac == 2):
                ddr4_write(self.dac_mem_12, data)
            elif (dac == 3):
                dac_bram_write(self.dac_mem_13, data)
            else:
                raise ValueError("dac value is imposible")
        else:
            raise ValueError("tile value is imposible")
    
    def adc_capture(self, number_of_32bits_samples = 1024):
        """ Start the capture of the adc (only ADC 00) output into BRAM """
        counter_max = number_of_32bits_samples * (32/256) - 1
        self.adc_controller_00.write(0x00, int(counter_max))
        self.adc_controller_00.write(0x04, 0x0)
        sleep(0.1)
        self.adc_controller_00.write(0x04, 0x1)
        sleep(0.1)

    def get_data(self, number_of_32_bits_samples = 1024, mode="IQ"):
        """ Read the data capture in BRAM """
        if mode == "IQ":
            data = adc_bram_read_IQ(self.adc_mem_00, number_of_32_bits_samples)
        elif (mode == "Real") or (mode == "real"):
            # In real mode the 256 axi stream as 128 bits at 0 (complex part = 0).
            data_read = adc_bram_read(self.adc_mem_00, number_of_32_bits_samples)
            data = np.zeros(int(data_read.size/2), dtype = np.int16)
            n = 0
            for i in range(0, data_read.size):
                if (i%16 <= 7):
                    data[n] = data_read[i]
                    n = n + 1
        else:
            raise ValueError("mode must be in ['IQ', 'Real']")
        return data

    def set_dac_controller(self, tile, dac, number_of_32bits_samples):
        """Set the controller associated with the driver of a DAC using its tile index and the DAC number in its tile.
        
        You can choose the number of 32 bits samples you want to capture.
        """
        self._check_if_dac_is_valid(tile, dac)
        self.check_data_width(tile, dac, number_of_32bits_samples)
        if (tile == 0):
            if (dac == 0):
                set_bram_dac_counter(self.dac_controller_00,
                                     number_of_32bits_samples)
            elif (dac == 1):
                set_bram_dac_counter(self.dac_controller_01,
                                     number_of_32bits_samples)
            elif (dac == 2):
                set_uram_dac_counter(self.dac_controller_02,
                                     number_of_32bits_samples)
            else:
                raise ValueError("dac value is imposible")
        elif (tile == 1):
            # if (dac == 0):
                # set_bram_dac_counter(self.dac_controller_10, number_of_32bits_samples)
            # elif (dac == 1):
                # set_bram_dac_counter(self.controller_11, number_of_32bits_samples)
            if (dac == 2):
                if (number_of_32bits_samples < 15e3):
                    print(
                        "WARNING : the number of 32 bits samples is too low for the DDR4, number_of_32_bits_samples must be greater than 12_000 samples")
                set_ddr4_controller(self.dac_controller_12,
                                    number_of_32bits_samples)
            elif (dac == 3):
                set_uram_dac_counter(self.dac_controller_13,
                                     number_of_32bits_samples)
            else:
                raise ValueError("dac value is imposible")
        else:
            raise ValueError("tile value is imposible")

########## RFDC Settings ###################

    def set_dac_tile_pll(self, tile, Fs = 6144):
        """Configures a DAC tile's PLL (rfdc), allowing you to choose your tile's sampling frequency.

        Args:
            tile (int): tile index (0 or 1)
            Fs (int, optional): Sampling Rate in MHz (MSPs), Fs must be a multiple of 409.6 MHz. Defaults to 6144 (Maximum).
        """
        if tile not in self.dacs_tiles:
            raise ValueError("Wrong tile value")
        self.rfdc.dac_tiles[tile].DynamicPLLConfig(1, self.ref_clock, Fs)
    
    def set_adc_tile_pll(self, Fs = 4096):
        """Configures the ADC tile 0 PLL (rfdc), allowing you to choose your tile sampling frequency.

        Args:
            Fs (int, optional):  Sampling Rate in MHz (MSPs), Fs must be a multiple of 409.6 MHz. Defaults to 4096 (Maximum).
        """
        self.rfdc.adc_tiles[0].DynamicPLLConfig(1, self.ref_clock, Fs)

    def set_all_pll(self, Fs = 4096):
        """Set all the PLL Config with the same Sampling Rate.

        Args:
            Fs (int, optional): Sampling Rate in MHz (MSPs), Fs must be a multiple of 409.6 MHz. Defaults to 4096 (Maximum).
        """
        for tile in self.dacs_tiles:
            self.set_dac_tile_pll(tile = tile, Fs = Fs)
        self.set_adc_tile_pll(Fs = Fs)

    def set_dac_nco(self, tile, dac, nco):
        """Set the Numerical Control Oscillator (NCO) of a DAC in a specific tile

        Args:
            tile (int): tile index
            dac (int): dac index in its tile
            nco (int): The NCO frequency will be the central frequency of the signal in the channel
        """
        self._check_if_dac_is_valid(tile, dac)
        self.rfdc.dac_tiles[tile].blocks[dac].MixerSettings['Freq'] = nco
    
    def set_adc_nco(self, nco):
        """Set the Numerical Control Oscillator (NCO) of the ADC00

        Args:
            nco (int): The NCO frequency will be the central frequency of the signal in the channel
        """
        self.rfdc.adc_tiles[0].blocks[0].MixerSettings['Freq'] = nco

    def set_dac_tile_nco(self, tile, nco_list):
        """ Set all the DAC NCO (MHz) parameters in a tile with the associated NCOs in the nco_list (list). """
        if tile not in self.dacs_tiles:
            raise ValueError("tile must be in [0,1]")

        if tile == 0:
            for i, dac in enumerate(self.dacs_tile0):
                self.rfdc.dac_tiles[tile].blocks[dac].MixerSettings['Freq'] = nco_list[i]
        else:
            for i, dac in enumerate(self.dacs_tile1):
                self.rfdc.dac_tiles[tile].blocks[dac].MixerSettings['Freq'] = nco_list[i]

    def set_dac_nz(self, tile, dac, nz):
        """ Set the Nyquist Zone for the one specific DAC"""
        self._check_if_dac_is_valid(tile, dac)
        self.rfdc.dac_tiles[tile].blocks[dac].NyquistZone = nz
        self.rfdc.dac_tiles[tile].blocks[dac].UpdateEvent(xrfdc.EVENT_MIXER)

    def set_dac_tile_nz(self, tile, nz_list):
        """ Set all the DAC Nyquist Zone (1 or 2) parameters in a tile with the associated Nyquist Zones in the nz_list. """
        if tile not in [0, 1]:
            raise ValueError("Wrong tile value")

        if tile == 0:
            for i, dac in enumerate(self.dacs_tile0):
                self.rfdc.dac_tiles[tile].blocks[dac].NyquistZone = nz_list[i]
        else:
            for i, dac in enumerate(self.dacs_tile1):
                self.rfdc.dac_tiles[tile].blocks[dac].NyquistZone = nz_list[i]

    def set_dac_interpolation(self, tile, interpolation_factor):
        """Set the interpolation factor of a DAC tile. 
        WARNING : tile must be set in IQ mode

        Args:
            tile (int): tile number (0 or 1)
            interpolation_factor (int): interpolation factor used in a DAC tile (2, 4 or 8)
        """
        if tile not in self.dacs_tiles:
            raise ValueError("Wrong tile value")

        # All interpolation mode are accepted
        if interpolation_factor not in [2, 4, 8]:
            raise ValueError("interpolation factor must be in [2, 4, 8]")

        self.rfdc.dac_tiles[tile].SetupFIFO(False)
        if (interpolation_factor == 2):
            self.rfdc.dac_tiles[tile].FabClkOutDiv = 2
        elif (interpolation_factor == 4):
            self.rfdc.dac_tiles[tile].FabClkOutDiv = 3
        else:  # 8
            self.rfdc.dac_tiles[tile].FabClkOutDiv = 4

        self.rfdc.dac_tiles[tile].InterpolationFactor = interpolation_factor

        if (tile == 0):
            for dac in self.dacs_tile0:
                self.rfdc.dac_tiles[tile].blocks[dac].InterpolationFactor = interpolation_factor
                self.rfdc.adc_tiles[tile].blocks[dac].IntrClr = 4294967295
        else:  # 1
            for dac in self.dacs_tile1:
                self.rfdc.dac_tiles[tile].blocks[dac].InterpolationFactor = interpolation_factor
                self.rfdc.adc_tiles[tile].blocks[dac].IntrClr = 4294967295

        self.rfdc.dac_tiles[tile].SetupFIFO(True)


    def set_adc_decmation(self, decimation_factor = 2):
        """Set the decimation factor of the ADC tile 0 
        WARNING : tile must be set in IQ mode

        Args:
            decimation_factor (int, optional): decimation factor used in ADC tile (2, 4, or 8). Defaults to 2.
        """
        if decimation_factor not in [2, 4, 8]:
            raise ValueError("interpolation factor must be in [2, 4, 8]")

        self.rfdc.adc_tiles[0].SetupFIFO(False)
        if (decimation_factor == 2):
            self.rfdc.adc_tiles[0].FabClkOutDiv = 2
        elif (decimation_factor == 4):
            self.rfdc.adc_tiles[0].FabClkOutDiv = 3
        else:  # 8
            self.rfdc.adc_tiles[0].FabClkOutDiv = 4

        self.rfdc.adc_tiles[0].InterpolationFactor = decimation_factor
        self.rfdc.adc_tiles[0].blocks[0].InterpolationFactor = decimation_factor
        self.rfdc.adc_tiles[0].blocks[0].IntrClr = 4294967295

        self.rfdc.adc_tiles[0].SetupFIFO(True)

    def update_dac_mixer(self, tile, dac):
        """ Update a specific DAC Mixer """
        self._check_if_dac_is_valid(tile, dac)
        self.rfdc.dac_tiles[tile].blocks[dac].UpdateEvent(xrfdc.EVENT_MIXER)

    def update_dacs_mixer(self):
        """ Update the mixer of tile 0 and tile 1 DACs """
        for dac in self.dacs_tile0:
            self.rfdc.dac_tiles[0].blocks[dac].UpdateEvent(xrfdc.EVENT_MIXER)
        for dac in self.dacs_tile1:
            self.rfdc.dac_tiles[1].blocks[dac].UpdateEvent(xrfdc.EVENT_MIXER)

    def update_adc_mixer(self, tile = 0, adc = 0):
        """ Update a specific ADC Mixer """
        self._check_if_adc_is_valid(tile, adc)
        self.rfdc.adc_tiles[0].blocks[0].UpdateEvent(xrfdc.EVENT_MIXER)

    def update_all_mixer(self):
        """ Update both DACs and ADCs Mixer """
        self.update_dacs_mixer()
        self.update_adc_mixer(tile = 0, adc = 0)


    ### Check methods ###

    def _check_if_dac_is_valid(self, tile, dac):
        if tile not in [0, 1]:
            raise ValueError("Tile must be in [0,1]")
        if dac not in [0, 1, 2, 3]:
            raise ValueError("dac must be in [0,1,2,3]")

        if (tile == 0 and dac not in self.dacs_tile0) or (tile == 1 and dac not in self.dacs_tile1):
            raise ValueError("The dac is not enable, please check the info method to see the available resources.")
        return 0
            
    def _check_if_adc_is_valid(self, tile, adc):
        # Only one adc valid
        if (tile == 0) and (adc == 0):
            return 0
        else:
            raise ValueError("tile must be 0 and adc 0")
        
    ### WIDTH PROBLEM ###
    
    def _check_bram_width(self, number_of_32bits_samples):
        factor = int(1024/32)
        if number_of_32bits_samples % factor != 0:
            print("WARNING : The signal must have a number of 32-bit samples multiple of 1024/32 = 32 (BRAM)")
    
    def _check_ddr4_width(self, number_of_32bits_samples):
        factor = int(512/32)
        if number_of_32bits_samples % factor != 0:
            print("WARNING : The signal must have a number of 32-bit samples multiple of 512/32 = 16 (URAM)")

        
    def check_data_width(self, tile, dac, number_of_32bits_samples):
        self._check_if_dac_is_valid(tile, dac)
        if (tile == 0):
            if (dac == 0):
               self._check_bram_width(number_of_32bits_samples)
            elif (dac == 1):
                self._check_bram_width(number_of_32bits_samples)
            elif (dac == 2):
                self._check_bram_width(number_of_32bits_samples)
            else:
                raise ValueError("dac value is imposible")
        elif (tile == 1):
            if (dac == 2):
                self._check_ddr4_width(number_of_32bits_samples)
            elif (dac == 3):
                self._check_bram_width(number_of_32bits_samples)
            else:
                raise ValueError("dac value is imposible")
        else:
            raise ValueError("tile value is imposible")


    # Mode : Real/IQ ###

    #  Real

    def set_dac_tile_real(self, tile):
        """ Set a tile in Real mode.

            interpolation factor = 1
            number of 16 bits samples (axi stream) = 16 (constant)
        """
        if tile not in self.dacs_tiles:
            raise ValueError("Wrong tile value")
        
        self.dacs_tiles_mode[tile] = "Real"
        
        interpolation_factor = 1
        if tile == 0:
            # change f_axi frequency
            for dac in self.dacs_tile0:
                self.rfdc.dac_tiles[tile].blocks[dac].MixerSettings = {
                    'CoarseMixFreq':  16,
                    'EventSource':    2,
                    'FineMixerScale': 0,
                    'Freq':           0.0,
                    'MixerMode':      4,
                    'MixerType':      1,
                    'PhaseOffset':    0.0
                }
                self.rfdc.dac_tiles[tile].blocks[dac].NyquistZone = 1

            for dac in self.dacs_tile0:
                self.rfdc.dac_tiles[tile].SetupFIFO(False)
                self.rfdc.dac_tiles[tile].FabClkOutDiv = 2
                self.rfdc.dac_tiles[tile].InterpolationFactor = interpolation_factor
                self.rfdc.dac_tiles[tile].blocks[dac].InterpolationFactor = interpolation_factor
                self.rfdc.adc_tiles[tile].blocks[dac].IntrClr = 4294967295
                self.rfdc.dac_tiles[tile].SetupFIFO(True)

        else:
            
            for dac in self.dacs_tile1:
                self.rfdc.dac_tiles[tile].blocks[dac].MixerSettings = {
                    'CoarseMixFreq':  16,
                    'EventSource':    2,
                    'FineMixerScale': 0,
                    'Freq':           0.0,
                    'MixerMode':      4,
                    'MixerType':      1,
                    'PhaseOffset':    0.0
                }
                self.rfdc.dac_tiles[tile].blocks[dac].NyquistZone = 1

            for dac in self.dacs_tile1:
                self.rfdc.dac_tiles[tile].SetupFIFO(False)
                self.rfdc.dac_tiles[tile].FabClkOutDiv = 2
                self.rfdc.dac_tiles[tile].InterpolationFactor = interpolation_factor
                self.rfdc.dac_tiles[tile].blocks[dac].InterpolationFactor = interpolation_factor
                self.rfdc.adc_tiles[tile].blocks[dac].IntrClr = 4294967295
                self.rfdc.dac_tiles[tile].SetupFIFO(True)

        self.update_dacs_mixer()
        print(f"Tile : {tile} is now in Real Mode (Mixer = Bypass, Interpolation = 1)")


    def set_adc_tile_real(self):
        """ Set all the ADC tile 0 in Real Mode """
        self.adcs_tiles_mode[0] = "Real"
        # Only one ADC 00
        self.rfdc.adc_tiles[0].blocks[0].MixerSettings = {
            'Freq': 0.0,
            'PhaseOffset': 0.0,
            'EventSource': 2,
            'CoarseMixFreq': 16,
            'MixerMode': 4,
            'FineMixerScale': 0,
            'MixerType': 1
        }
        interpolation_factor = 1
        self.rfdc.adc_tiles[0].SetupFIFO(False)
        self.rfdc.adc_tiles[0].FabClkOutDiv = 2
        self.rfdc.adc_tiles[0].InterpolationFactor = interpolation_factor
        self.rfdc.adc_tiles[0].blocks[0].InterpolationFactor = interpolation_factor
        self.rfdc.adc_tiles[0].blocks[0].IntrClr = 4294967295
        self.rfdc.adc_tiles[0].SetupFIFO(True)
        self.rfdc.adc_tiles[0].blocks[0].UpdateEvent(xrfdc.EVENT_MIXER)


    # IQ

    def set_dac_tile_IQ(self, tile = 0, interpolation_factor = 2, nco_freq = 1024, nz = 1):
        """ Set all the DACs tile to a specific configuraiton with IQ->Real mode

        Args:
            tile (int, optional): the DAC tile index. Defaults to 0.
            interpolation_factor (int, optional): interpolation factor (2, 4, or 8). Defaults to 2.
            nco_freq (int, optional): NCO frequency in MHz. Defaults to 1024 MHz.
            nz (int, optional): Nyquist Zone (1 or 2). Defaults to 1.

        """
        if tile not in [0, 1]:
            raise ValueError("tile must be in [0, 1]")
        
        self.dacs_tiles_mode[tile] = "IQ"

        if tile == 0:
            for dac in self.dacs_tile0:
                self.rfdc.dac_tiles[0].blocks[dac].MixerSettings = {
                    'CoarseMixFreq':  0,
                    'EventSource':    2,
                    'FineMixerScale': 0,
                    'Freq':           nco_freq,
                    'MixerMode':      2,
                    'MixerType':      2,
                    'PhaseOffset':    0.0
                }
                self.rfdc.dac_tiles[0].blocks[dac].NyquistZone = nz
                self.rfdc.dac_tiles[0].blocks[dac].UpdateEvent(xrfdc.EVENT_MIXER)
        else:
            for dac in self.dacs_tile1:
                self.rfdc.dac_tiles[1].blocks[dac].MixerSettings = {
                    'CoarseMixFreq':  0,
                    'EventSource':    2,
                    'FineMixerScale': 0,
                    'Freq':           nco_freq,
                    'MixerMode':      2,
                    'MixerType':      2,
                    'PhaseOffset':    0.0
                }
                self.rfdc.dac_tiles[1].blocks[dac].NyquistZone = nz
                self.rfdc.dac_tiles[1].blocks[dac].UpdateEvent(xrfdc.EVENT_MIXER)
        # Set the interpolation factor
        self.set_dac_interpolation(tile = tile, interpolation_factor=interpolation_factor)

    def set_adc_tile_IQ(self, decimation_factor = 2, nco_freq = 1024, nz = 1):
        """ Set the ADC tile 0 in IQ mode

        Args:
            decimation_factor (int, optional): ADC decimation factor (2, 4 or 8), 1 is not compatible. Defaults to 2.
        """
        
        self.adcs_tiles_mode[0] = "IQ"
        self.rfdc.adc_tiles[0].blocks[0].MixerSettings = {
                'CoarseMixFreq':  0,
                'EventSource':    2,
                'FineMixerScale': 0,
                'Freq':           nco_freq,
                'MixerMode':      3,
                'MixerType':      2,
                'PhaseOffset':    0.0
            }
        self.rfdc.adc_tiles[0].blocks[0].NyquistZone = nz
        self.rfdc.adc_tiles[0].blocks[0].UpdateEvent(xrfdc.EVENT_MIXER)
        self.set_adc_decmation(decimation_factor=decimation_factor)  

    ### Print methods ###     

    def info(self):
        """print all the DACs and ADC memory units
        """
        print("Class : Vsg7Overlay")
        print("\tDACs Info :")
        print("\tTILE 0: ")
        print("\t\tDAC 00 : BRAM(0) 1M")
        print("\t\tDAC 01 : BRAM(1) 1M")
        print("\t\tDAC 02 : URAM(1) 512k")
        print("\tTILE 1")
        print("\t\tDAC 12 : DDR4(0) 4G")
        print("\t\tDAC 13 : URAM(0) 2M")
        print("\tADCs Info :")
        print("\tTILE 0: ")
        print("\t\tADC 00 : BRAM(0) 1M")
        self.print_config()

    def print_config(self):
        """Print the PLL/Mixer Config
        """
        print("\n\nConfiguration :\n")
        print("DACs :")
        print("\tTile 0 PLL Config : ", self.rfdc.dac_tiles[0].PLLConfig)
        print("\tTile 1 PLL Config : ", self.rfdc.dac_tiles[1].PLLConfig)
        print("Mixer Config : ")
        for dac in self.dacs_tile0:
            print(f"\tDAC 0{dac} : {self.rfdc.dac_tiles[0].blocks[dac].MixerSettings}")
        for dac in self.dacs_tile1:
            print(f"\tDAC 1{dac} : {self.rfdc.dac_tiles[1].blocks[dac].MixerSettings}")
        
        print("\nADCs :")
        print("\tTile 0 PLL Config : ", self.rfdc.adc_tiles[0].PLLConfig)
        print("Mixer Config : ")
        for adc in self.adcs_tile0:
            print(f"\tADC 0{adc} : {self.rfdc.adc_tiles[0].blocks[adc].MixerSettings}")


    # Debug method/demonstration, these methods allow me to easily test the operating modes, but I advise you to use the example in the notebook to learn how to use the system.

    # def demo_qam(self, N=6400, nco=-1500, nz=2, interpolation_factor=2):
    #     """Demonstration function : all DACs are used with a 16 QAM and ADC 00 can be used for a loopback

    #     Args:
    #         N (int, optional): Number of symbols. Defaults to 6400.
    #         nco (int, optional): NCO frequency in MHz, this frequency will be the center frequency of the signal after mixing. Defaults to -1500.
    #         nz (int, optional): Nyquist Zone 1 or 2. Defaults to 2.
    #         interpolation_factor (int, optional): 2, 4 or 8. Defaults to 2.
    #     """

    #     self.set_all_pll(Fs = 4096)
    #     print("Warning : All PLL have been set to 4096 MHz")

    #     if interpolation_factor == 8:
    #         samples_per_symbol = 4
    #     elif interpolation_factor == 4:
    #         samples_per_symbol = 8
    #     elif interpolation_factor == 2:
    #         samples_per_symbol = 16
    #     else:
    #         raise ValueError("interpolation_factor must be in [2,4,8]")

    #     data, rrc_filter, factor = qam_gen(N=N, samples_per_symbol=samples_per_symbol)
    #     print("data size : ", data.size)

    #     self.set_dac_tile_IQ(tile = 0, interpolation_factor = interpolation_factor, nco_freq = nco, nz = nz)
    #     self.set_dac_tile_IQ(tile = 1, interpolation_factor = interpolation_factor, nco_freq = nco, nz = nz)

    #     sleep(1)
    #     self.update_dacs_mixer()
    #     # debug
    #     xrfclk.set_ref_clks()

    #     # Load the DATA in all DAC Driver
    #     for dac in self.dacs_tile0:
    #         self.load_data(0, dac, data)
    #     for dac in self.dacs_tile1:
    #         self.load_data(1, dac, data)

    #     # Set all DAC Driver Controller
    #     number_of_32bits_samples = int(data.size)
    #     for dac in self.dacs_tile0:
    #         self.set_dac_controller(0, dac, number_of_32bits_samples)
    #     for dac in self.dacs_tile1:
    #         self.set_dac_controller(1, dac, number_of_32bits_samples)
        
    #     self.set_adc_tile_IQ(decimation_factor=2)
    #     self.adc_capture(number_of_32bits_samples=number_of_32bits_samples)
    #     data = self.get_data(number_of_32_bits_samples=number_of_32bits_samples, mode="IQ")

    #     signal_rx = data / factor
    #     plot_fft(signal_rx, Fs = 4096e6, title = "FFT : rx signal")

    #     signal_rx = np.convolve(signal_rx, rrc_filter, "same")
    #     plot_fft(signal_rx, Fs = 4096e6, title = "FFT : rx signal after RRC filtering")
        
    #     # For a better demonstration of 16-QAM communicaiton, I advise you to use example 3 in the nootbook.


    def _find_solution(self, f, Fs = 4096e6, max_value = 0.5e6, opt = "min"):
        """ Try to fix the problem of data format (size multiple of 64) by giving a compatible number of périods. For a sin wave.

        Args:
            f (int): sin wave frequency
            Fs (_type_, optional): Sampling Rate in Hz. Defaults to 4096e6.
            max_value (_type_, optional): The maximum number of 32 bits sample inside a memory. Defaults to 0.5e6.
            opt (str, optional): "max" or "min", you can choose to have the biggest number of period or the lowest. Defaults to "min".

        Returns:
            int: The number of period to generate the sin wave
        """
        
        if opt == "min":
            valid_np = 0
            k = 1
            while True:
                np = (k * 64 * f) / Fs
                if np >= 1 and np.is_integer() and (Fs / f) * np < max_value/2 - 8:
                    valid_np = int(np)
                    break
                elif ((Fs / f) * np)*2 >= max_value:
                    break
                k += 1
        elif opt == "max":
            valid_np = 0
            k = 1
            while True:
                np = (k * 64 * f) / Fs
                if np >= 1 and np.is_integer() and (Fs / f) * np < max_value:
                    valid_np = int(np)
                elif ((Fs / f) * np)*2 >= max_value:
                    break
                k += 1
        else:
            raise ValueError("opt is 'min' or 'max'")
            
        return valid_np

    def demo_sin(self, Fs = 4096e6, f = 128e6, capture_size = None):
        """ Demonstration function : All DACs are used to send a sin wave and ADC 00 can be used for a loopback.
        
        Warning : Not all frequencies are available due to signal size restrictions.
        """
        
        # In Real Mode All DAC and ADC must be set with a PLL runing at 4096 MHz
        if (Fs > 4096e6):
            print("Warning : Fs max ADC = 4096 MHz")
            print(f"PLL DACs = {Fs/1e6} MHz\nPLL ADC = 4096 MHz")
            for tile in self.dacs_tiles:
                self.set_dac_tile_pll(tile, Fs = Fs/1e6)
            self.set_adc_tile_pll(Fs = 4096)
        else:
            self.set_all_pll(Fs = Fs/1e6)
            print(f"All PLL have been set to {Fs/1e6}] MHz")
        
        # DACs Drivers

        self.set_dac_tile_real(0)
        self.set_dac_tile_real(1)

        self.update_dacs_mixer()

        number_of_periods = self._find_solution(f = f, Fs = Fs, max_value = 0.5e6, opt = "max") # max_value lower for security
        if (number_of_periods == 0):
            raise ValueError("Fs and f are not compatible for the platform !")
        
        print("SIN GEN :")
        print(f"\tNumber of 16 bits samples (N) = {int(number_of_periods*Fs/f)}, number of periods for the sinus = {number_of_periods}")
        print(f"\tMemory Usage : {int(number_of_periods*Fs/f)*2/1e6} Mbytes")
        sinus = sin_gen(Fs = Fs, f = f, number_of_periods = number_of_periods, plot = False)

        # Load the DATA in all DAC Driver
        for dac in self.dacs_tile0:
            self.load_data(0, dac, sinus)
        for dac in self.dacs_tile1:
            self.load_data(1, dac, sinus)

        # Set all DAC Driver Controller
        number_of_32bits_samples = int(sinus.size)
        for dac in self.dacs_tile0:
            self.set_dac_controller(0, dac, number_of_32bits_samples)
        for dac in self.dacs_tile1:
            self.set_dac_controller(1, dac, number_of_32bits_samples)

        # ADC capture :

        self.set_adc_tile_real()
        if capture_size == None:
            self.adc_capture(number_of_32bits_samples = number_of_32bits_samples)
            sleep(1)
            data_adc = self.get_data(number_of_32_bits_samples = number_of_32bits_samples, mode = "Real")
        else:
            self.adc_capture(number_of_32bits_samples = capture_size)
            sleep(1)
            data_adc = self.get_data(number_of_32_bits_samples = capture_size, mode = "Real")
            
        return data_adc




