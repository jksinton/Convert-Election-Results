# Convert-Election-Results
Convert the election results from Harris County, Texas, to csv format.

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
