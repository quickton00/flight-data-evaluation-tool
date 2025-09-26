# Flight Data Evaluation Tool

The Flight Data Evaluation Tool is a Python package that provides a GUI for the evaluation of flight data.
It is developed for TUM internal usage at the Chair for Human Spaceflight Technology.

## How to package the code using pyinstaller

1. Install pyinstaller:

pip install pyinstaller

2. Navigate to the folder where gui.py is located, e.g.:

cd .\src\flight_data_evaluation_tool\

3. Build .exe:
pyinstaller --onefile --windowed --icon=icon.ico --add-data "icon.ico;." --add-data "results_template.json;." --add-data "database/*.json;database" app.py --name "Flight Data Evaluation Tool"

Note:
To better debug the application DON'T use --windowed to get prints in a terminal.

## Project Organization

- `.github/workflows`: Contains GitHub Actions used for building, testing, and publishing.
- `.devcontainer/Dockerfile`: Contains Dockerfile to build a development container for VSCode with all the necessary extensions for Python development installed.
- `.devcontainer/devcontainer.json`: Contains the configuration for the development container for VSCode, including the Docker image to use, any additional VSCode extensions to install, and whether or not to mount the project directory into the container.
- `.vscode/settings.json`: Contains VSCode settings specific to the project, such as the Python interpreter to use and the maximum line length for auto-formatting.
- `src`: Place new source code here.
- `tests`: Contains Python-based test cases to validate source code.
- `pyproject.toml`: Contains metadata about the project and configurations for additional tools used to format, lint, type-check, and analyze Python code.

## Contributing

Currently changes are currently committed directly to the main branch.
If multiple people work on the project consider using branches and Pull-Requests.

### `pyproject.toml`

Distribution via project.toml is currently not used.

The pyproject.toml file is a centralized configuration file for modern Python projects. It streamlines the development process by managing project metadata, dependencies, and development tool configurations in a single, structured file. This approach ensures consistency and maintainability, simplifying project setup and enabling developers to focus on writing quality code. Key components include project metadata, required and optional dependencies, development tool configurations (e.g., linters, formatters, and test runners), and build system specifications.

In this particular pyproject.toml file, the [build-system] section specifies that the Flit package should be used to build the project. The [project] section provides metadata about the project, such as the name, description, authors, and classifiers. The [project.optional-dependencies] section lists optional dependencies, like pyspark, while the [project.urls] section supplies URLs for project documentation, source code, and issue tracking.

The file also contains various configuration sections for different tools, including bandit, black, coverage, flake8, pyright, pytest, tox, and pylint. These sections specify settings for each tool, such as the maximum line length for flake8 and the minimum code coverage percentage for coverage.

#### Tool Sections

##### black

Black is a Python code formatter that automatically reformats Python code to conform to the PEP 8 style guide. It is used to maintain a consistent code style throughout the project.

The pyproject.toml file specifies the maximum line length and whether or not to use a "fast" mode for formatting. Black also allows for a pyproject.toml configuration file to be included in the project directory to customize its behavior.

##### coverage

Coverage is a tool for measuring code coverage during testing. It generates a report of which lines of code were executed during testing and which were not.

The pyproject.toml file specifies that branch coverage should be measured and that the tests should fail if the coverage falls below 100%. Coverage can be integrated with a variety of test frameworks, including pytest.

##### pytest

Pytest is a versatile testing framework for Python projects that simplifies test case creation and execution. It supports both pytest-style and unittest-style tests, offering flexibility in testing approaches. Key features include fixture support for clean test environments, parameterized tests to reduce code duplication, and extensibility through plugins for customization. Adopt pytest to streamline testing and tailor the framework to your project's specific needs.

The pyproject.toml file plays an essential role in configuring pytest for your project. It includes various test markers, such as integration, notebooks, gpu, spark, slow, and unit, which are used during testing. It also specifies options for generating test coverage reports, setting the Python path, and outputting test results in the xunit2 format. You can easily modify the pyproject.toml file to customize pytest for your project's specific needs.

##### pylint
Pylint is a versatile Python linter and static analysis tool that identifies errors and style issues in your code. It generates an in-depth report, presenting errors, warnings, and conventions found in the codebase. Pylint configurations are centralized in the pyproject.toml file, covering extension management, warning suppression, output formatting, and code style settings such as maximum function arguments and class attributes. The unique scoring system provided by Pylint helps developers assess and maintain code quality, ensuring a focus on readability and maintainability throughout the project's development.

##### pyright
Pyright is a static type checker for Python that uses type annotations to analyze your code and catch type-related errors. It is capable of analyzing Python code that uses type annotations as well as code that uses docstrings to specify types.

The pyproject.toml file contains configurations for Pyright, such as the directories to include or exclude from analysis, the virtual environment to use, and various settings for reporting missing imports and type stubs. By using Pyright, you can catch errors related to type mismatches before they even occur, which can save you time and improve the quality of your code.

##### flake8
Flake8 is a code linter for Python that checks your code for style and syntax issues. It checks your code for PEP 8 style guide violations, syntax errors, and more.

The pyproject.toml file contains configurations for Flake8, such as the maximum line length, which errors to ignore, and which style guide to follow. By using Flake8, you can ensure that your code follows the recommended style guide and catch syntax errors before they cause problems.

##### tox
In our repository, we use Tox to automate testing and building our Python package across various environments and versions. Configured through the pyproject.toml file, Tox is set up with four testing environments: py, integration, spark, and all. Each environment targets specific test categories or runs all tests together, ensuring compatibility and functionality in different scenarios.

The [tool.tox] section in the pyproject.toml file contains the Tox configuration details, including the legacy_tox_ini attribute. Our setup outlines the dependencies needed for each environment, as well as the test runner (e.g., pytest) and any associated commands. This ensures consistent test execution across all environments.

Tox helps us efficiently automate testing and building processes, maintaining the reliability and functionality of our Python package across a wide range of environments. By identifying potential compatibility issues early in the development process, we improve the quality and usability of our package. Our Tox configuration streamlines the development workflow, promoting code quality and consistency throughout the project.

### Development
#### Devcontainer
Dev Containers in Visual Studio Code allows you to use a Docker container as a complete development environment, opening any folder or repository inside a container and taking advantage of all of VS Code's features. A devcontainer.json file in your project describes how VS Code should access or create a development container with a well-defined tool and runtime stack. You can use an image as a starting point for your devcontainer.json. An image is like a mini-disk drive with various tools and an operating system pre-installed. You can pull images from a container registry, which is a collection of repositories that store images.

Creating a dev container in VS Code involves creating a devcontainer.json file that specifies how VS Code should start the container and what actions to take after it connects. You can customize the dev container by using a Dockerfile to install new software or make other changes that persist across sessions. Additional dev container configuration is also possible, including installing additional tools, automatically installing extensions, forwarding or publishing additional ports, setting runtime arguments, reusing or extending your existing Docker Compose setup, and adding more advanced container configuration.

After any changes are made, you must build your dev container to ensure changes take effect. Once your dev container is functional, you can connect to and start developing within it. If the predefined container configuration does not meet your needs, you can also attach to an already running container instead. If you want to install additional software in your dev container, you can use the integrated terminal in VS Code and execute any command against the OS inside the container.

When editing the contents of the .devcontainer folder, you'll need to rebuild for changes to take effect. You can use the Dev Containers: Rebuild Container command for your container to update. However, if you rebuild the container, you will have to reinstall anything you've installed manually. To avoid this problem, you can use the postCreateCommand property in devcontainer.json. There is also a postStartCommand that executes every time the container starts.

You can also use a Dockerfile to automate dev container creation. In your Dockerfile, use FROM to designate the image, and the RUN instruction to install any software. You can use && to string together multiple commands. If you don't want to create a devcontainer.json by hand, you can select the Dev Containers: Add Dev Container Configuration Files... command from the Command Palette (F1) to add the needed files to your project as a starting point, which you can further customize for your needs.
