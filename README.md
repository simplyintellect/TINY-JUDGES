# Tiny Judges

**Does asking several Gemma 4 "judges" beat asking one?**

Tiny Judges tests this on a small task: finding visual bugs in mobile website screenshots. It compares a single Gemma 4 call against a panel of Gemma 4 judges, and reports where the panel helps and where it does not.

## The problem

One AI answer is not always reliable. A model can miss a bug, invent a bug that is not there, or sound sure when it is wrong.

## The idea

Run the same screenshot through several Gemma 4 roles that work **independently**. Then a final Gemma 4 "verifier" compares their answers and gives one result.

```
                 Screenshot + short description
                               |
            +------------------+------------------+
            |                                     |
     SINGLE MODE                            JURY MODE
     1 Gemma 4 call             3 judges run one after another (they never
            |                   see each other's answers):
            |                     - Expert   (technical causes)
            |                     - Skeptic  (hunts for subtle, easily missed flaws)
            |                     - Beginner (plain-language view)
            |                                     |
            |                          Verifier (Gemma 4) checks the
            |                          screenshot again, compares the
            |                          judges and gives one answer
            |                                     |
            +------------------+------------------+
                               |
                          Evaluation
        (recall, false claims, no-bug accuracy, parse errors,
              crashed runs, latency, number of API calls)
```

## How Gemma 4 is used

Every AI step uses Gemma 4 through the Gemini API (`google-genai` SDK):

- Model: `gemma-4-31b-it` (fallback: `gemma-4-26b-a4b-it`). Both can be changed in `.env` (see [Configuration](#configuration)).
- Single mode: 1 call per screenshot.
- Jury mode: 3 judge calls + 1 verifier call per screenshot.
- No other AI model is used inside the project.

The judges are the same model with different role instructions. They are not different models.

**Failure handling**

- A call is retried once if the error is temporary (rate limit, server error, timeout, empty reply), waiting 1 s, then 2 s. If the first model keeps failing or is not found, the fallback model is tried.
- If one judge fails or returns invalid JSON, the jury continues with the other judges. That judge is left out of the verifier's input but still shown in the saved output.
- If all judges fail, the case is recorded as a failed run.
- If the verifier call itself fails, the result is the combined issues of the successful judges.

## Project files

| File | What it does |
|---|---|
| `llm.py` | Calls Gemma 4 (text + image). Retries once on temporary errors, then falls back to the second model. |
| `utils.py` | Extracts JSON from the model's reply (handles code fences, extra text, trailing commas). |
| `single.py` | Single-call baseline. |
| `jury.py` | 3 judges (run sequentially) + verifier. |
| `make_cases.py` | Builds 10 test web pages with known bugs and takes 390px-wide screenshots. |
| `eval.py` | Runs both modes on all cases and writes `results/results.md`. |
| `app.py` | Optional Streamlit page to compare both modes side by side. |

Folders created when you run the project:

| Folder / file | Contents |
|---|---|
| `cases/` | Case answer files (`case_01.json` ...) and screenshots (`case_01.png` ...) |
| `cases/html/` | The test pages the screenshots are taken from |
| `results/raw/` | The raw output of every run (also used to resume an interrupted evaluation) |
| `results/eval_metrics_summary.json` | Per-run scores, read by the demo page |
| `results/results.md` | The final report |
| `temp_uploads/` | Screenshots uploaded in the demo page |

## Setup

You need Python 3.10+ and a free Gemini API key from [Google AI Studio](https://aistudio.google.com).

```bash
git clone <your-repo-url>
cd <your-repo-folder>
python -m pip install -U google-genai httpx pillow streamlit playwright truststore
python -m playwright install chromium
```

`truststore` is optional. It lets Python use your operating system's certificate store, which fixes most SSL certificate errors on Windows.

Create a `.env` file in the project folder and add it to `.gitignore` so it is never committed:

```env
GEMINI_API_KEY=your_key_here
```

Never commit your real key.

## How to run

Run these from the project folder, in this order.

**1. Check the connection** (should print a short reply from Gemma):
```bash
python llm.py
```

**2. Create the test cases** (10 test pages, 10 screenshots and 10 answer files in `cases/`):
```bash
python make_cases.py
```

**3. Try one screenshot:**
```bash
python single.py cases/case_05.png --description "Mobile view of a search screen"
python jury.py   cases/case_05.png --description "Mobile view of a search screen"
```

**4. Run the full evaluation:**
```bash
python eval.py
```
By default each case runs once per mode (`REPEATS = 1` in `eval.py`). That is 10 single calls + 40 jury calls = **50 API calls**, plus any retries. Setting `REPEATS = 3` makes it 150 calls (30 single + 120 jury), which can take a while on the free tier.

Every run is saved to `results/raw/` as it finishes. If the evaluation stops, run the same command again and it continues where it left off. To ignore saved results and run everything again (for example after changing a prompt or the test cases), use:
```bash
python eval.py --fresh
```

**5. Optional demo page:**
```bash
python -m streamlit run app.py
```
Pick a test case or upload your own screenshot, then run the single model, the jury, or both side by side. The bottom of the page shows the benchmark summary once `eval.py` has been run.

## Configuration

Set these in `.env` or as environment variables.

| Setting | Default | Meaning |
|---|---|---|
| `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) | none, required | Your API key |
| `GEMMA_PRIMARY_MODEL` | `gemma-4-31b-it` | Model used first |
| `GEMMA_FALLBACK_MODEL` | `gemma-4-26b-a4b-it` | Model used if the first is missing or keeps failing |
| `GEMINI_VERIFY_SSL` | `true` | Set to `false` to turn off SSL certificate checking. **Insecure**: use only on a network you trust, and only if you still get certificate errors after installing `truststore`. |

Settings at the top of `eval.py`:

| Setting | Default | Meaning |
|---|---|---|
| `REPEATS` | `1` | Runs per case per mode |
| `THROTTLE_SLEEP` | `1.0` | Seconds to wait between runs. Raise it if you hit rate limits. |

## How the test works

- **10 test cases:** 4 clear bugs, 3 subtle bugs, 2 pages with no real bug, 1 vague description.
- Each case has a known answer written by us in advance (`cases/case_XX.json`, next to the screenshot).
- Screenshots are taken with a 390 x 844 viewport at 2x scale (the visible screen only, not the full page).
- **Scoring by keywords:** each case lists groups of keywords. A group counts as found if any of its words appears (as plain text, ignoring capital letters) anywhere in the model's answer, including the raw reply.
- **False claims:** each case also lists wrong claims. A run has a false claim if any of those phrases appears in its answer.
- Both modes are scored with the same code.
- **Winner per case:** on bug cases, the mode with more than 5 percentage points higher recall wins. If recall is within 5 points, the mode with fewer false-claim runs wins, otherwise it is a tie. On no-bug cases, the mode with more correct runs wins.

| Metric | Meaning |
|---|---|
| Recall | Share of expected bug groups the answer found (bug cases only; no-bug cases are left out) |
| False-claim rate | Share of all runs that made a known wrong claim |
| No-bug accuracy | On pages with no bug, how often the run reported zero issues and made no known wrong claim |
| Parse-failure rate | How often the reply was not valid JSON |
| Crashed runs | Runs that failed completely. They count as 0 recall and are left out of the latency and confidence averages. |
| Avg confidence | Average confidence the model reported (self-reported, not proof of being right) |
| Total API calls | Calls used by each mode across the whole run |
| Avg latency per case | Seconds per case |

## Results

<Paste the real tables from `results/results.md` here after running `eval.py`. Do not write numbers by hand.>

| Metric | Single | Jury |
|---|---|---|
| Recall | <x> | <x> |
| False-claim rate | <x> | <x> |
| No-bug accuracy | <x> | <x> |
| Parse-failure rate | <x> | <x> |
| Total API calls | <x> | <x> |
| Avg latency per case (s) | <x> | <x> |

**Where the jury helped:** <fill in from results>

**Where the jury did not help:** <fill in from results>

## Limitations

- **The case description is passed to the models.** `eval.py` sends each case's description (which says what the bug is) along with the screenshot. This makes both modes look better than they would on a real, unknown screenshot, and it can hide differences between them. For a fairer test, send a neutral description instead.
- Small test set (10 cases), so the results show a trend, not proof.
- With the default `REPEATS = 1`, each result is a single sample and model answers vary. Use `REPEATS = 3` or more for steadier numbers.
- All judges are the same Gemma 4 model, so they can share the same blind spots.
- Keyword scoring is approximate:
  - A correct answer worded differently may be missed.
  - Some keywords are generic (for example `icon`, `spacing`, `top`) and can match an answer that missed the bug.
  - A negated sentence such as "no overlapping elements" still matches the phrase "overlap" and can be counted as a false claim.
- Test pages are synthetic (made by us), not real user bug reports.
- Confidence values are written by the model and are not a measure of correctness.
- Jury mode costs 4 calls per screenshot instead of 1, and because the judges run one after another it takes roughly 4 times as long.

## Troubleshooting

| Problem | Fix |
|---|---|
| `ImportError: cannot import name 'genai' from 'google'` | Install the right package in the same Python you run the code with: `python -m pip install -U google-genai`. If it persists, uninstall the old packages first: `python -m pip uninstall google-generativeai google-ai-generativelanguage -y`. |
| `GEMINI_API_KEY is not set` | Create the `.env` file described in Setup. |
| `ModelNotFoundError` | Your key cannot use these model names. List what it can use with `python -c "from llm import get_client; print([m.name for m in get_client().models.list()])"`, then set `GEMMA_PRIMARY_MODEL` and `GEMMA_FALLBACK_MODEL`. |
| SSL certificate errors (common on Windows) | `python -m pip install truststore`. As a last resort on a trusted network, set `GEMINI_VERIFY_SSL=false`. |
| Many rate-limit (429) errors | Raise `THROTTLE_SLEEP` in `eval.py` (for example to `3.0`) and run again. Finished runs are kept. |
| Playwright errors in `make_cases.py` | `python -m pip install playwright` and `python -m playwright install chromium`. |
| Old results after changing prompts or cases | Run `python eval.py --fresh`. |

## Security

The key is read from `.env` (or the environment) and is never printed, hard-coded, or committed. API calls are made from your machine, but your prompts and screenshots are sent to Google's Gemini API. SSL certificate checking is on by default.

## Tools used

- Gemma 4 via the Gemini API and the `google-genai` SDK
- Playwright (screenshots), Streamlit (demo page)
- AI coding assistants (Antigravity, Claude, ChatGPT) helped write code and docs

## License

MIT. See `LICENSE`.