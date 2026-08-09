import argparse
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock
import xml.etree.ElementTree as ET

import create_java21_project as creator


SAMPLE_POM = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.old</groupId>
  <artifactId>sample</artifactId>
  <version>1.0-SNAPSHOT</version>
  <properties>
    <maven.compiler.source>7</maven.compiler.source>
    <maven.compiler.target>7</maven.compiler.target>
  </properties>
  <dependencies>
    <dependency>
      <groupId>junit</groupId>
      <artifactId>junit</artifactId>
      <version>4.11</version>
      <scope>test</scope>
    </dependency>
    <dependency>
      <groupId>com.example</groupId>
      <artifactId>keep-me</artifactId>
      <version>1.0</version>
    </dependency>
  </dependencies>
</project>
"""


class ValidationTests(unittest.TestCase):
    def test_accepts_safe_identifiers(self):
        self.assertEqual(creator.validate_artifact_id("game-math_21"), "game-math_21")
        self.assertEqual(
            creator.validate_group_id("com.example.game"), "com.example.game"
        )

    def test_rejects_path_like_artifact_ids(self):
        for value in ("../project", "nested/project", r"C:\project", ""):
            with self.subTest(value=value):
                with self.assertRaises(argparse.ArgumentTypeError):
                    creator.validate_artifact_id(value)

    def test_rejects_invalid_group_ids(self):
        for value in ("com.example-game", "9example.game", "com..game"):
            with self.subTest(value=value):
                with self.assertRaises(argparse.ArgumentTypeError):
                    creator.validate_group_id(value)

    def test_git_choice_is_strict(self):
        self.assertTrue(creator.parse_git_choice("YES"))
        self.assertFalse(creator.parse_git_choice("n"))
        with self.assertRaises(argparse.ArgumentTypeError):
            creator.parse_git_choice("maybe")


class PomTests(unittest.TestCase):
    def test_structured_pom_update_preserves_unrelated_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            pom_path = Path(directory) / "pom.xml"
            pom_path.write_text(SAMPLE_POM, encoding="utf-8")

            creator.adjust_pom_to_java21(pom_path)

            root = ET.parse(pom_path).getroot()
            q = creator.qualified
            properties = root.find(q("properties"))
            self.assertEqual(properties.findtext(q("maven.compiler.source")), "21")
            self.assertEqual(properties.findtext(q("maven.compiler.target")), "21")

            dependencies = root.find(q("dependencies"))
            versions = {
                (
                    dependency.findtext(q("groupId")),
                    dependency.findtext(q("artifactId")),
                ): dependency.findtext(q("version"))
                for dependency in dependencies.findall(q("dependency"))
            }
            self.assertEqual(versions[("junit", "junit")], creator.JUNIT_VERSION)
            self.assertEqual(versions[("com.example", "keep-me")], "1.0")
            self.assertEqual(
                versions[("org.apache.logging.log4j", "log4j-core")],
                creator.LOG4J_VERSION,
            )
            self.assertEqual(
                versions[("org.apache.poi", "poi-ooxml")], creator.POI_VERSION
            )



class ProjectCreationTests(unittest.TestCase):
    def make_args(self, workspace: Path, **overrides):
        values = {
            "artifact_id": "audit-project",
            "group_id": "com.audit",
            "initialize_git": False,
            "force": False,
            "workspace_root": workspace,
        }
        values.update(overrides)
        return argparse.Namespace(**values)

    def test_existing_destination_is_never_removed_without_force(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            destination = workspace / "audit-project"
            destination.mkdir()
            marker = destination / "important.txt"
            marker.write_text("keep", encoding="utf-8")

            with self.assertRaisesRegex(
                creator.ProjectCreationError, "Use --force"
            ):
                creator.create_project(self.make_args(workspace))

            self.assertEqual(marker.read_text(encoding="utf-8"), "keep")

    def test_happy_path_uses_checked_commands_and_creates_expected_files(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            commands = []

            def fake_run(command, cwd, **_kwargs):
                commands.append(command)
                if "archetype:generate" in command:
                    project = Path(cwd) / "audit-project"
                    project.mkdir()
                    (project / "pom.xml").write_text(SAMPLE_POM, encoding="utf-8")
                return subprocess.CompletedProcess(command, 0)

            with mock.patch.object(creator, "require_executable", return_value="mvn"):
                with mock.patch.object(creator, "run_checked", side_effect=fake_run):
                    destination = creator.create_project(self.make_args(workspace))

            self.assertTrue((destination / "pom.xml").is_file())
            self.assertTrue(
                (destination / "src/main/resources/log4j2.xml").is_file()
            )
            self.assertTrue((destination / ".vscode/settings.json").is_file())
            self.assertTrue((destination / ".gitignore").is_file())
            self.assertEqual(commands[-1], ["mvn", "clean", "test"])

    def test_command_failure_becomes_project_creation_error(self):
        failure = subprocess.CalledProcessError(7, ["mvn", "clean", "test"])
        with mock.patch.object(creator.subprocess, "run", side_effect=failure):
            with self.assertRaisesRegex(
                creator.ProjectCreationError, "exit code 7"
            ):
                creator.run_checked(["mvn", "clean", "test"], Path.cwd())


if __name__ == "__main__":
    unittest.main()
