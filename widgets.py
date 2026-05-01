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
            "transparent": (0, 0, 0, 0),
            "bg": (97, 103, 131, 255),
            "front": (0, 255, 255, 255),
            "text": None,
            "debug": "#9A4CB8"
        }
        self.pos = (0,0)
        self.rot = (0,0)

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

    @property
    def height(self):
        return self.bg.height

    @property
    def width(self):
        return self.bg.width




class LineGraphic(Widget):
    def __init__(self, length, line_width, colors=None, data_updater=None, pos=(0,0), rot=0):
        super().__init__(data_updater)
        self.length = length
        self.line_width = line_width
        # self._center = (self.length//2, self.line_width//2)
        self.pos = pos
        self.rot = rot
        if colors:
            self.colors.update(colors)

        # Pre-initialize layers to avoid repeated allocations
        self._bg = Image.new('RGBA', (length, self.line_width), color=self.colors["bg"])
        if self.rot:
            self._bg = self._bg.rotate(self.rot, expand=True)

    @property
    def bg(self):
        return self._bg

    @property
    def fg(self):
        # Recreate image to ensure a clean transparent canvas
        fg = Image.new('RGBA', (self.length, self.line_width), color=self.colors["transparent"])
        draw = ImageDraw.Draw(fg)
        fill = int((self.data / 100) * self.length)
        draw.rectangle((0, 0, fill, self.line_width), fill=self.colors["front"])
        if self.rot:
            return fg.rotate(self.rot, expand=True)
        return fg



class ArcGraphic(Widget):
    def __init__(self, angle, radius, line_width, start_angle=90, colors={}, data_updater=None, pos=(0,0), rot=0):
        super().__init__(data_updater)
        self.start_angle = start_angle
        self.angle = angle
        self.radius = radius
        self.line_width = line_width
        self.pos = pos
        self.rot = rot
        if colors:
            for k,v in colors.items():
                self.colors[k] = v

        self.size = 2 * self.radius + self.line_width
        self._bg = Image.new('RGBA', (self.size, self.size), color=self.colors["transparent"])
        draw = ImageDraw.Draw(self._bg)
        bbox = (self.line_width//2, self.line_width//2, self.size - self.line_width//2, self.size - self.line_width//2)
        draw.arc(bbox, start=self.start_angle, end=self.start_angle + self.angle, fill=self.colors["bg"], width=self.line_width)
        if self.rot:
            self._bg = self._bg.rotate(self.rot, expand=True)


    @property
    def bg(self):
        return self._bg

    @property
    def fg(self):
        fg = Image.new('RGBA', (self.size, self.size), color=self.colors["transparent"])
        draw = ImageDraw.Draw(fg)
        bbox = (self.line_width//2, self.line_width//2, self.size - self.line_width//2, self.size - self.line_width//2)
        end_angle = (self.data / 100) * self.angle + self.start_angle
        draw.arc(bbox, start=self.start_angle, end=end_angle, fill=self.colors["front"], width=self.line_width)
        if self.rot:
            return fg.rotate(self.rot, expand=True)
        return fg



class Text(Widget):
    def __init__(self, text_source, font_path, font_size, color=(255, 255, 255, 255), align="lb", pos=(0,0), rot=0):
        if callable(text_source):
            super().__init__(text_source)
            self.static = False
        else:
            super().__init__()
            self.data = text_source
            self.static = True

        self.font = ImageFont.truetype(font_path, font_size)
        self.align = "ls" if align == "left" else "rs"
        self.colors["text"] = color
        self.w = 0
        self.h = 0
        self.pos = pos
        self.rot = rot

        if self._bg is None:
            self._update_w_h()
            self._bg = Image.new('RGBA', (self.w + 4, self.h + 4), color=self.colors["transparent"])
            if self.static:
                draw = ImageDraw.Draw(self._bg)
                draw.text((2, 2), str(self.data), font=self.font, fill=self.colors["text"])
                if self.rot:
                    self._bg.rotate(self.rot, expand=True)

    @property
    def bg(self):
        return self._bg

    @property
    def fg(self):
        if not self.static:
            self._update_w_h()
            self._fg = Image.new('RGBA', self._bg.size, color=self.colors["transparent"])
            draw = ImageDraw.Draw(self._fg)
            draw.rectangle((0, 0, self.w + 4, self.h + 4), fill=self.colors["transparent"])
            draw.text((2, 2), str(self.data), font=self.font, fill=self.colors["text"], align=self.align)
            if self.rot:
                return self._fg.rotate(self.rot, expand=True)
        return self._fg

    def _update_w_h(self):
        bbox = self.font.getbbox(self.data, mode="ltr" if self.align == "left" else "rtl")
        self.w, self.h = 3*(bbox[2] - bbox[0])//2, 2*(bbox[3] - bbox[1])