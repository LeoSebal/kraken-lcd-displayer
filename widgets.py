from typing import Callable
from PIL import Image, ImageDraw, ImageFont



class Widget():
    def __init__(self, data_updater: Callable = None):
                #  drawer:Callable = None, data=Callable):
        self._bg = None
        self._fg = None
        self.data_updater = data_updater
        self.data = data_updater() if callable(data_updater) else 0
        self._center = (0,0)
        self.colors = {
            "transparent": "#FFFFFF00",
            "bg": "#616783",
            "front": "#00FFFF",
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
        if self._fg is None or self.update():
            # Recreate image to ensure a clean transparent canvas
            self._fg = Image.new('RGBA', (self.length, self.line_width), color=self.colors["transparent"])
            draw = ImageDraw.Draw(self._fg)
            fill = int((self.data / 100) * self.length)
            draw.rectangle((0, 0, fill, self.line_width), fill=self.colors["front"])
        if self.rot:
            return self._fg.rotate(self.rot, expand=True)
        return self._fg



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
        if self._fg is None or self.update():
            self._fg = Image.new('RGBA', (self.size, self.size), color=self.colors["transparent"])
            draw = ImageDraw.Draw(self._fg)
            bbox = (self.line_width//2, self.line_width//2, self.size - self.line_width//2, self.size - self.line_width//2)
            end_angle = (self.data / 100) * self.angle + self.start_angle
            draw.arc(bbox, start=self.start_angle, end=end_angle, fill=self.colors["front"], width=self.line_width)
        if self.rot:
            return self._fg.rotate(self.rot, expand=True)
        return self._fg



class Text(Widget):
    def __init__(self, text_source, font_path, font_size, color=(255, 255, 255, 255), align="lt", pos=(0,0), rot=0):
        if callable(text_source):
            super().__init__(text_source)
            self.static = False
        else:
            super().__init__()
            self.data = text_source
            self.static = True

        self.font = ImageFont.truetype(font_path, font_size)
        # normalize alignment into 'left', 'right' or 'center'
        a = (align or "").lower()
        if a.startswith("l"):
            self.halign = "left"
        elif a.startswith("r"):
            self.halign = "right"
        elif a.startswith("c"):
            self.halign = "center"
        else:
            self.halign = "left"

        self.colors["text"] = color
        self.w = 0
        self.h = 0
        self.pos = pos
        self.rot = rot

        # initialize background based on exact text bbox
        self._update_w_h()
        self._bg = Image.new('RGBA', (self.w + 4, self.h + 4), color=self.colors["transparent"])
        if self.static:
            draw = ImageDraw.Draw(self._bg)
            if self.halign == "left":
                x = 2
            elif self.halign == "right":
                x = self._bg.width - 2 - self.w
            else:
                x = (self._bg.width - self.w) // 2
            # account for font bbox top offset so tall glyphs don't get cut
            y = 2 - self._bbox[1]
            draw.text((x, y), str(self.data), font=self.font, fill=self.colors["text"])
            if self.rot:
                self._bg = self._bg.rotate(self.rot, expand=True)

    @property
    def bg(self):
        return self._bg

    @property
    def fg(self):
        if (self._fg is None or self.update()) and not self.static:
            self._update_w_h()
            self._fg = Image.new('RGBA', (self.w + 4, self.h + 4), color=self.colors["transparent"])
            draw = ImageDraw.Draw(self._fg)
            if self.halign == "left":
                x = 2
            elif self.halign == "right":
                x = self._fg.width - 2 - self.w
            else:
                x = (self._fg.width - self.w) // 2
            y = 2 - self._bbox[1]
            draw.text((x, y), str(self.data), font=self.font, fill=self.colors["text"])
        if self.rot:
            return self._fg.rotate(self.rot, expand=True)
        return self._fg

    def _update_w_h(self):
        # compute exact text bbox for current string
        text = str(self.data)
        bbox = self.font.getbbox(text)
        # store full bbox so drawing can be offset to avoid clipping
        self._bbox = bbox
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        self.w, self.h = text_w, text_h
