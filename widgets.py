from typing import Any, Callable
from pydantic import BaseModel, Field, PrivateAttr, field_serializer
from PIL import Image, ImageDraw, ImageFont

TRANSPARENT = "#FFFFFF00"
DEBUG = "#9A4CB8"



class Widget(BaseModel):
    colors: dict[str, str | tuple[int,int,int,int]] = {
        "bg": "#616783",
        "front": "#00FFFF",
        "stroke": TRANSPARENT,
        "text": "#FFFFFF",
    }
    pos: tuple[int,int]             = (0,0)                         # position of the image (x,y)
    rot: int                        = 0                             # rotation (degrees)
    _bg: Image.Image | None         = PrivateAttr(default=None)     # background image
    _fg: Image.Image | None         = PrivateAttr(default=None)     # foreground image
    _data_updater: Callable | None  = PrivateAttr(default=None)     # data function
    _data: Any                      = PrivateAttr(default=0)        # data content
    _center: tuple[int,int]         = PrivateAttr(default=(0,0))    # center of the image (x,y)
    _width: int                     = PrivateAttr(default=0)        # width of the image
    _height: int                    = PrivateAttr(default=0)        # height of the image

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
        if self._data_updater is not None:
            new_data = self._data_updater()
            if new_data != self._data:
                self._data = new_data
                return True  # frame updated
        return False  # frame not updated

    @property
    def center(self):
        if self._bg != None:
            return (self.bg.width//2, self.bg.height//2)
        else:
            return self._center

    def __str__(self):
        return f"{type(self).__name__}@{self.pos}, value={self._data}"

    def __repr__(self):
        return f"{self.__class__}, {self.__dict__}"

    @property
    def height(self):
        return self.bg.height

    @property
    def width(self):
        return self.bg.width



class LineGraphic(Widget):
    length:int
    line_width:int
    corners:tuple[bool,bool,bool,bool]  = (False,False,False,False)
    data_updater:Callable               = Field(exclude=True)

    def model_post_init(self, _):
        # Pre-initialize layers to avoid repeated allocations
        self._bg = Image.new('RGBA', (self.length, self.line_width), color=TRANSPARENT)
        draw = ImageDraw.Draw(self._bg)
        draw.rounded_rectangle((0, 0, self.length, self.line_width), fill=self.colors["bg"], corners=self.corners)
        if self.rot:
            self._bg = self._bg.rotate(self.rot, expand=True)

    @property
    def fg(self):
        if self._fg is None or self.update():
            # Recreate image to ensure a clean transparent canvas
            self._fg = Image.new('RGBA', (self.length, self.line_width), color=TRANSPARENT)
            draw = ImageDraw.Draw(self._fg)
            fill = int((self._data / 100) * self.length)
            draw.rounded_rectangle((0, 0, fill, self.line_width), fill=self.colors["front"], corners=self.corners)
        if self.rot:
            return self._fg.rotate(self.rot, expand=True)
        return self._fg



class ArcGraphic(Widget):
    radius:int
    line_width:int
    angle:int
    start_angle:int = 90
    color:dict      = None
    _size: int      = PrivateAttr(default=0)

    def model_post_init(self, _):
        self._size = 2 * self.radius + self.line_width
        self._bg = Image.new('RGBA', (self._size, self._size), color=TRANSPARENT)
        draw = ImageDraw.Draw(self._bg)
        bbox = (self.line_width//2, self.line_width//2, self._size - self.line_width//2, self._size - self.line_width//2)
        draw.arc(bbox, start=self.start_angle, end=self.start_angle + self.angle, fill=self.colors["bg"], width=self.line_width)
        if self.rot:
            self._bg = self._bg.rotate(self.rot, expand=True)

    @property
    def bg(self):
        return self._bg

    @property
    def fg(self):
        if self._fg is None or self.update():
            self._fg = Image.new('RGBA', (self._size, self._size), color=TRANSPARENT)
            draw = ImageDraw.Draw(self._fg)
            bbox = (self.line_width//2, self.line_width//2, self._size - self.line_width//2, self._size - self.line_width//2)
            end_angle = (self._data / 100) * self.angle + self.start_angle
            draw.arc(bbox, start=self.start_angle, end=end_angle, fill=self.colors["front"], width=self.line_width)
        if self.rot:
            return self._fg.rotate(self.rot, expand=True)
        return self._fg



class Text(Widget):
    text_source:str|Callable            = Field(exclude=True)
    font_path:str                       = "fonts/NZXTExtraBold-Regular.otf"
    font_size:int                       = 50
    color:str|tuple[int,int,int,int]    = Field(default=(255,255,255,255), exclude=True)
    align:str                           = "lt"
    _static: bool | None                = PrivateAttr(default=None)
    _font: ImageFont.ImageFont | None   = PrivateAttr(default=None)
    _bbox: tuple[int,int,int,int]       = PrivateAttr(default=(0,0,0,0))

    def model_post_init(self, _):
        if callable(self.text_source):
            self._data_updater = self.text_source
            self._static = False
        else:
            self._data = self.text_source
            self._static = True
        self._font = ImageFont.truetype(self.font_path, self.font_size)
        self.align = self.align.lower()
        self.colors["text"] = self.color

        # initialize background based on exact text bbox
        self._bg = Image.new('RGBA', (self.width + 4, self.height + 4), color=TRANSPARENT)
        if self._static:
            draw = ImageDraw.Draw(self._bg)
            x = 2 - self._bbox[0]
            y = 2 - self._bbox[1]
            draw.text((x, y), str(self._data), font=self._font, fill=self.colors["text"])
            if self.rot:
                self._bg = self._bg.rotate(self.rot, expand=True)

    @property
    def fg(self):
        if (self._fg is None or self.update()) and not self._static:
            self._fg = Image.new('RGBA', (self.width + 4, self.height + 4), color=TRANSPARENT)
            draw = ImageDraw.Draw(self._fg)
            x = 2 - self._bbox[0]
            y = 2 - self._bbox[1]
            draw.text((x, y), str(self._data), font=self._font, fill=self.colors["text"])
        if self.rot:
            return self._fg.rotate(self.rot, expand=True)
        return self._fg

    @property
    def width(self):
        self._bbox = self._font.getbbox(str(self._data))
        return self._bbox[2] - self._bbox[0]

    @property
    def height(self):
        self._bbox = self._font.getbbox(str(self._data))
        return self._bbox[3] - self._bbox[1]

    @width.setter
    def width(self, value):
        self._width = value

    @height.setter
    def height(self, value):
        self._height = value

    @property
    def pos(self):
        return self._pos

    @pos.setter
    def pos(self, value):
        match self.align[0]:
            case "l":  # default is left-aligned
                self._pos[0] = value[0]
            case "r":
                self._pos[0] = value[0] - self.width
            case "m":
                self._pos[0] = value[0] - self.width // 2
            case _:
                raise ValueError
        match self.align[1]:
            case "t":
                self._pos[1] = value[1] - self.height
            case "b":
                self._pos[1] = value[1]
            case "m":
                self._pos[1] = value[1] - self.height // 2
            case _:
                raise ValueError
