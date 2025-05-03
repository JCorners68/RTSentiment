# Using a GitHub Personal Access Token

Follow these steps to push to GitHub using a Personal Access Token (PAT):

1. **Create a Personal Access Token on GitHub**:
   - Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
   - Click "Generate new token" → "Generate new token (classic)"
   - Give it a name like "RTSentiment Development"
   - Select scopes: at minimum, check "repo" for full repo access
   - Click "Generate token"
   - **IMPORTANT**: Copy the token immediately as you won't be able to see it again

2. **Configure Git to store your credentials** (for convenience):
   ```bash
   git config --global credential.helper store
   ```

3. **Push to GitHub** (you'll be prompted for username and password):
   ```bash
   git push -u origin main
   ```
   - For username: enter your GitHub username "JCorners68"
   - For password: paste your Personal Access Token (not your GitHub password)

4. **On Windows WSL, another option is to use the Git Credential Manager**:
   ```bash
   git config --global credential.helper "/mnt/c/Program\ Files/Git/mingw64/bin/git-credential-manager.exe"
   ```
   This will use the Windows credential manager, which may already have your GitHub credentials.

Choose the approach that works best for you. The SSH method is more secure and convenient for long-term use.