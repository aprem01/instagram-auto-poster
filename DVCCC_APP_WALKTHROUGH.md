# DVCCC Instagram Content Manager
## Complete Feature Walkthrough Guide

---

# TABLE OF CONTENTS

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Dashboard](#dashboard)
4. [Create Content - AI Mode](#create-content---ai-mode)
5. [Create Content - Manual Mode](#create-content---manual-mode)
6. [Campaign Modes](#campaign-modes)
7. [Bilingual Support (English/Spanish)](#bilingual-support)
8. [REACH Amplify - Discovery Optimization](#reach-amplify)
9. [Awareness Calendar](#awareness-calendar)
10. [Impact Calculator](#impact-calculator)
11. [Multi-Platform Adaptation](#multi-platform-adaptation)
12. [Image Generation](#image-generation)
13. [Content Preview](#content-preview)
14. [Scheduling & Calendar](#scheduling--calendar)
15. [Post Management](#post-management)
16. [Video Content](#video-content)
17. [Settings & Configuration](#settings--configuration)
18. [Instagram Integration](#instagram-integration)
19. [Technical Architecture](#technical-architecture)
20. [Cost & Value](#cost--value)

---

# OVERVIEW

## What Is This App?

The DVCCC Instagram Content Manager is a custom-built web application designed specifically for the Domestic Violence Center of Chester County. It uses artificial intelligence to help create professional, compassionate social media content that reaches survivors in need.

## The Problem It Solves

| Challenge | Solution |
|-----------|----------|
| Staff time is precious | AI generates content in seconds |
| Writing captions is hard | AI writes in DVCCC's voice automatically |
| Finding good images is time-consuming | AI creates unique, professional images |
| Spanish content requires translation | One-click bilingual support |
| Missing awareness dates | Built-in awareness calendar |
| Inconsistent posting | Scheduling and content library |
| Multiple platforms need different formats | Multi-platform adaptation |

## Key Philosophy

**Human-in-the-Loop**: Nothing posts automatically. Every piece of content is reviewed and approved by staff before it goes anywhere.

---

# GETTING STARTED

## Accessing the App

**Live URL**: https://dvccc-instagram.onrender.com

The app runs in any web browser - no installation needed.

## Navigation

The app has these main sections:

| Section | Purpose |
|---------|---------|
| **Dashboard** | Overview, stats, recent posts |
| **Create** | Generate new content |
| **Calendar** | View scheduled posts |
| **Posts** | Manage all saved content |
| **Schedules** | Set up recurring posting |
| **Pending** | Review queue for scheduled content |
| **Video** | Create video/slideshow content |
| **Settings** | API configuration |

---

# DASHBOARD

## What You See

The dashboard provides an at-a-glance view of your content operation:

### Stats Cards
- **Total Posts**: All posts ever created
- **Scheduled**: Posts waiting to go out
- **Drafts**: Saved but not scheduled
- **Pending Review**: Awaiting approval
- **Active Schedules**: Recurring post schedules
- **This Week**: Posts created in last 7 days

### Recent Posts
Shows the 5 most recently created posts with:
- Theme/topic
- Preview of caption
- Status (draft/scheduled/posted)
- Creation date

### Upcoming Posts
Shows the next 5 scheduled posts with:
- Scheduled date/time
- Theme
- Quick preview

### Configuration Status
Shows whether API keys are properly configured:
- OpenAI API (for AI generation)
- ImgBB (for image hosting)
- Instagram API (for direct posting)

---

# CREATE CONTENT - AI MODE

## The Main Content Creation Interface

This is the heart of the app. Here's every element:

### 1. Language Toggle (Top Right)
```
[EN] / [ES]
```
- **EN**: Create content in English
- **ES**: Create content in Spanish
- Switching to ES auto-translates existing captions
- Helper text guides users: "Click ES to create Spanish content"

### 2. Mode Toggle
```
[AI Generated] [Manual]
```
- **AI Generated**: AI creates caption and image
- **Manual**: You write caption, AI creates image

### 3. Campaign Mode Selector
Five specialized modes that optimize content for different goals:
- **Awareness** (default)
- **Fundraising**
- **Events**
- **Youth**
- **Volunteer**

### 4. Awareness Calendar Panel
Shows upcoming awareness dates:
- Days until each event
- Category (DV Related, Youth, Women's Issues, etc.)
- Click to generate themed content

### 5. Impact Calculator (Fundraising Mode)
- Enter donation amount
- Shows what that donation provides
- Generate impact-focused content

### 6. Theme Input
```
[Text field for your theme/message]
```
Suggested themes available:
- "We see you, we believe you, and we are here for you"
- "Free confidential support available in Chester County"
- "Your journey to healing starts with one step"
- "You deserve to feel safe - help is available"
- "Hope lives here at DVCCC"
- "Our counselors are here to listen without judgment"
- "Every survivor has a story of strength"
- "Building healthy relationships after trauma"

### 7. Generate Button
```
[Generate Content]
```
Clicking this:
1. Sends theme to AI
2. Generates caption in DVCCC's voice
3. Creates unique image
4. Returns preview in ~15-30 seconds

---

# CREATE CONTENT - MANUAL MODE

## For When You Want to Write Your Own

In Manual Mode:

### 1. Caption Input
Large text area where you write your own caption.

### 2. Topic Field
Describe what the post is about (used for image generation).

### 3. Generate Image Only
AI creates an image based on your topic while keeping your caption.

### 4. Optimize Button
Runs your caption through REACH Amplify to:
- Suggest hashtags
- Generate alt text
- Score discoverability
- Provide optimization tips

---

# CAMPAIGN MODES

## Five Specialized Content Strategies

### 1. AWARENESS MODE (Default)
**Purpose**: General domestic violence awareness and education

**Content Focus**:
- Warning signs of abuse
- Support resources
- Survivor empowerment
- Community education

**Hashtags Include**:
- #DomesticViolenceAwareness
- #DVAwareness
- #EndDomesticViolence
- #SurvivorSupport

### 2. FUNDRAISING MODE
**Purpose**: Donor engagement and giving campaigns

**Content Focus**:
- Impact of donations
- Stories of change
- Giving campaigns
- Thank you messages

**Special Features**:
- Impact Calculator integration
- Donation amount visualizations
- Giving Tuesday support

**Hashtags Include**:
- #GiveHope
- #SupportSurvivors
- #NonprofitLove
- #GivingTuesday

### 3. EVENTS MODE
**Purpose**: Promote DVCCC events and activities

**Content Focus**:
- Event announcements
- Registration reminders
- Event recaps
- Volunteer opportunities at events

**Hashtags Include**:
- #DVCCCEvents
- #ChesterCountyEvents
- #CommunityEvent

### 4. YOUTH MODE
**Purpose**: Teen dating violence awareness and outreach

**Content Focus**:
- Teen dating violence warning signs
- Healthy relationship education
- Resources for young people
- School outreach

**Hashtags Include**:
- #TeenDatingViolence
- #TDVAM
- #HealthyRelationships
- #TeenSafety

### 5. VOLUNTEER MODE
**Purpose**: Recruit and appreciate volunteers

**Content Focus**:
- Volunteer opportunities
- Volunteer spotlights
- Training announcements
- Appreciation posts

**Hashtags Include**:
- #VolunteerWithUs
- #DVCCCVolunteers
- #MakeADifference

---

# BILINGUAL SUPPORT

## Reaching Spanish-Speaking Survivors

### How It Works

1. **Generate in English** (or Spanish)
2. **Toggle to ES** in the top right
3. **Automatic Translation** happens instantly
4. **Both versions saved** - switch freely between them

### Translation Quality

The AI translation is NOT Google Translate. It:
- Maintains emotional sensitivity
- Uses culturally appropriate phrasing
- Keeps hotline numbers unchanged
- Preserves emojis
- Adds Spanish-specific hashtags

### Spanish Hashtags Added
- #NoEstasSola (You are not alone)
- #ViolenciaDomestica
- #AyudaConfidencial
- #ChesterCounty

### Example Comparison

**English**:
```
We see you. We believe you. And we are here for you.

At DVCCC, we know that reaching out takes incredible courage.
That's why our services are always FREE and CONFIDENTIAL.
```

**Spanish**:
```
Te vemos. Te creemos. Y estamos aquí para ti.

En DVCCC, sabemos que pedir ayuda requiere un valor increíble.
Por eso nuestros servicios son siempre GRATUITOS y CONFIDENCIALES.
```

---

# REACH AMPLIFY

## AI-Powered Discovery Optimization

REACH Amplify is the app's intelligent optimization system that maximizes content visibility.

### What It Analyzes

1. **SEO Keywords**
   - Identifies searchable terms
   - Suggests additional keywords
   - Optimizes for search engines

2. **Hashtag Strategy**
   - Generates 10-15 relevant hashtags
   - Mixes popular and niche tags
   - Platform-appropriate selection

3. **Alt Text Generation**
   - Creates accessibility descriptions
   - Improves image searchability
   - Screen-reader friendly

4. **Discovery Score**
   - Grades content A-F
   - Identifies improvement areas
   - Compares to best practices

### REACH Amplify Panel (After Generation)

When content is generated, you'll see:

```
REACH Amplify - Discovery Optimization
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Discovery Score: A (92/100)

Hashtags (click to copy):
#DVCCC #ChesterCounty #DomesticViolenceAwareness
#SurvivorSupport #YouAreNotAlone #HopeAndHealing
#EndDV #DVAwareness #BreakTheSilence #SafeSpace

Alt Text:
"Warm photograph showing hands holding a purple ribbon,
symbolizing domestic violence awareness, with soft
natural lighting and supportive atmosphere"

SEO Keywords:
domestic violence help, Chester County support,
free confidential services, survivor resources

Tips:
• Post between 6-9 PM for best engagement
• Include a call-to-action
• Reply to comments within 1 hour
```

---

# AWARENESS CALENDAR

## Never Miss an Important Date

### Built-In Awareness Dates

| Month | Awareness Period |
|-------|-----------------|
| January | Human Trafficking Awareness Month |
| February | Teen Dating Violence Awareness Month (TDVAM) |
| April | Sexual Assault Awareness Month (SAAM) |
| October | Domestic Violence Awareness Month (DVAM) |

### Special Days Tracked

- **February 14**: V-Day / One Billion Rising
- **March 8**: International Women's Day
- **Purple Thursday**: First Thursday of October
- **November 25**: International Day for Elimination of Violence Against Women
- **Giving Tuesday**: Tuesday after Thanksgiving

### How It Works in the App

The Awareness Calendar panel shows:
```
Upcoming Awareness Days
━━━━━━━━━━━━━━━━━━━━━━

🟣 Domestic Violence Awareness Month
   NOW ACTIVE - October

📅 Purple Thursday
   In 3 days

🎗️ International Women's Day
   In 45 days
```

**Click any item** to auto-populate a themed caption for that awareness period.

---

# IMPACT CALCULATOR

## Show Donors What Their Gift Provides

### Available in Fundraising Mode

The Impact Calculator helps create compelling donation appeals by showing real impact.

### How It Works

1. **Enter a donation amount** (e.g., $50)
2. **See what it provides**:
   - $25 = One night of safe shelter
   - $50 = Crisis counseling session
   - $100 = Safety planning kit
   - $250 = Week of emergency housing
   - $500 = Legal advocacy support

3. **Generate impact-focused content** with one click

### Example Output

For a $100 donation:
```
Your gift of $100 provides a complete safety planning kit
for a survivor - including emergency contacts, important
documents checklist, and resources for their journey to safety.

Every dollar makes a difference. Every gift saves a life.

Donate today at dvcccpa.org/give 💜

#GiveHope #SupportSurvivors #DVCCC
```

---

# MULTI-PLATFORM ADAPTATION

## One Post, Every Platform

### Supported Platforms

| Platform | Character Limit | Hashtag Count | Tone |
|----------|----------------|---------------|------|
| Instagram | 2,200 | 10-15 | Visual, emotional |
| Facebook | 500 | 2-3 | Conversational |
| LinkedIn | 1,300 | 3-5 | Professional |
| TikTok | 150 | 4-5 | Casual, brief |

### How to Use

1. **Generate content for Instagram** (default)
2. **Click platform buttons** to see adapted versions:
   - Facebook version (shorter, fewer hashtags)
   - LinkedIn version (professional tone)
   - TikTok version (very brief, trendy)

### Adaptation Examples

**Instagram (Original)**:
```
We see you. We believe you. And we are here for you. 💜

At DVCCC, we understand that reaching out for help takes
incredible courage. That's why our doors are always open —
with FREE, CONFIDENTIAL services available to anyone in
Chester County experiencing domestic violence.

[... full caption ...]

#DVCCC #ChesterCounty #DomesticViolenceAwareness
#SurvivorSupport #YouAreNotAlone #HopeAndHealing
#EndDV #DVAwareness #BreakTheSilence #SafeSpace
```

**Facebook (Adapted)**:
```
We see you. We believe you. And we are here for you. 💜

DVCCC offers FREE, CONFIDENTIAL services to anyone in
Chester County experiencing domestic violence.

You don't have to face this alone. Visit dvcccpa.org

#DVCCC #DomesticViolenceAwareness #ChesterCounty
```

**TikTok (Adapted)**:
```
You're not alone 💜 FREE confidential help in Chester County.
Link in bio. #DVCCC #DVAwareness #YouAreNotAlone #FYP
```

---

# IMAGE GENERATION

## Professional AI-Created Images

### What Makes These Images Special

The AI generates images that look like **real photographs**, not typical AI art:

- **Documentary style** - Looks like a professional photographer took it
- **Natural lighting** - Soft, warm, authentic feel
- **Film grain** - Subtle texture for authenticity
- **Symbolic imagery** - Purple ribbons, candles, nature, hands holding
- **Never stock photos** - Every image is unique

### Image Specifications

| Attribute | Value |
|-----------|-------|
| Resolution | 1024 x 1024 pixels |
| Format | PNG (high quality) |
| Style | Natural, photographic |
| Aspect Ratio | 1:1 (Instagram optimized) |

### Image Themes Generated

Based on your content, images might include:
- Hands holding purple ribbons
- Supportive group settings
- Nature scenes (paths, sunrises) representing hope
- Candles symbolizing vigils and remembrance
- Open doors representing new beginnings
- Community settings showing support

### Regenerate Image

Don't like the image? Click **Regenerate Image** to get a new one while keeping your caption.

---

# CONTENT PREVIEW

## See Exactly How It Will Look

### Phone Preview

A realistic iPhone mockup shows:
- Your image as it will appear
- Caption text formatted correctly
- How it looks in the Instagram feed

### Preview Features

- **Real-time updates** - Edit caption, see changes instantly
- **Character count** - Know if you're within limits
- **Hashtag visibility** - See how hashtags will display

---

# SCHEDULING & CALENDAR

## Plan Your Content Strategy

### Calendar View

The calendar shows:
- **Green dots**: Scheduled posts
- **Yellow dots**: Pending review
- **Purple dots**: Special awareness dates

### Scheduling a Post

1. **Generate or create content**
2. **Click "Schedule Post"**
3. **Select date and time**
4. **Confirm**

Post moves to "Scheduled" status.

### Recurring Schedules

Set up automated content generation:

1. **Go to Schedules**
2. **Create New Schedule**
3. **Configure**:
   - Name (e.g., "Daily Awareness Post")
   - Times (e.g., 9 AM, 6 PM)
   - Days (e.g., Monday-Friday)
   - Themes to rotate through

4. **Choose Mode**:
   - **Same theme**: Use one theme repeatedly
   - **Rotate**: Cycle through multiple themes
   - **Random**: Randomly select from themes

### Review Queue

Scheduled content goes to the **Pending** queue:
- Review before it posts
- Edit captions
- Approve or reject
- Reschedule if needed

---

# POST MANAGEMENT

## Your Content Library

### Posts Page

View all created content:
- **All Posts**: Complete history
- **Drafts**: Saved but not scheduled
- **Scheduled**: Waiting to post
- **Posted**: Already published

### For Each Post

- **View**: See full details
- **Edit**: Modify caption
- **Copy**: Duplicate for new post
- **Delete**: Remove permanently
- **Reschedule**: Change posting time

### Search & Filter

Find posts by:
- Theme/topic
- Date range
- Status
- Campaign mode

---

# VIDEO CONTENT

## Create Instagram Reels Content

### Video Page

Access via the Video tab in navigation.

### Slideshow Mode

Creates multiple images for a video slideshow:

1. **Enter theme**
2. **Select "Slideshow"**
3. **Generate**
4. **Receive 3 coordinated images**

Use these in:
- Instagram Reels
- CapCut or other video editors
- Canva video creator

### AI Video (Future)

Placeholder for AI video generation:
- Integration with Runway ML
- Integration with Pika Labs
- Auto-generated video clips

---

# SETTINGS & CONFIGURATION

## API Configuration

### Required APIs

| API | Purpose | Status |
|-----|---------|--------|
| OpenAI | Caption + image generation | Required |
| ImgBB | Image hosting | Required |
| Instagram | Direct posting | Optional |

### Setting Up APIs

1. **OpenAI API Key**
   - Get from: platform.openai.com
   - Add to: Render environment variables
   - Variable: `OPENAI_API_KEY`

2. **ImgBB API Key**
   - Get from: api.imgbb.com
   - Add to: Render environment variables
   - Variable: `IMGBB_API_KEY`

3. **Instagram API** (Optional)
   - Get from: Meta Business Suite
   - Requires: Facebook Page + Instagram Business Account
   - Variables: `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_ACCOUNT_ID`

### Debug Endpoint

Visit `/api/debug-config` to see:
- Which APIs are configured
- Key prefix (for verification)
- Initialization status

---

# INSTAGRAM INTEGRATION

## Direct Posting (When Configured)

### Requirements

1. Facebook Business Page
2. Instagram Business or Creator Account
3. Page and Instagram linked
4. Access token with permissions:
   - `instagram_basic`
   - `instagram_content_publish`
   - `pages_show_list`
   - `pages_read_engagement`

### How It Works

1. **Generate content**
2. **Review and approve**
3. **Click "Post to Instagram"**
4. **Content publishes directly**

### Without Instagram API

Content can still be:
- Generated and previewed
- Copied to clipboard
- Images downloaded
- Manually posted to Instagram

---

# TECHNICAL ARCHITECTURE

## How It's Built

### Technology Stack

| Component | Technology |
|-----------|------------|
| Backend | Python Flask |
| Frontend | HTML, CSS, JavaScript |
| AI Text | OpenAI GPT-4 |
| AI Images | OpenAI DALL-E 3 |
| Database | SQLite |
| Hosting | Render.com |
| Image Storage | ImgBB |

### Security Features

- **No survivor data stored** - Only general content
- **API keys in environment** - Never in code
- **Human approval required** - Nothing auto-posts
- **HTTPS encryption** - Secure connections
- **No cookies/tracking** - Privacy focused

### Performance

- Content generation: 15-30 seconds
- Translation: 3-5 seconds
- Image hosting: 2-3 seconds
- Page loads: Under 2 seconds

---

# COST & VALUE

## Investment Required

### Monthly Costs

| Item | Cost | Notes |
|------|------|-------|
| OpenAI API | $30-50 | Based on usage |
| ImgBB | Free | Free tier sufficient |
| Render Hosting | Free | Free tier available |
| **Total** | **~$30-50/month** | |

### Cost Comparison

| Option | Monthly Cost |
|--------|--------------|
| Social media agency | $1,000-3,000 |
| Part-time social media staff | $1,500+ |
| Stock photo subscription | $30-50 |
| Design tools (Canva Pro) | $15 |
| **This tool** | **$30-50** |

### Time Savings

| Task | Traditional | With App |
|------|-------------|----------|
| Write caption | 20-30 min | 30 sec |
| Find/create image | 30-60 min | 30 sec |
| Spanish translation | 15-20 min | 5 sec |
| Hashtag research | 10-15 min | Auto |
| **Per post total** | **75-125 min** | **2-3 min** |

### Annual Value

- **Time saved**: 200+ hours/year
- **Cost saved**: $10,000+/year vs. agency
- **Consistency**: Daily posting possible
- **Reach**: More survivors find help

---

# QUICK REFERENCE

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Generate content | Enter (in theme field) |
| Copy caption | Click copy icon |
| Toggle language | Click EN/ES |

## Common Actions

| I want to... | Do this... |
|--------------|------------|
| Create a post | Click "Create" → Enter theme → Click "Generate" |
| Translate to Spanish | Click "ES" toggle |
| Get new image | Click "Regenerate Image" |
| Get new caption | Click "Regenerate Caption" |
| Copy everything | Click "Copy to Clipboard" |
| Save for later | Click "Save Draft" |
| Schedule post | Click "Schedule" → Pick date/time |

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Configuration Required" | Check API keys in Render settings |
| Slow generation | Normal - AI takes 15-30 seconds |
| Image won't load | Check ImgBB API key |
| Translation failed | Check OpenAI API key and credits |

---

# SUPPORT

## Getting Help

- **Technical issues**: Check `/api/debug-config` endpoint
- **Feature questions**: Reference this document
- **Bug reports**: Note the error message and steps to reproduce

## Future Updates

Planned enhancements:
- Analytics dashboard
- A/B testing for captions
- Automated posting schedules
- Email newsletter integration
- More language options

---

*Document Version: 1.0*
*Last Updated: February 2025*
*Built for the Domestic Violence Center of Chester County*
