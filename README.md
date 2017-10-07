# Convert Election Results
This package provides a python module to convert the [election results](http://www.harrisvotes.com/ElectionResults.aspx) of Harris County, Texas, into csv format. It accepts as input the PDF canvass report for the entire county. E.g., [General and Special Elections of November 2016](http://www.harrisvotes.com/HISTORY/20161108/canvass/canvass.pdf). The PDF canvas reports are available online [here](http://www.harrisvotes.com/ElectionResults.aspx).

It also generates a separate csv file for each office or proposition being tallied. The module will correct common errors on the OCR, but the final output is not accurate and requires manual review. For instance, the raw output for the November elections of 2012, 2014, and 2016 can be found [here](https://github.com/jksinton/Harris-County-Election-Results/tree/raw-output).

Please note that it does not process the cummulative reports. 

## Python Dependencies:
  * [pytesseract](https://github.com/madmaze/pytesseract)
  * [PyPDF2](https://github.com/mstamy2/PyPDF2)
  * [Pillow](https://github.com/python-pillow/Pillow)
  * cv2 (OpenCV 3.3+) See, e.g., [opencv-python](https://github.com/skvark/opencv-python) or [compile OpenCV with the Python module](https://www.pyimagesearch.com/2016/10/24/ubuntu-16-04-how-to-install-opencv/)

## Usage:

```
usage: convert-election-results.py [-h] [-p PDF] [-i IMAGE_FILE]
                                   [--first-page FIRST_PAGE]
                                   [--last-page LAST_PAGE] [-o OUTPUT_PATH]
                                   [-v] [-d]

Convert election results to computer readable format, e.g., csv, json, xml

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
                        path to write csv files
  -v, --version         show program's version number and exit
  -d, --debug           print debug messages

```

## Disclaimer
This product uses the election results available from the Harris County Clerk but is not endorsed or certified by the Harris County Clerk.
