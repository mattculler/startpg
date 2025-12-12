#!/usr/bin/env python3

from torso import Db, load_config

import time

def main():
    load_config()
    db = Db.writer()
    time.sleep(111)

if __name__ == "__main__":
    main()
