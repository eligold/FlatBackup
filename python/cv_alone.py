#!/usr/bin/env python3
import argparse
from bv import bv_BackupViewer as BackupViewer

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("index",type=int,default=0,help="integer camera index required",required=True)
    args = parser.parse_args()
    BackupViewer(args.index)