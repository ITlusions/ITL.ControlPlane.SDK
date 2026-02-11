# Quick version management for ITL ControlPlane SDK (PowerShell)
# Usage: .\version.ps1 -Command <command> -Type <major|minor|patch>

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet('current', 'context', 'bump', 'tag', 'release')]
    [string]$Command,
    
    [Parameter(Mandatory=$false)]
    [ValidateSet('major', 'minor', 'patch')]
    [string]$Type,
    
    [Parameter(Mandatory=$false)]
    [string]$Version,
    
    [Parameter(Mandatory=$false)]
    [string]$Message
)

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Script = Join-Path $RepoRoot "scripts\version.py"

# Colors
$Green = @{ ForegroundColor = 'Green' }
$Blue = @{ ForegroundColor = 'Cyan' }
$Yellow = @{ ForegroundColor = 'Yellow' }

function Show-Help {
    @"
ITL ControlPlane SDK - Version Management Tool (PowerShell)

Usage:
  .\version.ps1 -Command current
  .\version.ps1 -Command context
  .\version.ps1 -Command bump -Type <major|minor|patch>
  .\version.ps1 -Command tag -Version <version> [-Message "message"]
  .\version.ps1 -Command release -Type <major|minor|patch>

Examples:
  # Check current version
  .\version.ps1 -Command current

  # Show full context
  .\version.ps1 -Command context

  # Bump minor version (1.0.0 -> 1.1.0)
  .\version.ps1 -Command bump -Type minor

  # Create a release tag
  .\version.ps1 -Command tag -Version 1.1.0 -Message "Release v1.1.0"

  # Full release: bump version, commit, tag, push
  .\version.ps1 -Command release -Type minor

Note:
  - All version operations require a clean git state
  - Tags are created in format: v1.0.0
  - Releases require versions to match semantic versioning: MAJOR.MINOR.PATCH
"@
}

# ============================================================================
# VERSION CHECKS
# ============================================================================

if ($Command -eq 'current') {
    Write-Host "📌 Current Version" @Blue
    python $Script --get-version
    exit 0
}

if ($Command -eq 'context') {
    Write-Host "📊 Version Context" @Blue
    python $Script --detect-context
    exit 0
}

# ============================================================================
# VERSION BUMPING
# ============================================================================

if ($Command -eq 'bump') {
    if (-not $Type) {
        Write-Host "Error: -Type parameter required (major|minor|patch)" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "⬆️ Bumping $Type version..." @Yellow
    python $Script --bump $Type
    
    $NewVersion = python $Script --get-version
    Write-Host "✅ Version bumped to: $NewVersion" @Green
    Write-Host "Next steps:" @Yellow
    Write-Host "  1. git add pyproject.toml"
    Write-Host "  2. git commit -m 'chore(release): bump version to $NewVersion'"
    Write-Host "  3. .\version.ps1 -Command tag -Version $NewVersion"
    exit 0
}

# ============================================================================
# CREATE RELEASE TAG
# ============================================================================

if ($Command -eq 'tag') {
    if (-not $Version) {
        Write-Host "Error: -Version parameter required" -ForegroundColor Red
        exit 1
    }
    
    $TagMessage = $Message -or "Release version $Version"
    
    Write-Host "🏷️ Creating release tag..." @Yellow
    python $Script --create-tag $Version --message $TagMessage
    
    Write-Host "✅ Tag created: v$Version" @Green
    Write-Host "Next steps:" @Yellow
    Write-Host "  git push origin v$Version"
    Write-Host ""
    Write-Host "  Or push all tags:"
    Write-Host "  git push origin --tags"
    exit 0
}

# ============================================================================
# FULL RELEASE WORKFLOW
# ============================================================================

if ($Command -eq 'release') {
    if (-not $Type) {
        Write-Host "Error: -Type parameter required (major|minor|patch)" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "🚀 Starting release workflow for $Type..." @Blue
    Write-Host ""
    
    # Check git status
    $GitStatus = git status -s
    if ($GitStatus) {
        Write-Host "⚠️ Uncommitted changes detected:" @Yellow
        git status -s
        $Response = Read-Host "Continue? (y/n)"
        if ($Response -ne 'y' -and $Response -ne 'Y') {
            Write-Host "Cancelled"
            exit 1
        }
    }
    
    # Bump version
    Write-Host "1️⃣ Bumping version..." @Blue
    python $Script --bump $Type
    $NewVersion = python $Script --get-version
    Write-Host "✅ Bumped to: $NewVersion" @Green
    Write-Host ""
    
    # Commit version bump
    Write-Host "2️⃣ Committing version bump..." @Blue
    git add pyproject.toml
    git commit -m "chore(release): bump version to $NewVersion"
    Write-Host "✅ Committed" @Green
    Write-Host ""
    
    # Create tag
    Write-Host "3️⃣ Creating release tag..." @Blue
    python $Script --create-tag $NewVersion -m "Release version $NewVersion"
    Write-Host "✅ Tag created: v$NewVersion" @Green
    Write-Host ""
    
    # Push
    Write-Host "4️⃣ Pushing to GitHub..." @Blue
    $CurrentBranch = git rev-parse --abbrev-ref HEAD
    git push origin $CurrentBranch
    git push origin "v$NewVersion"
    Write-Host "✅ Pushed" @Green
    Write-Host ""
    
    Write-Host "🎉 Release workflow complete!" @Green
    Write-Host "GitHub Actions will now:" @Yellow
    Write-Host "  ✅ Run tests"
    Write-Host "  ✅ Build package"
    Write-Host "  ✅ Publish to PyPI"
    Write-Host "  ✅ Create GitHub Release"
    exit 0
}

# ============================================================================
# HELP
# ============================================================================

if ($Command) {
    Write-Host "Unknown command: $Command" -ForegroundColor Red
    Show-Help
    exit 1
}

Show-Help
