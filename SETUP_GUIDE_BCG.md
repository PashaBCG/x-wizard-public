# X-Wizard: Setup Guide for BCG

> Questions? Contact Pasha Barbashin — [barbashin.pasha@bcg.com](mailto:barbashin.pasha@bcg.com)

---

## What is X-Wizard?

X-Wizard turns Cursor (an AI-powered editor) into a personal automation assistant. You describe what you want in plain English — it drafts emails, exports documents, and can be taught to automate any repetitive task you do today. No coding required.

---

## Before You Start — Two Things to Sort Now

These take a day to process. **Send them now** while you read the rest of the guide.

---

### Step 0.1 — Request a Cursor AI License

BCG manages Cursor licenses centrally. You cannot use your BCG email until the platform team approves access.

**Click the link below** — it will open a pre-filled email in Outlook. Replace `[YOUR-CASE-CODE-HERE]` and `[YOUR NAME]`, then hit Send.

**[→ Request Cursor AI License](mailto:bcgxpi@bcg.com?subject=BCG%20X%20/%20Cursor%20AI%20License%20Request&body=Hi%20team%2C%0A%0AI%20need%20a%20paid%20Cursor%20AI%20license%20for%20X-Wizard%2C%20a%20BCG%20X%20internal%20automation%20tool%20built%20on%20Cursor.%0A%0AI%20acknowledge%3A%0A-%20Cost%3A%20%24400%2Fyear%20per%20user%0A-%20I%20will%20charge%20this%20to%20case%20code%3A%20%5BYOUR-CASE-CODE-HERE%5D%0A%0AReferred%20by%3A%20Pasha%20Barbashin%20%28barbashin.pasha%40bcg.com%29%0A%0ABest%2C%0A%5BYOUR%20NAME%5D)**

> **While you wait for approval (usually same day):** you can install Cursor and log in with a personal Google account to complete setup. Switch to your BCG email once the license is approved.

---

### Step 0.2 — Install Python 3.13 (Windows only — Mac users skip this)

X-Wizard needs Python to run. On Mac, Python is almost certainly already installed (it comes with common developer tools). The `/start` wizard will check automatically and tell you if anything is missing.

**Windows — you need to install Python. Here's how:**

1. Click the **Start** button → type `Microsoft Store` → press Enter
2. In the Store search bar, type **Python 3.13**
3. Click the result from **Python Software Foundation**
4. Click **Get** (or **Install** if it shows that)
5. Wait for the progress bar to complete — this takes 1–2 minutes
6. To verify: press `Win+R`, type `powershell`, press Enter, then type:
  ```
   python --version
  ```
   You should see `Python 3.xx.x`

> **Mac users:** skip this step. If Python is missing for some reason, `/start` will tell you and show you the one-click fix.

---

---

## Step 1 — Install Cursor

Cursor is the AI-powered editor where X-Wizard runs. Think of it like Word, but with a built-in AI assistant that can actually do things for you.

1. Go to **[cursor.com](https://cursor.com)** and click **Download**
2. Run the installer — click through all defaults
3. Launch Cursor
4. Sign in with your **BCG email** (prerequisite **=** Step 0.1)

---

## Step 2 — Get X-Wizard

1. Open Cursor
2. On the Cursor welcome screen, click **Clone Git Repository**
  *(If you've already opened a folder, go to File → New Window first to get the welcome screen back)*
3. Paste this URL:
  ```
   https://github.com/PashaBCG/x-wizard-public
  ```
4. Choose a save location — your Documents folder is fine
5. Click **Clone**
6. When prompted, click **Open** to open the cloned folder

You should now see the X-Wizard files in the sidebar on the left (or right)

---

## Step 3 — Run Setup

Open the AI chat panel:

- **Mac:** Press `Cmd+L`
- **Windows:** Press `Ctrl+L`

Type exactly:

```
/start
```

The setup wizard will take over from here. It will:

- Ask you a few short questions (name, role, AI experience)
- Automatically detect your operating system
- Install all required packages — you just need to click **Accept** when Cursor asks
- Configure your email signature
- Walk you through what X-Wizard can do

**Total time: about 5 minutes.**

---

---

## What's Next?

Once `/start` is complete, open a new chat (`Cmd+N` on Mac / `Ctrl+N` on Windows) and type `/create-skill` to build your first custom automation.

Or just describe what you want:

- "Draft an email to [name] summarising our last meeting"
- "Save this document as a PDF"
- "I want to automate my monthly reporting"

---

## More Skills

This public repo ships with three skills (email, PDF, skill creator). There are additional out-of-the-box skills available — including PowerPoint creation with full BCG identity, pipeline reporting, and more.

Reach out to [barbashin.pasha@bcg.com](mailto:barbashin.pasha@bcg.com) to get access to the extended skills library.

---

## Troubleshooting

**"Cursor login rejected / access denied" with BCG email**
Your license is not yet approved. Log in with a personal Google account and switch later.

**"Python not found" during setup**
Complete Step 0.2 above, then run `/start` again.

`**/start` not responding**
Make sure the x-wizard-public folder is open in Cursor (File → Open Folder). The skills load from the `.cursor/` folder inside the project.

**Something else went wrong**
Paste the full error into the Cursor chat: "I got this error, what should I do?" — it will diagnose and fix it.

---

*Questions? Contact Pasha Barbashin at [barbashin.pasha@bcg.com](mailto:barbashin.pasha@bcg.com)*