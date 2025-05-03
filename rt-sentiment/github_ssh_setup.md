# Setting up GitHub SSH Access

Follow these steps to set up SSH authentication for GitHub:

1. **Generate an SSH key** (skip if you already have one):
   ```bash
   ssh-keygen -t ed25519 -C "jonathan.corners@gmail.com"
   ```
   Press Enter to accept the default file location and optionally set a passphrase.

2. **Start the SSH agent**:
   ```bash
   eval "$(ssh-agent -s)"
   ```

3. **Add your SSH key to the agent**:
   ```bash
   ssh-add ~/.ssh/id_ed25519
   ```

4. **Copy your public key**:
   ```bash
   cat ~/.ssh/id_ed25519.pub
   ```
   (Copy the output)

5. **Add the key to your GitHub account**:
   - Go to GitHub → Settings → SSH and GPG keys → New SSH key
   - Paste your public key and give it a title (e.g., "WSL Development")
   - Click "Add SSH key"

6. **Change your remote URL to use SSH**:
   ```bash
   git remote set-url origin git@github.com:JCorners68/RTSentiment.git
   ```

7. **Now try pushing**:
   ```bash
   git push -u origin main
   ```