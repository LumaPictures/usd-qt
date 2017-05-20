
# USD Qt Components

Reusable UI components for viewing and authoring USD files.

The components in usdview are good reference, but they’re purpose built for the usdview application and are implemented in a way that makes them difficult to extract. All widgets in this library use separate models and views and a standardized set of signals to trigger updates makeing it easy to customize views and build applications a la carte.  Also, since these widgets are meant to be consumed anywhere and by everything, they will be designed to work in PyQt4/PyQt5/PySide/PySide2. Our long term goal is to break up the remaining parts of usdview and add them to this collection as well, such that it can be used to build usdview-like applications that are more easily customized.

**This is a first look to get feedback. This repo may go away!**

## Components

### Current
- prim outliner: view prim hierarchy
 - similar to the outliner in usdview, but built on an MVC design
 - also includes additional editing capabilities:
  - switch variant
  - add reference
  - add Xform
- sub-layer selector: view sub-layers and choose the current target
- layer editor: view usd ascii for current layer

### Planned
- variant set editor: display and create variants and variant sets
- stage signaler: convert stage notifications into Qt signals
- prim property editor
- hydra viewport

## Installing

First, install the dependencies:

```
pip install -r requirements.txt --user
```

Note that this assumes you have pyside/2 or pyqt4/5 installed.  If you don't, then 
run the following (and cross your fingers) or use homebrew:

```
pip install PySide --user
```

You'll also obviously need to make sure that you've built USD and placed the `pxr` python package on the `PYTHONPATH`.

## Testing

To test it out:

```
python usdqt/app.py /path/to/file.usd
```
