# Manual detection evaluation set

This is a **functional** checklist, not a statistical accuracy claim.
Do not use the training split as the only photos.

Suggested layout (create locally, do not commit large binaries):

```
eval_photos/
  isolated/     # ~20 single-item shots
  outfits/      # ~20 multi-item photos
  RESULTS.md    # expected / actual / confidence / correct
```

For each image record:

| field | meaning |
|---|---|
| Expected | true wardrobe type(s) |
| Actual | API `subcategory` / `detected` |
| Confidence | API confidence |
| Boxes | whether YOLO/person boxes appeared (`/detect`) |
| Correct | yes / no / partial |

Vary pose, background, distance, colour, and item position.
Isolated shots should still work when YOLO finds no person.
