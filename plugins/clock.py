from datetime import datetime

from wmii import Widget

class Clock(Widget):
    def __init__(self, name, format=None):
        super(Clock, self).__init__(name, 'rbar')
        if format is None:
            self.format = '%a %b %-e, %Y %-l:%M%p'
        else:
            self.format = format

    def update(self):
        self.label = datetime.now().strftime(self.format)
        return 1
