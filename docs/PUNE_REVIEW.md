# Review Pune litter images

Open **http://127.0.0.1:8765** while the local review server is running.

1. Enter your name or initials.
2. Look at the whole image. **Original-source detail** projects a 1280px or 1920px view directly from the local original panorama. Use **Enlarge photo** to inspect it at its actual pixel size. **Detector input (640 × 640)** shows the smaller view the model receives. Boxes use the same positions in both views.
3. Drag a tight box around each identifiable discarded item. Include all visible items you can distinguish, then choose **Save litter boxes**.
4. If you checked the entire image and found no visible litter, choose **I checked: no visible litter** and confirm.
5. If you cannot identify litter because of blur, darkness or ambiguous material, add a note and choose **Skip: unclear image**. A clearly identifiable tight cluster of tiny touching litter can use one box when the pieces cannot be separated.
6. Choose **Next unreviewed**. You can return to saved images to correct boxes. Unsaved edits trigger a warning when you leave.

Use separate boxes for distinguishable wrappers, bottles, cups, cans, cigarette litter and other identifiable discarded objects. Use one tight box around a touching cluster of tiny litter when individual pieces cannot be separated. Do not group distinguishable items across gaps of clean pavement. Do not label leaves, shadows, road markings, bins themselves or bags carried by people. Keep ambiguous examples for further review instead of guessing. Define these inclusion rules before inspecting model predictions; do not remove difficult cases simply because the model misses them. Record the number and reasons for excluded views alongside any reported score.

The current pool contains **72 perspective views from 12 original panoramas across nine Mapillary capture sequences**. Views from one panorama or sequence are related; this is not a set of 72 independent street scenes. Dates, contributors and source links appear beside each image. Original panoramas were downloaded before the six views were re-exported. Some source photos are still blurry, even at their available original resolution.

The full panoramas are 3840 × 1920 or 5760 × 2880 pixels spread across 360 degrees. A single direction therefore has fewer pixels than the whole panorama. Detail views preserve more source information than the initial 640px review crops, but do not reconstruct motion blur or missing small objects. Detail images are generated on first opening and cached locally under `inspection/`. Existing 640px images and label coordinates are retained for evaluating the current detector. If small objects are visible in the detail view but lost at 640px, that is a real model-input limitation to measure rather than a reason to omit the objects from labels.

Reviews are saved locally under `data/pune-review/reviews/`, with reviewer, date, image checksum and revision. The image files have no empty labels by default. An explicit human clean review is required to create an empty label during export. Browser checks used a separate temporary fixture and did not label these real images.

## Start or restart the page

From the project root in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m training.review_server
```

The service binds to this computer at `127.0.0.1:8765`. Keep the terminal running. It is separate from the map application.

## Export reviewed candidates

After reviewing, export to a new folder:

```powershell
.\.venv\Scripts\python.exe -m training.review_server --export data/pune-reviewed-v1
```

The export includes images, one-class YOLO box labels and review/source metadata. It includes only explicitly reviewed litter and clean views. Skipped and unreviewed views are omitted. Views without original imagery or capture sequence metadata cannot be exported. Existing export folders are protected from overwrite.

This is a reviewed candidate pool, not automatically a training or test set. Assign entire related capture groups to one split and reserve the Pune test set before training or threshold tuning. Collect more full-resolution litter-positive street scenes if this pool has too few confirmed objects. Keep roughly 50 reviewed test views from several independent streets and capture groups, including visible litter, clean scenes and difficult examples. Report precision and recall on that locked set; both must reach 85%. Training takes place in the existing Google Colab notebook after data review.
