
# usdQt

## Reusable UI widgets for viewing and authoring USD files

The components in usdview are good reference, but they’re purpose built for the usdview application and are implemented in a way that makes them difficult to extract.  We need widgets that provide similar functionality that we can use ad-hoc throughout our pipeline. 

### Project Goals
- make it easy to build standalione usdview-like applications, or integrate with client plugins (maya, katana, etc)
- long term, build a complete replacement of usdview

### Design Requirements
- separate models and views
- standardize signals/slots between widgets
- support PyQt4/PyQt5/PySide/PySide2


**This is a first look to get feedback. This repo may go away!**

## Components

### Current
- **prim outliner**: view prim hierarchy
  - similar to the outliner in usdview, but built on an MVC design
  - also includes editing capabilities:
    - switch variants
    - add references
    - add Xforms
- **sublayer view**: view sub-layers and choose the current target
- **layer editor**: view usd ascii for current layer

### Planned
- **variant set editor**: display and create variants and variant sets
- **stage signaler**: convert stage notifications into Qt signals
- **prim property editor**: view and edit properties/attributes of a prim
- **hydra viewport**: display changes to the stage in realtime

## Installing

First, install the dependencies:

```
pip install -r requirements.txt --user
```

Note that this assumes you have pyside/2 or pyqt4/5 installed.  If you don't, then 
run the following (and cross your fingers), or use homebrew:

```
pip install PySide --user
```

You'll also obviously need to make sure that you've built USD and placed the `pxr` python package on the `PYTHONPATH`.

## Testing

To test it out:

```
python usdQt/app.py /path/to/file.usd
```
