# Pipeline Update: Automated Version Management

## Update Complete!

The ITL ControlPlane SDK pipeline has been updated to automatically manage package versioning based on git tags, eliminating the need for manual `pyproject.toml` version updates.

## What Changed

### **Before (Manual Process)**
```bash
# 1. Manually edit pyproject.toml
sed -i 's/version = "1.0.0"/version = "1.1.0"/' pyproject.toml

# 2. Commit version change
git add pyproject.toml
git commit -m "Bump version to 1.1.0"

# 3. Create tag
git tag v1.1.0

# 4. Push both
git push origin main
git push origin v1.1.0

# 5. Pipeline validates tag matches pyproject.toml
```

### **After (Automated Process)**
```bash
# 1. Just create and push tag - that's it!
git tag v1.1.0
git push origin v1.1.0

# 2. Pipeline automatically:
# - Extracts version "1.1.0" from tag "v1.1.0"
# - Updates pyproject.toml with version = "1.1.0"
# - Builds and publishes package
# - Creates GitHub release
```

## Key Improvements

### **Simplified Release Process**
- **Before**: 4 manual steps + validation
- **After**: 1 command (`git tag v1.1.0 && git push origin v1.1.0`)

### **Eliminated Human Error**
- **Before**: Risk of version mismatch between tag and pyproject.toml
- **After**: Version automatically extracted from tag - impossible to mismatch

### **Better Developer Experience**
- **Before**: Remember to update version file before tagging
- **After**: Just create tag when ready to release

### **Consistent Versioning**
- **Development builds**: `1.0.0.dev123+abc1234` (auto-generated)
- **Release builds**: `1.1.0` (extracted from tag `v1.1.0`)

## Technical Changes

### **Pipeline Modifications**
1. **Added TOML libraries**: `tomli` and `tomli-w` for robust TOML handling
2. **Updated version detection**: Extracts version from git tags for releases
3. **Automated pyproject.toml updates**: Pipeline modifies version automatically
4. **Enhanced validation**: Shows version changes clearly in logs

### **New Dependencies**
```yaml
pip install tomli tomli-w  # Added to pipeline for TOML handling
```

### **Version Flow Logic**
```yaml
if: github.ref == refs/tags/v*
  # Release build - extract version from tag
  VERSION = tag_name without 'v' prefix
  UPDATE pyproject.toml with VERSION
else:
  # Development build - use existing version + dev suffix
  VERSION = current_pyproject_version + .devN+sha
```

## Files Updated

### **Pipeline Changes**
-  `.github/workflows/build-publish.yml` - Main pipeline with automated versioning

### **New Documentation**
-  `AUTOMATED_VERSIONING.md` - Complete versioning guide
-  Updated `PIPELINE_SETUP.md` - Reflects new simplified process
-  Updated `README.md` - Mentions automated versioning

### **Validation Status**
-  YAML syntax validated
-  TOML libraries tested locally
-  Version extraction logic verified

## Ready to Use

### **Next Release Process**
```bash
# Current version in pyproject.toml: "1.0.0"
# To release version 1.1.0:

git tag v1.1.0
git push origin v1.1.0

# Pipeline will automatically:
# 1. Extract "1.1.0" from tag "v1.1.0"
# 2. Update pyproject.toml: version = "1.1.0"
# 3. Build package: itl-controlplane-sdk==1.1.0
# 4. Publish to PyPI
# 5. Create GitHub release v1.1.0
```

### **Development Workflow Unchanged**
```bash
# Push to main/develop still works as before
git push origin main

# Creates: itl-controlplane-sdk==1.0.0.dev123+abc1234
# Publishes to Test PyPI only
```

## Benefits Summary

1. ** Faster releases** - One command instead of multiple steps
2. ** Error prevention** - No version mismatch possible
3. ** Single source of truth** - Git tags drive everything
4. ** Clear separation** - Development vs release versions
5. ** Backward compatible** - Existing workflow still works for development

## Status: Ready for Production

The automated versioning system is:
-  **Implemented and tested**
-  **Backward compatible**
-  **Documented completely**
-  **Ready for immediate use**

**Try it now:** Create a tag to test the new automated release process! 