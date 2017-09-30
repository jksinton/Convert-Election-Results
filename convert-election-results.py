#!/usr/bin/env python

# This file is part of OCR Election Results
# 
# Copyright (c) 2017, James Sinton
# All rights reserved.
# 
# Released under the BSD 3-Clause License
# See https://github.com/jksinton/Convert-Election-Results/tree/master

import sys
import os
import argparse
import pytesseract as tesseract
from PIL import Image
import cv2
import numpy as np
from matplotlib import pyplot as plt

VERSION = '0.1.0'

def read_settings(args):
    """Read the settings stored in settings.ini
    Args: 
        args: argparse.ArgumentParser object that stores command line arguments
    Returns: 
        settings: A dictionary holding the argument(s)
    Raises:
        Nothing (yet)
    """
    # Default values
    pdf_file = None
    
    # Set values in settings.ini
    #settings = ConfigParser.ConfigParser()
    #settings.read('settings.ini') # change example.settings.ini to settings.ini

    if args.file:
        pdf_file=args.file

    settings = {
                "pdf_file": pdf_file,
                "debug_is_on": True
            }

    return settings


def get_command_line_args():
    """Define command line arguments using argparse
    Args:
        None
    Return: 
        argparse.ArgumentParser object that stores command line arguments
    Raises:
        Nothing (yet)
    """
    _version=VERSION
    parser = argparse.ArgumentParser(description='Convert election results to a computer readable format, e.g., csv, json, xml')
    parser.add_argument('-f','--file', help='PDF file to process')
    parser.add_argument('-v','--version',action='version', 
            version='%(prog)s %(version)s' % {"prog": parser.prog, "version": _version})
    parser.add_argument('-d','--debug',help='print debug messages',action="store_true")

    return parser.parse_args()


def election_results_to_csv(pdf_file='', debug_is_on=True):
    """Convert the election results pdf to a computer readable format
    """
    
    # TODO convert pdf_file to tiff
    tiff=pdf_file

    cropped="cropped.tiff"
    img = cv2.imread(tiff,1)
    edges = cv2.Canny(img,100,200)

    im2, contours, hierarchy = cv2.findContours(edges, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    
    boxes = []
    for c in contours:
        if cv2.contourArea(c, True) > 0:
            x,y,w,h = cv2.boundingRect(c)
            if h > 50 and w > 50:
                boxes.append({'x': x, 'y': y, 'w': w, 'h': h}) 
                #column_headers.append({'x': x, 'y': y, 'w': w, 'h': h}) 
                if debug_is_on:
                    print "x: " +  str(x) + ", y: " + str(y) + ", w: " + str(w) + ", h: " + str(h)
                cv2.rectangle(img,(x,y),(x+w,y+h),(0,255,0),2)
        else:
            x,y,w,h = cv2.boundingRect(c)
            if w > 1000 and h > 50 and y > 1000:
                cv2.rectangle(img,(x,y),(x+w,y+h),(0,0,255),2)
                if debug_is_on:
                    print "Totals"
                    print "x: " +  str(x) + ", y: " + str(y) + ", w: " + str(w) + ", h: " + str(h)

    
    y_for_column_headers = boxes[0]['y']
    y_for_office = boxes[len(boxes)-2]['y']
    column_headers = []
    for i in range(len(boxes)):
        x = boxes[i]['x']
        y = boxes[i]['y']
        w = boxes[i]['w']
        h = boxes[i]['h']
        
        if y == y_for_column_headers:
            column_headers.append({'x': x, 'y': y, 'w': w, 'h': h}) 
        if y == y_for_office:
            office = {'x': x, 'y': y, 'w': w, 'h': h} 
    
    column_headers = sorted(column_headers, key=lambda k: k['x'])
    x = office['x']
    y = office['y']
    w = office['w']
    h = office['h']
    
    im = Image.open(tiff)
    cropped = im.crop((x+5,y+5,x+w-5,y+h-5))
    office_text = tesseract.image_to_string(cropped).replace('\n',' ')
    print(office_text)
    if debug_is_on:
        cropped.save('cropped_office.tiff', "TIFF")
    
    for i in range(len(column_headers)):
        x = column_headers[i]['x']
        y = column_headers[i]['y']
        w = column_headers[i]['w']
        h = column_headers[i]['h']
        cv2.rectangle(img,(x,y),(x+w,y+h),(255,0,0),3)
        
        im = Image.open(tiff)
        cropped = im.crop((x+5,y+5,x+w-5,y+h-5))
        
        if i > 5:
            cropped = cropped.transpose(Image.ROTATE_270)
        
        print tesseract.image_to_string(cropped).replace('\n', ' ')
        if debug_is_on:
            cropped.save('cropped_'+str(i)+'.tiff', "TIFF")


    if debug_is_on:
        cv2.imwrite('contours.png',img)
	cv2.imwrite('canny.png', edges)


def main():
    """Convert the election results pdf to csv
    """
    args = get_command_line_args()
    settings = read_settings(args)
    pdf_file = settings['pdf_file']
    debug_is_on = settings['debug_is_on']

    election_results_to_csv(pdf_file=pdf_file, debug_is_on=debug_is_on)


if __name__ == "__main__":
    main()
