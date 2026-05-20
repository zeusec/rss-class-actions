# rss-class-actions

A small Python daemon that aggregates class-action-law RSS feeds and posts new items to a Discord webhook.

## Setup

```sh
uv sync
cp .env.example .env
# put your Discord webhook URL into .env
```

Edit `feeds.yaml` to add/remove feeds.

## Run

Manual:

```sh
uv run run.py
```

Docker:

```sh
docker compose up -d --build
docker compose logs -f
```

State (`seen.db`) is persisted to `./data/` via the bind mount in `docker-compose.yml` and survives container rebuilds. Without compose, the equivalent is:

```sh
docker build -t rss-class-actions .
docker run -d --name rss-class-actions --restart unless-stopped \
  -e DISCORD_WEBHOOK_URL="$DISCORD_WEBHOOK_URL" \
  -e BACKLOG=0 \
  -e POLL_INTERVAL=15 \
  -v "$PWD/data:/data" \
  rss-class-actions
```

## Behavior

- Polls every `POLL_INTERVAL` minutes, defaulting to 15 minutes. All feeds are fetched in parallel each cycle.
- On first encounter of a feed (whether on initial startup or when a feed is added to `feeds.yaml` later), every entry currently visible in that feed is silently marked as seen. The daemon only posts items that appear AFTER it starts watching.
- `BACKLOG` only fires on the **first cycle after daemon startup**. If > 0, it posts the N newest items across all feeds regardless of seen state — handy for a recap on restart. Subsequent cycles ignore it and do a normal diff. `BACKLOG=0` (default) skips it entirely.
- State lives in `seen.db` (gitignored). Inspect with `sqlite3 seen.db`. Delete it to re-trigger first-encounter behavior for every feed.
- Each post is a Discord embed: feed name → title → link → first ~300 chars of summary → publish time.

## Environment

- `DISCORD_WEBHOOK_URL` (required) — where posts go.
- `BACKLOG` (default `0`) — count of newest items to post on the cycle where feeds are first-encountered, drawn across the whole pool.
- `POLL_INTERVAL` (default `15`) — minutes to wait between feed polling cycles.

## Files

- `run.py` — the daemon
- `feeds.yaml` — feed list (name + url)
- `seen.db` — SQLite state (`seen(feed_url, guid, posted_at)`); inspect with `sqlite3 seen.db`
- `.env` — `DISCORD_WEBHOOK_URL`, `BACKLOG`, `POLL_INTERVAL`
- `Dockerfile`, `docker-compose.yml` — container deployment

## Sources - WIP

- ✅ Implemented — class-action-scoped feed exists, parses, and is in `feeds.yaml`
- ❌ Broken feed — published URL is 404, malformed XML, or unreachable
- ❌ No class-action feed — only a firm-wide feed exists (too noisy) or no public feed at all

| # | Source | Status |
|---|--------|--------|
| 1 | Ellis & Winters LLP » Class Action Basics | ✅ Implemented |
| 2 | Dentons Commercial Litigation Blog » Class Action | ✅ Implemented |
| 3 | Carr Maloney P.C. » Class Action | ✅ Implemented |
| 4 | Workplace Class Action Blog | ✅ Implemented |
| 5 | Bilzin Sumberg » Food Court Law Blog | ✅ Implemented |
| 6 | Employment Class and Collective Action Update | ❌ Broken feed |
| 7 | Global Litigation News » Class Actions | ✅ Implemented |
| 8 | Class Action Insider | ✅ Implemented |
| 9 | ClassAction.org Blog | ✅ Implemented |
| 10 | Consumer Class Defense Blog | ✅ Implemented |
| 11 | Class Action Clinic Blog | ✅ Implemented |
| 12 | Class Defense Blog | ✅ Implemented |
| 13 | Class Action Countermeasures | ❌ Broken feed |
| 14 | ClassAction.com | ✅ Implemented |
| 15 | Osler Blog | ❌ No class-action feed |
| 16 | Podhurst Orseck » Class Action | ❌ Broken feed |
| 17 | Class Action Lawsuits In The News | ✅ Implemented |
| 18 | Lawyerly » Class Actions | ✅ Implemented |
| 19 | The D&O Diary » Securities Litigation | ✅ Implemented |
| 20 | Institute for Legal Reform » Class Action Litigation | ✅ Implemented |
| 21 | Ahead of the Class | ❌ Broken feed |
| 22 | Declassified | ✅ Implemented |
| 23 | Siskinds » Class Actions | ✅ Implemented |
| 24 | Financial Recovery Technologies, LLC | ✅ Implemented |
| 25 | Inside Class Actions | ✅ Implemented |
| 26 | Classified: The Class Action Blog | ❌ Broken feed |
| 27 | Stoll Berne » Class Actions | ✅ Implemented |
| 28 | Class Actions Brief | ✅ Implemented |
| 29 | Class Action Defense Strategy Blog | ❌ Broken feed |
| 30 | Piper Alderman » Class Actions | ✅ Implemented |
| 31 | Hellmuth & Johnson » Class Action Litigation | ✅ Implemented |
| 32 | Justia » Class Action | ✅ Implemented |
| 33 | Zebersky Payne Shaw Lewenz » Class Action Lawsuit | ❌ Broken feed |
| 34 | Drug & Device Law Blog » Class Action | ✅ Implemented |
| 35 | Shamis & Gentile P.A » Class Action Investigations | ❌ Broken feed |
| 36 | Minding Your Business » Class Action | ✅ Implemented |
| 37 | Silver Law Group Blog » Class Action | ✅ Implemented |
| 38 | The Lyon Firm Blog » Class Action | ✅ Implemented |
| 39 | Margarian Law Firm » Class Action | ✅ Implemented |
| 40 | Louisiana Personal Injury Lawyer Blog » Class Action | ❌ Broken feed |
| 41 | Sommers Schwartz Blog » Class Action | ✅ Implemented |
| 42 | Chicago Business Litigation Lawyer Blog » Class Action | ✅ Implemented |
| 43 | Christian Small » Class Action & Complex Litigation | ✅ Implemented |
| 44 | Poulos LoPiccolo PC » Class Action | ✅ Implemented |
| 45 | Diamond and Diamond Lawyers » Class Action | ✅ Implemented |
| 46 | Dann Law » Class Action Lawsuit | ✅ Implemented |
| 47 | Hariri Law Group » Class Action Lawsuit | ✅ Implemented |
| 48 | Hadsell Stormer » Class Action | ❌ No class-action feed |
| 49 | TDR News | ❌ No class-action feed |
| 50 | Top Class Actions | ✅ Implemented |
| 51 | Winston & Strawn LLP » Class Action Insider | ❌ Broken feed |
| 52 | JAMS Blog » Class Action | ❌ No class-action feed |
| 53 | BakerHostetler | ❌ No class-action feed |
| 54 | ClaimDepot | ❌ No class-action feed |
| 55 | OpenClassActions.com Blog | ❌ No class-action feed |
| 56 | Litigation Notes | ❌ No class-action feed |
| 57 | Class Dismissed | ✅ Implemented |
| 58 | First Class Defense | ✅ Implemented |
| 59 | BakerHostetler | ❌ No class-action feed |
| 60 | JD Supra » Class Action | ❌ No class-action feed |
| 61 | Lenczner Slaght News » Class Actions | ❌ No class-action feed |
| 62 | William Roberts Lawyers » Class Actions | ❌ No class-action feed |
| 63 | Hagens Berman Blog » Class Action | ✅ Implemented |
| 64 | Omni Bridgeway » Class Action | ❌ No class-action feed |
| 65 | Shine Lawyers Blog » Class Action | ❌ No class-action feed |
| 66 | Patterson Belknap » Misbranded Blog | ❌ No class-action feed |
| 67 | Gilbert + Tobin Lawyers | ❌ No class-action feed |
| 68 | Ontario Bar Association | ❌ No class-action feed |
| 69 | Maddens Lawyers Blog | ✅ Implemented |
| 70 | Maurice Blackburn Blog » Class Actions | ❌ No class-action feed |
| 71 | Corrs Chambers Westgarth » Class Actions | ❌ No class-action feed |
| 72 | John Foy & Associates » Class Action Lawsuit | ❌ No class-action feed |
| 73 | Kilpatrick Townsend & Stockton LLP Blog » Class Action | ❌ No class-action feed |
