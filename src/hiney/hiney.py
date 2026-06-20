#!/usr/bin/env python3

from torso import Db, load_config, util
import logging
import time

def main():
    logging.basicConfig(level=logging.INFO)
    conf = load_config()
    db = Db.writer()
    db.insert_config(conf)
    #breakpoint()

if __name__ == "__main__":
    main()
