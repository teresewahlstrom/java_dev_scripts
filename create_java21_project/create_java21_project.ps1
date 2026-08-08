param (
  [string]$ArtifactId,
  [string]$GroupId,
  [string]$InitGit
)

if (-not $GroupId) {
  $defaultGroup = "com.$($ArtifactId -replace '-', '.')"
  $GroupId = Read-Host "Enter Group ID [$defaultGroup]"
  if (-not $GroupId) {
    $GroupId = $defaultGroup
  }
}

if (-not $InitGit) {
  $gitInput = Read-Host "Initialize Git repository? (y/n) [y]"
  if ($gitInput -eq 'n' -or $gitInput -eq 'no') {
    $InitGit = "no"
  } else {
    $InitGit = "yes"
  }
} else {
  if ($InitGit -eq 'no' -or $InitGit -eq 'false' -or $InitGit -eq 'n') {
    $InitGit = "no"
  } else {
    $InitGit = "yes"
  }
}

# Resolve absolute destination path early
$workspaceRoot = Join-Path $PSScriptRoot "../.." | Resolve-Path
$destination = Join-Path $workspaceRoot $ArtifactId

Write-Host "`nCreating project '$ArtifactId' with Group ID '$GroupId'..." -ForegroundColor Cyan

Write-Host "`nGenerating project in temporary directory to prevent IDE race conditions..." -ForegroundColor Cyan
$tempDir = Join-Path $PSScriptRoot "temp_gen"
if (Test-Path $tempDir) {
  Remove-Item -Recurse -Force $tempDir
}
New-Item -ItemType Directory -Path $tempDir | Out-Null

$tempProjPath = Join-Path $tempDir $ArtifactId

try {
  # Run Maven archetype generate in temp directory
  Push-Location $tempDir
  mvn archetype:generate `
    "-B" `
    "-DarchetypeGroupId=org.apache.maven.archetypes" `
    "-DarchetypeArtifactId=maven-archetype-quickstart" `
    "-DarchetypeVersion=1.4" `
    "-DgroupId=$GroupId" `
    "-DartifactId=$ArtifactId" `
    "-Darchetype.interactive=false"
  Pop-Location
}
catch {
  Write-Error "Maven project generation failed: $_"
  if (Test-Path $tempDir) { Remove-Item -Recurse -Force $tempDir }
  exit 1
}

$pomPath = Join-Path $tempProjPath "pom.xml"
if (-not (Test-Path $pomPath)) {
  Write-Error "Could not find pom.xml at $pomPath"
  if (Test-Path $tempDir) { Remove-Item -Recurse -Force $tempDir }
  exit 1
}

Write-Host "`nAutomatically adjusting pom.xml to force Java 21 and configure employer dependencies..." -ForegroundColor Cyan
try {
  $content = Get-Content -Path $pomPath -Raw
  $content = $content -replace '<maven\.compiler\.source>.*?</maven\.compiler\.source>', '<maven.compiler.source>21</maven.compiler.source>'
  $content = $content -replace '<maven\.compiler\.target>.*?</maven\.compiler\.target>', '<maven.compiler.target>21</maven.compiler.target>'

  $dependenciesBlock = @"
  <dependencies>
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
  </dependencies>
"@

  $content = $content -replace '(?s)<dependencies>.*?</dependencies>', $dependenciesBlock
  Set-Content -Path $pomPath -Value $content -NoNewline
  Write-Host "Successfully updated pom.xml configurations." -ForegroundColor Green
}
catch {
  Write-Error "Error modifying pom.xml: $_"
  if (Test-Path $tempDir) { Remove-Item -Recurse -Force $tempDir }
  exit 1
}

Write-Host "`nSetting up project resource directories and default Log4j2 config..." -ForegroundColor Cyan
try {
  $mainResources = Join-Path $tempProjPath "src\main\resources"
  $testResources = Join-Path $tempProjPath "src\test\resources"
    
  New-Item -ItemType Directory -Path $mainResources -Force | Out-Null
  New-Item -ItemType Directory -Path $testResources -Force | Out-Null

  $log4jPath = Join-Path $mainResources "log4j2.xml"
  $log4jContent = @"
<?xml version="1.0" encoding="UTF-8"?>
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
"@
  Set-Content -Path $log4jPath -Value $log4jContent -Encoding utf8
  Write-Host "Created default log4j2.xml in src/main/resources." -ForegroundColor Green
}
catch {
  Write-Warning "Could not configure resources: $_"
}


Write-Host "`nAdding VS Code settings to automatically update project configuration..." -ForegroundColor Cyan
try {
  # Generate .vscode/settings.json in the temporary project directory
  $vscodePath = Join-Path $tempProjPath ".vscode"
  if (-not (Test-Path $vscodePath)) {
    New-Item -ItemType Directory -Path $vscodePath -Force | Out-Null
  }
  $settingsPath = Join-Path $vscodePath "settings.json"
  $settingsContent = @{
    "java.configuration.updateBuildConfiguration" = "automatic"
  } | ConvertTo-Json
  Set-Content -Path $settingsPath -Value $settingsContent -Encoding utf8

  # Generate/update .vscode/settings.json in the workspace root (two directories up)
  $workspaceRoot = Join-Path $PSScriptRoot "../.." | Resolve-Path
  $wsVscodePath = Join-Path $workspaceRoot ".vscode"
  if (-not (Test-Path $wsVscodePath)) {
    New-Item -ItemType Directory -Path $wsVscodePath -Force | Out-Null
  }
  $wsSettingsPath = Join-Path $wsVscodePath "settings.json"
  if (Test-Path $wsSettingsPath) {
    $wsSettings = Get-Content -Path $wsSettingsPath -Raw | ConvertFrom-Json
    if (-not $wsSettings) { $wsSettings = @{} }
    $wsSettings | Add-Member -NotePropertyName "java.configuration.updateBuildConfiguration" -NotePropertyValue "automatic" -Force
    $wsSettings | ConvertTo-Json | Set-Content -Path $wsSettingsPath -Encoding utf8
  }
  else {
    Set-Content -Path $wsSettingsPath -Value $settingsContent -Encoding utf8
  }
  Write-Host "Successfully configured VS Code settings." -ForegroundColor Green
}
catch {
  Write-Warning "Could not write VS Code settings: $_"
}

if ($InitGit -eq 'yes') {
  Write-Host "`nCreating Git configuration..." -ForegroundColor Cyan
  try {
    # Create .gitignore in the temp directory
    $gitignorePath = Join-Path $tempProjPath ".gitignore"
    
    # NOTE: The closing tag "@ must remain at the very start of the line (no indentation).
    $gitignoreContent = @"
# Maven build output
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
"@
    Set-Content -Path $gitignorePath -Value $gitignoreContent -Encoding utf8
    Write-Host "Created .gitignore." -ForegroundColor Green
  }
  catch {
    Write-Warning "Could not create .gitignore file: $_"
  }
}

Write-Host "`nMoving finalized project to workspace root..." -ForegroundColor Cyan
try {
  if (Test-Path $destination) {
    Remove-Item -Recurse -Force $destination
  }
  Move-Item -Path $tempProjPath -Destination $destination
  Write-Host "Project moved successfully to $destination" -ForegroundColor Green

  # Initialize Git in the destination folder
  if ($InitGit -eq 'yes') {
    Write-Host "`nInitializing Git repository..." -ForegroundColor Cyan
    try {
      git init $destination | Out-Null
          
      Push-Location $destination
      git add .
      git commit -m "Initial commit" 2>&1 | Out-Null
      Pop-Location
          
      if ($LASTEXITCODE -eq 0) {
        Write-Host "Successfully initialized Git and made the initial commit." -ForegroundColor Green
      }
      else {
        Write-Host "Successfully initialized Git (initial commit skipped due to missing user.name/email in git config)." -ForegroundColor Yellow
      }
    }
    catch {
      Write-Warning "Could not initialize Git repository: $_"
    }
  }
}
catch {
  Write-Error "Failed to move project: $_"
}
finally {
  # Clean up temp directory
  if (Test-Path $tempDir) {
    Remove-Item -Recurse -Force $tempDir
  }
}


Write-Host "`nVerifying the build..." -ForegroundColor Cyan
try {
  Push-Location $destination
  mvn clean test
  Pop-Location
  Write-Host "`n=== Success! Project is generated and verified with Java 21! ===" -ForegroundColor Green
  Write-Host "Project location: $destination" -ForegroundColor Green
}
catch {
  Write-Warning "Build verification failed. Please check the project manually."
}

