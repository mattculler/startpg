#!/usr/bin/env python3

import logging

from torso import Db, load_config


def main():
    logging.basicConfig(level=logging.INFO)
    conf = load_config()
    db = Db.writer()
    db.insert_config(conf)


if __name__ == "__main__":
    main()
