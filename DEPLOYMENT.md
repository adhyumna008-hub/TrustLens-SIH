# TrustLens Backend Deployment Guide

## Deploy to Render.com

### Prerequisites
- GitHub account
- Render.com account (free tier available)

### Steps

1. **Push to GitHub**
   ```bash
   cd trustlens-backend
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/trustlens-backend.git
   git push -u origin main
   ```

2. **Deploy on Render**
   - Go to [render.com](https://render.com)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Render will detect the `render.yaml` configuration
   - Set environment variables in Render dashboard:
     - `ANTHROPIC_API_KEY`: Your Anthropic API key (optional but recommended)
   - Click "Deploy Web Service"

3. **Get Your Backend URL**
   - After deployment, Render will provide a URL like: `https://trustlens-backend.onrender.com`
   - Use this URL in the Android app

## Environment Variables

Required for full functionality:
- `ANTHROPIC_API_KEY`: For conversation-risk analysis (optional - pipeline works without it)

## Free Tier Limitations

- Render free tier spins down after 15 minutes of inactivity
- First request after spin-down may take longer (~30 seconds)
- Consider upgrading for production use

## Alternative Hosting Platforms

- **Railway.app**: Similar to Render, good free tier
- **Fly.io**: Global deployment, Docker-based
- **PythonAnywhere**: Simple Python hosting
- **Heroku**: Reliable but paid (no free tier)