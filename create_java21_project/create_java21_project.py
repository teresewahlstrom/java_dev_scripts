#!/usr/bin/env python3
"""Create and verify a Java 21 Maven project."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET


ARCHETYPE_VERSION = "1.4"
JAVA_VERSION = "21"
JUNIT_VERSION = "4.13.2"
LOG4J_VERSION = "2.24.3"
POI_VERSION = "5.4.1"
MAVEN_NAMESPACE = "http://maven.apache.org/POM/4.0.0"

ARTIFACT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
GROUP_ID_PATTERN = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$"
)

DEPENDENCIES = (
    ("junit", "junit", JUNIT_VERSION, "test"),
    ("org.apache.logging.log4j", "log4j-api", LOG4J_VERSION, None),
    ("org.apache.logging.log4j", "log4j-core", LOG4J_VERSION, None),
    ("org.apache.poi", "poi", POI_VERSION, None),
    ("org.apache.poi", "poi-ooxml", POI_VERSION, None),
)

LOG4J_CONFIGURATION = """<?xml version="1.0" encoding="UTF-8"?>
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

GITIGNORE = """# Maven build output
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


class ProjectCreationError(RuntimeError):
    """Raised when a project cannot be created safely."""


def default_workspace_root() -> Path:
    """Return the default directory for generated projects."""
    return Path(__file__).resolve().parents[2]


def validate_artifact_id(value: str) -> str:
    """Validate an artifact ID that is safe as one path component."""
    if not ARTIFACT_ID_PATTERN.fullmatch(value):
        raise argparse.ArgumentTypeError(
            "artifactId must contain only letters, digits, dots, underscores, and "
            "hyphens, and must start with a letter or digit"
        )
    return value


def validate_group_id(value: str) -> str:
    """Validate a group ID that can also be used as a Java package."""
    if not GROUP_ID_PATTERN.fullmatch(value):
        raise argparse.ArgumentTypeError(
            "groupId must be dot-separated Java identifiers (for example com.example)"
        )
    return value


def parse_git_choice(value: str) -> bool:
    """Parse a yes/no command-line value."""
    normalized = value.strip().lower()
    if normalized in {"y", "yes", "true"}:
        return True
    if normalized in {"n", "no", "false"}:
        return False
    raise argparse.ArgumentTypeError("Git choice must be y/yes/true or n/no/false")


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse arguments, prompting for omitted project details."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact_id", nargs="?", help="Maven artifactId/project name")
    parser.add_argument("group_id", nargs="?", help="Maven groupId")
    parser.add_argument("initialize_git", nargs="?", help="Initialize Git: y or n")
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace an existing project directory with the same name",
    )
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=default_workspace_root(),
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args(argv)

    if args.artifact_id is None:
        args.artifact_id = input("Enter project name (artifactId): ").strip()
    try:
        args.artifact_id = validate_artifact_id(args.artifact_id)
    except argparse.ArgumentTypeError as error:
        parser.error(str(error))

    default_group = f"com.{args.artifact_id.replace('-', '.')}"
    if args.group_id is None:
        args.group_id = input(f"Enter Group ID [{default_group}]: ").strip()
        args.group_id = args.group_id or default_group
    try:
        args.group_id = validate_group_id(args.group_id)
    except argparse.ArgumentTypeError as error:
        parser.error(str(error))

    if args.initialize_git is None:
        git_input = input("Initialize Git repository? (y/n) [y]: ").strip() or "y"
    else:
        git_input = args.initialize_git
    try:
        args.initialize_git = parse_git_choice(git_input)
    except argparse.ArgumentTypeError as error:
        parser.error(str(error))

    args.workspace_root = args.workspace_root.expanduser().resolve()
    return args


def qualified(name: str) -> str:
    """Return a Maven-namespace-qualified XML element name."""
    return f"{{{MAVEN_NAMESPACE}}}{name}"


def get_or_insert_section(
    root: ET.Element, name: str, before: tuple[str, ...]
) -> ET.Element:
    """Find a POM section or insert it before later schema sections."""
    existing = root.find(qualified(name))
    if existing is not None:
        return existing

    section = ET.Element(qualified(name))
    before_tags = {qualified(item) for item in before}
    for index, child in enumerate(root):
        if child.tag in before_tags:
            root.insert(index, section)
            break
    else:
        root.append(section)
    return section


def set_child_text(parent: ET.Element, name: str, value: str) -> None:
    """Set a child element, creating it when necessary."""
    child = parent.find(qualified(name))
    if child is None:
        child = ET.SubElement(parent, qualified(name))
    child.text = value


def upsert_dependency(
    dependencies: ET.Element,
    group_id: str,
    artifact_id: str,
    version: str,
    scope: str | None,
) -> None:
    """Add or update one dependency without discarding unrelated dependencies."""
    dependency = None
    for candidate in dependencies.findall(qualified("dependency")):
        if (
            candidate.findtext(qualified("groupId")) == group_id
            and candidate.findtext(qualified("artifactId")) == artifact_id
        ):
            dependency = candidate
            break

    if dependency is None:
        dependency = ET.SubElement(dependencies, qualified("dependency"))
    set_child_text(dependency, "groupId", group_id)
    set_child_text(dependency, "artifactId", artifact_id)
    set_child_text(dependency, "version", version)

    scope_element = dependency.find(qualified("scope"))
    if scope is None and scope_element is not None:
        dependency.remove(scope_element)
    elif scope is not None:
        set_child_text(dependency, "scope", scope)


def adjust_pom_to_java21(pom_path: Path) -> None:
    """Configure Java 21 and required dependencies using structured XML editing."""
    print("\nConfiguring pom.xml for Java 21 and required dependencies...")
    try:
        parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
        tree = ET.parse(pom_path, parser=parser)
    except ET.ParseError as error:
        raise ProjectCreationError(f"Invalid generated pom.xml: {error}") from error

    root = tree.getroot()
    if root.tag != qualified("project"):
        raise ProjectCreationError(
            "Generated pom.xml does not use the Maven POM namespace"
        )

    properties = get_or_insert_section(
        root,
        "properties",
        ("dependencyManagement", "dependencies", "build", "profiles"),
    )
    set_child_text(properties, "maven.compiler.source", JAVA_VERSION)
    set_child_text(properties, "maven.compiler.target", JAVA_VERSION)
    set_child_text(properties, "project.build.sourceEncoding", "UTF-8")

    dependencies = get_or_insert_section(root, "dependencies", ("build", "profiles"))
    for dependency in DEPENDENCIES:
        upsert_dependency(dependencies, *dependency)


    ET.register_namespace("", MAVEN_NAMESPACE)
    ET.indent(tree, space="  ")
    tree.write(pom_path, encoding="utf-8", xml_declaration=True)
    print("Successfully updated pom.xml.")


def setup_project_files(project_path: Path) -> None:
    """Create resources, logging, editor settings, and ignore rules."""
    print("\nCreating resource directories and project configuration...")
    main_resources = project_path / "src" / "main" / "resources"
    test_resources = project_path / "src" / "test" / "resources"
    main_resources.mkdir(parents=True, exist_ok=True)
    test_resources.mkdir(parents=True, exist_ok=True)
    (main_resources / "log4j2.xml").write_text(LOG4J_CONFIGURATION, encoding="utf-8")

    vscode_directory = project_path / ".vscode"
    vscode_directory.mkdir(exist_ok=True)
    settings = {"java.configuration.updateBuildConfiguration": "automatic"}
    (vscode_directory / "settings.json").write_text(
        json.dumps(settings, indent=2) + "\n", encoding="utf-8"
    )
    (project_path / ".gitignore").write_text(GITIGNORE, encoding="utf-8")


def require_executable(name: str) -> str:
    """Resolve a required command or provide a useful error."""
    executable = shutil.which(name)
    if executable is None:
        raise ProjectCreationError(f"Required command not found on PATH: {name}")
    return executable


def run_checked(
    command: list[str], cwd: Path, **kwargs: object
) -> subprocess.CompletedProcess:
    """Run a command and convert failures into user-facing errors."""
    try:
        return subprocess.run(command, cwd=cwd, check=True, **kwargs)
    except subprocess.CalledProcessError as error:
        raise ProjectCreationError(
            f"Command failed with exit code {error.returncode}: {' '.join(command)}"
        ) from error
    except OSError as error:
        raise ProjectCreationError(f"Could not run {command[0]}: {error}") from error


def initialize_git_repository(project_path: Path) -> None:
    """Initialize Git, stage the project, and attempt the initial commit."""
    print("\nInitializing Git repository...")
    git = require_executable("git")
    run_checked([git, "init"], project_path, stdout=subprocess.DEVNULL)
    run_checked([git, "add", "."], project_path)

    commit = subprocess.run(
        [git, "commit", "-m", "Initial commit"],
        cwd=project_path,
        capture_output=True,
        text=True,
    )
    if commit.returncode == 0:
        print("Successfully made the initial commit.")
    else:
        reason = commit.stderr.strip() or commit.stdout.strip() or "unknown Git error"
        print(f"Warning: Git was initialized, but the initial commit failed: {reason}")


def safe_rmtree(path: Path) -> None:
    """Delete a known directory tree, handling read-only files on Windows."""
    if not path.exists():
        return

    def remove_readonly(function, item, _error_info):
        os.chmod(item, stat.S_IWRITE)
        function(item)

    shutil.rmtree(path, onerror=remove_readonly)


def create_project(args: argparse.Namespace) -> Path:
    """Generate, configure, move, optionally version, and verify one project."""
    workspace_root = args.workspace_root
    if not workspace_root.is_dir():
        raise ProjectCreationError(f"Workspace root does not exist: {workspace_root}")

    destination = (workspace_root / args.artifact_id).resolve()
    if destination.parent != workspace_root:
        raise ProjectCreationError(
            "Project destination must be inside the workspace root"
        )
    if destination.exists() and not args.force:
        raise ProjectCreationError(
            f"Destination already exists: {destination}. Use --force to replace it."
        )

    maven = require_executable("mvn")
    print(
        f"\nCreating '{args.artifact_id}' with Group ID '{args.group_id}' "
        "in an isolated temporary directory..."
    )
    temp_directory = Path(tempfile.mkdtemp(prefix="java_gen_"))
    try:
        command = [
            maven,
            "archetype:generate",
            "-B",
            "-DarchetypeGroupId=org.apache.maven.archetypes",
            "-DarchetypeArtifactId=maven-archetype-quickstart",
            f"-DarchetypeVersion={ARCHETYPE_VERSION}",
            f"-DgroupId={args.group_id}",
            f"-DartifactId={args.artifact_id}",
            "-Darchetype.interactive=false",
        ]
        run_checked(command, temp_directory)

        generated_project = temp_directory / args.artifact_id
        pom_path = generated_project / "pom.xml"
        if not pom_path.is_file():
            raise ProjectCreationError(
                f"Maven did not generate the expected file: {pom_path}"
            )

        adjust_pom_to_java21(pom_path)
        setup_project_files(generated_project)

        if destination.exists():
            safe_rmtree(destination)
        shutil.move(str(generated_project), str(destination))
    finally:
        safe_rmtree(temp_directory)

    if args.initialize_git:
        initialize_git_repository(destination)

    print("\nVerifying the generated project with mvn clean test...")
    run_checked([maven, "clean", "test"], destination)
    print("\n=== Success! Project generated and verified with Java 21. ===")
    print(f"Project location: {destination}")
    return destination


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point."""
    print("=== Java 21 Maven Project Creator ===")
    args = parse_arguments(argv)
    try:
        create_project(args)
    except (ProjectCreationError, OSError) as error:
        print(f"\nError: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
