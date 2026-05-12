# Kraken LCD Displayer

This project allows you to create and customize the display on NZXT's Kraken AIOs. It relies on liquidctl's ability to communicate with the device, in a more customizable manner than what CoolerControl allows.
That means displaying CPU, GPU and liquid temperature, CPU and GPU loads.

Its feature set is largely inspired by mrgogo7's [NZXT-ESC](https://github.com/mrgogo7/nzxt-esc/), without the CAM integration that makes it so efficient. This project actually started because, right before switching to Linux, I had just found out about this software and spent a few hours creating an overlay I liked.
All of the NZXT-ESC's features haven't been implemented, and some will probably never be, most notably animations, for reasons I cover lower down.

## Requirements

* [**liquidctl**](https://github.com/liquidctl/liquidctl/): the software actually in charge of the communication with the LCD.
* [**uv**](https://docs.astral.sh/uv/getting-started/installation/): to manage the virtual environment used by this project.
* If you use CoolerControl, it is necessary to disable its hold of the Kraken's display: in the list of devices, look for your Kraken AIO's LCD display, click "More options" and disable it. CoolerControl's GUI and its daemon will restart and release CoolerControl's hold on the device, allowing the daemon to run.

## Installation

Run `install.sh`.

## Uninstallation

Run `uninstall.sh`.

## Features

[x] Display a custom image
[x] Display CPU load & temperature, GPU load and temperature, liquid temperature
[x] Free rotation angles (by default, liquidctl only supports multiples of 90°)
[ ] Profile manager
[ ] Background image
[ ] NZXT-ESC profile load
[ ] Gradient-colored widgets

## Known issues

### Screen turns to black once in a while

This is due to liquidctl's driver, which is known to be unstable. Unfortunately, there is little I can do about this at this point, unless improving liquidctl's code directly, which is not my goal in the immediate term. If you have used CoolerControl, you may have noticed similar issues.

I really tried my best to make it as stable as possible: error checking, dimnishing the number of sends, only updating when necessary... Despite that, the screen still turns to black regularly. If anyone has suggestions, I'm listening!

### "Failed to switch active bucket" / Failed to setup bucket for data transfer"

It's actually the same error as above, both are synchronized. If it's happening too often, try to reduce the push rate.

### About GIF support and why it's probably not coming

Using liquidctl's API, you can send a GIF to the overlay, or you can send a static image. The data transfer rate of the Kraken display is through USB 2.0 (that's low, even for the 640x640 screen of the Kraken), and liquidctl's reverse-engineering doesn't allow overlaying of GIFs with static images or partial frame updates, which would be necessary for this to work. Moreover, updating a GIF resets the screen, which makes it blink every time a GIF is sent to the device.
This makes it seem unlikely to be possible to display GIF overlays at a comfortable framerate at this time.
