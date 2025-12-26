# Gmail Setup Guide for Job Scraper

## Step 1: Enable 2-Factor Authentication

1. Go to your Google Account: https://myaccount.google.com/
2. Click on **Security** in the left sidebar
3. Under "Signing in to Google", find **2-Step Verification**
4. Follow the prompts to enable 2-Step Verification (if not already enabled)

## Step 2: Generate an App Password

**Important:** You cannot use your regular Gmail password. You need to create an App Password.

1. Go to: https://myaccount.google.com/apppasswords
   - Or navigate: Google Account → Security → 2-Step Verification → App passwords
2. Select **Mail** as the app
3. Select **Other (Custom name)** as the device
4. Enter a name like "Job Scraper" or "Python Script"
5. Click **Generate**
6. Copy the 16-character password (it will look like: `abcd efgh ijkl mnop`)

## Step 3: Create .env File

Create a file named `.env` in your project root with the following content:

```
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=your_email@gmail.com
EMAIL_PASSWORD=your_16_character_app_password_here
EMAIL_TO=your_personal_email@gmail.com
```

**Replace:**
- `your_email@gmail.com` with your Gmail address
- `your_16_character_app_password_here` with the App Password from Step 2 (remove spaces)
- `your_personal_email@gmail.com` with your personal email where you want to receive job notifications

## Example .env File

**Note:** This is just an example - use your own credentials!

```
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=your_email@gmail.com
EMAIL_PASSWORD=xxxx xxxx xxxx xxxx
EMAIL_TO=recipient@gmail.com
```

**Important:** Replace all placeholder values with your actual credentials!

## Step 4: Test Your Email Setup

Run the test script to verify everything works:

```bash
python test_email.py
```

## Troubleshooting

**"Invalid credentials" error:**
- Make sure you're using an App Password, not your regular Gmail password
- Remove any spaces from the App Password
- Make sure 2-Step Verification is enabled

**"Less secure app access" error:**
- This shouldn't happen with App Passwords, but if it does, make sure you're using an App Password, not your regular password

**"Connection refused" error:**
- Check your firewall settings
- Make sure port 587 is not blocked
- Try using port 465 with SSL instead (change EMAIL_PORT to 465)

## Security Note

- Never commit your `.env` file to git (it's already in `.gitignore`)
- Keep your App Password secure
- You can revoke App Passwords anytime from your Google Account settings


