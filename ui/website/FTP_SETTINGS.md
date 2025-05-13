# FTP Deployment Settings Reference

**IMPORTANT: DO NOT CHANGE THESE VALUES**

When maintaining the deployment scripts, always keep these settings:

## FTP Server Settings
- Server: `ftp.yubacityplumbingpro.com` (NOT sentimark.ai or any other domain)
- Remote Directory: Empty string `""` (NOT `/public_html` or any other directory)

## Default Values in Scripts
Ensure these default values are used in the deployment scripts:

```bash
# In deploy_incremental.sh
FTP_SERVER="${SENTIMARK_FTP_SERVER:-ftp.yubacityplumbingpro.com}"
REMOTE_DIR="${SENTIMARK_FTP_REMOTE_DIR:-}"

# In deploy_full.sh
FTP_HOST="${SENTIMARK_FTP_SERVER:-ftp.yubacityplumbingpro.com}"
REMOTE_DIR="${SENTIMARK_FTP_REMOTE_DIR:-}"
```

## Notes
- The FTP credentials are loaded from the `.env` file if present
- For local testing, create a `.env` file based on `.env.example`
- Do not commit the `.env` file with real credentials

This file serves as a reminder to maintain these specific FTP settings for the Sentimark website deployment.