# fc-macros
This repo contains my collection of macros for FreeCAD.

### Search and replace
Provides a search and replace function for expressions in the document.
Currently, it only supports replacing all.

### Copy expressions by label
Copies all expression from one object to another given the label name of two objects.

### Named Part
Initializes a new document with a Part Container and a Part design body following a preffered naming convention.

### MVC Gui
Provides a widget for interacting with "Mini Version Control".

Depends on the mvc package being present in the FreeCAD python environment.
Clone the mvc package into the FreeCAD user mod directory:

    git clone https://github.com/jelle284/mvc.git

- Windows: %APPDATA%\FreeCAD\v1-1\Mod\
- Linux: ~/.local/share/FreeCAD/v1-1/Mod/
- macOS: ~/Library/Application Support/FreeCAD/v1-1/Mod/
