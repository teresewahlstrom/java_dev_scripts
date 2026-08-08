#!/usr/bin/env python3
import sys
import os
import subprocess
import re
import tempfile
import shutil
import json

def get_project_inputs():
    """Prompt the user or parse arguments for project details."""
    # Get project name (artifactId)
    if len(sys.argv) > 1:
        artifact_id = sys.argv[1]
    else:
        artifact_id = input("Enter project name (artifactId): ").strip()
        if not artifact_id:
            print("Error: Project name is required.")
            sys.exit(1)
            
    # Get groupId
    if len(sys.argv) > 2:
        group_id = sys.argv[2]
    else:
        default_group = f"com.{artifact_id.replace('-', '.')}"
        group_id = input(f"Enter Group ID [{default_group}]: ").strip()
        if not group_id:
            group_id = default_group

    # Get Git preference
    if len(sys.argv) > 3:
        git_pref = sys.argv[3].lower() in ('true', 'yes', 'y')
    else:
        git_input = input("Initialize Git repository? (y/n) [y]: ").strip().lower()
        git_pref = git_input not in ('n', 'no')

    return artifact_id, group_id, git_pref


def adjust_pom_to_java21(pom_path):
    """Modify pom.xml properties to target Java 21 and configure dependencies."""
    print("\nAutomatically adjusting pom.xml to force Java 21 and configure dependencies...")
    with open(pom_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Update compiler source/target properties
    updated_content = re.sub(
        r'<maven\.compiler\.source>.*?</maven\.compiler\.source>',
        '<maven.compiler.source>21</maven.compiler.source>',
        content
    )
    updated_content = re.sub(
        r'<maven\.compiler\.target>.*?</maven\.compiler\.target>',
        '<maven.compiler.target>21</maven.compiler.target>',
        updated_content
    )

    # Define the new dependencies block
    dependencies_block = """  <dependencies>
    <!-- Testing -->
    <dependency>
      <groupId>junit</groupId>
      <artifactId>junit</artifactId>
      <version>4.13.2</version>
      <scope>test</scope>
    </dependency>

    <!-- Logging (Log4j 2) -->
    <dependency>
      <groupId>org.apache.logging.log4j</groupId>
      <artifactId>log4j-api</artifactId>
      <version>2.24.3</version>
    </dependency>
    <dependency>
      <groupId>org.apache.logging.log4j</groupId>
      <artifactId>log4j-core</artifactId>
      <version>2.24.3</version>
    </dependency>

    <!-- Microsoft Office Open XML (Excel) -->
    <dependency>
      <groupId>org.apache.poi</groupId>
      <artifactId>poi</artifactId>
      <version>5.4.1</version>
    </dependency>
    <dependency>
      <groupId>org.apache.poi</groupId>
      <artifactId>poi-ooxml</artifactId>
      <version>5.4.1</version>
    </dependency>

    <!-- Proprietary/Internal Dependencies (Add these when connected to the company network):
    - com.ejs.games:game-api:1.2-SNAPSHOT (Scope: provided)
    - com.nolimitcity:game-simulator:1.8 (Scope: test)
    -->
  </dependencies>"""

    # Replace the existing dependencies block
    updated_content = re.sub(
        r'<dependencies>.*?</dependencies>',
        dependencies_block,
        updated_content,
        flags=re.DOTALL
    )

    with open(pom_path, 'w', encoding='utf-8') as f:
        f.write(updated_content)
    print("Successfully updated pom.xml configurations.")


def setup_resource_directories(temp_proj_path):
    """Create default resource directories and write the log4j2.xml configuration."""
    print("\nSetting up project resource directories and default Log4j2 config...")
    try:
        main_resources = os.path.join(temp_proj_path, "src", "main", "resources")
        test_resources = os.path.join(temp_proj_path, "src", "test", "resources")
        os.makedirs(main_resources, exist_ok=True)
        os.makedirs(test_resources, exist_ok=True)

        log4j_path = os.path.join(main_resources, "log4j2.xml")
        log4j_content = """<?xml version="1.0" encoding="UTF-8"?>
<Configuration status="WARN">
  <Appenders>
    <Console name="Console" target="SYSTEM_OUT">
      <PatternLayout pattern="%d{yyyy-MM-dd HH:mm:ss.SSS} [%t] %-5level %logger{36} - %msg%n"/>
    </Console>
  </Appenders>
  <Loggers>
    <Root level="info">
      <AppenderRef ref="Console"/>
    </Root>
  </Loggers>
</Configuration>
"""
        with open(log4j_path, 'w', encoding='utf-8') as f:
            f.write(log4j_content)
        print("Created default log4j2.xml in src/main/resources.")
    except Exception as e:
        print(f"Warning: Could not configure resources: {e}")



def configure_vscode_settings(temp_proj_path):
    """Write VS Code automatic configuration update settings in the project and workspace."""
    print("\nAdding VS Code settings to automatically update project configuration...")
    # Write .vscode/settings.json in the temporary project directory
    project_vscode_dir = os.path.join(temp_proj_path, ".vscode")
    os.makedirs(project_vscode_dir, exist_ok=True)
    project_settings_path = os.path.join(project_vscode_dir, "settings.json")
    settings_data = {
        "java.configuration.updateBuildConfiguration": "automatic"
    }
    with open(project_settings_path, 'w', encoding='utf-8') as f:
        json.dump(settings_data, f, indent=4)
    
    # Write/update .vscode/settings.json in the workspace root (two directories up)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    workspace_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
    ws_vscode_dir = os.path.join(workspace_root, ".vscode")
    os.makedirs(ws_vscode_dir, exist_ok=True)
    ws_settings_path = os.path.join(ws_vscode_dir, "settings.json")
    ws_settings = {}
    if os.path.exists(ws_settings_path):
        try:
            with open(ws_settings_path, 'r', encoding='utf-8') as f:
                ws_settings = json.load(f)
        except Exception:
            pass
    ws_settings["java.configuration.updateBuildConfiguration"] = "automatic"
    with open(ws_settings_path, 'w', encoding='utf-8') as f:
        json.dump(ws_settings, f, indent=4)
    print("Successfully configured VS Code settings.")


def create_gitignore_file(temp_proj_path):
    """Write standard Java/Maven .gitignore file in the project."""
    gitignore_path = os.path.join(temp_proj_path, ".gitignore")
    gitignore_content = """# Maven build output
target/

# IDE files
.vscode/
.idea/
*.iml
.classpath
.project
.settings/
.factorypath

# Compilation output
*.class
dependency-reduced-pom.xml

# Log files
*.log
logs/

# OS files
Thumbs.db
.DS_Store
"""
    with open(gitignore_path, 'w', encoding='utf-8') as f:
        f.write(gitignore_content)


def initialize_git_repository(project_path):
    """Initialize a Git repository and commit the initial files at the destination."""
    print("\nInitializing Git repository...")
    try:
        # Initialize Git and add files
        subprocess.run(["git", "init"], cwd=project_path, check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["git", "add", "."], cwd=project_path, check=True)
        
        # Try to commit (might skip if git user name/email are not configured)
        result = subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=project_path, capture_output=True, text=True)
        if result.returncode == 0:
            print("Successfully initialized Git and made the initial commit.")
        else:
            print("Successfully initialized Git (initial commit skipped due to missing user.name/email in git config).")
    except Exception as e:
        print(f"Warning: Could not initialize Git repository: {e}")


def safe_rmtree(path):
    """Deletes a directory tree safely, resolving Windows read-only file permission errors."""
    import stat
    if os.path.exists(path):
        def remove_readonly(func, p, excinfo):
            os.chmod(p, stat.S_IWRITE)
            func(p)
        shutil.rmtree(path, onerror=remove_readonly)


def verify_build(project_path):
    """Run Maven compilation and test suite to verify the project builds successfully."""
    print("\nVerifying the build...")
    try:
        # Run clean test in the new project directory
        subprocess.run(["mvn", "clean", "test"], cwd=project_path, check=True, shell=True)
        print("\n=== Success! Project is generated and verified with Java 21! ===")
        print(f"Project location: {os.path.abspath(project_path)}")
    except subprocess.CalledProcessError:
        print("\nWarning: Build verification failed. Please check the project manually.")


def main():
    print("=== Java 21 Maven Project Creator ===")
    
    artifact_id, group_id, initialize_git = get_project_inputs()
    print(f"\nCreating project '{artifact_id}' with Group ID '{group_id}'...")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    workspace_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
    destination = os.path.join(workspace_root, artifact_id)
    
    print("\nGenerating project in temporary directory to prevent IDE race conditions...")
    
    try:
        temp_dir = tempfile.mkdtemp(prefix="java_gen_")
    except Exception as e:
        print(f"Error creating temp directory: {e}")
        sys.exit(1)

    try:
        # Run Maven archetype generate in temp directory
        cmd = [
            "mvn", "archetype:generate",
            "-B",
            "-DarchetypeGroupId=org.apache.maven.archetypes",
            "-DarchetypeArtifactId=maven-archetype-quickstart",
            "-DarchetypeVersion=1.4",
            f"-DgroupId={group_id}",
            f"-DartifactId={artifact_id}",
            "-Darchetype.interactive=false"
        ]
        subprocess.run(cmd, cwd=temp_dir, check=True, shell=True)

        temp_proj_path = os.path.join(temp_dir, artifact_id)
        pom_path = os.path.join(temp_proj_path, "pom.xml")
        if not os.path.exists(pom_path):
            raise FileNotFoundError(f"Could not find pom.xml at {pom_path}")

        adjust_pom_to_java21(pom_path)
        setup_resource_directories(temp_proj_path)

        try:
            configure_vscode_settings(temp_proj_path)
        except Exception as e:
            print(f"Warning: Could not write VS Code settings: {e}")

        if initialize_git:
            try:
                create_gitignore_file(temp_proj_path)
            except Exception as e:
                print(f"Warning: Could not create .gitignore file: {e}")

        print("\nMoving finalized project to workspace root...")
        safe_rmtree(destination)
        shutil.move(temp_proj_path, destination)
        print(f"Project moved successfully to {destination}")

        if initialize_git:
            try:
                initialize_git_repository(destination)
            except Exception as e:
                print(f"Warning: Git initialization failed: {e}")

    except Exception as e:
        print(f"\nError: Project generation failed. {e}")
        sys.exit(1)
    finally:
        safe_rmtree(temp_dir)

    verify_build(destination)

if __name__ == "__main__":
    main()
