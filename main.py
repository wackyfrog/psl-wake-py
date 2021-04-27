# (C) 2021 Oleksandr Degtiar <adegtiar@gmail.com>

import psl
from pprint import pprint

if __name__ == '__main__':
    print("Started")
    wake = psl.Wake()
    port = wake.get_port("PSL-")
    if not port:
        raise Exception("Not found PSL compatible ports.")
    pctrl = psl.Control(port)
    pctrl.update()
    pprint(vars(pctrl))
