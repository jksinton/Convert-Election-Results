#!/usr/bin/env python

# This file is part of Convert Election Results
# 
# Copyright (c) 2018, James Sinton
# All rights reserved.
# 
# Released under the BSD 3-Clause License
# See https://github.com/jksinton/Convert-Election-Results/tree/master

# Python standard libraries
import argparse
import csv
import os
import tempfile
import time
import sys

# third-party dependencies
import cv2
from etaprogress.progress import ProgressBar
try:
    import Image
except ImportError:
    from PIL import Image
try:
    import ImageDraw
except ImportError:
    from PIL import ImageDraw
import numpy as np
from PyPDF2 import PdfFileReader
from PyPDF2 import PdfFileWriter
import pytesseract as tesseract

VERSION = '0.4.0'

# TODO Public API
# repair_csv()
# to_opencsv()

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
    check_csv_file = None
    check_csv_path = None
    logfile = None
    first_page = None
    last_page = None
    output_path = os.getcwd() + '/csv/'
    debug_is_on = False
    
    if args.pdf:
        pdf_file=args.pdf
    if args.first_page:
        first_page=int(args.first_page)
    if args.last_page:
        last_page=int(args.last_page)
    if args.output_path:
        output_path=os.path.normpath(args.output_path) + '/'
    if args.check_csvs:
        check_csv_path = args.check_csvs
    if args.check_csv:
        check_csv_file = args.check_csv
    if args.review_logfile:
        logfile = args.review_logfile
    if args.debug:
        debug_is_on=args.debug

    settings = {
                "pdf_file": pdf_file,
                "first_page": first_page,
                "last_page": last_page,
                "output_path": output_path,
                "check_csv_path": check_csv_path,
                "check_csv_file": check_csv_file,
                "logfile": logfile,
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
    parser = argparse.ArgumentParser(description='Convert election results to csv format')
    parser.add_argument('-p','--pdf', help='PDF file to process')
    parser.add_argument('-i','--image-file', help='image file to process')
    parser.add_argument('--first-page', help='page to begin processing')
    parser.add_argument('--last-page', help='page to end processing')
    parser.add_argument('-o','--output-path', help='path to write CSV files')
    parser.add_argument('-c','--check-csvs', help='path containing CSV files to error check')
    parser.add_argument('-e','--check-csv', help='CSV file to error check')
    parser.add_argument('-r','--review-logfile', help='log file to review and recommend repairs; requires --pdf PDF to be set')
    parser.add_argument('-v','--version',action='version', 
            version='%(prog)s %(version)s' % {"prog": parser.prog, "version": _version})
    parser.add_argument('-d','--debug',help='print debug messages',action="store_true")

    return parser.parse_args()


def tempname():
    """ returns a temporary filename 
    Args:
        Nothing
    Return: 
        tmpfile.name: string of temporary filename
    Raises:
        Nothing
    """
    tmpfile = tempfile.NamedTemporaryFile(prefix="votes_")
    return tmpfile.name


def locate(pattern, root=os.curdir):
    """ locate files based on the given pattern
    Args:
        pattern: file name pattern
        root: dir root
    Return:
        file path matching the pattern
    Raises:
        Nothing
    """
    for path, dirs, files in os.walk(os.path.abspath(root)):
        for filename in fnmatch.filter(files, pattern):
            yield os.path.join(path, filename)


def remove(filename):
    """ tries to remove the given filename. Ignores non-existent files 
    Args:
        filename: string of filename
    Return: 
        Nothing
    Raises:
        Nothing
    """
    try:
        os.remove(filename)
    except OSError:
        pass


def to_csv(filename, table, mode='a'):
    """ write the table to csv with the given filename
    Args:
        filename: string of filename for csv file
        table: a list of row objects (a list), i.e., a matrix
    Return: 
        Nothing
    Raises:
        Nothing
    """
    with open(filename, mode) as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerows(table)


def row_to_csv(filename, row, mode='a'):
    """ write the table to csv with the given filename
    Args:
        filename: string of filename for csv file
        row: a list of row objects (a list), i.e., a matrix
    Return: 
        Nothing
    Raises:
        Nothing
    """
    with open(filename, mode) as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(row)


def gs(output_image, pdf_file, page_num=1, dpi=300):
    """ Convert the page of a PDF to a png
    Args:
       output_image:
       pdf_file:
       page_num:
       dpi:
    Return: 
        Nothing
    Raises:
        Nothing
    """
    page="-dFirstPage={page_num} -dLastPage={page_num}".format(page_num=str(page_num))
    img_format="-sDEVICE=png16m"
    dpi_setting="-r{dpi}".format(dpi=str(dpi))
    threads="-dNumRenderingThreads=2"
    #postscript="-c 30000000 setvmthreshold -f"
    postscript=""
    #interpolate="-dINTERPOLATE"
    interpolate=""
    options="{img_format} {dpi} {interpolate} {page} {threads} {postscript}".format( 
            img_format=img_format,
            dpi=dpi_setting,
            interpolate=interpolate,
            page=page,
            threads=threads,
            postscript=postscript
        )
    os.system('gs -o %(output)s  %(options)s "%(pdf)s" > /dev/null 2>&1' % {
        "pdf": pdf_file, "output": output_image, "options": options })
 

def pdf_to_csv(pdf_file=None, first_page=None, last_page=None, 
        output_path=os.getcwd() + '/csv/', debug_is_on=False):
    """Convert the election results pdf to a computer readable format
    Args:
        pdf_file: filename of PDF file to process
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
        previous_candidate = ''
        office_data = []
        pages = []
        skipped_pages = []
        logfilename = "{filename}-error.log".format(filename=pdf_file.split('.')[0])

        with open(logfilename,'w') as logfile:
            logfile.write('')

        if os.path.isdir(output_path) == False:
            print "Making " + output_path
            os.mkdir(output_path)

        # TODO
        # prevent command line injection attacks
        # See https://www.kevinlondon.com/2015/07/26/dangerous-python-functions.html
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

        print "Converting {0}\n".format(pdf_file)
        
        bar = ProgressBar(total_pages, max_width=80)
        for page_num in pages:
            output_image="%s.png" % tempname()

            gs(pdf_file=pdf_file, output_image=output_image, page_num=page_num, dpi=300)
            
            office_text, headers_text, votes_text = image_to_text(
                    image_file=output_image,
                    debug_is_on=debug_is_on )
            
            remove(output_image)
            
            if office_text is not None: 
                if office_text != previous_office:
                    if len(office_data) > 0:
                        to_csv(output_path + previous_office.encode('utf-8') + '.csv', office_data, 'w')

                    office_data = []
                    previous_office = office_text
                
                if len(headers_text) >= 8:
                    current_candidate = headers_text[7] 
                else:
                    current_candidate = 'nothing'

                if current_candidate != previous_candidate:
                    previous_candidate = current_candidate
                    # TODO possibly create a new csv file
                    office_data.append(['Page'] + headers_text)
                
                for line in votes_text.split('\n'):
                    row = []
                    # if it's not the totals row
                    if 'Totals' not in line.split(' ')[0]:
                        line = line.replace('o','0')
                        row = line.split(' ')
                    # it's the totals row
                    else: 
                        row = line.split(' ')
                        # there's no percentage value in the totals row
                        # so add an empty value to provide column continuity
                        if len(row) > 6:
                            row.insert(5,'')
                        # Find element with Totals and make them all the same
                        totals_index = [i for i, j in enumerate(row) if 'Totals' in str(j)][0]
                        row[totals_index] = 'Totals'
                        # delete common OCR errors in the last element found in the totals row
                        # this reduces column continuity errors by about 1/3
                        if row[-1] == "|" or row[-1] == "I" or row[-1] == "l":
                            del row[-1]
                    row = [office_text] + row
                    office_data.append([page_num] + row)
                    
                    # error checking
                    if len(row) != len(headers_text):
                        error_row = ['column discontinuity', page_num] + row
                        row_to_csv(logfilename, error_row, 'a')
                    else:
                        try:
                            early_ballots = int(row[2])
                            election_ballots = int(row[3])
                            total_ballots = int(row[4])
                            if (early_ballots + election_ballots) != total_ballots:
                                error_row = ['election ballot error', page_num] + row
                                row_to_csv(logfilename, error_row, 'a')
                        except ValueError:
                            error_row = ['election ballot error', page_num] + row
                            row_to_csv(logfilename, error_row, 'a')
                        try: 
                            if "Totals" in headers_text[-1] and office_text != "President and Vice President":
                                candidate_ballots = sum(map(int, row[7:][:-1]))
                                candidates_total = int(row[-1])
                                if candidate_ballots != candidates_total:
                                    error_row = ['candidate ballot error', page_num] + row
                                    row_to_csv(logfilename, error_row, 'a')
                        except ValueError:
                            error_row = ['candidate ballot error', page_num] + row
                            row_to_csv(logfilename, error_row, 'a')

                if page_num == last_page:
                    to_csv(output_path + previous_office.encode('utf-8') + '.csv', office_data, 'w')
                
                numerator = (page_num + 1) - first_page
                bar.numerator = numerator

                print bar,
                print '\r',
                sys.stdout.flush()
                
            else:
                skipped_pages.append(page_num)
    else:
        """ raise error
        """

    print "\n"
    print "Done.\n"
    if len(skipped_pages) > 0:
        print "Page(s) skipped:",
        for page_num in skipped_pages:
            print '  ' + str(page_num),

        error_row = ['skipped pages'] + skipped_pages

        row_to_csv(logfilename, error_row, 'a')

    recommend_csv_repairs(logfilename, pdf_file)


def find_contour_boundaries(cv_img=None, image_file=None, h_min_th=1,  h_max_th=None, 
        w_max_th=None, w_min_th=1, debug_is_on=False):
    """Get the boundaries for features based on the heigth and width thresholds
    Args:
        image_file: filename for image file
        cv_img: filename for image file
        debug_is_on: boolean flag to trigger debug output
    Return: 
        boxes: array with the headers found in the image
        cv_img:
    Raises:
        Nothing
    """
    # set default values for thresholds
    if image_file is not None:
        cv_img = cv2.imread(image_file,1)
    height = cv_img.shape[0]
    width = cv_img.shape[1]
    
    if h_max_th is None:
        h_max_th = height
    if w_max_th is None:
        w_max_th = width

    edges = cv2.Canny(cv_img,100,200)

    im2, contours, hierarchy = cv2.findContours(edges, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)

    # find the boundaries within the box thresholds
    boxes = []
    cnts = []
    for contour in contours:
        if cv2.contourArea(contour, True) > 0:
            x,y,w,h = cv2.boundingRect(contour)
            # find the headers and office
            if h > h_min_th and h < h_max_th and w > w_min_th and w < w_max_th:
                boxes.append({'x': x, 'y': y, 'w': w, 'h': h}) 
                cnts.append(contour)
                if debug_is_on:
                    print "x: " +  str(x) + ", y: " + str(y) + ", w: " + str(w) + ", h: " + str(h)
                    cv2.rectangle(cv_img,(x,y),(x+w,y+h),(0,255,0),2)
   
    return boxes, cv_img, cnts


def image_to_text(image_file=None, debug_is_on=False):
    """Convert the image of the election results to text
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
    
    # find the boxes around the header and the office/proposition
    boxes = []
    lines = []
    
    boxes, cv_img, cnts = find_contour_boundaries(
            cv_img=cv_img, 
            h_min_th=60, 
            w_min_th=50, 
            debug_is_on=debug_is_on)
    
    lines, cv_img, cnts = find_contour_boundaries(
            cv_img=cv_img, 
            h_max_th=10, 
            w_min_th=100, 
            debug_is_on=debug_is_on)
    
    # if the boxes that surround the office and headers were found
    # process the page
    # TODO process the page without the office and headers
    if len(boxes) > 0:
        pil_img = Image.open(image_file)
        width, height = pil_img.size

        # find the location of the column headers and the office
        y_for_column_headers = boxes[0]['y']
        h_for_column_headers = boxes[0]['h']
        y_for_office = boxes[len(boxes)-2]['y']
        
        column_headers = []
        office = {}
        
        for box in boxes:
            x, y, w, h = ( box['x'], box['y'], box['w'], box['h'] )
            if y == y_for_column_headers:
                column_headers.append({'x': x, 'y': y, 'w': w, 'h': h}) 
            if y == y_for_office:
                office = {'x': x, 'y': y, 'w': w, 'h': h} 
        
        # crop the office or proposition text from the image
        x, y, w, h = ( office['x'], office['y'], office['w'], office['h'] )
        cropped = pil_img.crop((x+5,y+5,x+w-5,y+h-5))
        # OCR the office or proposition
        office_text = tesseract.image_to_string(cropped).replace('\n',' ').encode('utf-8')
        office_text = office_text.replace('|', 'I')
        if debug_is_on:
            cropped.save('cropped_office.tiff', "TIFF")

        headers_text = []
        headers_text.append('Office')
        
        column_headers = sorted(column_headers, key=lambda k: k['x'])
        header_index = 0
        for column_header in column_headers:
            # crop the header text from the image
            x, y, w, h = ( column_header['x'], column_header['y'], 
                    column_header['w'], column_header['h'] )
            cropped = pil_img.crop((x+5,y+5,x+w-5,y+h-5))
            
            # the candidates are vertically alligned text
            # so if the header is for the candidate or proposition, 
            # rotate the cropped image 90 degrees clockwise
            if header_index > 5:
                cropped = cropped.transpose(Image.ROTATE_270)
                
            # OCR the header
            header_text = tesseract.image_to_string(cropped).replace('\n', ' ').encode('utf-8')
            headers_text.append(header_text)

            if debug_is_on:
                cv2.rectangle(cv_img,(x,y),(x+w,y+h),(255,0,0),3)
                print header_text
                cropped.save('cropped_'+str(header_index)+'.tiff', "TIFF")
            header_index = header_index + 1 
        
        # draw a white rectangle over the reference lines
        # this mitigates tesseract from skipping a row
        if len(lines) > 0:
            draw = ImageDraw.Draw(pil_img)
            for line in lines:
                x, y, w, h = ( line['x'], line['y'], line['w'], line['h'] )
                draw.rectangle( (x, y, x+w, y+h), fill="white", outline=None)
        
        # crop the election results without the header from the image
        y = y_for_column_headers
        h = h_for_column_headers
        upper = y + h + 5
        left = 1
        right = width - 1
        lower = height - 1
        cropped = pil_img.crop((left, upper, right, lower))
        
        # Adaptive Thresholding
        cv_data_img = cv2.cvtColor(np.array(cropped), cv2.COLOR_RGB2BGR)
 
        cv_data_img = cv2.cvtColor(cv_data_img, cv2.COLOR_BGR2GRAY)

        cv_data_img = cv2.adaptiveThreshold(cv_data_img,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY,11,2)
        
        # TODO
        # Find total
        # boxes, cv_img = find_contour_boundaries(image_file='cropped_votes.tiff', h_min_th=100, debug_is_on=True)
        cropped = Image.fromarray(cv_data_img)
        
        # OCR the election results
        data_text = tesseract.image_to_string(image=cropped, config='-psm 6').encode('utf-8')
        
        # TODO make this optional
        # correct common errors in the OCR results
        data_text = data_text.replace(' e', '6')
        data_text = data_text.replace(' ,', '')
        data_text = data_text.replace(' .', '.')
        data_text = data_text.replace('. ', '.')
        data_text = data_text.replace(' %', '%')
        data_text = data_text.replace(',', '')
        
        if debug_is_on:
            print office_text

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
        cv2.imwrite('boxes.png',cv_img)

    return office_text, headers_text, data_text


def recommend_csv_repairs(logfilename, pdf_file, debug_is_on=False):
    """Recommend csv repairs according to the errors recorded in the log file
    Args:
        logfilename:
        pdf_file:
        debug_is_on: boolean flag to trigger debug output
    Return: 
        
    Raises:
        Nothing
    """
    if debug_is_on:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
    else: 
        timestamp = time.strftime("%Y%m%d")
    
    error_pdf = 'pages_with_ocr_errors_{timestamp}.pdf'.format(timestamp=timestamp)
    recommended_repairs = 'recommended_repairs_{timestamp}.txt'.format(timestamp=timestamp)

    candidate_error = 'candidate ballot error'
    candidate_error_pdf = 'candidate_error_pages_{timestamp}.pdf'.format(timestamp=timestamp)
    candidate_repairs = 'candidate_repairs_{timestamp}.txt'.format(timestamp=timestamp)
    
    ballot_error = 'election ballot error'
    ballot_error_pdf = 'ballot_error_pages_{timestamp}.pdf'.format(timestamp=timestamp)
    ballot_repairs = 'ballot_repairs_{timestamp}.txt'.format(timestamp=timestamp)
    
    column_error = 'column discontinuity'
    column_error_pdf = 'column_error_pages_{timestamp}.pdf'.format(timestamp=timestamp)
    column_repairs = 'column_repairs_{timestamp}.txt'.format(timestamp=timestamp)

    skipped_pages_error = 'skipped pages'
    skipped_pages_pdf = 'skipped_pages_{timestamp}.pdf'.format(timestamp=timestamp)
    
    candidate_errors = []
    ballot_errors = []
    column_errors = []
    skipped_pages = []
    with open(logfilename, 'rb') as csvlog:
        logreader = csv.reader(csvlog)
        for row in logreader:
            # process logfile
            if candidate_error == row[0]:
                candidate_errors.append([row[0]] + [int(row[1])] + row[2:])

            if ballot_error == row[0]:
                ballot_errors.append(row)

            if column_error == row[0]:
                column_errors.append([row[0]] + [int(row[1])] + row[2:])

            if skipped_pages_error == row[0]:
                skipped_pages = row[1:]
                skipped_pages = map(int, skipped_pages)
            
    # find unique patterns among the ballot errors
    ballot_error_patterns = dict((','.join(b_error[3:8]), b_error[0:]) for b_error in ballot_errors)
    
    ballot_errors = []
    for pattern, b_error in ballot_error_patterns.items():
        ballot_errors.append([b_error[0]] + [int(b_error[1])] + b_error[2:] )

    # find unique pages among the ballot errors
    ballot_error_pages = dict((b_error[1], '') for b_error in ballot_errors)
    ballot_error_pages = map(int, ballot_error_pages.keys())
    
    # find unique pages among the column errors
    column_error_pages = dict((col_error[1], '') for col_error in column_errors)
    column_error_pages = map(int, column_error_pages.keys())

    # find unique pages among the candidate errors
    candidate_error_pages = dict((can_error[1], '') for can_error in candidate_errors)
    candidate_error_pages = map(int, candidate_error_pages.keys())
    
    # find unique pages among all the errors 
    error_pages = {}
    error_pages = dict((page, '') 
            for page in ballot_error_pages + candidate_error_pages + column_error_pages)
    error_pages = map(int, error_pages.keys())
    
    infile = PdfFileReader(pdf_file, 'rb')
    # generate PDF file with the page(s) containing any errors
    output = PdfFileWriter()
    if len(error_pages) > 0:
        for page_num in sorted(error_pages):
            page = infile.getPage(page_num-1)
            output.addPage(page)

        with open(error_pdf, 'wb') as f:
            output.write(f)

    # generate the correction templates for all errors
    previous_page=''
    patterns=[]
    with open(recommended_repairs,'w') as recomm:
        # sort by page
        for error in sorted(column_errors + candidate_errors + ballot_errors, key=lambda x: x[1]):
            error_type = error[0]
            page=error[1]
            row_id=error[3]
            row='    '.join(error[3:])
            if error_type == ballot_error:
                pattern=','.join(error[3:8])
            else:
                pattern=','.join(error[3:])
            search_file = '{office}.csv'.format(office=error[2])
            if page != previous_page:
                # sort the patterns by precinct
                for p in sorted(patterns):
                    if p['error_type'] == ballot_error:
                        search = '*'
                    else:
                        search = '\'{search}\''.format(search=p['search_file'])

                    #recomm.write('# {row_id} \n'.format(
                    #    row_id=p['row_id']))
                    recomm.write('# {error}:\n'.format(
                        error=p['error_type']))
                    recomm.write('# {row} \n'.format(
                        row=p['row']))
                    recomm.write(
                            '\tgrep \"{pattern}\" {search}\n'.format(
                                pattern=p['pattern'],search=search)
                            )
                    recomm.write(
                            '\tsed -i \'s/{pattern}/{pattern}/g\' {search}\n\n'.format(
                                pattern=p['pattern'],search=search)
                            )
                recomm.write('#################################\n')
                recomm.write('# Page {page}\n'.format(page=page))
                recomm.write('#################################\n')
                previous_page = page

                patterns=[]
            patterns.append({
                'row_id':     row_id,
                'pattern':      pattern,
                'search_file':  search_file,
                'error_type':   error_type,
                'row':          row
                })
        # TODO flip the loop so we don't have to do this
        # write last recommendations 
        for p in sorted(patterns):
            if p['error_type'] == ballot_error:
                search = '*'
            else:
                search = '\'{search}\''.format(search=p['search_file'])
            
            #recomm.write('# {row_id} \n'.format(
            #    row_id=p['row_id']))
            recomm.write('# {error}:\n'.format(
                error=p['error_type']))
            recomm.write('# {row} \n'.format(
                row=p['row']))
            recomm.write(
                    '\tgrep \'{pattern}\' {search}\n'.format(
                        pattern=p['pattern'],search=search)
                    )
            recomm.write(
                    '\tsed -i \'s/{pattern}/{pattern}/g\' {search}\n\n'.format(
                        pattern=p['pattern'],search=search)
                    )

    if debug_is_on:
        # generate PDF file with the page(s) containing the ballot errors
        output = PdfFileWriter()
        if len(ballot_error_pages) > 0:
            for page_num in sorted(ballot_error_pages):
                page = infile.getPage(page_num-1)
                output.addPage(page)

            with open(ballot_error_pdf, 'wb') as f:
                output.write(f)
        
        # generate PDF file with the skipped page(s)
        output = PdfFileWriter()
        if len(skipped_pages) > 0:
            for page_num in sorted(skipped_pages):
                page = infile.getPage(page_num-1)
                output.addPage(page)

            with open(skipped_pages_pdf, 'wb') as f:
                output.write(f)

        # generate PDF file with the page(s) containing the ballot errors
        output = PdfFileWriter()
        if len(column_error_pages) > 0:
            for page_num in sorted(column_error_pages):
                page = infile.getPage(page_num-1)
                output.addPage(page)

            with open(column_error_pdf, 'wb') as f:
                output.write(f)

        # generate PDF file with the page(s) containing the candidate errors
        output = PdfFileWriter()
        if len(candidate_error_pages) > 0:
            for page_num in sorted(candidate_error_pages):
                page = infile.getPage(page_num-1)
                output.addPage(page)

            with open(candidate_error_pdf, 'wb') as f:
                output.write(f)
        
        # generate the correction templates for ballot errors
        previous_page=''
        patterns=[]
        with open(ballot_repairs,'w') as recomm:
            # sort by page
            for key, value in sorted(ballot_error_patterns.items(), key=lambda x: x[1][0]):
                page=ballot_error_patterns[key][0]
                precinct=ballot_error_patterns[key][2]
                pattern=key
                if page != previous_page:
                    # sort the patterns by precinct
                    for p in sorted(patterns):
                        recomm.write('# Precinct {precinct}\n'.format(precinct=p[0]))
                        recomm.write('\tgrep \'{pattern}\' *\n'.format(pattern=p[1]))
                        recomm.write('\tsed -i \'s/{pattern}/{pattern}/g\' *\n'.format(pattern=p[1]))
                    recomm.write('#################################\n')
                    recomm.write('# Page {page}\n'.format(page=page))
                    recomm.write('#################################\n')
                    previous_page = page

                    patterns=[]
                patterns.append([precinct,pattern])
            # write last recommendations 
            for p in sorted(patterns):
                recomm.write('# Precinct {precinct}\n'.format(precinct=p[0]))
                recomm.write('\tgrep \'{pattern}\' *\n'.format(pattern=p[1]))
                recomm.write('\tsed -i \'s/{pattern}/{pattern}/g\' *\n'.format(pattern=p[1]))

        # generate the correction templates for column discontinuities
        previous_page=''
        patterns=[]
        with open(column_repairs,'w') as recomm:
            # sort by page
            for col_error in sorted(column_errors, key=lambda x: x[1]):
                page=col_error[1]
                precinct=col_error[3]
                pattern=','.join([str(col_error[1])] + col_error[2:])
                csv_file = '{office}.csv'.format(office=col_error[2])
                if page != previous_page:
                    # sort the patterns by precinct
                    for p in sorted(patterns):
                        recomm.write('# {precinct}\n'.format(precinct=p[0]))
                        recomm.write(
                                '\tgrep \'{pattern}\' \'{csv_file}\'\n'.format(
                                    pattern=p[1],csv_file=p[2])
                                )
                        recomm.write(
                                '\tsed -i \'s/{pattern}/{pattern}/g\' \'{csv_file}\'\n'.format(
                                    pattern=p[1],csv_file=p[2])
                                )
                    recomm.write('#################################\n')
                    recomm.write('# Page {page}\n'.format(page=page))
                    recomm.write('#################################\n')
                    previous_page = page

                    patterns=[]
                patterns.append([precinct,pattern,csv_file])
            # write last recommendations 
            for p in sorted(patterns):
                recomm.write('# {precinct}\n'.format(precinct=p[0]))
                recomm.write(
                        '\tgrep \'{pattern}\' \'{csv_file}\'\n'.format(
                            pattern=p[1],csv_file=p[2])
                        )
                recomm.write(
                        '\tsed -i \'s/{pattern}/{pattern}/g\' \'{csv_file}\'\n'.format(
                            pattern=p[1],csv_file=p[2])
                        )
        
        # generate the correction templates for candidate errors
        previous_page=''
        patterns=[]
        with open(candidate_repairs,'w') as recomm:
            # sort by page
            for can_error in sorted(candidate_errors, key=lambda x: x[1]):
                page=can_error[1]
                precinct=can_error[3]
                pattern=','.join([str(can_error[1])] + can_error[2:])
                csv_file = '{office}.csv'.format(office=can_error[2])
                if page != previous_page:
                    # sort the patterns by precinct
                    for p in sorted(patterns):
                        recomm.write('# Precinct {precinct}\n'.format(precinct=p[0]))
                        recomm.write(
                                '\tgrep \'{pattern}\' \'{csv_file}\'\n'.format(
                                    pattern=p[1],csv_file=p[2])
                                )
                        recomm.write(
                                '\tsed -i \'s/{pattern}/{pattern}/g\' \'{csv_file}\'\n'.format(
                                    pattern=p[1],csv_file=p[2])
                                )
                    recomm.write('#################################\n')
                    recomm.write('# Page {page}\n'.format(page=page))
                    recomm.write('#################################\n')
                    previous_page = page

                    patterns=[]
                patterns.append([precinct,pattern,csv_file])
            # write last recommendations 
            for p in sorted(patterns):
                recomm.write('# Precinct {precinct}\n'.format(precinct=p[0]))
                recomm.write(
                        '\tgrep \'{pattern}\' \'{csv_file}\'\n'.format(
                            pattern=p[1],csv_file=p[2])
                        )
                recomm.write(
                        '\tsed -i \'s/{pattern}/{pattern}/g\' \'{csv_file}\'\n'.format(
                            pattern=p[1],csv_file=p[2])
                        )
    


def find_errors_in_csv_files(csv_path=None, debug_is_on=False):
    """Find csv errors contained in the files inside csv_path
    Args:
        csv_path: path to locate csv files name of csv file
        debug_is_on: boolean flag to trigger debug output
    Return:
        Nothing
    Raises:
        Nothing
    """
    csv_files = "*.csv"

    timestamp = time.strftime("%Y%m%d_%H%M%S")

    logfile = "csv_errors_" + timestamp + ".log"
    
    for csv_file in locate(csv_files, csv_path):
        find_errors_in_csv_file(csv_file, logfile)


def find_errors_in_csv_file(csv=None, logfilename="errors.log", debug_is_on=False):
    """Find csv errors in the csv file
    Args:
        csv: file name of csv file to error check
        logfilename: name of error log file
        debug_is_on: boolean flag to trigger debug output
    Return:
        Nothing
    Raises:
        Nothing
    """
    with open(csv, 'rb') as csvfile:
        csvreader = csv.reader(csvfile)
        header = csvreader.next()
        for row in csvreader:
            if row[1] == "Office":
                header = row
            else: 
                if len(row) != len(header):
                    error_row = ['column discontinuity'] + row
                    row_to_csv(logfilename, error_row, 'a')
                else:
                    try:
                        early_ballots = int(row[3])
                        election_ballots = int(row[4])
                        total_ballots = int(row[5])
                        if (early_ballots + election_ballots) != total_ballots:
                            error_row = ['election ballot error'] + row
                            row_to_csv(logfilename, error_row, 'a')
                    except ValueError:
                        error_row = ['election ballot error'] + row
                        row_to_csv(logfilename, error_row, 'a')
                    try: 
                        if "Totals" in header[-1]:
                            candidate_ballots = sum(map(int, row[8:][:-1]))
                            candidates_total = int(row[-1])
                            if candidate_ballots != candidates_total:
                                error_row = ['candidate ballot error'] + row
                                row_to_csv(logfilename, error_row, 'a')
                    except ValueError:
                        error_row = ['candidate ballot error'] + row
                        row_to_csv(logfilename, error_row, 'a')


def main():
    """Convert the election results in a pdf to csv format
       Check for errors in the csv files
       Provide recommendations for correcting those errors
    """
    args = get_command_line_args()
    settings = read_settings(args)
    pdf_file = settings['pdf_file']
    first_page = settings['first_page']
    last_page = settings['last_page']
    output_path = settings['output_path']
    check_csv_path = settings['check_csv_path']
    check_csv_file = settings['check_csv_file']
    logfile = settings['logfile']
    debug_is_on = settings['debug_is_on']
    
    if logfile is not None:
        if pdf_file is not None:
            recommend_csv_repairs(logfilename=logfile, pdf_file=pdf_file)
        else:
            print "Recommending repairs requires a PDF file of the election results"
    elif check_csv_path is not None:
        find_errors_in_csv_files(csv_path=check_csv_path)
    elif check_csv_file is not None:
        find_errors_in_csv_file(csv=check_csv_file)
    else:
        pdf_to_csv(
                pdf_file=pdf_file, 
                first_page=first_page,
                last_page=last_page,
                output_path=output_path,
                debug_is_on=debug_is_on
            )


if __name__ == "__main__":
    main()
