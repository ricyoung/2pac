# Hugging Face Space Setup Guide

## Step 1: Create the Hugging Face Space

1. Go to https://huggingface.co/new-space

2. Fill in the details:
   - **Owner:** richardyoung (your HF username)
   - **Space name:** `2pac`
   - **License:** MIT
   - **Select the SDK:** Gradio
   - **SDK version:** gradio 4.44.0 (or latest)
   - **Space hardware:** CPU basic - free (sufficient for this app)
   - **Visibility:** Public

3. Click **"Create Space"**

## Step 2: Configure the Space

After creating the Space, you'll be on the Space page. You need to copy the README_SPACE.md content to README.md:

```bash
# In the 2pac repository
cd ~/2pac
cp README_SPACE.md README.md
git add README.md
git commit -m "Add Hugging Face Space README"
git push origin main
```

## Step 3: Push Code to Hugging Face

### Option A: Link GitHub Repository (Recommended - Auto-sync)

1. On your Hugging Face Space page, go to **Settings** (gear icon)
2. Scroll to **"Git repository"** section
3. Click **"Link to GitHub"**
4. Authorize Hugging Face to access your GitHub
5. Select repository: `ricyoung/2pac`
6. Select branch: `main`
7. Click **"Link repository"**

This will automatically sync your GitHub repo to HF Space on every push!

### Option B: Manual Git Push

```bash
cd ~/2pac

# Add HF Space as a remote (get your token from https://huggingface.co/settings/tokens)
git remote add space https://richardyoung:[YOUR_HF_TOKEN]@huggingface.co/spaces/richardyoung/2pac

# Push to HF Space
git push space main
```

## Step 4: Set Up GitHub Secret for Auto-Sync

If you used Option A (GitHub link), you still need to add the secret for the GitHub Action:

1. Go to https://huggingface.co/settings/tokens
2. Click **"New token"**
3. Name: `GitHub Auto-Sync`
4. Type: **Write** access
5. Click **"Generate a token"**
6. **Copy the token** (you won't see it again!)

7. Go to your GitHub repository: https://github.com/ricyoung/2pac/settings/secrets/actions
8. Click **"New repository secret"**
9. Name: `HF_TOKEN`
10. Value: *paste your Hugging Face token*
11. Click **"Add secret"**

## Step 5: Verify the Space is Running

1. Go to https://huggingface.co/spaces/richardyoung/2pac
2. Wait for the Space to build (first build takes 2-3 minutes)
3. You should see the Gradio interface with 3 tabs
4. Test each tab to ensure everything works:
   - **Hide Data:** Upload an image and hide text
   - **Detect:** Analyze an image for steganography
   - **Extract:** Try extracting from the image you just created
   - **Check Corruption:** Validate an image

## Step 6: Test Auto-Sync (Optional)

Make a small change to test the auto-sync:

```bash
cd ~/2pac
echo "# Test update" >> app.py
git add app.py
git commit -m "Test auto-sync"
git push origin main
```

Check GitHub Actions: https://github.com/ricyoung/2pac/actions

You should see the workflow running, and the HF Space will update automatically!

## Common Issues

### Space won't build
- **Check logs** in the Space's "Logs" tab
- **Common issue:** Missing dependencies in requirements.txt
- **Solution:** The requirements.txt should have all needed packages

### GitHub Action fails
- **Check:** Is `HF_TOKEN` secret set correctly?
- **Check:** Does the token have write access?
- **Solution:** Regenerate token with write access and update secret

### 404 Error on Space
- **Wait:** First build takes time
- **Check:** Is the Space name exactly `2pac`?
- **Check:** Is your username `richardyoung`?

## Expected URLs

Once set up, your Space will be available at:

- **Space URL:** https://huggingface.co/spaces/richardyoung/2pac
- **Direct App URL:** https://richardyoung-2pac.hf.space
- **Embed URL:** Use `https://richardyoung-2pac.hf.space` in iframes

## Next Steps

After the Space is running:
1. Copy the embed URL: `https://richardyoung-2pac.hf.space`
2. Continue to integrate it into demo.deepneuro.ai (next task)

---

Need help? Check:
- Hugging Face Spaces docs: https://huggingface.co/docs/hub/spaces-overview
- Gradio docs: https://gradio.app/docs/
