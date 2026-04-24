class Camera:
    def __init__(self):
        self.offset_x = 0
        self.offset_y = 0

    def apply(self, rect):
        return rect.move(self.offset_x, self.offset_y)
