# RFSoC SDR
RFSoC SDR is an embedded lab for the [ZCU111 development board](https://www.xilinx.com/products/boards-and-kits/zcu111.html). It allows easy manipulation of 5 DACs and 1 ADC of the RFSoC by exploring operating modes and configuration parameters (Real, IQ, Sampling Rate, NCO, Interpolation, Decimation, Nyquist Zone, ...).

This project is part of an internship project conducted at the Instituto de Telecomunicações, Universidade de
Aveiro, Campus Universitário de Santiago 3810 - 193 Aveiro, Portugal.

## ACKNOWLEDGMENT

* [strath-sdr](https://github.com/strath-sdr)
* [Commpy](https://github.com/veeresht/CommPy)
* [PYNQ](ttps://pynq.readthedocs.io/en/latest)

## Installation

Steps : 
* Format an SD card to FAT32 (e.g., using GParted).
* Install the PYNQ images for your baord : [pynq.io](https://www.pynq.io/boards.html)
* unzip it
* Flash the SD card with the PYNQ image (e.g., using Balena Etcher).
* Set the board switches for SD card usage, SW6 : (OFF = 1 = High, ON = 0 = Low) SD = OFF, OFF, OFFF, ON = 1110.!
* <img src="pictures/sw6.png" alt="SW6" width="50"/>
* Insert the card into your board.
* Plug the board to your Computer (ethernet cable).
* Start the board.
* Access from a browser at the address: 192.168.2.90 (you can change the static ip [here](https://pynq.readthedocs.io/en/v2.7.0/appendix/assign_a_static_ip.html))
WARNING: If you want the board to access the internet or you want to access it remotely in a lab, please consult your network supervisor.
* If you can't connect in this way, connect a usb cable (micro usb to usb) between the board and your computer and open a serial link terminal (e.g. with putty) with a baud rate of 115200 on one of the three COM ports (see /dev/ttyUSBx). You can then find out the correct ip with ifconfig cmd. (you can change the static ip [here](https://pynq.readthedocs.io/en/v2.7.0/appendix/assign_a_static_ip.html))
* Download this repository.
* Upload the rfsoc_sdr sub-folder tp Jupyter and open the notebook file to experiment.

## Important note

If you're using a loopback, you may need to add an attenuator (e.g. -5db).

## Resources

There are two folders: the `rfsoc_sdr` folder contains the source code and the bistream (and .hwh), and the `vivado` folder contains the vivado project (Vivado version: 2023.1).

## Code Documentation

Most functions are documented via a docstring or comments, so I'd advise you to look at the source code, as it's pretty straightforward. What's more, the best source of documentation will be the commented examples in notebook form that come with the source code. You can also go directly to the PYNQ source code, and in particular the RF Data Converter configuration methods ([xrfdc](https://github.com/Xilinx/PYNQ/tree/master/sdbuild/packages/xrfdc/package)).

## License

Fully Open and Free


