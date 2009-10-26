import logging

from clock import Clock
from spacer import Spacer

try:
    from battery import Battery
except:
    logging.error('Could not load battery widget.')

try:
    from volume import Volume
except:
    logging.error('Could not load volume widget.  '
            '(Do you have the alsaaudio python module?)')

try:
    from wicdnet import Wicd
except:
    logging.error('Could not load Wicd widget.  '
            '(Do you have wicd installed?)')
