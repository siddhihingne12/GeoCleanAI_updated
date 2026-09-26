# Team labelling guide: GeoCleanAI Pune batch

Four of us label **960 Pune street views** (160 panoramas) and review **232 TACO training photos**, all on one computer and one web page: **http://127.0.0.1:8765**. These labels are the main fix for why the first model found nothing in Pune: it had only seen close-up photos of litter, never Pune streets.

## Who labels what

Photo numbers are shown at the top of the page ("Photo 12 of 960"). Each person's range covers whole panoramas (6 photos each), so nobody labels half of a scene.

| Person | Pune photos | TACO sheet rows |
|---|---|---|
| A | 1–240 | 1–58 |
| B | 241–480 | 59–116 |
| C | 481–720 | 117–174 |
| D | 721–960 | 175–232 |

## How to work

1. **Label together first (about 10 minutes).** Sit together and do photos 1–6 (the first panorama) as a group. Agree out loud on the rules below and on any borderline case. Then split up.
2. **Go to your start photo.** Use the photo dropdown next to the Previous/Next buttons and pick your first photo number, then move with **Next →**. Don't use **Next unreviewed**: it jumps to the first unlabelled photo in the whole batch, which may be in someone else's range.
3. **Enter your own name** before saving, so every label records who made it.
4. **Everything saves immediately.** Take turns on the computer, or use separate browser windows at the same time. If two windows open the same photo, the second save is refused, so reload and check.
5. **Fill in the TACO sheet**, `data/litter-review/review-queue.csv`. Open it in Excel, one person at a time, and only edit your rows. The pictures are in `data/litter-review/queue/<image_id>.jpg`, and the columns are explained in `docs/DATA_QUALITY.md`.
6. **Cross-check at the end.** Each person opens 10 photos that someone else marked "no visible litter" and confirms them. A wrong "clean" teaches the model to ignore real litter.

## Labelling rules

The whole team must follow the same rules, because the model learns from all four of us at once.

- **Draw one tight box per item you can tell apart**: wrappers, bottles, cups, cans, cigarette litter, paper, bags lying on the ground.
- **Draw one box around a touching clump of tiny pieces** that can't be told apart. Never group separate items across clean ground.
- **Don't box anything that isn't litter**: leaves, stones, shadows, road markings, bins themselves, bags people are carrying, construction material, flags, people.
- **Use the original-detail view** (the default) and **Enlarge photo** to inspect, and label litter you can see there even if it's tiny.
- **Choose "I checked: no visible litter" only after scanning the whole photo.**
- **Use "Skip: unclear image" plus a short note** when you genuinely can't tell (blur, darkness).
- **Label what is actually there.** Don't try to guess what a model would or wouldn't find.

## Starting the page

If the page isn't open, run this from the project folder in PowerShell and keep the window open:

```powershell
.\.venv\Scripts\python.exe -m training.review_server --data data/pune-label-v2
```

When everyone has finished, tell the project owner. The next steps are exporting and splitting the labels, then the Colab training run.
