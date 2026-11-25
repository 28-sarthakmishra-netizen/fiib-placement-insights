# FIIB Placement Insights

A web app for the Career Management Centre. For every company coming to campus it gives:

- **A tier from the CTC:** below ₹10 L is Tier 3, ₹10 L to ₹15 L is Tier 2, ₹15 L and above is Tier 1. The CMC can move an exceptional brand or role up one tier, with a reason.
- **A reality check from the web:** employee reviews (AmbitionBox, Glassdoor), Reddit, salary and interview reports and news. Every point links to its source.
- **"How many people say this?":** the code counts separate sources for each point. It is *widely reported* (3+ sources on 2+ platforms), *repeated* (2) or a *single mention* (1).
- **A score and a verdict:** package 40%, brand 20%, role 20% and work environment 20%. The verdict is Recommend, Go with caution or Avoid.
- **Student reviews with a fake-review guard:** one review per FIIB email per company, automatic flags, and a check of each review against outside sources.

Everything runs on free plans. No card is needed.

| Part | Service | Free limit |
|---|---|---|
| App and hosting | Streamlit Community Cloud | Unlimited public apps; the app sleeps after 12 hours with no visitors |
| AI reading | Google Gemini API | Free tier, no card |
| Web search | Tavily | 1,000 searches a month, about 200 assessments |
| Database | Google Sheet with Apps Script | Free |

---

## 1. Try it on your computer (sample data, 5 minutes)

### Windows

1. Right-click the zip and choose **Extract All**.
2. Install Python from **python.org/downloads**. On the first install screen, tick **Add python.exe to PATH**.
3. Open the extracted `fiib-placement-insights` folder. Click the address bar at the top, type `cmd` and press Enter. A black window opens.
4. Paste these lines one at a time, pressing Enter after each:

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

If Windows says `python` is not found, use `py` instead of `python` in the first line.

### Mac

Open **Terminal** and run:

```bash
cd ~/Downloads/fiib-placement-insights
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Your browser opens the app with four made-up sample companies. When you're done, press `Ctrl + C` in Terminal.

> If `python3` is missing, macOS offers to install the developer tools. Accept, then run the commands again.

---

## 2. Get the two free keys (10 minutes)

1. **Gemini:** go to **aistudio.google.com**, sign in with a Google account, click **Get API key**, then **Create API key**. Copy it.
2. **Tavily:** go to **app.tavily.com**, sign up, and copy the key that starts with `tvly-`.

---

## 3. Set up the Google Sheet (10 minutes)

1. Create a new Google Sheet named **FIIB Placement Insights data**. Use the CMC's Google account so the data belongs to the college.
2. Click **Extensions > Apps Script**. Delete the sample code and paste everything from `apps_script/Code.gs`.
3. On the line `const TOKEN = '...'`, replace the text with a long random password. Click **Save**.
4. Click **Deploy > New deployment**. Click the gear icon, choose **Web app**, then set:
   - Execute as: **Me**
   - Who has access: **Anyone**
5. Click **Deploy**, then **Authorize access**. Google warns that the app is unverified, because it is your own script: click **Advanced**, then **Go to … (unsafe)**, then **Allow**.
6. Copy the **Web app URL**. It ends in `/exec`.

The app creates the **Assessments** and **Reviews** tabs by itself. The CMC can open the Sheet at any time to see or export the data.

> If you later change `Code.gs`, use **Deploy > Manage deployments > Edit > New version**. That way the URL stays the same.

---

## 4. Put it online (15 minutes)

1. **GitHub:** create a free account if you don't have one. Click **New repository**, name it `fiib-placement-insights` and create it. Then choose **uploading an existing file** and drag in everything from this folder.
   - Make sure the `.streamlit` folder is uploaded too, because it holds the colours and fonts. On Windows it shows normally. On a Mac it is hidden: in Finder, press `Cmd + Shift + .` to show it.
   - Do **not** upload a `secrets.toml` file with real keys. Only `secrets.toml.example` goes to GitHub.
2. **Streamlit:** go to **share.streamlit.io** and sign in with GitHub. Click **Create app > Deploy a public app from GitHub**. Choose your repository, branch `main` and file `app.py`.
3. Click **Advanced settings > Secrets**. Paste the contents of `.streamlit/secrets.toml.example` and fill in your values: the two keys, a CMC passcode, the Sheet URL, the token and any random text for `REVIEW_SALT`.
4. Click **Deploy**. In about two minutes you get a link like `https://fiib-placement-insights.streamlit.app` to share.

Anyone with the link can browse companies and post reviews. Only people with the CMC passcode can run assessments or use the CMC panel.

---

## 5. Test it with 10 companies

1. Pick 10 companies that came to campus before and that the CMC already has a clear opinion on, both good and bad.
2. Assess each one under **New assessment**.
3. Compare each verdict with what the CMC knows. Where the app is too generous or too harsh, change the weights or cut-offs in `core/config.py`.
4. Change a file in GitHub by opening it and clicking the pencil icon. The app updates by itself within a minute.

---

## What can be changed easily

Everything is in **`core/config.py`**:

- the tier cut-offs (₹10 L and ₹15 L)
- the weights (40 / 20 / 20 / 20)
- the verdict cut-offs (7 and 5)
- the bond length that counts as a red flag
- how many sources count as "widely reported"
- the searches that run for each company, and which sites they look at

## Good to know

- **Saving free searches:** if a company was searched in the last 14 days, its saved results are reused. Tick "Search the web again" to force a fresh search.
- **Student privacy:** reviewer emails are stored scrambled and are never shown or sent to the AI. Google may use free-tier Gemini inputs to improve its products, so never type student personal details into the app.
- **When the free limits run out:** Tavily resets every month. If Gemini's free limit is hit, the app tries the next free model by itself.
- **If it goes well and the college wants to spend:** turn on Gemini's paid tier to use Google Search inside the AI, buy more Tavily credits, and move from the Sheet to a proper database.

## Files

```
app.py                  the web app (pages and layout)
core/config.py          all rules and numbers
core/rules.py           tiers, scores, verdicts, source counting
core/reviews.py         fake-review checks
core/search.py          Tavily web search
core/ai.py              Gemini reading and its instructions
core/pipeline.py        one full assessment, start to finish
core/storage.py         Google Sheet or local file
core/demo.py            sample companies (all made up)
ui/components.py        colours, fonts and visual pieces
apps_script/Code.gs     Google Sheet connector
tests/test_core.py      automatic checks: run `python -m pytest -q`
```
