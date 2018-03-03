# votes2csv

## What Is It
This package provides a python module to convert the [election results](http://www.harrisvotes.com/ElectionResults.aspx) of Harris County, Texas, into CSV format. It accepts as input the PDF canvass report for the entire county. E.g., [General and Special Elections of November 2016](http://www.harrisvotes.com/HISTORY/20161108/canvass/canvass.pdf). The PDF canvas reports are available online [here](http://www.harrisvotes.com/ElectionResults.aspx).

It also generates a separate csv file for each office or proposition being tallied. The module will correct common errors on the OCR, but the final output is not accurate and requires manual review. For instance, the raw output for the November elections of 2012, 2014, and 2016 will look similar to [this](https://github.com/jksinton/Harris-County-Election-Results/tree/raw-output).

Please note that it does not process the cummulative reports. 

## Install

### Python Dependencies
  * [etaprogress](https://github.com/Robpol86/etaprogress)
  * [numpy](https://github.com/numpy/numpy)
  * [pytesseract](https://github.com/madmaze/pytesseract)
  * [PyPDF2](https://github.com/mstamy2/PyPDF2)
  * [Pillow](https://github.com/python-pillow/Pillow)
  * cv2 (OpenCV 3.3+) See, e.g., [opencv-python](https://github.com/skvark/opencv-python) or [compile OpenCV with the Python module](https://www.pyimagesearch.com/2016/10/24/ubuntu-16-04-how-to-install-opencv/)

### Ghostscript
  * [GPL Ghostscript](https://www.ghostscript.com/) 9.18+
    * This script converts each page of the PDF into a TIFF file using Ghostscript.
    * Check your version:  ``gs -v``

#### Install Ghostscript
  * Ubuntu:  ```sudo apt-get install ghostscript```
  * macOS:  ```brew install ghostscript```

## Instructions
1. Convert the election results to CSV format by providing the pdf file and output path to store the CSVs:  `python votes.py -p canvass-2016.pdf -o 2016`

2. Correct any errors flagged in the error.log file.  
  *  This MUST be done.  There will likely be thousands (e.g., 3000+) of errors identified, but many of the identified errors are duplicates and on the same page.  
  * Only three types of errors are detected: 
    * Column discontinuity (i.e., a row does not have the same number of columns as its header), 
    * Errors in the ballot counts (i.e., there's an error in the precinct level ballot counts), and 
    * Errors in the candidate vote counts (i.e., there's an error in the votes for one of the candidates or total votes). It does not check whether the precinct values are correct or the percentages.
  * Recommended command templates will be generated in the `recommended_repairs.txt` file. You MUST edit the repair commands, by finding the error in the corresponding `error_pages.pdf` file.  This PDF file is a concatenated version of the canvass PDF to facilitate updating the repair commands.

3. Check for errors again by providing the path to all the csv files:  `python votes.py -c 2016`

4. Generate the command templates based on any new errors found by providing the error log file and the canvass PDF:  `python votes.py -r new_error.log -p cavnass.pdf`

5. Repeat steps 2 and 3 as needed until no errors are found.


### An example repair command for a column discontinuity error looks like this:
```bash
# column discontinuity:
# 0010    703    232    935    1830    51    09%    92    466    7    7    572 
	grep "0010,703,232,935,1830,51,09%,92,466,7,7,572" 'Straight Party.csv'
	sed -i 's/0010,703,232,935,1830,51,09%,92,466,7,7,572/0010,703,232,935,1830,51,09%,92,466,7,7,572/g' 'Straight Party.csv'
```
* The first line identifies the type of error.  
* The second line provides a reproduction of the CSV row with each column spaced by whitespace to provide a human readable version of the row to aid in identifying the error.  
* The grep command allows you to check whether the error exists and has been resolved.  
* The sed command is used to correct the error. You edit the second half of the sed command, i.e., you make the correction in the string after the `/`.  

In this example, the percent turnout is split by an extra comma.  To correct this, you would replace the comma with a `.` as provided below.  Finally, you run the following in the directory of the CSV files. You can check if the error has been resolved with the grep command.
```bash
# column discontinuity:
# 0010    703    232    935    1830    51    09%    92    466    7    7    572 
	grep "0010,703,232,935,1830,51,09%,92,466,7,7,572" 'Straight Party.csv'
	sed -i 's/0010,703,232,935,1830,51,09%,92,466,7,7,572/0010,703,232,935,1830,51.09%,92,466,7,7,572/g' 'Straight Party.csv'
```

## Usage

```
usage: votes.py [-h] [-p PDF] [-i IMAGE_FILE] [--first-page FIRST_PAGE]
                [--last-page LAST_PAGE] [-o OUTPUT_PATH] [-c CHECK_CSVS]
                [-e CHECK_CSV] [-r REVIEW_LOGFILE] [-v] [-d]

Convert election results to csv format

optional arguments:
  -h, --help            show this help message and exit
  -p PDF, --pdf PDF     PDF file to process
  -i IMAGE_FILE, --image-file IMAGE_FILE
                        image file to process
  --first-page FIRST_PAGE
                        page to begin processing
  --last-page LAST_PAGE
                        page to end processing
  -o OUTPUT_PATH, --output-path OUTPUT_PATH
                        path to write CSV files
  -c CHECK_CSVS, --check-csvs CHECK_CSVS
                        path containing CSV files to error check
  -e CHECK_CSV, --check-csv CHECK_CSV
                        CSV file to error check
  -r REVIEW_LOGFILE, --review-logfile REVIEW_LOGFILE
                        log file to review and recommend repairs; requires
                        --pdf PDF to be set
  -v, --version         show program's version number and exit
  -d, --debug           print debug messages
```

## Disclaimer
This product uses the election results available from the Harris County Clerk but is not endorsed or certified by the Harris County Clerk.
