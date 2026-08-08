# Java 21 Maven Project Creator

This directory contains utility scripts to automatically generate, configure, and verify Java 21 Maven projects tailored exactly to the development constraints of your future employer.

---

## 🛠️ What the Scripts Do

There are two versions of the generation script available:
* **PowerShell**: [create_java21_project.ps1](file:///D:/java/kenny/tw_scripts/create_java21_project/create_java21_project.ps1)
* **Python**: [create_java21_project.py](file:///D:/java/kenny/tw_scripts/create_java21_project/create_java21_project.py)

When you run either script to create a new project:
1. **Generates in Temp Folder**: Runs Maven archetype generation inside your system's temporary directory. This prevents VS Code from scanning or parsing half-completed project configurations.
2. **Injects Custom Configurations**: Modifies the `pom.xml` to force Java 21, upgrade JUnit, and add the logging and Excel reader dependencies.
3. **Creates Resources & Logging Config**: Creates standard Java resources folders (`src/main/resources` and `src/test/resources`) and writes a default `log4j2.xml` console logging template.
4. **Writes IDE Settings**: Sets up a local `.vscode/settings.json` configuring VS Code to automatically update project builds on any configuration change.
5. **Initializes Git & Commits (Optional)**: Optionally runs `git init`, creates a standard `.gitignore` file (configured for Maven, logs, and IDEs), and attempts to make the "Initial commit" automatically.
6. **Atomic Move**: Moves the fully constructed project folder directly to your workspace root.
7. **Verifies the Build**: Runs `mvn clean test` on the final project to verify that all dependencies download and compile successfully.

---

## 📦 What the Setup Configures For You

The generated project sets up a robust, industry-standard vanilla Java development sandbox:

### 1. **Java 21 Configuration**
Sets up your compiler source and target properties to **Java 21**, ensuring your code complies with modern LTS standards.

### 2. **JUnit 4.13.2 (Testing)**
* **What it is**: A tool for writing automatic unit tests.
* **Why it's used**: Instead of manually starting and clicking buttons in a running game server to verify changes, you write short code tests that check if functions produce the expected output. In slot development, this is crucial for running simulation loops to prove your mathematical return-to-player (RTP) models.

### 3. **Log4j 2.24.3 (Fast Logging)**
* **What it is**: A high-throughput logging framework for recording console and file messages.
* **Why it's used**: In professional servers, standard prints (`System.out.println()`) are too slow and degrade performance. Log4j records server actions (e.g. `[INFO] Player bet $1`) and writes them to files or console streams efficiently. A default console appender config is generated in `src/main/resources/log4j2.xml`.

### 4. **Apache POI 5.4.1 (Excel Reader/Writer)**
* **What it is**: A Java library that reads and writes Microsoft Office spreadsheets.
* **Why it's used**: Slot game reels, paytables, weights, and mathematical models are designed by game mathematicians in Excel files. Java code reads these spreadsheets at server startup using Apache POI to dynamically load the game data.

---

## 💼 Employer & Technical Stack Constraints

The project structure is 100% aligned with the guidelines of the target company and their `vindictanoctis-server` repository:

* **Vanilla Java**: No heavy microframeworks like **Spring Boot**, **Quarkus**, or **Micronaut** are used.
* **Maven Build Tool**: Standard POM file format.
* **Proprietary Dependencies Pre-configured**:
  The script automatically places placeholders in your project `pom.xml` (commented out for offline safety) for their private internal tools:
  * `com.ejs.games:game-api:1.2-SNAPSHOT` (Scope: `provided` - compiled against, but supplied by the running game server container).
  * `com.nolimitcity:game-simulator:1.8` (Scope: `test` - used exclusively for simulations and tests).
  
  *Once you are onboarded and connected to the company network, simply uncomment these in your `pom.xml` to fetch them.*

---

## 🚀 How to Run the Scripts

From the root directory (`D:\java\kenny`), run either command to generate a new sandbox project:

### Using PowerShell:
* **Interactive**:
  ```powershell
  .\tw_scripts\create_java21_project\create_java21_project.ps1 -ArtifactId "your-project-name"
  ```
  *(It will prompt you for the Group ID and whether you want Git initialization.)*
* **Batch Mode (No Prompts)**:
  ```powershell
  .\tw_scripts\create_java21_project\create_java21_project.ps1 -ArtifactId "your-project-name" -GroupId "com.yourname" -InitGit "yes"
  ```

### Using Python:
* **Interactive**:
  ```bash
  python tw_scripts/create_java21_project/create_java21_project.py
  ```
  *(It will prompt you for the project name, Group ID, and whether you want Git initialization.)*
* **Batch Mode (No Prompts)**:
  ```bash
  python tw_scripts/create_java21_project/create_java21_project.py your-project-name com.yourname y
  ```