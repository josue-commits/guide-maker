# health.json contract

`scripts/scan_all.py` writes `<out-dir>/health.json` on every run, including runs that fail. Other skills read this file to decide whether the topic research is trustworthy before they build anything on it. The shape is fixed. Keys are never added, renamed or dropped without a major version bump.

## Shape

```json
{
  "config_present": {"youtube": false, "reddit": false, "x": false},
  "youtube": {"channels_configured": 0, "channels_with_videos": 0, "videos": 0, "errors": []},
  "reddit": {"subs": 0, "posts": 0},
  "x": {"accounts": 0, "posts": 0, "cost_usd": 0.0},
  "correlation": {"topics_2plus": 0, "topics_all": 0},
  "web_search_used": false
}
```

| Key | Type | Meaning |
|---|---|---|
| `config_present.<source>` | bool | The real config file for that source exists in the config directory (`youtube-channels.json`, `subreddits.json`, `x-accounts.json`). Checked for all three sources, whether or not they were requested. |
| `youtube.channels_configured` | int | Channel entries in the config. |
| `youtube.channels_with_videos` | int | Distinct channels that returned at least one video inside the window. A dead or renamed channel shows up as this number being lower than `channels_configured`. |
| `youtube.videos` | int | Videos kept after the date filter. |
| `youtube.errors` | list of str | One line per channel that warned, errored or timed out, copied from the scanner's stderr, plus a line if the scanner itself exited non-zero. A 404 channel lands here with the yt-dlp message. |
| `reddit.subs` | int | Subreddit entries in the config. |
| `reddit.posts` | int | Posts kept after the upvote and date filters. |
| `x.accounts` | int | Account entries in the config. |
| `x.posts` | int | Posts kept after dedupe. |
| `x.cost_usd` | float | What the Apify run reported, `0.0` when it did not run. |
| `correlation.topics_all` | int | Topics `correlate.py` produced at `--min-sources` (default 1). |
| `correlation.topics_2plus` | int | Of those, topics seen on two or more sources. This is the number that matters: it is the count of topics with cross-source validation. |
| `web_search_used` | bool | Always `false`. This tool never substitutes web search for a missing or empty source. A reader that finds `true` here is reading a file this tool did not write. |

Sources that were not requested keep their zero values. `config_present` is the only block that reports on sources that did not run.

## Exit code

`scan_all.py` exits `1` when any of these is true, and still writes `health.json` first:

- no source was requested (`--sources none`)
- a requested source has no config file
- a requested source returned zero results
- `correlate.py` failed

It exits `0` only when every requested source had a config and returned at least one result.

## Companion file: run.json

`health.json` carries exactly the keys above. Everything else about the run goes to `<out-dir>/run.json`:

```json
{
  "scan_date": "2026-09-02",
  "sources_requested": ["youtube", "reddit", "x"],
  "dry_run": false,
  "out_dir": "/tmp/tf-scan",
  "failures": ["x: zero posts"]
}
```

`failures` is the human-readable list behind the exit code.

## How a caller should read it

1. Exit code `1` means stop and show the user `run.json.failures`. Do not fall back to web search or invent topics.
2. `youtube.errors` non-empty with exit `0` means the scan ran but some channels are dead. Show them so the user can prune the config.
3. `correlation.topics_2plus == 0` with exit `0` means the sources are healthy but nothing crossed platforms this week. Say so. Single-source topics are in `topics.json` and may still be worth covering, with a lower trending score.
4. `x.cost_usd` is what the run cost. Print it so nobody is surprised by the Apify bill.

## Other files in the out dir

| File | What |
|---|---|
| `youtube.json`, `reddit.json`, `x.json` | Raw scanner output, only for the sources that ran. |
| `topics.json` | `correlate.py --json` output: `mode`, `pool`, `topics_all`, `topics_2plus`, and `topics[]` with the top resources per source. |
| `topics.txt` | The same report in the readable text form. |
| `logs/<source>.log` | Scanner stderr, for debugging a dead channel or an Apify error. |
