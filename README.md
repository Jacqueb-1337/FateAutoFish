
# Auto Fishing for FATE by WildTangent

A simple python script to automate fishing.

## How to use:
https://www.youtube.com/watch?v=QL5kxrQK4DI


## Build Requirements
`python`

`pip`

## Build steps

Install PyInstaller:
```bash
  pip install --upgrade PyInstaller
```
Install requirement Python nodes:
```bash
pip install PyQt5 keyboard opencv-python numpy pyautogui pygetwindow pytesseract
```
Use the provided autofish.spec with PyInstaller to create an executable:
```bash
  pyinstaller autofish.spec
```
If pyinstaller can't be found, it's probably because your PATH variables aren't set correctly. Easy bypass:
```bash
  python -m PyInstaller autofish.spec
```
"PyInstaller" capitalization DOES matter here.
## Building executable without console
You can build the executable so that it will not show the console at runtime. Edit `autofish.spec` and change line 32 from `console=False,` to `console=True,`
## Running the script directly
If you want to just run the script without building an executable, open command prompt in the same directory as autofish.py, and run:
```bash
  pip install PyQt5 keyboard opencv-python numpy pyautogui pygetwindow pytesseract

  python autofish.py
```
