# SonarQube Setup for Kinwise Backend

## Overview
This project uses SonarQube for continuous code quality and security analysis.

**Current Metrics:**
- Test Coverage: 97.25%
- Tests: 837 passing
- Files with 100% coverage: 211

## Local Setup with Docker (Recommended)

### Prerequisites
1. Docker and Docker Compose installed
2. Python 3.13+
3. Project dependencies installed

### Quick Start (Easiest Method)

**PowerShell:**
```powershell
# 1. Start SonarQube
.\sonar-docker.ps1

# 2. Login to http://localhost:9000 (admin/admin)
# 3. Change password and create a token (My Account → Security)

# 4. Set token
$env:SONAR_TOKEN = "your-generated-token"

# 5. Run analysis
.\sonar-docker.ps1 -Analyze
```

**Linux/Mac:**
```bash
# 1. Start SonarQube
docker-compose -f docker-compose.sonarqube.yml up -d

# 2. Login to http://localhost:9000 (admin/admin)
# 3. Change password and create a token

# 4. Set token
export SONAR_TOKEN="your-generated-token"

# 5. Run analysis
./run-sonar.sh
```

### Management Commands

**PowerShell:**
```powershell
.\sonar-docker.ps1           # Start SonarQube
.\sonar-docker.ps1 -Status   # Check status
.\sonar-docker.ps1 -Logs     # View logs
.\sonar-docker.ps1 -Stop     # Stop SonarQube
.\sonar-docker.ps1 -Restart  # Restart SonarQube
.\sonar-docker.ps1 -Clean    # Remove all data
.\sonar-docker.ps1 -Analyze  # Run analysis
```

### Manual Docker Setup (Alternative)

1. **Start SonarQube:**
```bash
docker-compose -f docker-compose.sonarqube.yml up -d
```

2. **Wait for startup (1-2 minutes):**
```bash
docker-compose -f docker-compose.sonarqube.yml logs -f
```

3. **Access SonarQube:**
- URL: http://localhost:9000
- Default credentials: admin/admin (change immediately!)

4. **Create a token:**
- Login → My Account → Security → Generate Token
- Name: `kinwise-local`
- Save the token securely

5. **Set environment variable:**
```powershell
# PowerShell
$env:SONAR_TOKEN = "your-token-here"

# Linux/Mac
export SONAR_TOKEN="your-token-here"
```

6. **Run analysis:**
```bash
# Generate coverage
python -m pytest --cov --cov-report=xml

# Run SonarScanner in Docker
docker run --rm \
  --network host \
  -v "$(pwd):/usr/src" \
  -e SONAR_HOST_URL="http://localhost:9000" \
  -e SONAR_TOKEN="$SONAR_TOKEN" \
  sonarsource/sonar-scanner-cli
```

## GitHub Actions Setup

### Required Secrets
Add these secrets to your GitHub repository (Settings → Secrets → Actions):

1. **SONAR_TOKEN**: Your SonarQube authentication token
2. **SONAR_HOST_URL**: Your SonarQube server URL
   - For SonarCloud: `https://sonarcloud.io`
   - For self-hosted: Your server URL

### Workflow
The workflow (`.github/workflows/sonarqube.yml`) runs on:
- Push to `main` or `develop` branches
- Pull requests

It automatically:
1. Runs all tests with coverage
2. Uploads results to SonarQube
3. Checks quality gates
4. Comments on PRs with analysis results

## Quality Gates

### Default Configuration
- **Coverage**: Maintain >80% on new code
- **Duplications**: <3% duplicated lines
- **Maintainability**: No new code smells rated C or worse
- **Reliability**: No new bugs
- **Security**: No new vulnerabilities

### Custom Quality Gates
You can configure stricter gates in SonarQube:
- Quality Gates → Create
- Set conditions (e.g., "Overall Coverage > 95%")
- Assign to your project

## SonarCloud Alternative

For public repositories, use SonarCloud (free for open source):

1. Go to https://sonarcloud.io
2. Sign in with GitHub
3. Import your repository
4. Update `sonar-project.properties`:
```properties
sonar.organization=your-org-name
sonar.host.url=https://sonarcloud.io
```

## Interpreting Results

### Metrics
- **Bugs**: Issues that could cause runtime errors
- **Vulnerabilities**: Security issues (OWASP Top 10)
- **Code Smells**: Maintainability issues
- **Coverage**: % of code covered by tests (currently 97.25%!)
- **Duplications**: Repeated code blocks

### Ratings (A-E)
- **A**: Excellent (your target!)
- **B**: Good
- **C**: Acceptable
- **D**: Needs improvement
- **E**: Poor

### Technical Debt
Shows estimated time to fix all issues.

## Django-Specific Rules

SonarQube checks for:
- SQL injection in raw queries
- XSS vulnerabilities in templates
- Hardcoded secrets/credentials
- CSRF protection issues
- Insecure Django settings
- Missing authentication checks

## Excluding Files

Already configured exclusions:
- Migrations: `**/migrations/**`
- Cache: `**/__pycache__/**`
- Coverage reports: `**/htmlcov/**`
- Static files: `**/staticfiles/**`
- Virtual environments: `**/venv/**`, `**/.venv/**`

To exclude more files, edit `sonar.exclusions` in `sonar-project.properties`.

## Troubleshooting

### "Coverage report not found"
```bash
# Generate XML coverage report
python -m pytest --cov --cov-report=xml
```

### "Quality gate failed"
Check the SonarQube dashboard for specific issues:
- New bugs or vulnerabilities
- Coverage dropped below threshold
- Too many code smells

### "Token authentication failed"
Regenerate your token in SonarQube and update GitHub secrets.

## Integration with IDEs

### VS Code
Install "SonarLint" extension:
- Real-time analysis as you code
- Connects to SonarQube server
- Shows issues inline

### PyCharm
Install "SonarLint" plugin from marketplace.

## Next Steps

1. Set up SonarQube server (local or cloud)
2. Configure GitHub secrets
3. Push code to trigger analysis
4. Review and fix any issues
5. Set up quality gate for PRs
6. Add SonarQube badge to README

## Resources

- [SonarQube Docs](https://docs.sonarqube.org/)
- [SonarCloud](https://sonarcloud.io)
- [Python Analysis](https://docs.sonarqube.org/latest/analyzing-source-code/languages/python/)
- [Quality Gates](https://docs.sonarqube.org/latest/user-guide/quality-gates/)
