# GitHub Setup Guide

This guide will help you set up your project for GitHub.

## Files That Are Hidden (in .gitignore)

The following files are **NOT** committed to GitHub for security and cleanliness:

### Sensitive Files (Never Commit!)
- `jobs.db` - Your database with job listings
- `.env` - Environment variables (Gmail credentials, etc.)
- `*.db`, `*.sqlite`, `*.sqlite3` - Any database files

### Generated/Temporary Files
- `__pycache__/` - Python bytecode cache
- `*.pyc`, `*.pyo` - Compiled Python files
- `*.html` - Temporary HTML files from testing
- `*.log` - Log files
- `chromedriver*`, `geckodriver*` - Browser drivers

### IDE/OS Files
- `.vscode/`, `.idea/` - IDE settings
- `.DS_Store`, `Thumbs.db` - OS files

## Step-by-Step Setup

### 1. Configure Git (if not already done)
```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

### 2. Add All Files to Git
```bash
git add .
```

This will add all files EXCEPT those in `.gitignore`.

### 3. Make Your First Commit
```bash
git commit -m "Initial commit: Job scraper with multiple job boards"
```

### 4. Create a GitHub Repository

1. Go to [GitHub.com](https://github.com) and sign in
2. Click the "+" icon in the top right → "New repository"
3. Name it (e.g., `job-scraper` or `careers-scraper`)
4. **DO NOT** initialize with README, .gitignore, or license (we already have these)
5. Click "Create repository"

### 5. Connect Local Repository to GitHub

After creating the repository, GitHub will show you commands. Use these:

```bash
# Add the remote repository (replace YOUR_USERNAME and REPO_NAME)
git remote add origin https://github.com/YOUR_USERNAME/REPO_NAME.git

# Rename branch to main (if needed)
git branch -M main

# Push your code
git push -u origin main
```

### 6. Verify Setup

Go to your GitHub repository page and verify all files are there (except the ignored ones).

## Important Notes

### Before Pushing to GitHub:

1. **Check for sensitive data:**
   - Make sure `.env` is in `.gitignore` ✓
   - Make sure `jobs.db` is in `.gitignore` ✓
   - Never commit passwords, API keys, or tokens

2. **Review what will be committed:**
   ```bash
   git status
   ```
   This shows what files will be added.

3. **If you accidentally added sensitive files:**
   ```bash
   # Remove from staging (but keep the file locally)
   git rm --cached jobs.db
   git rm --cached .env
   
   # Then commit the removal
   git commit -m "Remove sensitive files from tracking"
   ```

## Future Commits

After the initial setup, use these commands for future updates:

```bash
# Check what changed
git status

# Add specific files or all changes
git add .
# OR
git add specific_file.py

# Commit with a descriptive message
git commit -m "Add Google scraper with pagination"

# Push to GitHub
git push
```

## Creating a .env File Template

You might want to create a `.env.example` file (this CAN be committed) to show what environment variables are needed:

```bash
# Create .env.example
echo "GMAIL_USER=your_email@gmail.com" > .env.example
echo "GMAIL_APP_PASSWORD=your_app_password" >> .env.example
```

This helps others (or future you) know what environment variables are required without exposing your actual credentials.

