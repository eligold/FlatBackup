### Example evtest touch input frame:
# Event: time 1707153627.150887, type 3 (EV_ABS), code 53 (ABS_MT_POSITION_X), value 1057
# Event: time 1707153627.150887, type 3 (EV_ABS), code 54 (ABS_MT_POSITION_Y), value 253
# Event: time 1707153627.150887, type 3 (EV_ABS), code 0 (ABS_X), value 1057
# Event: time 1707153627.150887, type 3 (EV_ABS), code 1 (ABS_Y), value 253
# Event: time 1707153627.150887, type 4 (EV_MSC), code 5 (MSC_TIMESTAMP), value 0
# Event: time 1707153627.150887, -------------- SYN_REPORT ------------
class touchEvent():
    isX = False
    isY = False
    valid = False

    def __init__(self, line):
            try:
                self._line = line
                segments = line.strip().split(", ")
                self.time = float(segments[0].lstrip("Eventim: "))
                frame = segments[1:]
                if len(frame) > 1:
                    event = self._sep_field(frame[0],"type")
                    self.event_id = int(event[0])
                    self.event = event[1]
                    code = self._sep_field(frame[1],"code")
                    self.code = code[1]
                    self.code_id = int(code[0])
                    if self.code_id == 0: self.isX = True
                    elif self.code_id == 1: self.isY = True
                    self.value = int(frame[-1].lstrip("value ").rstrip())
                    self.valid = True
                else: self.code = frame[0]
            except: self.value = f'error for line:\n{line}'

    def _sep_field(text, key):
        return text.lstrip(f"{key} ").rstrip(")").split(" (")

    def pretty(self):
        if self.valid:
            return f'{self.event}[{self.event_id}]: {self.code}[#{self.code_id}] -> {self.value}'
        return self._line