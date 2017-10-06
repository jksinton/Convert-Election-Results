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
from PyPDF2 import PdfFileReader
from PIL import Image
import cv2
import csv

VERSION = '0.2.2'

def read_settings(args):
    """Processing the settings from commandline
    Args: 
        args: argparse.ArgumentParser object that stores command line arguments
    Returns: 
        settings: A dictionary to pass the settings to main
    Raises:
        Nothing
    """
    # Default values
    pdf_file = None
    image_file = None
    first_page = None
    last_page = None
    output_path = os.getcwd() + '/csv/'
    debug_is_on = False
    
    if args.pdf:
        pdf_file=args.pdf
    if args.image_file:
        image_file=args.image_file
    if args.first_page:
        first_page=int(args.first_page)
    if args.last_page:
        last_page=int(args.last_page)
    if args.output_path:
        output_path=os.path.normpath(args.output_path) + '/'
    if args.debug:
        debug_is_on=args.debug

    settings = {
                "pdf_file": pdf_file,
                "image_file": image_file,
                "first_page": first_page,
                "last_page": last_page,
                "output_path": output_path,
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
        Nothing
    """
    _version=VERSION
    parser = argparse.ArgumentParser(description='Convert election results to computer readable format, e.g., csv, json, xml')
    parser.add_argument('-p','--pdf', help='PDF file to process')
    parser.add_argument('-i','--image-file', help='image file to process')
    parser.add_argument('--first-page', help='page to begin processing')
    parser.add_argument('--last-page', help='page to end processing')
    parser.add_argument('-o','--output-path', help='path to write csv files')
    parser.add_argument('-v','--version',action='version', 
            version='%(prog)s %(version)s' % {"prog": parser.prog, "version": _version})
    parser.add_argument('-d','--debug',help='print debug messages',action="store_true")

    return parser.parse_args()


def convert_election_results(pdf_file=None, image_file=None, first_page=None, 
        last_page=None, output_path=None, debug_is_on=True):
    """Convert the election results pdf to a computer readable format
    Args:
        pdf_file: filename of PDF file to process
        image_file: filename of image file to process
        first_page: page number of the first page to process in the PDF file
        last_page: page number of the last page to process in the PDF file, default is final_page
        output_path: path to store csv output
        debug_is_on: boolean flag to trigger debug output
    Return: 
        Nothing
    Raises:
        Nothing
    """
    if pdf_file is not None:
        final_page = PdfFileReader(open(pdf_file, 'rb')).getNumPages()
        total_pages = final_page
        previous_office = ''
        office_data = []
        pages = []
        skipped_pages = []
        
        if os.path.isdir(output_path) == False:
            print "\tMaking " + output_path
            os.mkdir(output_path)
        if (last_page is not None) and (first_page is not None):
            total_pages = (last_page+1) - first_page
            pages = range(first_page, last_page+1)
        elif first_page is not None:
            total_pages = (final_page + 1) - first_page
            last_page = final_page
            pages = range(first_page, last_page+1)
        else:
            last_page = final_page
            first_page = 1
            pages = range(first_page, last_page+1)

        print "Reading {0}\n".format(pdf_file)

        for page_num in pages:
            tmp_tiff="tmp.tiff"
            options="-sDEVICE=tiffgray -r300 -dINTERPOLATE -dFirstPage={page_num} -dLastPage={page_num} -dNumRenderingThreads=4 -sCompression=lzw -c 30000000 setvmthreshold".format(page_num=str(page_num))
            
            os.system('gs -o %(tiff)s  %(options)s -f "%(pdf)s" > /dev/null 2>&1' % {"pdf": pdf_file, "tiff": tmp_tiff, "options": options})
            
            office_text, headers_text, data_text = convert_image(image_file=tmp_tiff, debug_is_on=debug_is_on)
            os.remove(tmp_tiff)
           
            if office_text is not None: 
                if office_text not in previous_office:
                    if len(office_data) > 0:
                        with open(output_path + previous_office.encode('utf-8') + '.csv', 'w') as f:
                            writer = csv.writer(f)
                            writer.writerows(office_data)

                    office_data = []
                    previous_office = office_text
                
                office_data.append(headers_text)
                
                for line in data_text.split('\n'):
                    if 'Totals' not in line.split(' ')[0]:
                        line = line.replace('o','0')
                    office_data.append([office_text] + line.split(' '))
                
                if page_num == last_page:
                        print "writing last file"
                        with open(output_path + office_text.encode('utf-8') + '.csv', 'w') as f:
                            writer = csv.writer(f)
                            writer.writerows(office_data)
                
                status_line1 = '{office_text}'.format(office_text=office_text)
                status_line2 = r"%10d  [%3.2f%%]" % (page_num, ((page_num + 1) - first_page) * 100. / total_pages)
                
                print status_line1
                print '\t' + status_line2 + '\n'
            else:
                skipped_pages.append(page_nume)
                print "Skipping page {page_num} . . .\n".format(page_num=page_num) 
    
    print "Done.\n"
    if len(skipped_pages) > 0:
        print "Page(s) skipped:",
        for page_num in skipped_pages:
            print '  ' + page_num,

    if image_file is not None:
        office_text, headers_text, data_text = convert_image(image_file=tmp_tiff, debug_is_on=debug_is_on)
        if office_text is not None: 
            print headers_text
            print data_text


def convert_image(image_file=None, debug_is_on=False):
    """Convert the election results pdf to a computer readable format
    Args:
        image_file: filename for image file
        debug_is_on: boolean flag to trigger debug output
    Return: 
        office_text: string with the office found in the image
        headers_text: array with the headers found in the image
        data_text: string with the election results found in the image
    Raises:
        Nothing
    """
    office_text = None
    headers_text = None
    data_text = None

    cv_img = cv2.imread(image_file,1)
    edges = cv2.Canny(cv_img,100,200)

    im2, contours, hierarchy = cv2.findContours(edges, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)

    # find the boxes around the header
    boxes = []
    for c in contours:
        if cv2.contourArea(c, True) > 0:
            x,y,w,h = cv2.boundingRect(c)
            if h > 50 and w > 50:
                boxes.append({'x': x, 'y': y, 'w': w, 'h': h}) 
                if debug_is_on:
                    print "x: " +  str(x) + ", y: " + str(y) + ", w: " + str(w) + ", h: " + str(h)
                    cv2.rectangle(cv_img,(x,y),(x+w,y+h),(0,255,0),2)
        else:
            x,y,w,h = cv2.boundingRect(c)
            if w > 1000 and h > 50 and y > 1000:
                if debug_is_on:
                    cv2.rectangle(cv_img,(x,y),(x+w,y+h),(0,0,255),2)
                    print "Totals"
                    print "x: " +  str(x) + ", y: " + str(y) + ", w: " + str(w) + ", h: " + str(h)

    if len(boxes) > 0:
        pil_img = Image.open(image_file)
        width, height = pil_img.size

        # find the location of the column headers and the office
        y_for_column_headers = boxes[0]['y']
        h_for_column_headers = boxes[0]['h']
        y_for_office = boxes[len(boxes)-2]['y']
        
        column_headers = []
        office = {}
        
        for i in range(len(boxes)):
            x, y, w, h = ( boxes[i]['x'], boxes[i]['y'], boxes[i]['w'], boxes[i]['h'] )
            
            if y == y_for_column_headers:
                column_headers.append({'x': x, 'y': y, 'w': w, 'h': h}) 
            if y == y_for_office:
                office = {'x': x, 'y': y, 'w': w, 'h': h} 
        
        # crop the office or proposition text from the image
        x, y, w, h = ( office['x'], office['y'], office['w'], office['h'] )
        cropped = pil_img.crop((x+5,y+5,x+w-5,y+h-5))
        # OCR the office or proposition
        office_text = tesseract.image_to_string(cropped).replace('\n',' ').encode('utf-8')
        
        headers_text = []
        headers_text.append('Office')
        
        column_headers = sorted(column_headers, key=lambda k: k['x'])
        for i in range(len(column_headers)):
            # crop the header text from the image
            x, y, w, h = ( column_headers[i]['x'], column_headers[i]['y'], 
                    column_headers[i]['w'], column_headers[i]['h'] )
            cropped = pil_img.crop((x+5,y+5,x+w-5,y+h-5))
            
            # the candidates are vertically alligned text
            # so if the header is for the candidate or proposition, 
            # rotate the cropped image 90 degrees clockwise
            if i > 5:
                cropped = cropped.transpose(Image.ROTATE_270)
            
            # OCR the header
            header_text = tesseract.image_to_string(cropped).replace('\n', ' ').encode('utf-8')
            headers_text.append(header_text)

            if debug_is_on:
                cv2.rectangle(cv_img,(x,y),(x+w,y+h),(255,0,0),3)
                print header_text
                cropped.save('cropped_'+str(i)+'.tiff', "TIFF")
        
        # crop the election results without the header from the image
        y = y_for_column_headers
        h = h_for_column_headers
        upper = y + h + 5
        left = 1
        right = width - 1
        lower = height - 1
        cropped = pil_img.crop((left, upper, right, lower))
        
        # OCR the election results
        data_text = tesseract.image_to_string(image=cropped, config='-psm 6').encode('utf-8')
        
        # correct common errors in the OCR results
        data_text = data_text.replace(' ,', '')
        data_text = data_text.replace(' .', '.')
        data_text = data_text.replace(' %', '%')
        data_text = data_text.replace(',', '')
        
        if debug_is_on:
            print office_text
            cropped.save('cropped_office.tiff', "TIFF")

            for header_text in headers_text:
                header_text = header_text.encode('utf-8')
                print '{header_text},'.format(header_text = header_text),
            print '\n',
            
            for line in data_text.split('\n'):
                if 'Totals' not in line.split(' ')[0]:
                    line = line.replace('o','0')
                print line.replace(' ', ',').encode('utf-8')
    
    if debug_is_on:
        cropped.save('cropped_data.tiff', "TIFF")
        cv2.imwrite('contours.png',cv_img)
        cv2.imwrite('canny.png', edges)

    return office_text, headers_text, data_text


def main():
    """Convert the election results pdf to csv
    """
    args = get_command_line_args()
    settings = read_settings(args)
    pdf_file = settings['pdf_file']
    image_file = settings['image_file']
    first_page = settings['first_page']
    last_page = settings['last_page']
    output_path = settings['output_path']
    debug_is_on = settings['debug_is_on']

    convert_election_results(
            pdf_file=pdf_file, 
            image_file=image_file, 
            first_page=first_page,
            last_page=last_page,
            output_path=output_path,
            debug_is_on=debug_is_on
        )


if __name__ == "__main__":
    main()
