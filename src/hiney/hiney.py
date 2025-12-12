#!/usr/bin/env python3

from torso import Db, load_config



def main():
    load_config()
    db = Db.writer()

if __name__ == "__main__":
    main()
