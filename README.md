# Flight Data Evaluation Tool

The Flight Data Evaluation Tool is a Python package that provides a GUI for the evaluation of flight data.
It is developed for TUM internal usage at the Chair for Human Spaceflight Technology.

## Quick Start (VS Code on Windows)

Prerequisites:
- Python 3.8–3.11 installed (Windows recommended)
- VS Code + “Python” extension

1) Clone and open in VS Code
```powershell
# original Code Repository: (Read only)
git clone https://github.com/quickton00/flight-data-evaluation-tool.git

# HSP-Fork of above Repository: (use for further development)
git clone https://github.com/HSP-admin/flight-data-evaluation-tool.git
cd flight-data-evaluation-tool
code .
```

2) Create and activate a virtual environment
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
# If activation is blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

3) Install dependencies
```powershell
python -m pip install -U pip
pip install -r requirements.txt
```

4) Select the interpreter in VS Code
- Ctrl+Shift+P → “Python: Select Interpreter” → choose .venv\Scripts\python.exe

5) Run the app
- Terminal:
```powershell
python .\src\flight_data_evaluation_tool\app.py
```

Troubleshooting:
- PowerShell activation: use .\.venv\Scripts\Activate.ps1 (CMD: .\.venv\Scripts\activate.bat)
- VS Code auto-activation: after selecting interpreter, open a new terminal

## How to package the code using pyinstaller

1. Install pyinstaller:

pip install pyinstaller

2. Navigate to the folder where app.py is located, e.g.:

cd .\src\flight_data_evaluation_tool\

3. Build .exe:
pyinstaller --clean '.\Flight Data Evaluation Tool.spec'

Note:
To better debug the application DON'T use --windowed to get prints in a terminal.

## Create requirements.txt

1. install pipreqs

pip install pipreqs

2. Navigate to the folder where requirements.txt is located

2. Build requirements.txt

pipreqs . --force --savepath requirements.txt --ignore tests,.git,.venv

## Rebuild Database

In case you changed the implementation of the metrics used in evaluation, run helper/rebuild_database.py to make the database coherent to your state of implementation.

## Project Organization

- `.github/workflows`: Contains GitHub Actions used for building, testing, and publishing.
- `.devcontainer/Dockerfile`: Contains Dockerfile to build a development container for VSCode with all the necessary extensions for Python development installed.
- `.devcontainer/devcontainer.json`: Contains the configuration for the development container for VSCode, including the Docker image to use, any additional VSCode extensions to install, and whether or not to mount the project directory into the container.
- `.vscode/settings.json`: Contains VSCode settings specific to the project, such as the Python interpreter to use and the maximum line length for auto-formatting.
- `src`: Place new source code here.
- `tests`: Contains Python-based test cases to validate source code.
- `pyproject.toml`: Contains metadata about the project and configurations for additional tools used to format, lint, type-check, and analyze Python code.

## Contributing

Currently changes are committed directly to the main branch.
If multiple people work on the project consider using branches and Pull-Requests.

### `pyproject.toml`

Distribution via project.toml is currently not used, see requirements.txt.

### Development
#### Devcontainer
Dev Container usage is not tested and might not be operational.

Dev Containers in Visual Studio Code allows you to use a Docker container as a complete development environment, opening any folder or repository inside a container and taking advantage of all of VS Code's features. A devcontainer.json file in your project describes how VS Code should access or create a development container with a well-defined tool and runtime stack. You can use an image as a starting point for your devcontainer.json. An image is like a mini-disk drive with various tools and an operating system pre-installed. You can pull images from a container registry, which is a collection of repositories that store images.

Creating a dev container in VS Code involves creating a devcontainer.json file that specifies how VS Code should start the container and what actions to take after it connects. You can customize the dev container by using a Dockerfile to install new software or make other changes that persist across sessions. Additional dev container configuration is also possible, including installing additional tools, automatically installing extensions, forwarding or publishing additional ports, setting runtime arguments, reusing or extending your existing Docker Compose setup, and adding more advanced container configuration.

After any changes are made, you must build your dev container to ensure changes take effect. Once your dev container is functional, you can connect to and start developing within it. If the predefined container configuration does not meet your needs, you can also attach to an already running container instead. If you want to install additional software in your dev container, you can use the integrated terminal in VS Code and execute any command against the OS inside the container.

When editing the contents of the .devcontainer folder, you'll need to rebuild for changes to take effect. You can use the Dev Containers: Rebuild Container command for your container to update. However, if you rebuild the container, you will have to reinstall anything you've installed manually. To avoid this problem, you can use the postCreateCommand property in devcontainer.json. There is also a postStartCommand that executes every time the container starts.

You can also use a Dockerfile to automate dev container creation. In your Dockerfile, use FROM to designate the image, and the RUN instruction to install any software. You can use && to string together multiple commands. If you don't want to create a devcontainer.json by hand, you can select the Dev Containers: Add Dev Container Configuration Files... command from the Command Palette (F1) to add the needed files to your project as a starting point, which you can further customize for your needs.
