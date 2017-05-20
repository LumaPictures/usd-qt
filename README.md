
# USD Qt Components

Reusable UI components for viewing and authoring USD files.

**This is a first look to start some conversations. This repo may go away!**

## Installing

First, install the dependencies:

```
pip install -r requirements.txt --user
```

Note that this assumes you have pyside/2 or pyqt4/5 installed.  If you don't, then 
run the following (and cross your fingers):

```
pip install PySide --user
```

You'll also obviously need to make sure that you've built USD and placed the `pxr` python package on the `PYTHONPATH`.

## Testing

To test it out:

```
python usdqt/app.py /path/to/file.usd
```
