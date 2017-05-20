
# USD Qt Components

Reusable UI components for viewing and authoring USD files.

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
