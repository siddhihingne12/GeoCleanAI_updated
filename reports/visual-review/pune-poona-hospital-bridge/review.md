# Poona Hospital / Two-Wheeler Bridge visual review

Reviewed 13 September 2026. **Not approved for annotation: no confirmed roadside dump or overflowing bin in the initial sample.**

43 downloaded perspective images were individually inspected across all 15 recent sequences (three evenly distributed frames per sequence, or the available count if smaller). These are preliminary observations, not training labels.

| Observation | Images |
|---|---:|
| No clear target | 18 |
| Limited visibility | 12 |
| Potential difficult negative | 4 |
| Weak accumulation below label threshold | 1 |
| Unusable camera aim | 4 |
| Unusable image quality | 3 |
| Unusable occlusion | 1 |
| Total | 43 |

Image `1312012446502350` shows a small curbside heap of leaves, paper and wrappers. It does not establish a substantial roadside dump under the current class definition; nearby bins show no clear overflow. Construction rubble, produce stalls, transported cardboard and concrete rocks remain potential negative examples. Ordinary containers and scattered gutter litter were not promoted to positive labels.

Several sequences show traffic, windshield glare, downward camera aim or evening blur. Others provide clearer pavement views. The last two kiosk samples share coordinates and are near duplicates; 43 reviewed images do not mean 43 independent locations. Sequences `cCqFRfvNk79Qd2UG1ueoEO` and `ZjeJ3SI92RMApGN71Cr0gO` also occur in the Dandekar screening, so candidate folders must not be used as independent train/test groups.

This sparse screening does not prove that the full rectangle or all recent images lack waste. No clear target justified denser target-follow-up sampling. Retain the samples and proceed to Hadapsar market edges. Annotation and training remain gated on finding suitable positives for both classes.

Evidence: [gallery](index.html), [per-image notes](review-notes.json), [source manifest and attribution](manifest.json), [coverage decision](../../coverage/20260913-073542/coverage-decision.md).
