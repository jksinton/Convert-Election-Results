#!/usr/bin/env python

# This file is part of Convert Election Results
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
from pyPdf import PdfFileWriter, PdfFileReader
from PIL import Image
import cv2
import numpy as np
import csv

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
    image_file = None
    debug_is_on = False
    
    if args.pdf:
        pdf_file=args.pdf
    if args.image_file:
        image_file=args.image_file
    if args.debug:
        debug_is_on=args.debug

    settings = {
                "pdf_file": pdf_file,
                "image_file": image_file,
                "debug_is_on": debug_is_on
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
    parser.add_argument('-p','--pdf', help='PDF file to process')
    parser.add_argument('-i','--image-file', help='image file to process')
    parser.add_argument('-v','--version',action='version', 
            version='%(prog)s %(version)s' % {"prog": parser.prog, "version": _version})
    parser.add_argument('-d','--debug',help='print debug messages',action="store_true")

    return parser.parse_args()


def convert_election_results(pdf_file=None, image_file=None, debug_is_on=True):
    """Convert the election results pdf to a computer readable format
    """
    if pdf_file is not None:
        pdf = PdfFileReader(open(pdf_file, 'rb'))
        total_pages = pdf.getNumPages()
        old_office = ''
        office_data = []
        for page_num in range(total_pages):
            tmp_tiff="tmp.tiff"
            options="-sDEVICE=tiffgray -r300 -dINTERPOLATE -dFirstPage={page_num} -dLastPage={page_num} -dNumRenderingThreads=4 -sCompression=lzw -c 30000000 setvmthreshold".format(page_num=str(page_num + 1))
            
            os.system('gs -o %(tiff)s  %(options)s -f "%(pdf)s" > /dev/null 2>&1' % {"pdf": pdf_file, "tiff": tmp_tiff, "options": options})
            
            office_text, headers_text, data_text = convert_image(image_file=tmp_tiff, debug_is_on=debug_is_on)
            
            if office_text is not None: 
                if office_text not in old_office:
                    if len(office_data) > 0:
                        with open('csv/' + old_office.encode('utf-8') + '.csv', 'w') as f:
                            writer = csv.writer(f)
                            writer.writerows(office_data)

                    office_data = []
                    old_office = office_text
                
                office_data.append(headers_text)
                
                for line in data_text.split('\n'):
                    if 'Totals' not in line.split(' ')[0]:
                        line = line.replace('o','0')
                    office_data.append([office_text] + line.split(' '))

                status = r"%s    %10d  [%3.2f%%]" % (office_text, page_num+1, (page_num+1) * 100. / total_pages)
                status = status + chr(8)*(len(status)+1)
                print status,

    if image_file is not None:
        convert_image(image_file=image_file, debug_is_on=debug_is_on)


def convert_image(image_file=None, debug_is_on=False):
    """Return the office, headers, and data found contained in the image
    """
    office_text = None
    headers_text = None
    data_text = None

    cropped="cropped.tiff"
    img = cv2.imread(image_file,1)
    edges = cv2.Canny(img,100,200)

    im2, contours, hierarchy = cv2.findContours(edges, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    
    boxes = []
    for c in contours:
        if cv2.contourArea(c, True) > 0:
            x,y,w,h = cv2.boundingRect(c)
            if h > 50 and w > 50:
                boxes.append({'x': x, 'y': y, 'w': w, 'h': h}) 
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
    if len(boxes) > 0:
        y_for_column_headers = boxes[0]['y']
        h_for_column_headers = boxes[0]['h']
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
        
        im = Image.open(image_file)
        
        width, height = im.size

        cropped = im.crop((x+5,y+5,x+w-5,y+h-5))
        office_text = tesseract.image_to_string(cropped).replace('\n',' ').encode('utf-8')
        if debug_is_on:
            print office_text
            cropped.save('cropped_office.tiff', "TIFF")
        
        headers_text = []
        headers_text.append('Office')
        for i in range(len(column_headers)):
            x = column_headers[i]['x']
            y = column_headers[i]['y']
            w = column_headers[i]['w']
            h = column_headers[i]['h']
            cv2.rectangle(img,(x,y),(x+w,y+h),(255,0,0),3)
            
            cropped = im.crop((x+5,y+5,x+w-5,y+h-5))
            
            if i > 5:
                cropped = cropped.transpose(Image.ROTATE_270)
            
            header_text = tesseract.image_to_string(cropped).replace('\n', ' ').encode('utf-8')
            headers_text.append(header_text)

            if debug_is_on:
                print header_text
                cropped.save('cropped_'+str(i)+'.tiff', "TIFF")
        if debug_is_on:
            for header_text in headers_text:
                header_text = header_text.encode('utf-8')
                print '{header_text},'.format(header_text = header_text),
            print '\n',

        y = y_for_column_headers
        h = h_for_column_headers
        upper = y + h + 5
        left = 1
        right = width - 1
        lower = height - 1
        cropped = im.crop((left, upper, right, lower))
        data_text = tesseract.image_to_string(image=cropped, config='-psm 6').encode('utf-8')
        data_text = data_text.replace(' ,', '')
        data_text = data_text.replace(' .', '.')
        data_text = data_text.replace(',', '')
        
        if debug_is_on:
            for line in data_text.split('\n'):
                if 'Totals' not in line.split(' ')[0]:
                    line = line.replace('o','0')
                print line.replace(' ', ',').encode('utf-8')

    if debug_is_on:
        cropped.save('cropped_data.tiff', "TIFF")
        cv2.imwrite('contours.png',img)
        cv2.imwrite('canny.png', edges)
    
    if image_file is 'tmp.tiff':
        os.remove(image_file)

    return office_text, headers_text, data_text


def main():
    """Convert the election results pdf to csv
    """
    args = get_command_line_args()
    settings = read_settings(args)
    pdf_file = settings['pdf_file']
    image_file = settings['image_file']
    debug_is_on = settings['debug_is_on']

    convert_election_results(pdf_file=pdf_file, image_file=image_file, debug_is_on=debug_is_on)


if __name__ == "__main__":
    main()
