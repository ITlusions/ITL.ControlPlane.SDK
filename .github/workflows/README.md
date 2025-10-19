# GitHub Actions Workflows

This directory contains the CI/CD pipeline configuration for the ITL ControlPlane SDK.

## Workflows Overview

### 1. `build-publish.yml` - Main Build and Publish Pipeline

**Triggers:**
- Manual dispatch (workflow_dispatch) with configurable options
- Push to main, develop, and feature branches
- Pull requests to main and develop
- Version tags (v*)

**Key Features:**
- **Multi-Python Testing**: Tests across Python 3.8-3.12
- **Security Scanning**: Bandit, Safety, and pip-audit
- **Package Building**: Creates both wheel and source distributions
- **Test PyPI Publishing**: Automatic for all builds
- **Production PyPI Publishing**: Only for version tags
- **GitHub Releases**: Automatic creation with release notes
- **Artifact Management**: Stores build artifacts and security reports

**Environments:**
- `staging`: For test builds and Test PyPI
- `production`: For production PyPI and GitHub releases

### 2. `ci.yml` - Continuous Integration

**Triggers:**
- Pull requests to main/develop
- Push to main/develop (for core changes)

**Purpose:**
- Fast feedback for developers
- Multi-version Python testing
- Code quality checks (mypy, black)
- Example validation

### 3. `provider-testing.yml` - Provider Development Support

**Triggers:**
- Manual dispatch with provider selection
- Changes to provider code
- Commit messages containing `[test-containers]`

**Features:**
- Individual provider testing
- Containerized provider validation
- Docker compose stack testing
- Provider structure validation

## Required Secrets

Configure these secrets in your GitHub repository:

### For PyPI Publishing
- `PYPI_TOKEN`: Production PyPI API token
- `TEST_PYPI_TOKEN`: Test PyPI API token

### For Notifications (Optional)
- `TEAMS_WEBHOOK`: Microsoft Teams webhook URL

## Workflow Usage

### Development Workflow

1. **Feature Development**:
   ```bash
   git checkout -b feature/my-feature
   # Make changes
   git push origin feature/my-feature
   # Create PR - triggers ci.yml
   ```

2. **Provider Development**:
   - Changes to `providers/` trigger provider-testing.yml
   - Use `[test-containers]` in commit message to test Docker builds

3. **Release Process**:
   ```bash
   # Update version in pyproject.toml
   git tag v1.1.0
   git push origin v1.1.0
   # Triggers full build-publish.yml pipeline
   ```

### Manual Triggers

**Build and Publish Pipeline**:
- Go to Actions → "Build, Test and Publish ITL ControlPlane SDK"
- Click "Run workflow"
- Choose environment and options

**Provider Testing**:
- Go to Actions → "Provider Testing and Validation"
- Click "Run workflow"
- Select specific provider or "all"

## Pipeline Stages

### 1. Test Stage
- Runs on multiple Python versions
- Validates SDK functionality
- Checks code quality
- Tests examples

### 2. Security Stage
- Dependency vulnerability scanning
- Code security analysis
- Generates security reports

### 3. Build Stage
- Creates Python packages (wheel + sdist)
- Version management
- Package validation
- Installation testing

### 4. Publish Stage
- **Test PyPI**: All successful builds
- **Production PyPI**: Only version tags
- **GitHub Releases**: Version tags with artifacts

### 5. Notification Stage
- Teams notifications (if configured)
- Workflow summary

## Package Versioning

- **Release versions**: Use tags like `v1.0.0`
- **Development versions**: Auto-generated as `1.0.0.devN+sha`
- **Version validation**: Ensures tag matches pyproject.toml

## Artifact Storage

**Build Artifacts** (30 days):
- Python packages (wheel + sdist)
- Security reports
- Release documentation

**Release Artifacts** (permanent):
- GitHub releases with packages
- PyPI published packages

## Troubleshooting

### Common Issues

1. **Version Mismatch**:
   - Ensure pyproject.toml version matches git tag
   - Remove 'v' prefix from version numbers

2. **PyPI Upload Failures**:
   - Check API tokens are valid
   - Verify version doesn't already exist
   - Review package metadata

3. **Test Failures**:
   - Check Python version compatibility
   - Validate import paths
   - Review dependency versions

### Monitoring

- Check Actions tab for workflow status
- Review artifact uploads
- Monitor PyPI package availability
- Verify GitHub release creation

## Security Considerations

- Uses OpenID Connect for trusted PyPI publishing
- Secrets are environment-scoped
- Security scanning integrated into pipeline
- Artifact retention policies enforced

## Next Steps

1. Configure PyPI API tokens
2. Set up repository environments
3. Add Teams webhook for notifications
4. Test the pipeline with a development release
5. Create first production release with version tag