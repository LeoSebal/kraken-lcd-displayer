# Kraken LCD Displayer

The objective of this project is to be able to control and fine-tune the LCD display of my Kraken Elite 2023.
That means displaying CPU and GPU temps and loads, 
It is therefore built for my config: Kraken Elite and Nvidia GPU.

It originated from the fact that, right before I switched to Linux, I had spent 3h designing a nice looking frame using [NZXT-ESC](https://github.com/mrgogo7/nzxt-esc).
Besides. I wanted support for non-90° angles, because my own liquid cooler is angled at 30°, so there's that too.

* As of now, I am able to send a regularly updated frame that contains GPU and CPU temps at ~1FPS, but the display blinks to black on a regular basis.
* Next step will be to have a pretty-looking image to be displayed (that was the case at an earlier point, before I refactored everything), and then to have a stable frame.
* Ultimately, I'd like to be able to support a GIF stream with custom overlays, and maybe even to be able to take a NZXT-ESC JSON as input.
