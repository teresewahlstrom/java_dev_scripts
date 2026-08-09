# Java 21 Maven Project Creator

This directory contains one Python utility that generates, configures, and verifies a vanilla Java 21 Maven project.

## What it does

The script:

1. Generates a Maven quickstart project in an isolated system temporary directory.
2. Updates the POM with structured XML editing rather than regular expressions.
3. Configures Java 21, JUnit 4.13.2, Log4j 2.24.3, and Apache POI 5.4.1.
4. Adds resource directories, a console Log4j configuration, project-local VS Code settings, and a Java/Maven `.gitignore`.
5. Moves the completed project to the workspace root.
6. Optionally initializes Git and attempts an initial commit.
7. Runs `mvn clean test` and returns a nonzero exit code if generation or verification fails.

## Why these tools and dependencies are included

This project is meant to help you practise in an environment that resembles the employer's vanilla Java and Maven setup. Each part has a different job.

### Maven and `pom.xml`

**Maven** is the build tool. It compiles Java, downloads libraries, runs tests, and packages the project. The `pom.xml` file is Maven's project description: it records the Java version, project name, dependencies, and build configuration.

When this README says **dependency**, it means external code that the project uses. Maven downloads public dependencies from Maven Central and places them on the project's classpath, so you do not copy library files into the repository manually.

### Java 21

The compiler source and target are set to Java 21. This makes the practice project compile using the same Java language level you expect to encounter at the employer. Java 21 is an LTS (long-term support) release.

### JUnit 4.13.2 — automated testing

**What it is:** JUnit is a framework for writing tests that check Java code automatically. JUnit is given `test` scope, which means it is available while tests are compiled and run, but it is not included as a runtime dependency of the main application.

**Why it is useful here:** Game mathematics and slot simulations need repeatable checks. A test can verify a payout calculation, reel result, or edge case every time the code changes instead of relying on manual testing.

### Log4j 2.24.3 — application logging

**What it is:** Log4j records messages from the application. It supports severity levels such as `DEBUG`, `INFO`, `WARN`, and `ERROR`, and can send messages to the console or log files.

**Why it is useful here:** Logging makes it easier to observe server and simulation behaviour without scattering `System.out.println()` calls throughout the code. The script creates `src/main/resources/log4j2.xml` with a console logger so Log4j works immediately. `log4j-api` is the interface used by Java code; `log4j-core` is the implementation that processes and outputs the messages.

### Apache POI 5.4.1 — Excel files

**What it is:** Apache POI is a Java library for reading and writing Microsoft Office formats. `poi` provides the core spreadsheet APIs, while `poi-ooxml` adds support for modern `.xlsx` workbooks.

**Why it is useful here:** In game development, reel strips, symbol weights, paytables, and mathematical configurations are often maintained in spreadsheets. Java can load that data with POI rather than duplicating every value by hand.

### Relationship to the employer's private stack

The employer's real projects also use private game-server and simulation dependencies. This project intentionally does not include placeholders for those libraries because they are proprietary and unavailable outside the employer's environment.

Instead, this setup reproduces the surrounding public technology and development workflow: Java, Maven, automated testing, logging, spreadsheet-driven configuration, and simulation-oriented code. It is a practice environment, not a copy of the employer's internal codebase.

## Requirements

- Python 3.10 or newer
- Java 21
- Maven available on `PATH`
- Git on `PATH` when Git initialization is requested
- Network access to Maven Central when required artifacts are not already cached

## Usage

Run commands from the directory that contains `tw_scripts`.

Interactive:

```powershell
python .\tw_scripts\create_java21_project\create_java21_project.py
```

Batch mode:

```powershell
python .\tw_scripts\create_java21_project\create_java21_project.py your-project-name com.yourname y
```

The third positional argument accepts `y`, `yes`, `true`, `n`, `no`, or `false`.

### Replacing an existing project

The script refuses to overwrite an existing destination. Replacement must be explicitly requested:

```powershell
python .\tw_scripts\create_java21_project\create_java21_project.py your-project-name com.yourname y --force
```

**Warning:** `--force` recursively removes the existing project directory after Maven has successfully generated the replacement. Commit or back up valuable work first.

## Generated configuration

- Java compiler source and target: 21
- JUnit: 4.13.2, test scope
- Log4j API and Core: 2.24.3
- Apache POI and POI OOXML: 5.4.1
- Log4j console configuration: `src/main/resources/log4j2.xml`
- VS Code setting: `.vscode/settings.json`

The script only writes VS Code settings inside the generated project. It does not change settings in the parent workspace.

## Tests

The tests do not require Maven or network access:

```powershell
python -m unittest discover -s .\tw_scripts\create_java21_project -p "test_*.py"
```
