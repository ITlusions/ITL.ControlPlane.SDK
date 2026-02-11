#!/bin/bash
# Quick version management commands for ITL ControlPlane SDK

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="${REPO_ROOT}/scripts/version.py"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ============================================================================
# VERSION CHECKS
# ============================================================================

if [[ "$1" == "current" ]]; then
  echo -e "${BLUE}📌 Current Version${NC}"
  python "$SCRIPT" --get-version
  exit 0
fi

if [[ "$1" == "context" ]]; then
  echo -e "${BLUE}📊 Version Context${NC}"
  python "$SCRIPT" --detect-context
  exit 0
fi

# ============================================================================
# VERSION BUMPING
# ============================================================================

if [[ "$1" == "bump" ]]; then
  if [[ -z "$2" ]]; then
    echo "Usage: $0 bump <major|minor|patch>"
    exit 1
  fi
  
  echo -e "${YELLOW}⬆️ Bumping $2 version...${NC}"
  python "$SCRIPT" --bump "$2"
  
  NEW_VERSION=$(python "$SCRIPT" --get-version)
  echo -e "${GREEN}✅ Version bumped to: $NEW_VERSION${NC}"
  echo -e "${YELLOW}Next steps:${NC}"
  echo "  1. git add pyproject.toml"
  echo "  2. git commit -m 'chore(release): bump version to $NEW_VERSION'"
  echo "  3. $0 tag $NEW_VERSION"
  exit 0
fi

# ============================================================================
# CREATE RELEASE TAG
# ============================================================================

if [[ "$1" == "tag" ]]; then
  if [[ -z "$2" ]]; then
    echo "Usage: $0 tag <version> [message]"
    exit 1
  fi
  
  VERSION="$2"
  MESSAGE="${3:-Release version $VERSION}"
  
  echo -e "${YELLOW}🏷️ Creating release tag...${NC}"
  python "$SCRIPT" --create-tag "$VERSION" --message "$MESSAGE"
  
  echo -e "${GREEN}✅ Tag created: v$VERSION${NC}"
  echo -e "${YELLOW}Next steps:${NC}"
  echo "  git push origin v$VERSION"
  echo ""
  echo "  Or push all tags:"
  echo "  git push origin --tags"
  exit 0
fi

# ============================================================================
# FULL RELEASE WORKFLOW
# ============================================================================

if [[ "$1" == "release" ]]; then
  if [[ -z "$2" ]]; then
    echo "Usage: $0 release <major|minor|patch>"
    exit 1
  fi
  
  BUMP_TYPE="$2"
  
  echo -e "${BLUE}🚀 Starting release workflow for $BUMP_TYPE...${NC}"
  echo ""
  
  # Ensure clean git state
  if [[ -n $(git status -s) ]]; then
    echo -e "${YELLOW}⚠️ Uncommitted changes detected${NC}"
    git status -s
    read -p "Continue? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
      echo "Cancelled"
      exit 1
    fi
  fi
  
  # Bump version
  echo -e "${BLUE}1️⃣ Bumping version...${NC}"
  NEW_VERSION=$(python "$SCRIPT" --bump "$BUMP_TYPE")
  echo -e "${GREEN}✅ Bumped to: $NEW_VERSION${NC}"
  echo ""
  
  # Commit version bump
  echo -e "${BLUE}2️⃣ Committing version bump...${NC}"
  git add pyproject.toml
  git commit -m "chore(release): bump version to $NEW_VERSION"
  echo -e "${GREEN}✅ Committed${NC}"
  echo ""
  
  # Create tag
  echo -e "${BLUE}3️⃣ Creating release tag...${NC}"
  python "$SCRIPT" --create-tag "$NEW_VERSION" -m "Release version $NEW_VERSION"
  echo -e "${GREEN}✅ Tag created: v$NEW_VERSION${NC}"
  echo ""
  
  # Push
  echo -e "${BLUE}4️⃣ Pushing to GitHub...${NC}"
  git push origin "$(git rev-parse --abbrev-ref HEAD)"
  git push origin "v$NEW_VERSION"
  echo -e "${GREEN}✅ Pushed${NC}"
  echo ""
  
  echo -e "${GREEN}🎉 Release workflow complete!${NC}"
  echo -e "${YELLOW}GitHub Actions will now:${NC}"
  echo "  ✅ Run tests"
  echo "  ✅ Build package"
  echo "  ✅ Publish to PyPI"
  echo "  ✅ Create GitHub Release"
  exit 0
fi

# ============================================================================
# HELP
# ============================================================================

cat << 'EOF'
ITL ControlPlane SDK - Version Management Tool

Usage:
  ./version.sh current                    # Show current version
  ./version.sh context                    # Show version context (branch, tags, etc.)
  ./version.sh bump <major|minor|patch>   # Bump version in pyproject.toml
  ./version.sh tag <version> [message]    # Create git release tag
  ./version.sh release <major|minor|patch> # Full automated release workflow

Examples:
  # Check current version
  ./version.sh current

  # Show full context
  ./version.sh context

  # Bump minor version (1.0.0 -> 1.1.0) 
  ./version.sh bump minor

  # Create a release tag
  ./version.sh tag 1.1.0 "Release v1.1.0"

  # Full release: bump version, commit, tag, push
  ./version.sh release minor

Note:
  - All version operations require a clean git state
  - Tags are created in format: v1.0.0
  - Releases require versions to match semantic versioning: MAJOR.MINOR.PATCH
EOF

exit 1
