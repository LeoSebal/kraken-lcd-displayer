from typing import Callable
from PIL import Image, ImageDraw, ImageFont, ImageOps


class Widget():
    def __init__(self, data_updater: Callable = None):
                #  drawer:Callable = None, data=Callable):
        self._bg = None
        self._fg = None
        self.data_updater = data_updater
        self.data = data_updater() if callable(data_updater) else 0
        self._center = (0,0)
        self.colors = {
            "bg": (97, 103, 131, 255),
            "front": (0, 255, 255, 255),
            "text": None,
            "debug": "#9A4CB8"
        }
        self.pos = (0,0)

    @property
    def bg(self):
        return self._bg

    @bg.setter
    def bg(self, value):
        self._bg = value

    @property
    def fg(self):
        return self._fg

    @fg.setter
    def fg(self, value):
        self._fg = value

    def update(self):
        if self.data_updater is not None:
            new_data = self.data_updater()
            if new_data != self.data:
                self.data = new_data
                return 1  # frame updated
        return 0  # frame not updated

    @property
    def center(self):
        if self._bg != None:
            return (self.bg.width//2, self.bg.height//2)
        else:
            return self._center

    def __str__(self):
        return f"{type(self).__name__}@{self.pos}, value={self.data}"

    def __repr__(self):
        return f"{self.__class__}, {self.__dict__}"




class LineGraphic(Widget):
    def __init__(self, length, width, colors=None, data_updater=None):
        super().__init__(data_updater)
        self.length = length
        self.width = width
        # self._center = (self.length//2, self.width//2)
        if colors:
            self.colors.update(colors)

        # Pre-initialize layers to avoid repeated allocations
        self._bg = Image.new('RGBA', (self.length, self.width), color=(0, 0, 0, 0))
        draw = ImageDraw.Draw(self._bg)
        draw.rectangle((0, 0, self.length, self.width), fill=self.colors["bg"])
        self._fg = Image.new('RGBA', (self.length, self.width), color=(0, 0, 0, 0))

    @property
    def bg(self):
        return self._bg

    @property
    def fg(self):
        draw = ImageDraw.Draw(self._fg)
        # Clear current foreground layer without re-allocating memory
        draw.rectangle((0, 0, self.length, self.width), fill=(0, 0, 0, 0))
        fill = int((self.data / 100) * self.length)
        # Draw horizontal bar
        draw.rectangle((0, 0, fill, self.width), fill=self.colors["front"])
        return self._fg



class ArcGraphic(Widget):
    def __init__(self, angle, radius, line_width, start_angle=90, colors={}, data_updater=None):
        super().__init__(data_updater)
        self.start_angle = start_angle
        self.angle = angle
        self.radius = radius
        self.line_width = line_width
        if colors:
            for k,v in colors.items():
                self.colors[k] = v

        size = 2 * self.radius + self.line_width
        self._bg = Image.new('RGBA', (size, size), color=(0, 0, 0, 0))
        draw = ImageDraw.Draw(self._bg)
        bbox = (self.line_width//2, self.line_width//2, size - self.line_width//2, size - self.line_width//2)
        draw.arc(bbox, start=self.start_angle, end=self.start_angle + self.angle, fill=self.colors["bg"], width=self.line_width)
        self._fg = Image.new('RGBA', (size, size), color=(0, 0, 0, 0))


    @property
    def bg(self):
        return self._bg

    @property
    def fg(self):
        draw = ImageDraw.Draw(self._fg)
        size = self._fg.width
        draw.rectangle((0, 0, size, size), fill=(0, 0, 0, 0))
        bbox = (self.line_width//2, self.line_width//2, size - self.line_width//2, size - self.line_width//2)
        end_angle = (self.data / 100) * self.angle + self.start_angle
        draw.arc(bbox, start=self.start_angle, end=end_angle, fill=self.colors["front"], width=self.line_width)
        return self._fg



class Text(Widget):
    def __init__(self, text_source, font_path, font_size, color=(255, 255, 255, 255), align="lm"):
        if callable(text_source):
            super().__init__(text_source)
            self.static = False
        else:
            super().__init__()
            self.data = text_source
            self.static = True

        self.font = ImageFont.truetype(font_path, font_size)
        self.align = align
        self.colors["text"] = color
        self.w = 0
        self.h = 0

        if self._bg is None:
            bbox = self.font.getbbox(str(self.data))
            self.w, self.h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            self._bg = Image.new('RGBA', (self.w + 4, self.h + 4), color=(0,0,0,0))
            if self.static:
                draw = ImageDraw.Draw(self._bg)
                draw.text((2, 2), str(self.data), font=self.font, fill=self.colors["text"])
            else:
                self._fg = Image.new('RGBA', self._bg.size, color=(0,0,0,0))


    @property
    def bg(self):
        return self._bg

    @property
    def fg(self):
        if not self.static:
            draw = ImageDraw.Draw(self._fg)
            draw.rectangle((0, 0, self.w + 4, self.h + 4), fill=(0, 0, 0, 0))
            draw.text((2, 2), str(self.data), font=self.font, fill=self.colors["text"])
        return self._fg
