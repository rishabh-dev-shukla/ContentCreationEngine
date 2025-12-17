# Railway Deployment Checklist

## Pre-Deployment

- [ ] Install gunicorn: `pip install gunicorn>=21.2.0`
- [ ] Test the app works locally with `python run_web.py`
- [ ] Ensure Firebase is working (check migration was successful)
- [ ] Generate Firebase credentials for Railway

## Step 1: Prepare Firebase Credentials

Run this script to generate the environment variable format:

```bash
python scripts/prepare_firebase_for_railway.py
```

This will output a single-line JSON that you'll add to Railway as `FIREBASE_SERVICE_ACCOUNT`.

## Step 2: Initialize Git Repository

```bash
# Initialize git (if not already done)
git init

# Add files
git add .

# Commit
git commit -m "Initial commit - Ready for Railway deployment"
```

## Step 3: Create GitHub Repository

1. Go to https://github.com/new
2. Create a new repository (e.g., "ContentCreationEngine")
3. Don't initialize with README (we already have files)

```bash
# Add remote
git remote add origin https://github.com/YOUR_USERNAME/ContentCreationEngine.git

# Push to GitHub
git branch -M main
git push -u origin main
```

## Step 4: Deploy to Railway

1. Go to https://railway.app
2. Sign in/up with GitHub
3. Click **"New Project"**
4. Select **"Deploy from GitHub repo"**
5. Choose your `ContentCreationEngine` repository
6. Railway will auto-detect and build

## Step 5: Add Environment Variables

In Railway dashboard → Your service → Variables:

### Required Variables

```
FLASK_SECRET_KEY=<generate-a-random-secret-key>
FLASK_ENV=production
FIREBASE_SERVICE_ACCOUNT=<paste-single-line-json-from-step-1>
FIREBASE_API_KEY=<from-firebase-console>
FIREBASE_AUTH_DOMAIN=content-engine-8be02.firebaseapp.com
FIREBASE_PROJECT_ID=content-engine-8be02
FIREBASE_STORAGE_BUCKET=content-engine-8be02.appspot.com
FIREBASE_MESSAGING_SENDER_ID=<from-firebase-console>
FIREBASE_APP_ID=<from-firebase-console>
```

### Optional (AI Providers you use)

```
OPENAI_API_KEY=<your-key>
DEEPSEEK_API_KEY=<your-key>
GROK_API_KEY=<your-key>
DEFAULT_AI_PROVIDER=openai
```

### Optional (Other APIs)

```
REDDIT_CLIENT_ID=<your-key>
REDDIT_CLIENT_SECRET=<your-key>
NEWS_API_KEY=<your-key>
YOUTUBE_API_KEY=<your-key>
SERPER_API_KEY=<your-key>
```

## Step 6: Get Your Domain

1. Railway dashboard → Settings → Networking
2. Click **"Generate Domain"**
3. You'll get a URL like: `your-app.railway.app`

## Step 7: Configure Firebase for Production

1. Go to Firebase Console → Authentication → Settings
2. Add your Railway domain to **Authorized domains**:
   - `your-app.railway.app`

3. That's it! Firebase will automatically allow auth from this domain.

## Step 8: Test Your Deployment

1. Visit your Railway URL
2. Try logging in with Google
3. Check that personas load
4. Verify content displays correctly

## Troubleshooting

### Check Logs
Railway dashboard → Your service → Deployments → View logs

### Common Issues

**Build fails:**
- Check `requirements.txt` is complete
- Verify Python version in `runtime.txt`

**App crashes:**
- Check deployment logs
- Verify all environment variables are set
- Ensure `FIREBASE_SERVICE_ACCOUNT` is valid JSON

**Can't login:**
- Verify Railway domain in Firebase authorized domains
- Check Firebase client config variables are correct

## Cost Monitoring

- Check Railway dashboard → Usage
- Free tier: $5/month credit
- Your app should fit in free tier with light usage
- Railway auto-sleeps after inactivity to save credits

## Updates

After making code changes:

```bash
git add .
git commit -m "Description of changes"
git push
```

Railway automatically detects the push and redeploys!

---

✅ **Done!** Your app is now live and accessible to your team!
